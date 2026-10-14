# """
# Centralized Human-In-The-Loop (HITL) management for LangGraph deal intelligence workflow.

# Handles:
# - Dynamic steering (real-time instruction injection)
# - Manual pause/resume at node boundaries
# - Mandatory review checkpoints
# - State management and persistence
# """
# import logging
# from datetime import datetime
# from typing import Dict, Any, Optional, List
# from uuid import UUID

# from sqlalchemy.ext.asyncio import AsyncSession

# from agents.state import DealIntelligenceState
# from app.repositories.deal_intelligence_repository import DealIntelligenceRepository
# from app.repositories.deal_repository import DealRepository
# from app.schemas.hitl import (
#     CheckpointStatus,
#     DynamicInstructionRequest,
#     ManualPauseRequest,
#     ManualResumeRequest,
#     MandatoryReviewApprovalRequest,
# )
# from app.utils.serializers import to_primitive

# logger = logging.getLogger(__name__)

# # Nodes where mandatory review checkpoint must occur
# MANDATORY_CHECKPOINT_NODES = ["service_mapper"]  # Before cxo_brief_generator

# # Nodes where manual pause is allowed
# PAUSABLE_NODES = [
#     "company_research",
#     "financial_intelligence",
#     "stakeholder_intel",
#     "industry_analysis",
#     "pain_point_detector",
#     "enterprise_rag_matcher",
#     "service_mapper",
# ]


# class HITLManager:
#     """
#     Manages all Human-In-The-Loop interactions with the deal intelligence workflow.
#     """

#     def __init__(self, db: AsyncSession):
#         self.db = db
#         self.intel_repo = DealIntelligenceRepository(db)
#         self.deal_repo = DealRepository(db)

#     # =========================================================================
#     # 1. DYNAMIC STEERING: Real-time instruction injection
#     # =========================================================================

#     async def submit_dynamic_instruction(
#         self,
#         deal_id: UUID,
#         request: DynamicInstructionRequest,
#     ) -> Dict[str, Any]:
#         """
#         Injects real-time steering instructions into active node execution.
        
#         These instructions are appended to the active node's LLM prompt context
#         without pausing the workflow.
        
#         Args:
#             deal_id: Target deal ID
#             request: Dynamic instruction request with instructions and optional target node
            
#         Returns:
#             Response dict with status and updated state
#         """
#         logger.info(f"Submitting dynamic instructions for deal {deal_id}")
        
#         # Get latest snapshot to access current state
#         snapshot = self.intel_repo.get_latest_intelligence_snapshot(deal_id)
#         if not snapshot:
#             raise ValueError(f"No active workflow for deal {deal_id}")
        
#         thread_id = snapshot.thread_id
#         active_state = snapshot.snapshot_data or {}
        
#         # Append instructions to state; the snapshot can legitimately contain no prior list.
#         existing_instructions = active_state.get("dynamic_instructions") or []
#         updated_instructions = list(existing_instructions) + list(request.instructions or [])

#         state_patch = {
#             "dynamic_instructions": updated_instructions,
#             "node_statuses": {
#                 "instructions_submitted": f"Instruction batch submitted at {datetime.utcnow().isoformat()}",
#                 "priority": request.priority,
#             }
#         }
        
#         # Save updated snapshot
#         await self.intel_repo.save_intelligence_snapshot(
#             deal_id=deal_id,
#             thread_id=thread_id,
#             current_step=active_state.get("current_step", "EXECUTING"),
#             snapshot_data=to_primitive({**active_state, **state_patch}),
#         )
        
#         logger.info(f"Dynamic instructions queued for deal {deal_id}: {len(request.instructions)} new instructions")
        
#         return {
#             "success": True,
#             "message": f"Queued {len(request.instructions)} instructions for active node execution",
#             "current_step": active_state.get("current_step"),
#             "execution_paused": False,
#             "instructions_queued": len(request.instructions),
#         }

#     # =========================================================================
#     # 2. MANUAL PAUSE & RESUME: Stop at node boundaries
#     # =========================================================================

#     async def request_manual_pause(
#         self,
#         deal_id: UUID,
#         request: ManualPauseRequest,
#     ) -> Dict[str, Any]:
#         """
#         Requests manual pause at next node boundary.
        
#         The workflow will complete the current node and pause before the next node
#         begins execution.
        
#         Args:
#             deal_id: Target deal ID
#             request: Pause request with optional reason
            
#         Returns:
#             Response dict with status
#         """
#         logger.info(f"Manual pause requested for deal {deal_id}. Reason: {request.reason}")
        
