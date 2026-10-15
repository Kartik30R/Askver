from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.db.models.user import User
from app.schemas.deal_analytics import DealAnalyticsResult
from app.schemas.meeting_analysis import MeetingAnalysisResult
from app.services.meeting_analytics_service import MeetingAnalyticsService

router = APIRouter(prefix="/deals/{deal_id}/analytics", tags=["Meeting Analytics"])


@router.get("/meetings/{meeting_id}", response_model=MeetingAnalysisResult)
async def get_meeting_analysis(
    deal_id: UUID,
    meeting_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = MeetingAnalyticsService(db)
    try:
        return await service.get_meeting_analysis(deal_id=deal_id, meeting_id=meeting_id, owner_id=current_user.id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/meetings/{meeting_id}/run", response_model=MeetingAnalysisResult)
async def rerun_meeting_analysis(
    deal_id: UUID,
    meeting_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = MeetingAnalyticsService(db)
    try:
        return await service.analyze_meeting(deal_id=deal_id, meeting_id=meeting_id, owner_id=current_user.id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/deal", response_model=DealAnalyticsResult)
async def get_deal_analytics(
    deal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = MeetingAnalyticsService(db)
    try:
        return await service.get_deal_analysis(deal_id=deal_id, owner_id=current_user.id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/deal/run", response_model=DealAnalyticsResult)
async def rerun_deal_analytics(
    deal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = MeetingAnalyticsService(db)
    try:
        return await service.analyze_deal(deal_id=deal_id, owner_id=current_user.id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
