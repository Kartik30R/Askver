from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID

class ChatQueryRequest(BaseModel):
    question: str = Field(..., description="The user's question about the deal or client documents.")

class ChatQueryResponse(BaseModel):
    answer: str
    citations: List[str] = []

class ProposeEditRequest(BaseModel):
    instruction: str = Field(..., description="e.g., 'Rewrite the pitch to focus on AWS cloud migration'")

class ProposeEditResponse(BaseModel):
    proposed_diff_id: UUID = Field(..., description="Temporary ID for the proposed text diff")
    current_text: str
    proposed_text: str

class ApproveEditRequest(BaseModel):
    proposed_diff_id: UUID