#         snapshot = self.intel_repo.get_latest_intelligence_snapshot(deal_id)
#         if not snapshot:
#             raise ValueError(f"No active workflow for deal {deal_id}")
        
#         thread_id = snapshot.thread_id
#         active_state = snapshot.snapshot_data or {}
        
#         # Set pause flag
#         state_patch = {
#             "pause_requested": True,
#             "execution_paused_at": datetime.utcnow().isoformat(),
#             "node_statuses": {
#                 "pause_requested_at": datetime.utcnow().isoformat(),
#                 "pause_reason": request.reason or "User-requested pause",
#             }
#         }
        
#         # Update deal status to PAUSED
#         await self.deal_repo.update_deal_status(deal_id, "PAUSED")
        
#         # Save updated snapshot
#         await self.intel_repo.save_intelligence_snapshot(
#             deal_id=deal_id,
#             thread_id=thread_id,
#             current_step="PAUSED_AT_BOUNDARY",
#             snapshot_data=to_primitive({**active_state, **state_patch}),
#         )
        
#         logger.info(f"Pause request recorded for deal {deal_id}")
        
#         return {
#             "success": True,
#             "message": "Workflow will pause at next node boundary",
#             "current_step": active_state.get("current_step"),
#             "execution_paused": True,
#             "pause_requested_at": datetime.utcnow().isoformat(),
#         }

#     async def resume_workflow_after_pause(
#         self,
#         deal_id: UUID,
#         request: ManualResumeRequest,
#     ) -> Dict[str, Any]:
#         """
#         Resumes workflow execution after manual pause.
        
#         Optionally applies new instructions before resuming.
        
#         Args:
#             deal_id: Target deal ID
#             request: Resume request with optional instructions and feedback
            
#         Returns:
#             Response dict with status
#         """
#         logger.info(f"Resuming workflow for deal {deal_id}")
        
#         snapshot = await self.intel_repo.get_latest_intelligence_snapshot(deal_id)
#         if not snapshot:
#             raise ValueError(f"No paused workflow for deal {deal_id}")
        
#         thread_id = snapshot.thread_id
#         active_state = snapshot.snapshot_data or {}
        
#         # Apply instructions if provided; guard against a snapshot that has no list yet.
#         existing_instructions = list(active_state.get("dynamic_instructions") or [])
#         if request.instructions:
#             existing_instructions.extend(request.instructions)

#         state_patch = {
#             "pause_requested": False,
#             "dynamic_instructions": existing_instructions if existing_instructions else None,
#             "human_feedback": request.feedback or active_state.get("human_feedback"),
#             "last_execution_resumption": datetime.utcnow().isoformat(),
#             "node_statuses": {
#                 "resumed_at": datetime.utcnow().isoformat(),
#                 "resumption_feedback": request.feedback or "No additional feedback",
#             }
#         }
        
#         # Update deal status to RUNNING
#         await self.deal_repo.update_deal_status(deal_id, "RUNNING")
        
#         # Save updated snapshot
#         await self.intel_repo.save_intelligence_snapshot(
#             deal_id=deal_id,
#             thread_id=thread_id,
#             current_step="RESUMED_FROM_PAUSE",
#             snapshot_data=to_primitive({**active_state, **state_patch}),
#         )
        
#         logger.info(f"Workflow resumed for deal {deal_id}")
        
#         return {
#             "success": True,
#             "message": "Workflow execution resumed",
#             "current_step": "RESUMED_FROM_PAUSE",
#             "execution_paused": False,
#             "resumed_at": datetime.utcnow().isoformat(),
#             "instructions_applied": len(request.instructions or []),
#         }

#     # =========================================================================
#     # 3. MANDATORY REVIEW CHECKPOINT: Before CXO brief generation
#     # =========================================================================

#     def evaluate_mandatory_checkpoint(
#         self,
#         state: DealIntelligenceState,
#     ) -> Dict[str, Any]:
#         """
#         Evaluates whether mandatory review checkpoint should pause workflow.
        
#         This is called before entering cxo_brief_generator node.
#         Returns state updates to pause if not yet approved.
        
#         Args:
#             state: Current deal intelligence state
            
#         Returns:
#             Dict with mandatory_review_checkpoint status and any state patches
#         """
#         current_checkpoint = state.get("mandatory_review_checkpoint", "pending")
#         deal_id = state.get("deal_id", "")
        
#         logger.info(f"Evaluating mandatory review checkpoint for deal {deal_id}. Status: {current_checkpoint}")
        
#         # If already approved, allow proceeding
#         if current_checkpoint == CheckpointStatus.APPROVED:
#             return {"mandatory_review_checkpoint": CheckpointStatus.APPROVED}
        
