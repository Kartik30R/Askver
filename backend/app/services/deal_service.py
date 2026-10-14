from contextlib import aclosing
import logging
from uuid import UUID, uuid4
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.deal_repository import DealRepository
from app.repositories.deal_intelligence_repository import DealIntelligenceRepository
from app.repositories.execution_history_repository import ExecutionHistoryRepository
from app.schemas.deal_intelligence import HumanApprovalRequest
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

    STAGES = [
    ("company_research",),
    ("industry_analysis", "financial_intelligence", "stakeholder_intel"),
    ("pain_point_detector",),
    ("enterprise_rag_matcher",),
    ("service_mapper",),
    ("mandatory_review",),
    ("cxo_brief_generator",),
    ("report_indexer",),
    ]
    DONE = {"COMPLETED", "FAILED"}


    async def _persist(self, deal_id, thread_id, values: dict, final: Optional[str] = None):
        """Mirror graph state to deal_intelligence. Derives RUNNING from the topology, not from aget_state()."""
        data = to_primitive(dict(values or {}))
        statuses = dict(data.get("node_statuses") or {})
        if final is None:
            for stage in self.STAGES:
                if all(statuses.get(n) in self.DONE for n in stage):
                    continue
                for n in stage:
                    if statuses.get(n) not in self.DONE:
                        statuses[n] = "AWAITING_REVIEW" if n == "mandatory_review" else "RUNNING"
                data["current_step"] = ("MANDATORY_REVIEW_CHECKPOINT" if stage == ("mandatory_review",)
                                        else "RUNNING: " + ", ".join(stage))
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
    
    
    async def run_deal_intelligence_workflow(self, deal_id: UUID, thread_id: Optional[str] = None):
        deal = await self.deal_repo.get_deal_by_id(deal_id)
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")

        latest = await self.intel_repo.get_latest_intelligence_snapshot(deal_id)
        rerun_from = None
        if latest and latest.snapshot_data:
            rerun_from = latest.snapshot_data.get("rerun_from_node")

        if rerun_from:
            return await self.run_pipeline_from_node(deal_id, rerun_from, thread_id=latest.thread_id if latest else None)

        tid = latest.thread_id if latest else f"deal_{deal_id}"
        graph = get_deal_intelligence_graph()
        config = {"configurable": {"thread_id": tid}, "recursion_limit": 50}

        existing = await graph.aget_state(config)
        if existing.next:
            graph_input = None
        else:
            if existing.values:
                tid = f"deal_{deal_id}_{uuid4().hex[:8]}"
                config = {"configurable": {"thread_id": tid}, "recursion_limit": 50}
            graph_input = self._initial_state(deal)
            await self._persist(deal_id, tid, graph_input)

        await self.deal_repo.update_deal_status(deal_id, "RUNNING")
        values: dict = {}
        try:
            async with aclosing(graph.astream(graph_input, config=config, stream_mode="values")) as stream:
                async for values in stream:
                    await self._persist(deal_id, tid, values)
                    await self.db.refresh(deal)
                    if deal.status == "PAUSE_REQUESTED":
                        break

            final = await graph.aget_state(config)
            vals = to_primitive(dict(final.values or values))
            if "mandatory_review" in final.next:
                status = "AWAITING_REVIEW"
            elif final.next:
                status = "PAUSED"
            elif vals.get("mandatory_review_checkpoint") == "rejected":
                status = "REJECTED"
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

    def _hydrate_run_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return _hydrate(state)

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
    def _initial_state(self, deal) -> dict:
        return {
            "deal_id": str(deal.id), "target_company": deal.target_company,
            "target_industry": deal.target_industry, "meeting_objective": deal.meeting_objective,
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
            "active_state": snapshot.snapshot_data if snapshot else {},
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