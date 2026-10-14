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
from app.services.hitl_manager import HITLManager
from app.services.execution_history_service import ExecutionHistoryService
from app.schemas.deals import DealCreate
from app.utils.serializers import to_primitive

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
        tid = latest.thread_id if latest else f"deal_{deal_id}"
        graph = get_deal_intelligence_graph()
        config = {"configurable": {"thread_id": tid}, "recursion_limit": 50}
    
        existing = await graph.aget_state(config)
        if existing.next:                       # interrupted / failed / paused -> continue from checkpoint
            graph_input = None
        else:
            if existing.values:                 # previous run finished -> fresh thread
                tid = f"deal_{deal_id}_{uuid4().hex[:8]}"
                config = {"configurable": {"thread_id": tid}, "recursion_limit": 50}
            graph_input = self._initial_state(deal)
            await self._persist(deal_id, tid, graph_input)
    
        await self.deal_repo.update_deal_status(deal_id, "RUNNING")
        values: dict = {}
        try:
            async with aclosing(graph.astream(graph_input, config=config, stream_mode="values")) as stream:
                async for values in stream:                       # full state after every step
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
    def _initial_state(self, deal) -> dict:
        return {
            "deal_id": str(deal.id), "target_company": deal.target_company,
            "target_industry": deal.target_industry, "meeting_objective": deal.meeting_objective,
            "pause_requested": False, "mandatory_review_checkpoint": "pending",
            "human_approved": False, "node_statuses": {}, "current_step": "STARTED",
        }
    
    # async def _persist(self, deal_id, thread_id, graph, config):
    #     snap = await graph.aget_state(config)
    #     data = to_primitive(dict(snap.values or {}))
    #     statuses = dict(data.get("node_statuses") or {})
    #     for n in snap.next:                                   # nodes about to run / waiting
    #         statuses[n] = "AWAITING_REVIEW" if n == "mandatory_review" else "RUNNING"
    #     data["node_statuses"] = statuses
    #     if "mandatory_review" in snap.next:
    #         data["current_step"] = "MANDATORY_REVIEW_CHECKPOINT"
    #     elif snap.next:
    #         data["current_step"] = "RUNNING: " + ", ".join(snap.next)
    #     await self.intel_repo.save_intelligence_snapshot(
    #         deal_id=deal_id, thread_id=thread_id,
    #         current_step=data.get("current_step") or "EXECUTING", snapshot_data=data)
    #     return snap
    
    # async def run_deal_intelligence_workflow(self, deal_id: UUID, thread_id: Optional[str] = None):
    #     deal = await self.deal_repo.get_deal_by_id(deal_id)
    #     if not deal:
    #         raise ValueError(f"Deal {deal_id} not found")
    
    #     latest = await self.intel_repo.get_latest_intelligence_snapshot(deal_id)
    #     tid = latest.thread_id if latest else f"deal_{deal_id}"      # never trust a client-supplied "1"
    #     graph = get_deal_intelligence_graph()
    #     config = {"configurable": {"thread_id": tid}, "recursion_limit": 50}
    
    #     existing = await graph.aget_state(config)
    #     if existing.next:                       # interrupted / failed mid-run -> CONTINUE from checkpoint
    #         graph_input = None
    #     else:                                   # new run (or previous run finished) -> fresh thread
    #         if existing.values:
    #             tid = f"deal_{deal_id}_{uuid4().hex[:8]}"
    #             config = {"configurable": {"thread_id": tid}, "recursion_limit": 50}
    #         graph_input = self._initial_state(deal)
    #         init = {**graph_input, "node_statuses": {"company_research": "RUNNING"},
    #                 "current_step": "RUNNING: company_research"}
    #         await self.intel_repo.save_intelligence_snapshot(
    #             deal_id=deal_id, thread_id=tid, current_step=init["current_step"], snapshot_data=init)
    
    #     await self.deal_repo.update_deal_status(deal_id, "RUNNING")
    #     try:
    #         async for _ in graph.astream(graph_input, config=config, stream_mode="updates"):
    #             await self._persist(deal_id, tid, graph, config)     # DB updated after every node
    
    #         final = await self._persist(deal_id, tid, graph, config)
    #         vals = final.values or {}
    #         if "mandatory_review" in final.next:
    #             status = "AWAITING_REVIEW"
    #         elif final.next:
    #             status = "PAUSED"
    #         elif vals.get("mandatory_review_checkpoint") == "rejected":
    #             status = "REJECTED"
    #         else:
    #             status = "COMPLETED"
    #         await self.deal_repo.update_deal_status(deal_id, status)
    #         return to_primitive(vals)
    #     except Exception as e:
    #         logger.exception("Workflow failed for deal %s", deal_id)
    #         await self.deal_repo.update_deal_status(deal_id, "FAILED")
    #         await self.intel_repo.save_intelligence_snapshot(
    #             deal_id=deal_id, thread_id=tid, current_step="FAILED",
    #             snapshot_data={**to_primitive(dict((await graph.aget_state(config)).values or {})),
    #                            "current_step": "FAILED", "errors": [str(e)]})
    #         raise
        
    # async def apply_review_decision(self, deal_id: UUID, patch: dict):
    #     """Write the human decision into the graph's own state. The caller then enqueues run_deal_intelligence_workflow."""
    #     latest = await self.intel_repo.get_latest_intelligence_snapshot(deal_id)
    #     if not latest:
    #         raise ValueError(f"No workflow for deal {deal_id}")
    #     config = {"configurable": {"thread_id": latest.thread_id}}
    #     await get_deal_intelligence_graph().aupdate_state(config, patch)
    # async def submit_human_approval(self, deal_id: UUID, approval_request: HumanApprovalRequest):
    #     """
    #     Legacy endpoint interface. Handles resume state patching for human feedback.
    #     """
    #     logger.warning(
    #         f"Using legacy submit_human_approval endpoint. "
    #         f"Consider migrating to /hitl/mandatory-review/approve."
    #     )

    #     latest_snapshot = await self.intel_repo.get_latest_intelligence_snapshot(deal_id)
    #     if not latest_snapshot:
    #         raise ValueError(f"No snapshot found for deal {deal_id}")

    #     thread_id = latest_snapshot.thread_id
    #     config = {"configurable": {"thread_id": thread_id}}
    #     graph = get_deal_intelligence_graph()

    #     resume_state_patch = {
    #         "human_approved": approval_request.approved,
    #         "human_feedback": approval_request.feedback,
    #         "custom_selected_assets": approval_request.custom_selected_assets or [],
    #         "service_mappings": approval_request.service_mappings or [],
    #         "current_step": "HUMAN_REVIEW_SUBMITTED",
    #         "mandatory_review_checkpoint": "approved" if approval_request.approved else "pending",
    #     }

    #     await self.deal_repo.update_deal_status(deal_id, "RUNNING")
    #     final_state = await graph.ainvoke(resume_state_patch, config=config)

    #     current_step = final_state.get("current_step", "COMPLETED")
    #     await self.deal_repo.update_deal_status(deal_id, "COMPLETED" if "COMPLETED" in current_step else "PAUSED")

    #     serial_state = to_primitive(final_state)

    #     await self.intel_repo.save_intelligence_snapshot(
    #         deal_id=deal_id,
    #         thread_id=thread_id,
    #         current_step=current_step,
    #         snapshot_data=serial_state,
    #     )
    #     return serial_state

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