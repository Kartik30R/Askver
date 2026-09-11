from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime

class DealCreate(BaseModel):
    title: str
    target_company: str
    target_industry: str
    meeting_objective: str

class DealResponse(BaseModel):
    id: UUID
    title: str
    target_company: str
    target_industry: str
    meeting_objective: str
    status: str
    owner_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)