from uuid import UUID
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.deal_service import DealService
from app.schemas.deal_intelligence import HumanApprovalRequest

router = APIRouter(prefix="/deals/{deal_id}/pipeline", tags=["Pipeline & HITL"])


@router.post("/trigger")
async def trigger_pipeline(
    deal_id: UUID, 
    thread_id: Optional[str] = None, 
    db: Session = Depends(get_db)
):
    """
    Starts or resumes the LangGraph agent state machine (Nodes 1–6).
    """
    deal_service = DealService(db)
    try:
        result = await deal_service.run_deal_intelligence_workflow(
            deal_id=deal_id, 
            thread_id=thread_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Pipeline execution failed: {str(e)}")


@router.get("/status")
def get_pipeline_status(deal_id: UUID, db: Session = Depends(get_db)):
    """
    Checks the current execution status (RUNNING, PAUSED_FOR_HUMAN_REVIEW, COMPLETED, FAILED).
    """
    deal_service = DealService(db)
    deal = deal_service.deal_repo.get_deal_by_id(deal_id)
    if not deal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
    
    return {
        "deal_id": deal.id,
        "status": deal.status
    }


@router.get("/state")
def get_pipeline_state(deal_id: UUID, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Returns the accumulated state dictionary for frontend review during the HITL pause.
    """
    deal_service = DealService(db)
    context = deal_service.get_deal_context(deal_id)
    if not context:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
    
    return context.get("active_state", {})


@router.post("/human-approval")
async def submit_human_approval(
    deal_id: UUID, 
    approval_request: HumanApprovalRequest, 
    db: Session = Depends(get_db)
):
    """
    Submits user edits/feedback on asset mappings and resumes execution to Nodes 7–8.
    """
    deal_service = DealService(db)
    try:
        result = await deal_service.submit_human_approval(
            deal_id=deal_id, 
            approval_request=approval_request
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to resume pipeline: {str(e)}")