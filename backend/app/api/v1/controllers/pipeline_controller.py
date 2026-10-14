import logging
from uuid import UUID
from typing import Optional, Dict, Any
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Import SessionLocal (or your session maker) to create isolated background DB sessions
from app.core.database import get_db, SessionLocal 
from app.services.deal_service import DealService
from app.services.hitl_manager import HITLManager, InvalidWorkflowState
from app.schemas.deal_intelligence import (
    HumanApprovalRequest,
    PipelineStatusResponse,
    PipelineTriggerResponse,
)
from app.schemas.hitl import (
    CheckpointStatus,
    DynamicInstructionRequest,
    ManualPauseRequest,
    ManualResumeRequest,
    MandatoryReviewApprovalRequest,
    WorkflowStateSnapshot,
)

router = APIRouter(prefix="/deals/{deal_id}/pipeline", tags=["Pipeline & HITL"])

# ============================================================================
# BACKGROUND WORKER
# ============================================================================

async def run_pipeline_background(deal_id: UUID, thread_id: Optional[str]):
    """Background worker with an independent DB session lifecycle."""
    async with SessionLocal() as db:
        try:
            deal_service = DealService(db)
            await deal_service.run_deal_intelligence_workflow(deal_id=deal_id, thread_id=thread_id)
        except Exception:
            logger.exception("Background pipeline execution failed for deal %s", deal_id)


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/trigger", status_code=status.HTTP_202_ACCEPTED, response_model=PipelineTriggerResponse)
async def trigger_pipeline(
    deal_id: UUID,
    background_tasks: BackgroundTasks,
    thread_id: Optional[str] = None, 
    db: AsyncSession = Depends(get_db)
):
    """
    Starts or resumes the LangGraph agent state machine (Nodes 1–6).
    """
    deal_service = DealService(db)

    deal = await deal_service.get_deal(deal_id)
    if not deal:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deal not found")
    if deal.status in ("RUNNING", "PAUSE_REQUESTED", "AWAITING_REVIEW"):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Pipeline is {deal.status}")
    await deal_service.deal_repo.update_deal_status(deal_id, "RUNNING")   # claim it before queuing
    background_tasks.add_task(run_pipeline_background, deal_id, None)
    return PipelineTriggerResponse(
        status="processing",
        message=f"Pipeline execution queued for deal {deal_id}.",
        thread_id=thread_id,
    )


