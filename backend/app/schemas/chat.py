from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID

class ChatQueryRequest(BaseModel):
    question: str = Field(..., description="The user's question about the deal or client documents.")

class ChatQueryResponse(BaseModel):
    deal_id: str
    answer: str
    citations: List[str] = Field(default_factory=list)

class ProposeEditRequest(BaseModel):
    section: Optional[str] = Field(None, description="Target workflow section or node, e.g. financial_intelligence or cxo_executive_brief")
    instruction: str = Field(..., description="e.g., 'Rewrite the pitch to focus on AWS cloud migration'")
    current_text: Optional[str] = Field(None, description="Optional source text if caller wants to edit a specific section text")

class ProposeEditResponse(BaseModel):
    deal_id: str
    section: Optional[str] = None
    proposed_diff_id: UUID = Field(..., description="Temporary ID for the proposed text diff")
    current_text: str
    proposed_text: str
    status: str = "proposal_created"

class ApproveEditRequest(BaseModel):
    proposed_diff_id: UUID
    approved: bool = True