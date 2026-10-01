from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class InternalKnowledgeCreate(BaseModel):
    title: str
    asset_type: str  # CASE_STUDY, PROPOSAL, SOW, SUCCESS_STORY, PRESENTATION, SOLUTION_ACCELERATOR
    file_path: str
    file_type: str
    industry_tag: Optional[str] = None
    technology_tags: Optional[List[str]] = None
    summary: Optional[str] = None
    vector_doc_id: Optional[str] = None
    indexing_status: str = "INDEXED"


class InternalKnowledgeUpdate(BaseModel):
    title: Optional[str] = None
    asset_type: Optional[str] = None
    industry_tag: Optional[str] = None
    technology_tags: Optional[List[str]] = None
    file_path: Optional[str] = None
    file_type: Optional[str] = None
    summary: Optional[str] = None
    vector_doc_id: Optional[str] = None
    indexing_status: Optional[str] = None


class InternalKnowledgeResponse(BaseModel):
    id: UUID
    title: str
    asset_type: str
    industry_tag: Optional[str] = None
    technology_tags: Optional[List[str]] = None
    file_path: str
    file_type: str
    summary: Optional[str] = None
    vector_doc_id: Optional[str] = None
    indexing_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)