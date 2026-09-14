"""
Centralized Human-In-The-Loop (HITL) management for LangGraph deal intelligence workflow.

Handles:
- Dynamic steering (real-time instruction injection)
- Manual pause/resume at node boundaries
- Mandatory review checkpoints
- State management and persistence
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

from sqlalchemy.orm import Session

from app.agents.state import DealIntelligenceState
from app.repositories.deal_intelligence_repository import DealIntelligenceRepository
from app.repositories.deal_repository import DealRepository
from app.schemas.hitl import (
    CheckpointStatus,
    DynamicInstructionRequest,
    ManualPauseRequest,
    ManualResumeRequest,
    MandatoryReviewApprovalRequest,
)

logger = logging.getLogger(__name__)

# Nodes where mandatory review checkpoint must occur
MANDATORY_CHECKPOINT_NODES = ["service_mapper"]  # Before cxo_brief_generator

# Nodes where manual pause is allowed
PAUSABLE_NODES = [
    "company_research",
    "financial_intelligence",
    "stakeholder_intel",
    "industry_analysis",
    "pain_point_detector",
    "enterprise_rag_matcher",
    "service_mapper",
]


class HITLManager:
    """
    Manages all Human-In-The-Loop interactions with the deal intelligence workflow.
    """

    def __init__(self, db: Session):
        self.db = db
        self.intel_repo = DealIntelligenceRepository(db)
        self.deal_repo = DealRepository(db)

    # =========================================================================
    # 1. DYNAMIC STEERING: Real-time instruction injection
    # =========================================================================

    def submit_dynamic_instruction(
        self,
        deal_id: UUID,
        request: DynamicInstructionRequest,
    ) -> Dict[str, Any]:
        """
        Injects real-time steering instructions into active node execution.
        
        These instructions are appended to the active node's LLM prompt context
        without pausing the workflow.
        
        Args:
            deal_id: Target deal ID
            request: Dynamic instruction request with instructions and optional target node
            
        Returns:
            Response dict with status and updated state
        """
        logger.info(f"Submitting dynamic instructions for deal {deal_id}")
        
        # Get latest snapshot to access current state
        snapshot = self.intel_repo.get_latest_intelligence_snapshot(deal_id)
        if not snapshot:
            raise ValueError(f"No active workflow for deal {deal_id}")
        
        thread_id = snapshot.thread_id
        active_state = snapshot.snapshot_data or {}
        
        # Append instructions to state
        existing_instructions = active_state.get("dynamic_instructions") or []
        updated_instructions = existing_instructions + request.instructions
        
        state_patch = {
            "dynamic_instructions": updated_instructions,
            "node_statuses": {
                "instructions_submitted": f"Instruction batch submitted at {datetime.utcnow().isoformat()}",
                "priority": request.priority,
            }
        }
        
        # Save updated snapshot
        self.intel_repo.save_intelligence_snapshot(
            deal_id=deal_id,
            thread_id=thread_id,
            current_step=active_state.get("current_step", "EXECUTING"),
            snapshot_data={**active_state, **state_patch}
        )
        
        logger.info(f"Dynamic instructions queued for deal {deal_id}: {len(request.instructions)} new instructions")
        
        return {
            "success": True,
            "message": f"Queued {len(request.instructions)} instructions for active node execution",
            "current_step": active_state.get("current_step"),
            "execution_paused": False,
            "instructions_queued": len(request.instructions),
        }

    # =========================================================================
    # 2. MANUAL PAUSE & RESUME: Stop at node boundaries
    # =========================================================================

    def request_manual_pause(
        self,
        deal_id: UUID,
        request: ManualPauseRequest,
    ) -> Dict[str, Any]:
        """
        Requests manual pause at next node boundary.
        
        The workflow will complete the current node and pause before the next node
        begins execution.
        
        Args:
            deal_id: Target deal ID
            request: Pause request with optional reason
            
        Returns:
            Response dict with status
        """
        logger.info(f"Manual pause requested for deal {deal_id}. Reason: {request.reason}")
        
        snapshot = self.intel_repo.get_latest_intelligence_snapshot(deal_id)
        if not snapshot:
            raise ValueError(f"No active workflow for deal {deal_id}")
        
        thread_id = snapshot.thread_id
        active_state = snapshot.snapshot_data or {}
        
        # Set pause flag
        state_patch = {
            "pause_requested": True,
            "execution_paused_at": datetime.utcnow().isoformat(),
            "node_statuses": {
                "pause_requested_at": datetime.utcnow().isoformat(),
                "pause_reason": request.reason or "User-requested pause",
            }
        }
        
        # Update deal status to PAUSED
        self.deal_repo.update_deal_status(deal_id, "PAUSED")
        
        # Save updated snapshot
        self.intel_repo.save_intelligence_snapshot(
            deal_id=deal_id,
            thread_id=thread_id,
            current_step="PAUSED_AT_BOUNDARY",
            snapshot_data={**active_state, **state_patch}
        )
        
        logger.info(f"Pause request recorded for deal {deal_id}")
        
        return {
            "success": True,
            "message": "Workflow will pause at next node boundary",
            "current_step": active_state.get("current_step"),
            "execution_paused": True,
            "pause_requested_at": datetime.utcnow().isoformat(),
        }

    def resume_workflow_after_pause(
        self,
        deal_id: UUID,
        request: ManualResumeRequest,
    ) -> Dict[str, Any]:
        """
        Resumes workflow execution after manual pause.
        
        Optionally applies new instructions before resuming.
        
        Args:
            deal_id: Target deal ID
            request: Resume request with optional instructions and feedback
            
        Returns:
            Response dict with status
        """
        logger.info(f"Resuming workflow for deal {deal_id}")
        
        snapshot = self.intel_repo.get_latest_intelligence_snapshot(deal_id)
        if not snapshot:
            raise ValueError(f"No paused workflow for deal {deal_id}")
        
        thread_id = snapshot.thread_id
        active_state = snapshot.snapshot_data or {}
        
        # Apply instructions if provided
        existing_instructions = active_state.get("dynamic_instructions") or []
        if request.instructions:
            existing_instructions.extend(request.instructions)
        
        state_patch = {
            "pause_requested": False,
            "dynamic_instructions": existing_instructions if existing_instructions else None,
            "human_feedback": request.feedback or active_state.get("human_feedback"),
            "last_execution_resumption": datetime.utcnow().isoformat(),
            "node_statuses": {
                "resumed_at": datetime.utcnow().isoformat(),
                "resumption_feedback": request.feedback or "No additional feedback",
            }
        }
        
        # Update deal status to RUNNING
        self.deal_repo.update_deal_status(deal_id, "RUNNING")
        
        # Save updated snapshot
        self.intel_repo.save_intelligence_snapshot(
            deal_id=deal_id,
            thread_id=thread_id,
            current_step="RESUMED_FROM_PAUSE",
            snapshot_data={**active_state, **state_patch}
        )
        
        logger.info(f"Workflow resumed for deal {deal_id}")
        
        return {
            "success": True,
            "message": "Workflow execution resumed",
            "current_step": "RESUMED_FROM_PAUSE",
            "execution_paused": False,
            "resumed_at": datetime.utcnow().isoformat(),
            "instructions_applied": len(request.instructions or []),
        }

    # =========================================================================
    # 3. MANDATORY REVIEW CHECKPOINT: Before CXO brief generation
    # =========================================================================

    def evaluate_mandatory_checkpoint(
        self,
        state: DealIntelligenceState,
    ) -> Dict[str, Any]:
        """
        Evaluates whether mandatory review checkpoint should pause workflow.
        
        This is called before entering cxo_brief_generator node.
        Returns state updates to pause if not yet approved.
        
        Args:
            state: Current deal intelligence state
            
        Returns:
            Dict with mandatory_review_checkpoint status and any state patches
        """
        current_checkpoint = state.get("mandatory_review_checkpoint", "pending")
        deal_id = state.get("deal_id", "")
        
        logger.info(f"Evaluating mandatory review checkpoint for deal {deal_id}. Status: {current_checkpoint}")
        
        # If already approved, allow proceeding
        if current_checkpoint == CheckpointStatus.APPROVED:
            return {"mandatory_review_checkpoint": CheckpointStatus.APPROVED}
        
        # Otherwise, pause for review
        return {
            "mandatory_review_checkpoint": CheckpointStatus.PENDING,
            "execution_paused_at": datetime.utcnow().isoformat(),
            "node_statuses": {
                "mandatory_checkpoint": "PAUSED_FOR_MANDATORY_REVIEW",
                "paused_at": datetime.utcnow().isoformat(),
            }
        }

    def submit_mandatory_review_approval(
        self,
        deal_id: UUID,
        request: MandatoryReviewApprovalRequest,
    ) -> Dict[str, Any]:
        """
        Submits approval/rejection for mandatory review checkpoint.
        
        Args:
            deal_id: Target deal ID
            request: Approval request with status and optional modifications
            
        Returns:
            Response dict with status
        """
        logger.info(
            f"Submitting mandatory review approval for deal {deal_id}. "
            f"Status: {request.checkpoint_status}"
        )
        
        snapshot = self.intel_repo.get_latest_intelligence_snapshot(deal_id)
        if not snapshot:
            raise ValueError(f"No workflow at checkpoint for deal {deal_id}")
        
        thread_id = snapshot.thread_id
        active_state = snapshot.snapshot_data or {}
        
        # Update checkpoint status
        state_patch = {
            "mandatory_review_checkpoint": request.checkpoint_status,
            "human_feedback": request.feedback or active_state.get("human_feedback"),
            "custom_selected_assets": request.custom_selected_assets or active_state.get("custom_selected_assets"),
            "node_statuses": {
                "mandatory_checkpoint_resolved": datetime.utcnow().isoformat(),
                "checkpoint_status": request.checkpoint_status,
            }
        }
        
        # If modifications requested, merge them into cxo_executive_brief
        if request.executive_brief_modifications:
            current_brief = active_state.get("cxo_executive_brief", {})
            current_brief.update(request.executive_brief_modifications)
            state_patch["cxo_executive_brief"] = current_brief
        
        # Update deal status based on checkpoint decision
        if request.checkpoint_status == CheckpointStatus.APPROVED:
            self.deal_repo.update_deal_status(deal_id, "RUNNING")  # Continue to final brief generation
        elif request.checkpoint_status == CheckpointStatus.REJECTED:
            self.deal_repo.update_deal_status(deal_id, "REJECTED")
            logger.info(f"Workflow rejected at mandatory checkpoint for deal {deal_id}")
        elif request.checkpoint_status == CheckpointStatus.NEEDS_REVISION:
            self.deal_repo.update_deal_status(deal_id, "PAUSED")  # Pause for revision
        
        # Save updated snapshot
        self.intel_repo.save_intelligence_snapshot(
            deal_id=deal_id,
            thread_id=thread_id,
            current_step=f"MANDATORY_CHECKPOINT_{request.checkpoint_status.upper()}",
            snapshot_data={**active_state, **state_patch}
        )
        
        logger.info(f"Mandatory review processed for deal {deal_id}: {request.checkpoint_status}")
        
        return {
            "success": True,
            "message": f"Checkpoint status updated to: {request.checkpoint_status}",
            "checkpoint_status": request.checkpoint_status,
            "execution_paused": request.checkpoint_status in [
                CheckpointStatus.NEEDS_REVISION,
                CheckpointStatus.REJECTED,
            ],
            "can_proceed": request.checkpoint_status == CheckpointStatus.APPROVED,
        }

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_workflow_checkpoint_state(
        self,
        deal_id: UUID,
    ) -> Dict[str, Any]:
        """
        Returns current state for HITL review and decision-making.
        """
        snapshot = self.intel_repo.get_latest_intelligence_snapshot(deal_id)
        if not snapshot:
            raise ValueError(f"No workflow found for deal {deal_id}")
        
        state = snapshot.snapshot_data or {}
        
        return {
            "deal_id": str(deal_id),
            "current_step": state.get("current_step"),
            "execution_paused_at": state.get("execution_paused_at"),
            "last_execution_resumption": state.get("last_execution_resumption"),
            "pause_requested": state.get("pause_requested", False),
            "manual_pause_at_node": state.get("manual_pause_at_node"),
            "dynamic_instructions": state.get("dynamic_instructions"),
            "mandatory_review_checkpoint": state.get("mandatory_review_checkpoint", "pending"),
            "human_approved": state.get("human_approved", False),
            "human_feedback": state.get("human_feedback"),
            "available_assets": len(state.get("matched_internal_assets", [])),
            "available_service_mappings": len(state.get("service_mappings", [])),
            "node_statuses": state.get("node_statuses", {}),
            "errors": state.get("errors"),
        }