@router.get("/status", response_model=PipelineStatusResponse)
async def get_pipeline_status(deal_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Checks the current execution status (RUNNING, PAUSED_FOR_HUMAN_REVIEW, COMPLETED, FAILED).
    """
    deal_service = DealService(db)
    deal = await deal_service.deal_repo.get_deal_by_id(deal_id)
    if not deal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")

    return PipelineStatusResponse(deal_id=deal.id, status=deal.status)


@router.get("/state", response_model=WorkflowStateSnapshot)
async def get_pipeline_state(deal_id: UUID, db: AsyncSession = Depends(get_db)) -> WorkflowStateSnapshot:
    """
    Returns the accumulated state snapshot for frontend review during the HITL pause.
    """
    deal_service = DealService(db)
    deal = await deal_service.get_deal(deal_id)
    context = await deal_service.get_deal_context(deal_id)
    if not context:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")

    active_state = context.get("active_state") or {}
    ps = active_state.get("priorities_and_pain_points") or {}
    if not isinstance(ps, dict):
        ps = {}
    normalized_state = {
        "deal_id": str(deal_id),
        "current_step": active_state.get("current_step"),
        "execution_paused_at": active_state.get("execution_paused_at"),
        "last_execution_resumption": active_state.get("last_execution_resumption"),
        "pause_requested": bool(active_state.get("pause_requested", False)),
        "manual_pause_at_node": active_state.get("manual_pause_at_node"),
        "dynamic_instructions": active_state.get("dynamic_instructions"),
        "mandatory_review_checkpoint": active_state.get("mandatory_review_checkpoint", "pending"),
        "human_approved": bool(active_state.get("human_approved", False)),
        "human_feedback": active_state.get("human_feedback"),
        "target_company": active_state.get("target_company") or (deal.target_company if deal else None),
        "target_industry": active_state.get("target_industry") or (deal.target_industry if deal else None),
        "meeting_objective": active_state.get("meeting_objective") or (deal.meeting_objective if deal else None),
        "company_overview": active_state.get("company_research"),
        "financial_intelligence": active_state.get("financial_intelligence"),
        "stakeholder_intelligence": active_state.get("stakeholder_intelligence"),
        "industry_analysis": active_state.get("industry_analysis"),
        "priorities": ps.get("priorities") or [],
        "detected_pain_points": ps.get("pain_points") or [],
        "service_mappings": active_state.get("service_mappings") or [],
        "matched_internal_assets": active_state.get("matched_internal_assets") or [],
        "cxo_executive_brief": active_state.get("cxo_executive_brief") or None,
        "node_statuses": active_state.get("node_statuses") or {},
        "errors": active_state.get("errors"),
    }
    return WorkflowStateSnapshot.model_validate(normalized_state)

@router.post("/human-approval")          # legacy: same path
async def submit_human_approval(
    deal_id: UUID, approval_request: HumanApprovalRequest,
    background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db),
):
    req = MandatoryReviewApprovalRequest(
        checkpoint_status=CheckpointStatus.APPROVED if approval_request.approved else CheckpointStatus.NEEDS_REVISION,
        feedback=approval_request.feedback,
        custom_selected_assets=approval_request.custom_selected_assets,
    )
    return await submit_mandatory_review_approval(deal_id, req, background_tasks, db)

# ============================================================================
# NEW HITL ENDPOINTS: Dynamic Steering, Pause/Resume, Mandatory Review
# ============================================================================

@router.post("/hitl/dynamic-instruction")
async def submit_dynamic_instruction(
    deal_id: UUID,
    instruction_request: DynamicInstructionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    DYNAMIC STEERING: Submits real-time instruction guidance to the active node.
    
    The executing node will append these instructions to its LLM prompt context
    and incorporate them into analysis WITHOUT pausing the workflow.
    
    Example:
        POST /deals/{deal_id}/pipeline/hitl/dynamic-instruction
        {
            "instructions": [
                "Focus on recent AI investments and cloud migration initiatives",
                "Prioritize the semiconductor fabrication division in your analysis"
            ],
            "apply_to_node": null,  // Applies to current node
            "priority": 5
        }
    """
    hitl_manager = HITLManager(db)
    try:
        result = await hitl_manager.submit_dynamic_instruction(deal_id, instruction_request)
        if result.get("should_run"):
            if instruction_request.rerun_from_node:
                deal_service = DealService(db)
                await deal_service.run_pipeline_from_node(deal_id, instruction_request.rerun_from_node)
            else:
                background_tasks.add_task(run_pipeline_background, deal_id, None)
        return result
    except InvalidWorkflowState as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit dynamic instruction: {str(e)}"
        )


@router.post("/hitl/pause")
async def request_manual_pause(
    deal_id: UUID,
    pause_request: ManualPauseRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    MANUAL PAUSE: Requests workflow pause at the next node boundary.
    
    Workflow will complete current node and halt before the next node begins.
    User can then submit instructions and click resume.
    
    Example:
        POST /deals/{deal_id}/pipeline/hitl/pause
        {
            "reason": "CEO requested to review identified pain points before proceeding"
        }
    """
    hitl_manager = HITLManager(db)
    try:
        result = await hitl_manager.request_manual_pause(deal_id, pause_request)
        return result
    except InvalidWorkflowState as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to request pause: {str(e)}"
        )


@router.post("/hitl/resume")
async def resume_workflow_after_pause(
    deal_id: UUID,
    resume_request: ManualResumeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    MANUAL RESUME: Resumes workflow execution after manual pause.
    
    Optionally applies new instructions before resuming.
    
    Example:
        POST /deals/{deal_id}/pipeline/hitl/resume
        {
            "instructions": [
                "Include the 3 modernized pain point analyses in the brief",
                "De-prioritize the legacy system migration for this meeting"
            ],
            "feedback": "Good analysis on digital initiatives. Proceed."
        }
    """
    hitl_manager = HITLManager(db)
    try:
        result = await hitl_manager.resume_workflow_after_pause(deal_id, resume_request)
        if result.get("should_run"):
            background_tasks.add_task(run_pipeline_background, deal_id, None)
        return result
    except InvalidWorkflowState as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume workflow: {str(e)}"
        )


