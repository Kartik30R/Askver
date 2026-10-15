from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MeetingCreate(BaseModel):
    title: str
    deal_id: UUID
    meeting_date: date
    meeting_type: Optional[str] = None
    attendees: Optional[str] = None
    objectives: Optional[str] = None
    notes: Optional[str] = None
    transcript_text: str
    summary: Optional[str] = None


class MeetingUpdate(BaseModel):
    title: Optional[str] = None
    meeting_date: Optional[date] = None
    meeting_type: Optional[str] = None
    attendees: Optional[str] = None
    objectives: Optional[str] = None
    notes: Optional[str] = None
    transcript_text: Optional[str] = None
    summary: Optional[str] = None


class MeetingResponse(BaseModel):
    id: UUID
    deal_id: UUID
    owner_id: UUID
    title: str
    meeting_date: date
    meeting_type: Optional[str] = None
    attendees: Optional[str] = None
    objectives: Optional[str] = None
    notes: Optional[str] = None
    transcript_text: str
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
