import logging
from datetime import date
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meeting import Meeting

logger = logging.getLogger(__name__)


class MeetingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_meeting(
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
        transcript_text: str = "",
        summary: Optional[str] = None,
    ) -> Meeting:
        meeting = Meeting(
            deal_id=deal_id,
            owner_id=owner_id,
            title=title,
            meeting_date=meeting_date,
            meeting_type=meeting_type,
            attendees=attendees,
            objectives=objectives,
            notes=notes,
            transcript_text=transcript_text,
            summary=summary,
        )
        self.db.add(meeting)
        await self.db.commit()
        await self.db.refresh(meeting)
        logger.info("Created meeting %s for deal %s", meeting.id, deal_id)
        return meeting

    async def get_by_id(self, meeting_id: UUID) -> Optional[Meeting]:
        result = await self.db.execute(select(Meeting).where(Meeting.id == meeting_id))
        return result.scalar_one_or_none()

    async def list_for_deal(self, deal_id: UUID, *, skip: int = 0, limit: int = 50) -> List[Meeting]:
        result = await self.db.execute(
            select(Meeting)
            .where(Meeting.deal_id == deal_id)
            .order_by(desc(Meeting.meeting_date), desc(Meeting.created_at))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_for_owner(self, owner_id: UUID, *, skip: int = 0, limit: int = 50) -> List[Meeting]:
        result = await self.db.execute(
            select(Meeting)
            .where(Meeting.owner_id == owner_id)
            .order_by(desc(Meeting.meeting_date), desc(Meeting.created_at))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_meeting(
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
        if title is not None:
            meeting.title = title
        if meeting_date is not None:
            meeting.meeting_date = meeting_date
        if meeting_type is not None:
            meeting.meeting_type = meeting_type
        if attendees is not None:
            meeting.attendees = attendees
        if objectives is not None:
            meeting.objectives = objectives
        if notes is not None:
            meeting.notes = notes
        if transcript_text is not None:
            meeting.transcript_text = transcript_text
        if summary is not None:
            meeting.summary = summary

        await self.db.commit()
        await self.db.refresh(meeting)
        return meeting

    async def delete_meeting(self, meeting: Meeting) -> None:
        await self.db.delete(meeting)
        await self.db.commit()
