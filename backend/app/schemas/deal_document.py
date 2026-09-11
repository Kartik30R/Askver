from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime

class DealDocumentResponse(BaseModel):
    id: UUID
    deal_id: UUID
    filename: str
    document_category: str
    file_type: str
    file_size_bytes: Optional[int]
    chunk_count: int
    indexing_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)