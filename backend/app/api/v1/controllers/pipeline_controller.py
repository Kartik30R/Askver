import logging
from uuid import UUID
from typing import Optional, Dict, Any
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Import SessionLocal (or your session maker) to create isolated background DB sessions
from app.api.deps import get_current_user
from app.core.database import get_db, SessionLocal 
from app.db.models.user import User
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


def ensure_deal_owned_by_user(deal, current_user: User) -> None:
    if not deal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
    if deal.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this deal")

# ============================================================================
# BACKGROUND WORKER
# ============================================================================

async def run_pipeline_background(
    deal_id: UUID,
    thread_id: Optional[str],
    research_depth: Optional[str] = None,
    meeting_duration_minutes: Optional[int] = None,
):
    """Background worker with an independent DB session lifecycle."""
    async with SessionLocal() as db:
        try:
            deal_service = DealService(db)
            await deal_service.run_deal_intelligence_workflow(
                deal_id=deal_id,
                thread_id=thread_id,
                research_depth=research_depth,
                meeting_duration_minutes=meeting_duration_minutes,
            )
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
    research_depth: Optional[str] = None,
    meeting_duration_minutes: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Starts or resumes the LangGraph agent state machine (Nodes 1–6).
    """
    deal_service = DealService(db)

    deal = await deal_service.get_deal(deal_id)
    ensure_deal_owned_by_user(deal, current_user)
    if deal.status in ("RUNNING", "PAUSE_REQUESTED", "AWAITING_REVIEW"):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Pipeline is {deal.status}")
    await deal_service.deal_repo.update_deal_status(deal_id, "RUNNING")   # claim it before queuing
    background_tasks.add_task(
        run_pipeline_background,
        deal_id,
        None,
        research_depth,
        meeting_duration_minutes,
    )
    return PipelineTriggerResponse(
        status="processing",
        message=f"Pipeline execution queued for deal {deal_id}.",
        thread_id=thread_id,
    )


@router.get("/status", response_model=PipelineStatusResponse)
async def get_pipeline_status(
    deal_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Checks the current execution status (RUNNING, PAUSED_FOR_HUMAN_REVIEW, COMPLETED, FAILED).
    """
    deal_service = DealService(db)
    deal = await deal_service.deal_repo.get_deal_by_id(deal_id)
    ensure_deal_owned_by_user(deal, current_user)

    return PipelineStatusResponse(deal_id=deal.id, status=deal.status)


@router.get("/state", response_model=WorkflowStateSnapshot)
async def get_pipeline_state(
    deal_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkflowStateSnapshot:
    """
    Returns the accumulated state snapshot for frontend review during the HITL pause.
    """
    deal_service = DealService(db)
    deal = await deal_service.get_deal(deal_id)
    ensure_deal_owned_by_user(deal, current_user)
    context = await deal_service.get_deal_context(deal_id)
    if not context:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")

    mapped = DealService.map_state_to_api_response(context.get("active_state") or {})
    return WorkflowStateSnapshot.model_validate(mapped)

@router.post("/human-approval")          # legacy: same path
async def submit_human_approval(
    deal_id: UUID,
    approval_request: HumanApprovalRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deal_service = DealService(db)
    deal = await deal_service.get_deal(deal_id)
    ensure_deal_owned_by_user(deal, current_user)
    req = MandatoryReviewApprovalRequest(
        checkpoint_status=CheckpointStatus.APPROVED if approval_request.approved else CheckpointStatus.NEEDS_REVISION,
        feedback=approval_request.feedback,
        custom_selected_assets=approval_request.custom_selected_assets,
    )
    return await submit_mandatory_review_approval(deal_id, req, background_tasks, db, current_user=current_user)

# ============================================================================
# NEW HITL ENDPOINTS: Dynamic Steering, Pause/Resume, Mandatory Review
# ============================================================================

@router.post("/hitl/dynamic-instruction")
async def submit_dynamic_instruction(
    deal_id: UUID,
    instruction_request: DynamicInstructionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    deal_service = DealService(db)
    deal = await deal_service.get_deal(deal_id)
    ensure_deal_owned_by_user(deal, current_user)
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    deal_service = DealService(db)
    deal = await deal_service.get_deal(deal_id)
    ensure_deal_owned_by_user(deal, current_user)
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    deal_service = DealService(db)
    deal = await deal_service.get_deal(deal_id)
    ensure_deal_owned_by_user(deal, current_user)
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    deal_service = DealService(db)
    deal = await deal_service.get_deal(deal_id)
    ensure_deal_owned_by_user(deal, current_user)
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    deal_service = DealService(db)
    deal = await deal_service.get_deal(deal_id)
    ensure_deal_owned_by_user(deal, current_user)
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
