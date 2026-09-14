"""
Schemas for Human-In-The-Loop (HITL) operations in the deal intelligence workflow.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class CheckpointStatus(str, Enum):
    """Status of mandatory review checkpoints."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class DynamicInstructionRequest(BaseModel):
    """
    Submits real-time steering instructions to update the active node's execution.
    These instructions are appended to the node's current LLM prompt context.
    """
    instructions: List[str] = Field(
        ..., 
        description="List of instructions to inject into the active node's LLM prompt"
    )
    apply_to_node: Optional[str] = Field(
        None,
        description="Specific node name to apply instructions to. If None, applies to current node."
    )
    priority: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Priority level (1-10) for instruction execution"
    )


class ManualPauseRequest(BaseModel):
    """
    Requests manual pause of workflow at the next node boundary.
    """
    reason: Optional[str] = Field(
        None,
        description="Reason for pausing (for audit log)"
    )


class ManualResumeRequest(BaseModel):
    """
    Resumes workflow after manual pause with optional new instructions.
    """
    instructions: Optional[List[str]] = Field(
        None,
        description="Instructions to apply when resuming"
    )
    feedback: Optional[str] = Field(
        None,
        description="Human feedback on paused state"
    )


class MandatoryReviewApprovalRequest(BaseModel):
    """
    Submits approval/feedback for the mandatory review checkpoint (before cxo_brief_generator).
    """
    checkpoint_status: CheckpointStatus = Field(
        ...,
        description="Approval status for the review checkpoint"
    )
    feedback: Optional[str] = Field(
        None,
        description="Reviewer feedback or revision notes"
    )
    custom_selected_assets: Optional[List[str]] = Field(
        None,
        description="Hand-selected proof assets to use in final brief"
    )
    executive_brief_modifications: Optional[Dict[str, Any]] = Field(
        None,
        description="Specific modifications to make to the executive brief sections"
    )


class HumanApprovalRequest(BaseModel):
    """
    Legacy: Approval request for asset review during HITL gate.
    Now integrated into MandatoryReviewApprovalRequest.
    """
    approved: bool = Field(..., description="Whether the sales leader approves")
    feedback: Optional[str] = Field(None, description="Optional feedback")
    custom_selected_assets: Optional[List[str]] = Field(
        None,
        description="Hand-selected assets from matched internal assets"
    )


class WorkflowStateSnapshot(BaseModel):
    """
    Returns current workflow state for HITL review and interaction.
    """
    deal_id: str
    current_step: Optional[str]
    execution_paused_at: Optional[str]
    last_execution_resumption: Optional[str]
    pause_requested: bool
    manual_pause_at_node: Optional[str]
    dynamic_instructions: Optional[List[str]]
    mandatory_review_checkpoint: str
    human_approved: bool
    human_feedback: Optional[str]
    
    # Summary of key intelligence data for review
    company_overview: Optional[Dict[str, Any]] = None
    detected_pain_points: Optional[List[Dict[str, Any]]] = None
    service_mappings: Optional[List[Dict[str, Any]]] = None
    matched_internal_assets: Optional[List[Dict[str, Any]]] = None
    
    node_statuses: Optional[Dict[str, str]] = None
    errors: Optional[List[str]] = None


class HITLEventMessage(BaseModel):
    """
    WebSocket/Server-Sent-Events message for HITL updates during execution.
    """
    event_type: str  # "pause", "resume", "instruction_needed", "checkpoint_reached", "error"
    timestamp: str
    deal_id: str
    node_name: Optional[str] = None
    message: str
    current_state_snapshot: Optional[Dict[str, Any]] = None
    requires_action: bool = False


class WorkflowControlResponse(BaseModel):
    """
    Response from workflow control operations (pause, resume, dynamic instruction).
    """
    success: bool
    message: str
    current_step: Optional[str] = None
    execution_paused: bool
    action_timestamp: str
    next_actions: Optional[List[str]] = None
