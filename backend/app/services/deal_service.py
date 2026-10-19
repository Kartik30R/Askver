from contextlib import aclosing
import logging
from uuid import UUID, uuid4
from typing import Optional, Dict, Any, Iterable, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.deal_repository import DealRepository
from app.repositories.deal_intelligence_repository import DealIntelligenceRepository
from app.repositories.execution_history_repository import ExecutionHistoryRepository
from app.schemas.deal_intelligence import HumanApprovalRequest
from app.schemas.playbook import MeetingPlaybook
from agents.graph import get_deal_intelligence_graph
from agents.nodes.company_research import company_research_node
from agents.nodes.cxo_brief_synthesizer import cxo_brief_generator_node
from agents.nodes.enterprise_rag_matcher import enterprise_rag_matcher_node
from agents.nodes.financial_intelligence import financial_intelligence_node
from agents.nodes.industry_analysis import industry_analysis_node
from agents.nodes.pain_point_detector import pain_point_detector_node
from agents.nodes.report_indexer import report_indexer_node
from agents.nodes.service_mapper import service_mapper_node
from agents.nodes.stakeholder_intelligence import stakeholder_intelligence_node
from app.services.hitl_manager import HITLManager
from app.services.execution_history_service import ExecutionHistoryService
from app.schemas.deals import DealCreate
from app.utils.serializers import to_primitive
from agents.graph import _hydrate

logger = logging.getLogger(__name__)