#         # Otherwise, pause for review
#         return {
#             "mandatory_review_checkpoint": CheckpointStatus.PENDING,
#             "execution_paused_at": datetime.utcnow().isoformat(),
#             "node_statuses": {
#                 "mandatory_checkpoint": "PAUSED_FOR_MANDATORY_REVIEW",
#                 "paused_at": datetime.utcnow().isoformat(),
#             }
#         }

#     async def submit_mandatory_review_approval(
#         self,
#         deal_id: UUID,
#         request: MandatoryReviewApprovalRequest,
#     ) -> Dict[str, Any]:
#         """
#         Submits approval/rejection for mandatory review checkpoint.
        
#         Args:
#             deal_id: Target deal ID
#             request: Approval request with status and optional modifications
            
#         Returns:
#             Response dict with status
#         """
#         logger.info(
#             f"Submitting mandatory review approval for deal {deal_id}. "
#             f"Status: {request.checkpoint_status}"
#         )
        
#         snapshot = await self.intel_repo.get_latest_intelligence_snapshot(deal_id)
#         if not snapshot:
#             raise ValueError(f"No workflow at checkpoint for deal {deal_id}")
        
#         thread_id = snapshot.thread_id
#         active_state = snapshot.snapshot_data or {}
        
#         # Update checkpoint status
#         state_patch = {
#             "mandatory_review_checkpoint": request.checkpoint_status,
#             "human_feedback": request.feedback or active_state.get("human_feedback"),
#             "custom_selected_assets": request.custom_selected_assets or active_state.get("custom_selected_assets"),
#             "node_statuses": {
#                 "mandatory_checkpoint_resolved": datetime.utcnow().isoformat(),
#                 "checkpoint_status": request.checkpoint_status,
#             }
#         }
        
#         # If modifications requested, merge them into cxo_executive_brief
#         if request.executive_brief_modifications:
#             current_brief = active_state.get("cxo_executive_brief", {})
#             current_brief.update(request.executive_brief_modifications)
#             state_patch["cxo_executive_brief"] = current_brief
        
#         # Update deal status based on checkpoint decision
#         if request.checkpoint_status == CheckpointStatus.APPROVED:
#             await self.deal_repo.update_deal_status(deal_id, "RUNNING")
#         elif request.checkpoint_status == CheckpointStatus.REJECTED:
#             await self.deal_repo.update_deal_status(deal_id, "REJECTED")
#             logger.info(f"Workflow rejected at mandatory checkpoint for deal {deal_id}")
#         elif request.checkpoint_status == CheckpointStatus.NEEDS_REVISION:
#             await self.deal_repo.update_deal_status(deal_id, "PAUSED")
        
#         # Save updated snapshot
#         await self.intel_repo.save_intelligence_snapshot(
#             deal_id=deal_id,
#             thread_id=thread_id,
#             current_step=f"MANDATORY_CHECKPOINT_{request.checkpoint_status.upper()}",
#             snapshot_data=to_primitive({**active_state, **state_patch}),
#         )
        
#         logger.info(f"Mandatory review processed for deal {deal_id}: {request.checkpoint_status}")
        
#         return {
#             "success": True,
#             "message": f"Checkpoint status updated to: {request.checkpoint_status}",
#             "checkpoint_status": request.checkpoint_status,
#             "execution_paused": request.checkpoint_status in [
#                 CheckpointStatus.NEEDS_REVISION,
#                 CheckpointStatus.REJECTED,
#             ],
#             "can_proceed": request.checkpoint_status == CheckpointStatus.APPROVED,
#         }

#     # =========================================================================
#     # Utility Methods
#     # =========================================================================

#     async def get_workflow_checkpoint_state(
#         self,
#         deal_id: UUID,
#     ) -> Dict[str, Any]:
#         """
#         Returns current state for HITL review and decision-making.
#         """
#         snapshot = await self.intel_repo.get_latest_intelligence_snapshot(deal_id)
#         if not snapshot:
#             raise ValueError(f"No workflow found for deal {deal_id}")
        
#         state = snapshot.snapshot_data or {}
        
#         return {
#             "deal_id": str(deal_id),
#             "current_step": state.get("current_step"),
#             "execution_paused_at": state.get("execution_paused_at"),
#             "last_execution_resumption": state.get("last_execution_resumption"),
#             "pause_requested": state.get("pause_requested", False),
#             "manual_pause_at_node": state.get("manual_pause_at_node"),
#             "dynamic_instructions": state.get("dynamic_instructions"),
#             "mandatory_review_checkpoint": state.get("mandatory_review_checkpoint", "pending"),
#             "human_approved": state.get("human_approved", False),
#             "human_feedback": state.get("human_feedback"),
#             "available_assets": len(state.get("matched_internal_assets", [])),
#             "available_service_mappings": len(state.get("service_mappings", [])),
#             "node_statuses": state.get("node_statuses", {}),
#             "errors": state.get("errors"),
#         }


