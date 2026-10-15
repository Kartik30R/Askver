import logging
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.deal import Deal
from app.db.models.meeting import Meeting
from app.repositories.meeting_repository import MeetingRepository

logger = logging.getLogger(__name__)


class MeetingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = MeetingRepository(db)

    async def create_meeting_for_deal(
        self,
        *,
        deal_id: UUID,
        owner_id: UUID,
        title: str,
        meeting_date: date,
        meeting_type: Optional[str] = None,
        attendees: Optional[str] = None,
        objectives: Optional[str] = None,
        notes: Optional[str] = None,
        transcript_text: Optional[str] = None,
        summary: Optional[str] = None,
    ) -> Meeting:
        deal = await self.db.get(Deal, deal_id)
        if deal is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
        if str(deal.owner_id) != str(owner_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this deal")

        if not title or not title.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Meeting title is required")
        if not meeting_date:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Meeting date is required")
        if not transcript_text or not transcript_text.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Meeting transcript is required")

        return await self.repo.create_meeting(
            deal_id=deal_id,
            owner_id=owner_id,
            title=title.strip(),
            meeting_date=meeting_date,
            meeting_type=meeting_type.strip() if meeting_type else None,
            attendees=attendees.strip() if attendees else None,
            objectives=objectives.strip() if objectives else None,
            notes=notes.strip() if notes else None,
            transcript_text=transcript_text.strip(),
            summary=summary.strip() if summary else None,
        )

    async def get_meeting(self, meeting_id: UUID, *, owner_id: UUID) -> Meeting:
        meeting = await self.repo.get_by_id(meeting_id)
        if not meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
        if str(meeting.owner_id) != str(owner_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this meeting")
        return meeting

    async def get_meeting_for_deal(self, deal_id: UUID, meeting_id: UUID, *, owner_id: UUID) -> Meeting:
        meeting = await self.repo.get_by_id(meeting_id)
        if not meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
        if str(meeting.deal_id) != str(deal_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting does not belong to this deal")
        if str(meeting.owner_id) != str(owner_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this meeting")
        return meeting

    async def list_meetings_for_deal(self, deal_id: UUID, *, owner_id: UUID, skip: int = 0, limit: int = 50):
        deal = await self.db.get(Deal, deal_id)
        if deal is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
        if str(deal.owner_id) != str(owner_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this deal")
        return await self.repo.list_for_deal(deal_id, skip=skip, limit=limit)

    async def list_meetings_for_owner(self, owner_id: UUID, *, skip: int = 0, limit: int = 50):
        return await self.repo.list_for_owner(owner_id, skip=skip, limit=limit)

    async def update_meeting_metadata(
        self,
        meeting: Meeting,
        *,
        title: Optional[str] = None,
        meeting_date: Optional[date] = None,
        meeting_type: Optional[str] = None,
        attendees: Optional[str] = None,
        objectives: Optional[str] = None,
        notes: Optional[str] = None,
        transcript_text: Optional[str] = None,
        summary: Optional[str] = None,
    ) -> Meeting:
        if title is not None and not title.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Meeting title is required")
        if meeting_date is not None and not meeting_date:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Meeting date is required")
        if transcript_text is not None and not transcript_text.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Meeting transcript is required")

        return await self.repo.update_meeting(
            meeting,
            title=title.strip() if title is not None else None,
            meeting_date=meeting_date,
            meeting_type=meeting_type.strip() if meeting_type is not None else None,
            attendees=attendees.strip() if attendees is not None else None,
            objectives=objectives.strip() if objectives is not None else None,
            notes=notes.strip() if notes is not None else None,
            transcript_text=transcript_text.strip() if transcript_text is not None else None,
            summary=summary.strip() if summary is not None else None,
        )
