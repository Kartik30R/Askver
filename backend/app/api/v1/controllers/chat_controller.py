from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.chat import (
    ApproveEditRequest,
    ApproveEditResponse,
    ChatQueryRequest,
    ChatQueryResponse,
    ProposeEditRequest,
    ProposeEditResponse,
)
from app.services.chat_service import ChatService

router = APIRouter(
    prefix="/deals/{deal_id}/chat",
    tags=["Deal Chat & Edits"],
)


@router.post("/query", response_model=ChatQueryResponse)
async def ask_deal_query(
    deal_id: UUID,
    request: ChatQueryRequest,
    db: AsyncSession = Depends(get_db),
):
    """Processes a natural language query about a specific deal or the current report."""
    try:
        service = ChatService(db)
        result = await service.answer_deal_query(deal_id=deal_id, question=request.question)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat query.",
        ) from exc


@router.post("/edit", response_model=ProposeEditResponse)
async def propose_text_edit(
    deal_id: UUID,
    request: ProposeEditRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generates a proposed revision for a specific report section or the full report."""
    try:
        service = ChatService(db)
        result = await service.propose_text_edit(
            deal_id=deal_id,
            instruction=request.instruction,
            section=request.section,
            current_text=request.current_text,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate text edit proposal.",
        ) from exc


@router.post("/approve", response_model=ApproveEditResponse)
async def approve_text_edit(
    deal_id: UUID,
    request: ApproveEditRequest,
    db: AsyncSession = Depends(get_db),
):
    """Accepts or rejects a proposed text edit for the deal and stores the human decision."""
    try:
        service = ChatService(db)
        result = await service.approve_text_edit(
            deal_id=deal_id,
            proposed_diff_id=request.proposed_diff_id,
            approved=request.approved,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process edit approval.",
        ) from exc