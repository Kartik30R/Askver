from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class InternalKnowledgeResponse(BaseModel):
    id: UUID
    title: str
    asset_type: str
    industry_tag: Optional[str]
    technology_tags: Optional[List[str]]
    indexing_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
    