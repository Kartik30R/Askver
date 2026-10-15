from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_user
from app.core.database import get_db
from app.db.models.user import User
from app.schemas.meeting import MeetingCreate, MeetingResponse, MeetingUpdate
from app.services.meeting_service import MeetingService

router = APIRouter(prefix="/meetings", tags=["Meetings"])


@router.get("", response_model=list[MeetingResponse])
async def list_my_meetings(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    service = MeetingService(db)
    meetings = await service.list_meetings_for_owner(current_user.id, skip=skip, limit=limit)
    return [MeetingResponse.model_validate(meeting) for meeting in meetings]


@router.get("/deal/{deal_id}", response_model=list[MeetingResponse])
async def list_meetings_for_deal(
    deal_id: UUID,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    service = MeetingService(db)
    meetings = await service.list_meetings_for_deal(deal_id, owner_id=current_user.id, skip=skip, limit=limit)
    return [MeetingResponse.model_validate(meeting) for meeting in meetings]


@router.post("", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    payload: MeetingCreate,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    service = MeetingService(db)
    meeting = await service.create_meeting_for_deal(
        deal_id=payload.deal_id,
        owner_id=current_user.id,
        title=payload.title,
        meeting_date=payload.meeting_date,
        meeting_type=payload.meeting_type,
        attendees=payload.attendees,
        objectives=payload.objectives,
        notes=payload.notes,
        transcript_text=payload.transcript_text,
        summary=payload.summary,
    )
    return MeetingResponse.model_validate(meeting)


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting_id: UUID,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    service = MeetingService(db)
    meeting = await service.get_meeting(meeting_id, owner_id=current_user.id)
    return MeetingResponse.model_validate(meeting)


@router.patch("/{meeting_id}", response_model=MeetingResponse)
async def update_meeting(
    meeting_id: UUID,
    payload: MeetingUpdate,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    service = MeetingService(db)
    meeting = await service.get_meeting(meeting_id, owner_id=current_user.id)
    updated = await service.update_meeting_metadata(
        meeting,
        title=payload.title,
        meeting_date=payload.meeting_date,
        meeting_type=payload.meeting_type,
        attendees=payload.attendees,
        objectives=payload.objectives,
        notes=payload.notes,
        transcript_text=payload.transcript_text,
        summary=payload.summary,
    )
    return MeetingResponse.model_validate(updated)


@router.delete("/{meeting_id}")
async def delete_meeting(
    meeting_id: UUID,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    service = MeetingService(db)
    meeting = await service.get_meeting(meeting_id, owner_id=current_user.id)
    await db.delete(meeting)
    await db.commit()
    return {"status": "success", "message": "Meeting deleted"}
