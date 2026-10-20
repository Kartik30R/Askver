"""
Schemas for Human-In-The-Loop (HITL) operations in the deal intelligence workflow.
"""
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class CheckpointStatus(str, Enum):
    """Status of mandatory review checkpoints."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class DynamicInstructionRequest(BaseModel):
    """
    Submits real-time steering instructions to update a node or set of nodes.
    These instructions are appended to the node's current LLM prompt context.
    """
    instructions: List[str] = Field(
        ..., 
        description="List of instructions to inject into the target node(s)"
    )
    apply_to_node: Optional[str] = Field(
        None,
        description="Specific node name to apply instructions to. Deprecated alias for target_nodes when only one node is selected."
    )
    target_nodes: Optional[List[str]] = Field(
        default=None,
        description="Specific node names that this instruction should apply to. If omitted, it applies to all nodes."
    )
    rerun_from_node: Optional[str] = Field(
        default=None,
        description="Resume the workflow from this node after injecting the instruction."
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
        description="Deprecated, ignored"
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
    deal_id: str
    current_step: Optional[str] = None
    execution_paused_at: Optional[str] = None
    last_execution_resumption: Optional[str] = None
    pause_requested: bool = False
    manual_pause_at_node: Optional[str] = None
    dynamic_instructions: Optional[List[Union[str, Dict[str, Any]]]] = None
    target_nodes: Optional[List[str]] = None
    rerun_from_node: Optional[str] = None
    mandatory_review_checkpoint: str = "pending"
    human_approved: bool = False
    human_feedback: Optional[str] = None
    target_company: Optional[str] = None
    target_industry: Optional[str] = None
    meeting_objective: Optional[str] = None
    research_depth: Optional[str] = None
    meeting_duration_minutes: Optional[int] = None
    research_plan: Optional[Dict[str, Any]] = None
    sources: Optional[Dict[str, Any]] = None
    facts: Optional[Dict[str, Any]] = None
    research_gaps: Optional[List[str]] = None
    financial_snapshot: Optional[Dict[str, Any]] = None
    strategic_frameworks: Optional[Dict[str, Any]] = None
    commercial_frameworks: Optional[Dict[str, Any]] = None
    evidence_report: Optional[Dict[str, Any]] = None
    insight_synthesis: Optional[Dict[str, Any]] = None
    verification_report: Optional[Dict[str, Any]] = None
    meeting_playbook: Optional[Dict[str, Any]] = None
    progress: Optional[Dict[str, Any]] = None
    markdown_export: Optional[str] = None

    priorities: Optional[List[Any]] = None
    detected_pain_points: Optional[List[Any]] = None
    service_mappings: Optional[List[Any]] = None
    matched_internal_assets: Optional[List[Any]] = None
    cxo_executive_brief: Optional[Dict[str, Any]] = None

    node_statuses: Optional[Dict[str, Any]] = None
    errors: Optional[List[Any]] = None

    @field_validator("dynamic_instructions", mode="before")
    @classmethod
    def normalize_dynamic_instructions(cls, value):
        if value is None:
            return None
        normalized = []
        for entry in value:
            if isinstance(entry, str):
                normalized.append(entry)
                continue
            if isinstance(entry, dict):
                text = entry.get("text") or entry.get("instruction") or entry.get("message")
                if text is None:
                    continue
                targets = entry.get("target_nodes") or entry.get("nodes") or entry.get("targets") or []
                if isinstance(targets, str):
                    targets = [targets]
                normalized.append({"text": str(text), "target_nodes": list(targets)})
                continue
            normalized.append(entry)
        return normalized

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
