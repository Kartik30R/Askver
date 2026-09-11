import logging
from uuid import UUID
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.repositories.deal_repository import DealRepository
from app.repositories.deal_intelligence_repository import DealIntelligenceRepository
from app.schemas.deal import DealCreate
from app.schemas.deal_intelligence import HumanApprovalRequest
from app.agents.workflow import deal_intelligence_graph  # Compiled LangGraph instance

logger = logging.getLogger(__name__)


class DealService:
    def __init__(self, db: Session):
        self.db = db
        self.deal_repo = DealRepository(db)
        self.intel_repo = DealIntelligenceRepository(db)

    def create_new_deal(self, owner_id: UUID, deal_data: DealCreate):
        return self.deal_repo.create_deal(
            owner_id=owner_id,
            title=deal_data.title,
            target_company=deal_data.target_company,
            target_industry=deal_data.target_industry,
            meeting_objective=deal_data.meeting_objective
        )

    async def run_deal_intelligence_workflow(self, deal_id: UUID, thread_id: Optional[str] = None):
        deal = self.deal_repo.get_deal_by_id(deal_id)
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")

        effective_thread_id = thread_id or f"thread_{deal_id}"
        initial_state = {
            "deal_id": str(deal.id),
            "target_company": deal.target_company,
            "target_industry": deal.target_industry,
            "meeting_objective": deal.meeting_objective,
            "human_approved": False,
            "human_feedback": None,
            "custom_selected_assets": None,
            "current_step": "STARTED"
        }

        self.deal_repo.update_deal_status(deal_id, "RUNNING")
        config = {"configurable": {"thread_id": effective_thread_id}}
        
        final_state = await deal_intelligence_graph.ainvoke(initial_state, config=config)
        current_step = final_state.get("current_step", "COMPLETED")
        
        status = "PAUSED_FOR_HUMAN_REVIEW" if "PAUSED" in current_step else "COMPLETED"
        self.deal_repo.update_deal_status(deal_id, status)

        self.intel_repo.save_intelligence_snapshot(
            deal_id=deal_id,
            thread_id=effective_thread_id,
            current_step=current_step,
            snapshot_data=final_state
        )
        return final_state

    async def submit_human_approval(self, deal_id: UUID, approval_request: HumanApprovalRequest):
        """
        Resumes LangGraph execution after human sales leader edits or approves asset mappings.
        """
        latest_snapshot = self.intel_repo.get_latest_intelligence_snapshot(deal_id)
        if not latest_snapshot:
            raise ValueError(f"No snapshot found for deal {deal_id}")

        thread_id = latest_snapshot.thread_id
        config = {"configurable": {"thread_id": thread_id}}

        resume_state_patch = {
            "human_approved": approval_request.approved,
            "human_feedback": approval_request.feedback,
            "custom_selected_assets": approval_request.custom_selected_assets or [],
            "current_step": "HUMAN_REVIEW_SUBMITTED"
        }

        self.deal_repo.update_deal_status(deal_id, "RUNNING")
        final_state = await deal_intelligence_graph.ainvoke(resume_state_patch, config=config)
        
        current_step = final_state.get("current_step", "COMPLETED")
        self.deal_repo.update_deal_status(deal_id, "COMPLETED" if "COMPLETED" in current_step else "PAUSED_FOR_HUMAN_REVIEW")

        self.intel_repo.save_intelligence_snapshot(
            deal_id=deal_id,
            thread_id=thread_id,
            current_step=current_step,
            snapshot_data=final_state
        )
        return final_state