import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import UUID

from langgraph.errors import InvalidUpdateError
from sqlalchemy.ext.asyncio import AsyncSession

from agents.graph import get_deal_intelligence_graph
from app.repositories.deal_intelligence_repository import DealIntelligenceRepository
from app.repositories.deal_repository import DealRepository
from app.schemas.hitl import (
    CheckpointStatus, DynamicInstructionRequest, ManualPauseRequest,
    ManualResumeRequest, MandatoryReviewApprovalRequest,
)
from app.utils.serializers import to_primitive

logger = logging.getLogger(__name__)
REVIEW_NODE = "mandatory_review"


class InvalidWorkflowState(Exception):
    """Action not allowed in the workflow's current state (map to HTTP 409)."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class HITLManager:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.intel_repo = DealIntelligenceRepository(db)
        self.deal_repo = DealRepository(db)

    async def _deal(self, deal_id: UUID):
        deal = await self.deal_repo.get_deal_by_id(deal_id)
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")
        return deal

    async def _config(self, deal_id: UUID):
        snap = await self.intel_repo.get_latest_intelligence_snapshot(deal_id)
        if not snap:
            raise ValueError(f"No workflow for deal {deal_id}")
        return {"configurable": {"thread_id": snap.thread_id}}

    async def _patch_state(self, config, patch: dict, as_node: str | None = None):
        graph = get_deal_intelligence_graph()
        if as_node:
            return await graph.aupdate_state(config, patch, as_node=as_node)
        try:
            return await graph.aupdate_state(config, patch)
        except InvalidUpdateError:
            # several nodes finished in the last step (parallel stage): attribute the edit to one of them
            return await graph.aupdate_state(config, patch, as_node="stakeholder_intel")

    async def _mirror(self, deal_id: UUID, config, current_step: str | None = None):
        """Copy graph state into deal_intelligence, keeping the node_statuses/current_step the runner wrote."""
        snap = await get_deal_intelligence_graph().aget_state(config)
        prev = await self.intel_repo.get_latest_intelligence_snapshot(deal_id)
        prev_data = (prev.snapshot_data or {}) if prev else {}
        data = to_primitive(dict(snap.values or {}))
        data["node_statuses"] = prev_data.get("node_statuses") or data.get("node_statuses") or {}
        data["current_step"] = current_step or (prev.current_step if prev else None)
        await self.intel_repo.save_intelligence_snapshot(
            deal_id=deal_id, thread_id=config["configurable"]["thread_id"],
            current_step=data["current_step"] or "EXECUTING", snapshot_data=data)

    # 1. Dynamic steering ------------------------------------------------------
    async def submit_dynamic_instruction(self, deal_id: UUID, request: DynamicInstructionRequest) -> Dict[str, Any]:
        deal = await self._deal(deal_id)
        config = await self._config(deal_id)

        target_nodes = list(request.target_nodes or [])
        if request.apply_to_node and not target_nodes:
            target_nodes = [request.apply_to_node]

        # Keep rerun selection independent from the actual instruction target list.
        # The rerun node controls where the workflow resumes; target_nodes controls
        # which downstream nodes should receive the instruction payload.
        formatted_instructions = [
            {"text": instruction, "target_nodes": target_nodes or ["*"]}
            for instruction in request.instructions or []
        ]
        patch: Dict[str, Any] = {
            "dynamic_instructions": formatted_instructions,
            "target_nodes": target_nodes or None,
            "rerun_from_node": request.rerun_from_node,
            "current_step": "INSTRUCTION_QUEUED",
        }
        await self._patch_state(config, patch)
        await self.deal_repo.update_deal_status(deal_id, "RUNNING")
        await self._mirror(deal_id, config, "INSTRUCTION_QUEUED")
        n = len(request.instructions or [])
        return {
            "success": True,
            "message": f"Queued {n} instructions for the selected node(s)",
            "execution_paused": False,
            "instructions_queued": n,
            "target_nodes": target_nodes,
            "rerun_from_node": request.rerun_from_node,
            "should_run": bool(request.rerun_from_node),
        }

    # 2. Pause / resume --------------------------------------------------------
    async def request_manual_pause(self, deal_id: UUID, request: ManualPauseRequest) -> Dict[str, Any]:
        deal = await self._deal(deal_id)
        if deal.status != "RUNNING":
            raise InvalidWorkflowState(f"Only a RUNNING workflow can be paused (status={deal.status})")
        await self.deal_repo.update_deal_status(deal_id, "PAUSE_REQUESTED")   # the runner polls this
        return {"success": True, "message": "Workflow will pause at the next step boundary",
                "execution_paused": False, "pause_requested_at": _now()}

    async def resume_workflow_after_pause(self, deal_id: UUID, request: ManualResumeRequest) -> Dict[str, Any]:
        deal = await self._deal(deal_id)
        if deal.status != "PAUSED":
            raise InvalidWorkflowState(f"Only a PAUSED workflow can be resumed (status={deal.status})")
        config = await self._config(deal_id)
        patch: Dict[str, Any] = {"last_execution_resumption": _now()}
        if request.instructions:
            patch["dynamic_instructions"] = [
                {"text": instruction, "target_nodes": ["*"]}
                for instruction in request.instructions
            ]
        if request.feedback:
            patch["human_feedback"] = request.feedback
        await self._patch_state(config, patch)
        await self.deal_repo.update_deal_status(deal_id, "RUNNING")
        await self._mirror(deal_id, config, "RESUMED_FROM_PAUSE")
        return {"success": True, "message": "Workflow resumed", "should_run": True,
                "instructions_applied": len(request.instructions or [])}

    # 3. Mandatory review ------------------------------------------------------
    async def submit_mandatory_review_approval(self, deal_id: UUID, request: MandatoryReviewApprovalRequest) -> Dict[str, Any]:
        deal = await self._deal(deal_id)
        if deal.status != "AWAITING_REVIEW":
            raise InvalidWorkflowState(f"Deal is not awaiting review (status={deal.status})")

        graph = get_deal_intelligence_graph()
        config = await self._config(deal_id)
        snap = await graph.aget_state(config)
        if REVIEW_NODE not in snap.next:
            raise InvalidWorkflowState("Workflow is not waiting at the mandatory review checkpoint")

        values = snap.values or {}
        status = request.checkpoint_status
        patch: Dict[str, Any] = {
            "mandatory_review_checkpoint": status.value,          # .value, never the Enum
            "human_approved": status == CheckpointStatus.APPROVED,
            "human_feedback": request.feedback or values.get("human_feedback"),
            "custom_selected_assets": request.custom_selected_assets or values.get("custom_selected_assets"),
        }
        if request.executive_brief_modifications:
            # The brief doesn't exist yet; pass the edits to the CXO node as steering instructions.
            patch["dynamic_instructions"] = [
                {
                    "text": "Reviewer edits to apply to the executive brief: "
                    + json.dumps(request.executive_brief_modifications, default=str),
                    "target_nodes": ["cxo_brief_generator"],
                }
            ]

        await graph.aupdate_state(config, patch, as_node="service_mapper")   # next node stays mandatory_review

        should_run = status in (CheckpointStatus.APPROVED, CheckpointStatus.REJECTED)
        if should_run:
            await self.deal_repo.update_deal_status(deal_id, "RUNNING")
        await self._mirror(deal_id, config, f"MANDATORY_CHECKPOINT_{status.value.upper()}")
        return {"success": True, "message": f"Checkpoint status updated to: {status.value}",
                "checkpoint_status": status.value, "should_run": should_run,
                "can_proceed": status == CheckpointStatus.APPROVED,
                "execution_paused": not should_run}

    # Utility ------------------------------------------------------------------
    async def get_workflow_checkpoint_state(self, deal_id: UUID) -> Dict[str, Any]:
        snapshot = await self.intel_repo.get_latest_intelligence_snapshot(deal_id)
        if not snapshot:
            raise ValueError(f"No workflow found for deal {deal_id}")
        s = snapshot.snapshot_data or {}
        return {
            "deal_id": str(deal_id),
            "current_step": s.get("current_step"),
            "execution_paused_at": s.get("execution_paused_at"),
            "last_execution_resumption": s.get("last_execution_resumption"),
            "pause_requested": s.get("pause_requested", False),
            "dynamic_instructions": s.get("dynamic_instructions"),
            "mandatory_review_checkpoint": s.get("mandatory_review_checkpoint", "pending"),
            "human_approved": s.get("human_approved", False),
            "human_feedback": s.get("human_feedback"),
            "available_assets": len(s.get("matched_internal_assets") or []),
            "available_service_mappings": len(s.get("service_mappings") or []),
            "node_statuses": s.get("node_statuses") or {},
            "errors": s.get("errors"),
        }