@router.post("/hitl/mandatory-review/approve")
async def submit_mandatory_review_approval(
    deal_id: UUID,
    approval_request: MandatoryReviewApprovalRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    MANDATORY REVIEW GATE: Submits approval/modifications for final brief review.
    
    Workflow always pauses before CXO brief generation to allow human review.
    User can approve, reject, or request revision of the briefing materials.
    
    Example (Approve):
        POST /deals/{deal_id}/pipeline/hitl/mandatory-review/approve
        {
            "checkpoint_status": "approved",
            "feedback": "Executive brief looks comprehensive.",
            "custom_selected_assets": ["asset_001", "asset_003"],
            "executive_brief_modifications": {
                "executive_summary": "Updated summary text...",
                "talking_points": ["Updated point 1", "Updated point 2"]
            }
        }
    
    Example (Request Revision):
        {
            "checkpoint_status": "needs_revision",
            "feedback": "Please strengthen the cloud modernization section",
            "custom_selected_assets": null,
            "executive_brief_modifications": null
        }
    """
    hitl_manager = HITLManager(db)
    try:
        result = await hitl_manager.submit_mandatory_review_approval(deal_id, approval_request)
        if result.get("should_run"):
            background_tasks.add_task(run_pipeline_background, deal_id, None)
        return result
    except InvalidWorkflowState as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit review approval: {str(e)}"
        )


@router.get("/hitl/checkpoint-state")
async def get_checkpoint_state(
    deal_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    WORKFLOW STATE FOR REVIEW: Returns current workflow state at HITL checkpoints.
    
    Provides all relevant intelligence data and control state for human review.
    Useful for UI to display current pause point and available actions.
    
    Returns:
        {
            "deal_id": "...",
            "current_step": "MANDATORY_REVIEW_CHECKPOINT",
            "execution_paused_at": "2026-09-14T10:30:00Z",
            "pause_requested": false,
            "dynamic_instructions": [...],
            "mandatory_review_checkpoint": "pending",
            "available_assets": 12,
            "available_service_mappings": 8,
            "node_statuses": {...},
            ...
        }
    """
    hitl_manager = HITLManager(db)
    try:
        state = await hitl_manager.get_workflow_checkpoint_state(deal_id)
        return state
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve checkpoint state: {str(e)}"
        )


# ============================================================================
# EXECUTION HISTORY & CHECKPOINTING ENDPOINTS (PostgreSQL Persistence)
# ============================================================================

@router.get("/execution/history")
async def get_execution_timeline(deal_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get all execution versions/runs for this deal with their checkpoints."""
    deal_service = DealService(db)
    try:
        return await deal_service.get_execution_timeline(deal_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/execution/checkpoints/{thread_id}")
async def get_thread_history(
    deal_id: UUID,
    thread_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all checkpoints in a specific execution thread."""
    deal_service = DealService(db)
    try:
        return await deal_service.get_thread_history(deal_id, thread_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/execution/checkpoint/{checkpoint_id}")
async def get_checkpoint_state_detail(
    deal_id: UUID,
    checkpoint_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get full state snapshot at a specific checkpoint."""
    deal_service = DealService(db)
    from app.services.execution_history_service import ExecutionHistoryService
    history_service = ExecutionHistoryService(db)
    try:
        state = await history_service.get_checkpoint_state(deal_id, checkpoint_id)
        if not state:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checkpoint not found")
        return state
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/execution/checkpoint/{checkpoint_id}/resume")
async def resume_from_checkpoint(
    deal_id: UUID,
    checkpoint_id: str,
    thread_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Resume workflow from a specific past checkpoint."""
    deal_service = DealService(db)
    try:
        result = await deal_service.resume_from_checkpoint(
            deal_id=deal_id,
            checkpoint_id=checkpoint_id,
            thread_id=thread_id
        )
        return {
            "success": True,
            "message": "Workflow resumed from checkpoint",
            "result": result
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume from checkpoint: {str(e)}"
        )