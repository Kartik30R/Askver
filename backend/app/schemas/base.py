from pydantic import BaseModel, Field
from typing import List, Optional

class SourceCitation(BaseModel):
    title: str = Field(description="Title of the source document or web article")
    url: Optional[str] = Field(default=None, description="URL if sourced from public web")
    snippet: str = Field(description="Relevant text excerpt or quote from the source")
    source_type: str = Field(description="e.g., 'WEB_NEWS', '10K_FILING', 'INTERNAL_CASE_STUDY', 'CLIENT_RFP'")

class DetailedPoint(BaseModel):
    headline: str = Field(description="Concise summary bullet point")
    detailed_narrative: str = Field(description="Expanded paragraph explaining the bullet point in detail")
    citations: List[SourceCitation] = Field(default_factory=list, description="Source references")