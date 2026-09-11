from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional

# Adjust the import path based on your project structure
from services import chat_service 

router = APIRouter(
    prefix="/deals/{deal_id}/chat",
    tags=["Deal Chat & Edits"]
)

# --- Pydantic Schemas ---

class ChatQueryRequest(BaseModel):
    query: str = Field(..., description="The user's question regarding the deal.")
    user_id: Optional[str] = None 

class ChatQueryResponse(BaseModel):
    deal_id: str
    answer: str

class EditProposalRequest(BaseModel):
    section_id: Optional[str] = Field(None, description="Specific section to edit, if applicable.")
    instructions: str = Field(..., description="Natural language instructions for the edit.")
    user_id: Optional[str] = None

class EditProposalResponse(BaseModel):
    deal_id: str
    proposed_text: str
    version_id: str
    status: str

# --- Endpoints ---

@router.post("/query", response_model=ChatQueryResponse)
async def ask_deal_query(deal_id: str, request: ChatQueryRequest):
    """
    Processes a natural language query about a specific deal.
    """
    try:
        answer = await chat_service.answer_deal_query(
            deal_id=deal_id,
            query=request.query
        )
        return ChatQueryResponse(deal_id=deal_id, answer=answer)
        
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process chat query.")

@router.post("/edit", response_model=EditProposalResponse)
async def propose_text_edit(deal_id: str, request: EditProposalRequest):
    """
    Proposes a versioned edit to the deal's text based on chat instructions.
    """
    try:
        # Assuming the service returns a dict or object with the new text and version details
        edit_result = await chat_service.propose_text_edit(
            deal_id=deal_id,
            instructions=request.instructions,
            section_id=request.section_id
        )
        
        return EditProposalResponse(
            deal_id=deal_id,
            proposed_text=edit_result.get("proposed_text", ""),
            version_id=edit_result.get("version_id", ""),
            status="proposal_created"
        )
        
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate text edit proposal.")