class DealService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.deal_repo = DealRepository(db)
        self.intel_repo = DealIntelligenceRepository(db)
        self.hitl_manager = HITLManager(db)
        self.history_service = ExecutionHistoryService(db)
        self.history_repo = ExecutionHistoryRepository(db)

    async def create_new_deal(self, owner_id: UUID, deal_data: DealCreate):
        """Creates a new deal record mapping strictly to the DealCreate schema."""
        return await self.deal_repo.create_deal(
            owner_id=owner_id,
            deal_in=deal_data,
        )

    PROGRESS_PHASES = [
        ("Planning", ["research_planner"]),
        ("Research", [
            "research_business_model", "research_financial", "research_strategy",
            "research_technology", "research_leadership", "research_industry",
            "research_competitors", "research_triggers",
        ]),
        ("Evidence check", ["evidence_gate", "research_refine"]),
        ("Analysis", ["strategic_frameworks", "commercial_frameworks", "insight_synthesis", "verifier"]),
        ("Pain points & solutions", ["pain_point_detector", "enterprise_rag", "service_mapper"]),
        ("Human review", ["mandatory_review"]),
        ("Playbook", ["playbook_questions", "playbook_room", "playbook_assemble", "report_indexing"]),
    ]
    DONE = {"COMPLETED", "FAILED"}

    @staticmethod
    def validate_research_depth(research_depth: Optional[str]) -> str:
        depth = (research_depth or "standard").strip().lower()
        if depth not in {"quick", "standard", "deep"}:
            raise ValueError("research_depth must be one of: quick, standard, deep")
        return depth

    @staticmethod
    def validate_meeting_duration(meeting_duration_minutes: Optional[int]) -> int:
        duration = 45 if meeting_duration_minutes is None else int(meeting_duration_minutes)
        if not 15 <= duration <= 180:
            raise ValueError("meeting_duration_minutes must be between 15 and 180")
        return duration

    @classmethod
    def compute_progress(cls, state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        statuses = (state or {}).get("node_statuses") or {}
        nodes_in_scope: List[str] = []
        for _, phase_nodes in cls.PROGRESS_PHASES:
            nodes_in_scope.extend(node for node in phase_nodes if node in statuses or node in (state or {}))

        if not nodes_in_scope:
            return {"percent": 0, "phase": "Planning", "completed": 0, "total": 0}

        completed = sum(1 for node in nodes_in_scope if statuses.get(node) == "COMPLETED")
        total = len(set(nodes_in_scope))
        percent = min(100, max(0, int(round((completed / total) * 100)))) if total else 0
        phase = "Planning"
        for label, phase_nodes in cls.PROGRESS_PHASES:
            if any(node in statuses for node in phase_nodes):
                phase = label
        return {"percent": percent, "phase": phase, "completed": completed, "total": total}

    @staticmethod
    def _coerce_reference_ids(ids: Optional[Iterable[str]] | str) -> List[str]:
        if ids is None:
            return []
        if isinstance(ids, str):
            values = ids.split(",")
        else:
            values = list(ids)
        return [str(item).strip() for item in values if str(item).strip()]

    @staticmethod
    def build_citations_map(state: Optional[Dict[str, Any]], ids: Optional[Iterable[str]] | str = None) -> Dict[str, Dict[str, Any]]:
        s = state or {}
        facts = s.get("facts") or {}
        sources = s.get("sources") or {}
        requested_ids = DealService._coerce_reference_ids(ids)
        if not requested_ids:
            requested_ids = []
            for fact in facts.values():
                requested_ids.extend(fact.get("source_ids") or [])
            requested_ids = list(dict.fromkeys(requested_ids))
        referenced = set(requested_ids)
        citations: Dict[str, Dict[str, Any]] = {}
        for fact_id in sorted(referenced):
            fact = facts.get(fact_id)
            if not fact:
                continue
            source_entries = []
            for source_id in fact.get("source_ids") or []:
                source = sources.get(source_id) or {}
                if not source:
                    continue
                source_entries.append({
                    "id": source_id,
                    "title": source.get("title"),
                    "url": source.get("url"),
                    "tier": source.get("tier"),
                    "published_date": source.get("published_date"),
                })
            citations[fact_id] = {
                "claim": fact.get("claim"),
                "period": fact.get("period"),
                "confidence": fact.get("confidence"),
                "sources": source_entries,
            }
        return citations

    @staticmethod
    def map_state_to_api_response(state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        s = dict(state or {})
        payload: Dict[str, Any] = {}
        for key in [
            "meeting_playbook", "verification_report", "insight_synthesis", "strategic_frameworks",
            "commercial_frameworks", "research_plan", "evidence_report", "research_gaps",
            "financial_snapshot", "priorities_and_pain_points", "company_research",
            "financial_intelligence", "stakeholder_intelligence", "industry_analysis",
            "matched_internal_assets", "service_mappings", "cxo_executive_brief",
            "markdown_export", "meeting_duration_minutes", "research_depth",
        ]:
            if key in s and s.get(key) not in (None, "", [], {}):
                payload[key] = s[key]
        if s.get("meeting_playbook"):
            payload["citations"] = DealService.build_citations_map(s, [
                item_id
                for item in [
                    (s.get("meeting_playbook") or {}).get("talking_points", []),
                    (s.get("meeting_playbook") or {}).get("discovery_questions", []),
                    (s.get("meeting_playbook") or {}).get("objections", []),
                    (s.get("meeting_playbook") or {}).get("attendees", []),
                    (s.get("meeting_playbook") or {}).get("proof_points", []),
                    (s.get("meeting_playbook") or {}).get("pitch_and_ask", {}).get("fact_ids", []),
                ]
                for item in (item if isinstance(item, list) else [item])
                for item_id in ((item.get("fact_ids", []) if isinstance(item, dict) else []) or [])
            ])
            payload["playbook_warning"] = bool(
                ((s.get("meeting_playbook") or {}).get("overall_confidence") == "LOW")
                or any((item.get("unverified_figures") or []) for item in ((s.get("meeting_playbook") or {}).get("talking_points", []) if isinstance((s.get("meeting_playbook") or {}).get("talking_points", []), list) else []))
            )
            payload["meeting_playbook_warning"] = payload["playbook_warning"]
        if s.get("verification_report"):
            payload["verification_report"] = s["verification_report"]
            payload["verification_warning"] = bool((s["verification_report"].get("overall_confidence") == "LOW") if isinstance(s["verification_report"], dict) else False)
        if s.get("research_planner") is not None and isinstance(s.get("research_planner"), dict):
            payload["research_plan"] = s["research_planner"]
        return payload

    async def _persist(self, deal_id, thread_id, values: dict, final: Optional[str] = None):
        """Mirror graph state to deal_intelligence. Derives RUNNING from the topology, not from aget_state()."""
        data = to_primitive(dict(values or {}))
        statuses = dict(data.get("node_statuses") or {})
        progress = self.compute_progress(data)
        data["progress_percent"] = progress["percent"]
        data["progress_phase"] = progress["phase"]
        if final is None:
            for _, phase_nodes in self.PROGRESS_PHASES:
                if all(statuses.get(n) in self.DONE for n in phase_nodes if n in statuses):
                    continue
                for n in phase_nodes:
                    if n in statuses and statuses.get(n) not in self.DONE:
                        statuses[n] = "AWAITING_REVIEW" if n == "mandatory_review" else "RUNNING"
                data["current_step"] = ("MANDATORY_REVIEW_CHECKPOINT" if any(n == "mandatory_review" for n in phase_nodes)
                                        else "RUNNING: " + ", ".join(phase_nodes))
                break
        elif final == "AWAITING_REVIEW":
            statuses["mandatory_review"] = "AWAITING_REVIEW"
            data["current_step"] = "MANDATORY_REVIEW_CHECKPOINT"
        elif final == "PAUSED":
            data["current_step"] = "PAUSED_AT_BOUNDARY"
        else:
            data["current_step"] = final            # COMPLETED / REJECTED / FAILED
        data["node_statuses"] = statuses
        await self.intel_repo.save_intelligence_snapshot(
            deal_id=deal_id, thread_id=thread_id,
            current_step=data["current_step"], snapshot_data=data)
    
    
    async def run_deal_intelligence_workflow(
        self,
        deal_id: UUID,
        thread_id: Optional[str] = None,
        research_depth: Optional[str] = None,
        meeting_duration_minutes: Optional[int] = None,
    ):
        deal = await self.deal_repo.get_deal_by_id(deal_id)
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")

        latest = await self.intel_repo.get_latest_intelligence_snapshot(deal_id)
        rerun_from = None
        if latest and latest.snapshot_data:
            rerun_from = latest.snapshot_data.get("rerun_from_node")

        if rerun_from:
            return await self.run_pipeline_from_node(deal_id, rerun_from, thread_id=latest.thread_id if latest else None)

        tid = thread_id or (latest.thread_id if latest else f"deal_{deal_id}")
        graph = get_deal_intelligence_graph()
        config = {"configurable": {"thread_id": tid}, "recursion_limit": 50}
        existing = await graph.aget_state(config)

        if existing and existing.next:
            graph_input = None
        else:
            if existing and existing.values and not thread_id:
                tid = f"deal_{deal_id}_{uuid4().hex[:8]}"
                config = {"configurable": {"thread_id": tid}, "recursion_limit": 50}
            graph_input = self._initial_state(
                deal,
                research_depth=research_depth,
                meeting_duration_minutes=meeting_duration_minutes,
            )
            await self._persist(deal_id, tid, graph_input)

        try:
            final_state = await graph.ainvoke(graph_input, config=config)
            vals = to_primitive(dict(final_state or {}))
            if vals.get("mandatory_review_checkpoint") == "rejected":
                status = "REJECTED"
            elif any(v == "AWAITING_REVIEW" for v in (vals.get("node_statuses") or {}).values()):
                status = "AWAITING_REVIEW"
            elif any(v == "FAILED" for v in (vals.get("node_statuses") or {}).values()):
                status = "FAILED"
            else:
                status = "COMPLETED"
            await self._persist(deal_id, tid, vals, final=status)
            await self.deal_repo.update_deal_status(deal_id, status)
            return vals
        except Exception as e:
            logger.exception("Workflow failed for deal %s", deal_id)
            await self.db.rollback()
            try:
                snap = await graph.aget_state(config)
                v = to_primitive(dict(snap.values or {}))
            except Exception:
                v = {}
            v["errors"] = list(v.get("errors") or []) + [str(e)]
            await self._persist(deal_id, tid, v, final="FAILED")
            await self.deal_repo.update_deal_status(deal_id, "FAILED")
            raise

    @staticmethod
    def _hydrate_run_state_static(state: Dict[str, Any]) -> Dict[str, Any]:
        return _hydrate(state)

    def _hydrate_run_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return self._hydrate_run_state_static(state)

    async def run_pipeline_from_node(self, deal_id: UUID, node_name: str, thread_id: Optional[str] = None):
        deal = await self.deal_repo.get_deal_by_id(deal_id)
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")

        latest = await self.intel_repo.get_latest_intelligence_snapshot(deal_id)
        state = dict((latest.snapshot_data or {}) if latest else {})
        state.setdefault("deal_id", str(deal.id))
        state.setdefault("target_company", deal.target_company)
        state.setdefault("target_industry", deal.target_industry)
        state.setdefault("meeting_objective", deal.meeting_objective)
        state["current_step"] = f"RUNNING: {node_name}"
        state["rerun_from_node"] = None

        node_order = [
            "company_research",
            "financial_intelligence",
            "stakeholder_intel",
            "industry_analysis",
            "pain_point_detector",
            "enterprise_rag_matcher",
            "service_mapper",
            "mandatory_review",
            "cxo_brief_generator",
            "report_indexer",
        ]
        if node_name not in node_order:
            raise ValueError(f"Unknown rerun node: {node_name}")

        start_index = node_order.index(node_name)
        prior_statuses = dict((state.get("node_statuses") or {}).items())
        for name in node_order:
            if name in node_order[start_index:]:
                prior_statuses.pop(name, None)
            else:
                prior_statuses[name] = prior_statuses.get(name) or "COMPLETED"
        state["node_statuses"] = prior_statuses

        for name in node_order[start_index:]:
            state.setdefault("node_statuses", {})
            state["node_statuses"].pop(name, None)
            if name in state:
                state.pop(name, None)

            node_fn = {
                "company_research": company_research_node,
                "financial_intelligence": financial_intelligence_node,
                "stakeholder_intel": stakeholder_intelligence_node,
                "industry_analysis": industry_analysis_node,
                "pain_point_detector": pain_point_detector_node,
                "enterprise_rag_matcher": enterprise_rag_matcher_node,
                "service_mapper": service_mapper_node,
                "mandatory_review": None,
                "cxo_brief_generator": cxo_brief_generator_node,
                "report_indexer": report_indexer_node,
            }.get(name)

            if node_fn is None:
                if name == "mandatory_review":
                    state["mandatory_review_checkpoint"] = state.get("mandatory_review_checkpoint", "pending")
                    state["node_statuses"][name] = "AWAITING_REVIEW"
                    state["current_step"] = "MANDATORY_REVIEW_CHECKPOINT"
                    await self._persist(deal_id, thread_id or (latest.thread_id if latest else f"deal_{deal_id}"), state, final="AWAITING_REVIEW")
                    await self.deal_repo.update_deal_status(deal_id, "AWAITING_REVIEW")
                    return state
                continue

            try:
                hydrated_state = self._hydrate_run_state(state)
                update = dict(node_fn(hydrated_state) or {})
                for key, value in update.items():
                    if not key.startswith("_"):
                        state[key] = value
                state["node_statuses"] = {**state.get("node_statuses", {}), **(update.get("node_statuses") or {})}
                state["current_step"] = f"RUNNING: {name}"
                await self._persist(deal_id, thread_id or (latest.thread_id if latest else f"deal_{deal_id}"), state)
                await self.db.refresh(deal)
                if deal.status == "PAUSE_REQUESTED":
                    break
            except Exception as exc:
                logger.exception("Rerun-from-node failed at %s for deal %s", name, deal_id)
                state.setdefault("errors", [])
                state["errors"] = list(state.get("errors") or []) + [f"{name}: {exc}"]
                state["node_statuses"][name] = "FAILED"
                await self._persist(deal_id, thread_id or (latest.thread_id if latest else f"deal_{deal_id}"), state, final="FAILED")
                await self.deal_repo.update_deal_status(deal_id, "FAILED")
                raise

        if state.get("mandatory_review_checkpoint") == "rejected":
            status = "REJECTED"
        elif state.get("node_statuses", {}).get("mandatory_review") == "AWAITING_REVIEW":
            status = "AWAITING_REVIEW"
        elif any(v == "FAILED" for v in (state.get("node_statuses") or {}).values()):
            status = "FAILED"
        else:
            status = "COMPLETED"

        await self._persist(deal_id, thread_id or (latest.thread_id if latest else f"deal_{deal_id}"), state, final=status)
        await self.deal_repo.update_deal_status(deal_id, status)
        return state
    def _initial_state(self, deal, research_depth: Optional[str] = None, meeting_duration_minutes: Optional[int] = None) -> dict:
        depth = self.validate_research_depth(research_depth)
        duration = self.validate_meeting_duration(meeting_duration_minutes)
        return {
            "deal_id": str(deal.id), "target_company": deal.target_company,
            "target_industry": deal.target_industry, "meeting_objective": deal.meeting_objective,
            "research_depth": depth,
            "meeting_duration_minutes": duration,
            "pause_requested": False, "mandatory_review_checkpoint": "pending",
            "human_approved": False, "node_statuses": {}, "current_step": "STARTED",
        }
    
    async def get_deal(self, deal_id: UUID):
        return await self.deal_repo.get_deal_by_id(deal_id)

    async def get_deal_context(self, deal_id: UUID) -> Optional[Dict[str, Any]]:
        deal = await self.deal_repo.get_deal_by_id(deal_id)
        if not deal:
            return None

        snapshot = await self.intel_repo.get_latest_intelligence_snapshot(deal_id)
        active_state = snapshot.snapshot_data if snapshot else {}
        mapped = self.map_state_to_api_response(active_state)
        if not mapped and active_state:
            mapped = dict(active_state)
        return {
            "deal": {
                "id": str(deal.id),
                "title": deal.title,
                "target_company": deal.target_company,
                "target_industry": deal.target_industry,
                "meeting_objective": deal.meeting_objective,
                "status": deal.status,
                "owner_id": str(deal.owner_id),
                "created_at": deal.created_at,
                "updated_at": deal.updated_at,
            },
            "active_state": mapped or {},
        }

    async def get_evidence_by_ids(self, deal_id: UUID, ids: Optional[str]) -> Dict[str, Any]:
        context = await self.get_deal_context(deal_id)
        if not context:
            raise ValueError(f"Deal {deal_id} not found")
        state = context.get("active_state") or {}
        return {
            "ids": self._coerce_reference_ids(ids),
            "citations": self.build_citations_map(state, self._coerce_reference_ids(ids)),
        }

    async def resume_from_checkpoint(self, deal_id: UUID, checkpoint_id: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
        deal = await self.deal_repo.get_deal_by_id(deal_id)
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")

        checkpoint_state = await self.history_service.prepare_resume_state(deal_id, checkpoint_id)
        if not checkpoint_state:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")

        new_thread_id = thread_id or f"thread_{deal_id}_resumed"
        await self.deal_repo.update_deal_status(deal_id, "RUNNING")
        config = {"configurable": {"thread_id": new_thread_id}}
        graph = get_deal_intelligence_graph()

        try:
            final_state = await graph.ainvoke(checkpoint_state, config=config)
            current_step = final_state.get("current_step", "COMPLETED")
            status = "PAUSED" if "PAUSED" in current_step else "COMPLETED"

            await self.deal_repo.update_deal_status(deal_id, status)
            serial_state = to_primitive(final_state)
            await self.intel_repo.save_intelligence_snapshot(
                deal_id=deal_id,
                thread_id=new_thread_id,
                current_step=current_step,
                snapshot_data=serial_state,
            )
            return serial_state
        except Exception as e:
            logger.error(f"Failed to resume from checkpoint {checkpoint_id}: {str(e)}")
            await self.deal_repo.update_deal_status(deal_id, "FAILED")
            raise

    async def get_execution_timeline(self, deal_id: UUID) -> Dict[str, Any]:
        return {"timeline": await self.history_service.get_deal_timeline(deal_id)}

    async def get_thread_history(self, deal_id: UUID, thread_id: str) -> Dict[str, Any]:
        return {"checkpoints": await self.history_service.get_thread_history(thread_id, deal_id)}