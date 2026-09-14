import logging
from uuid import UUID
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.repositories.deal_repository import DealRepository
from app.repositories.deal_intelligence_repository import DealIntelligenceRepository
from app.repositories.execution_history_repository import ExecutionHistoryRepository
from app.schemas.deal import DealCreate
from app.schemas.deal_intelligence import HumanApprovalRequest
from app.agents.graph import deal_intelligence_graph
from app.services.hitl_manager import HITLManager
from app.services.execution_history_service import ExecutionHistoryService

logger = logging.getLogger(__name__)


class DealService:
    def __init__(self, db: Session):
        self.db = db
        self.deal_repo = DealRepository(db)
        self.intel_repo = DealIntelligenceRepository(db)
        self.hitl_manager = HITLManager(db)
        self.history_service = ExecutionHistoryService(db)
        self.history_repo = ExecutionHistoryRepository(db)

    def create_new_deal(self, owner_id: UUID, deal_data: DealCreate):
        return self.deal_repo.create_deal(
            owner_id=owner_id,
            title=deal_data.title,
            target_company=deal_data.target_company,
            target_industry=deal_data.target_industry,
            meeting_objective=deal_data.meeting_objective
        )

    async def run_deal_intelligence_workflow(self, deal_id: UUID, thread_id: Optional[str] = None):
        """
        Starts or resumes the deal intelligence workflow with full HITL support.
        
        Handles:
        - Initial state setup with HITL fields
        - Workflow execution with checkpoint persistence
        - Dynamic instruction injection
        - Pause/resume lifecycle
        """
        deal = self.deal_repo.get_deal_by_id(deal_id)
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")

        effective_thread_id = thread_id or f"thread_{deal_id}"
        
        # Check if resuming from existing snapshot
        existing_snapshot = self.intel_repo.get_latest_intelligence_snapshot(deal_id)
        
        if existing_snapshot:
            # Resume from checkpoint: merge latest state with any updates
            logger.info(f"Resuming workflow for deal {deal_id} from checkpoint")
            active_state = existing_snapshot.snapshot_data or {}
            effective_thread_id = existing_snapshot.thread_id
        else:
            # Initial execution: set up fresh state with HITL fields
            logger.info(f"Starting new workflow for deal {deal_id}")
            active_state = {
                "deal_id": str(deal.id),
                "target_company": deal.target_company,
                "target_industry": deal.target_industry,
                "meeting_objective": deal.meeting_objective,
                # HITL Control Fields
                "pause_requested": False,
                "manual_pause_at_node": None,
                "dynamic_instructions": None,
                "mandatory_review_checkpoint": "pending",
                "human_approved": False,
                "human_feedback": None,
                "custom_selected_assets": None,
                "current_step": "STARTED",
                "execution_paused_at": None,
                "last_execution_resumption": None,
                "node_statuses": {},
                "errors": None,
                "cxo_executive_brief": {},
                "markdown_export": None,
            }

        self.deal_repo.update_deal_status(deal_id, "RUNNING")
        config = {"configurable": {"thread_id": effective_thread_id}}
        
        try:
            # Execute workflow with LangGraph
            final_state = await deal_intelligence_graph.ainvoke(active_state, config=config)
            current_step = final_state.get("current_step", "COMPLETED")
            
            # Determine status based on final state
            if "PAUSED" in current_step or final_state.get("pause_requested"):
                status = "PAUSED"
            elif current_step == "MANDATORY_REVIEW_CHECKPOINT":
                status = "AWAITING_REVIEW"
            elif "REJECTED" in current_step:
                status = "REJECTED"
            else:
                status = "COMPLETED"
            
            self.deal_repo.update_deal_status(deal_id, status)
            
            # Persist final state snapshot
            self.intel_repo.save_intelligence_snapshot(
                deal_id=deal_id,
                thread_id=effective_thread_id,
                current_step=current_step,
                snapshot_data=final_state
            )
            
            logger.info(f"Workflow execution completed for deal {deal_id} with status: {status}")
            return final_state
            
        except Exception as e:
            logger.error(f"Workflow execution failed for deal {deal_id}: {str(e)}")
            self.deal_repo.update_deal_status(deal_id, "FAILED")
            raise

    async def submit_human_approval(self, deal_id: UUID, approval_request: HumanApprovalRequest):
        """
        Legacy method: Resumes LangGraph execution after human sales leader edits or approves asset mappings.
        
        Now delegates to HITLManager.submit_mandatory_review_approval for consistency.
        """
        logger.warning(
            f"Using legacy submit_human_approval endpoint. "
            f"Consider using /hitl/mandatory-review/approve instead."
        )
        
        latest_snapshot = self.intel_repo.get_latest_intelligence_snapshot(deal_id)
        if not latest_snapshot:
            raise ValueError(f"No snapshot found for deal {deal_id}")

        thread_id = latest_snapshot.thread_id
        config = {"configurable": {"thread_id": thread_id}}

        resume_state_patch = {
            "human_approved": approval_request.approved,
            "human_feedback": approval_request.feedback,
            "custom_selected_assets": approval_request.custom_selected_assets or [],
            "current_step": "HUMAN_REVIEW_SUBMITTED",
            "mandatory_review_checkpoint": "approved" if approval_request.approved else "pending",
        }

        self.deal_repo.update_deal_status(deal_id, "RUNNING")
        final_state = await deal_intelligence_graph.ainvoke(resume_state_patch, config=config)
        
        current_step = final_state.get("current_step", "COMPLETED")
        self.deal_repo.update_deal_status(deal_id, "COMPLETED" if "COMPLETED" in current_step else "PAUSED")

        self.intel_repo.save_intelligence_snapshot(
            deal_id=deal_id,
            thread_id=thread_id,
            current_step=current_step,
            snapshot_data=final_state
        )
        return final_state

    def get_deal_context(self, deal_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Returns comprehensive deal context for frontend display.
        """
        deal = self.deal_repo.get_deal_by_id(deal_id)
        if not deal:
            return None
        
        snapshot = self.intel_repo.get_latest_intelligence_snapshot(deal_id)
        
        return {
            "deal": {
                "id": str(deal.id),
                "title": deal.title,
                "target_company": deal.target_company,
                "status": deal.status,
            },
            "active_state": snapshot.snapshot_data if snapshot else {},
        }

    async def resume_from_checkpoint(
        self,
        deal_id: UUID,
        checkpoint_id: str,
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Resume workflow from a specific checkpoint."""
        deal = self.deal_repo.get_deal_by_id(deal_id)
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")

        checkpoint_state = self.history_service.prepare_resume_state(deal_id, checkpoint_id)
        if not checkpoint_state:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")

        new_thread_id = thread_id or f"thread_{deal_id}_resumed"
        self.deal_repo.update_deal_status(deal_id, "RUNNING")
        config = {"configurable": {"thread_id": new_thread_id}}

        try:
            final_state = await deal_intelligence_graph.ainvoke(checkpoint_state, config=config)
            current_step = final_state.get("current_step", "COMPLETED")
            status = "PAUSED" if "PAUSED" in current_step else "COMPLETED"
            
            self.deal_repo.update_deal_status(deal_id, status)
            self.intel_repo.save_intelligence_snapshot(
                deal_id=deal_id,
                thread_id=new_thread_id,
                current_step=current_step,
                snapshot_data=final_state
            )
            return final_state
        except Exception as e:
            logger.error(f"Failed to resume from checkpoint {checkpoint_id}: {str(e)}")
            self.deal_repo.update_deal_status(deal_id, "FAILED")
            raise

    def get_execution_timeline(self, deal_id: UUID) -> Dict[str, Any]:
        """Get all execution versions and their checkpoints."""
        return {"timeline": self.history_service.get_deal_timeline(deal_id)}

    def get_thread_history(self, deal_id: UUID, thread_id: str) -> Dict[str, Any]:
        """Get all checkpoints in a specific thread."""
        return {"checkpoints": self.history_service.get_thread_history(thread_id, deal_id)}
