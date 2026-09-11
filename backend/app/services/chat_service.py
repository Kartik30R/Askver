import logging
import uuid
from typing import List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.deal_document_repository import DealDocumentRepository
from app.repositories.deal_intelligence_repository import DealIntelligenceRepository
from app.schemas.chat import ChatQueryResponse, ProposeEditResponse
from app.services.vector_service import query_client_deal_docs

logger = logging.getLogger(__name__)


class ChatService:
    """
    Handles RAG-based deal Q&A against ingested documents 
    and generates AI-assisted text diff proposals for sales pitches.
    """
    def __init__(self, db: Session):
        self.db = db
        self.doc_repo = DealDocumentRepository(db)
        self.intel_repo = DealIntelligenceRepository(db)

    async def answer_deal_query(self, deal_id: UUID, question: str) -> ChatQueryResponse:
        """
        Executes hybrid vector retrieval across deal documents and global knowledge,
        passing context to Gemini to construct a grounded response with citations.
        """
        vector_collection_name = f"deal_{deal_id}"
        
        # 1. Retrieve top-k context chunks from PGVector
        retrieved_chunks = await self._query_vector_store(
            collection_name=vector_collection_name, 
            query_text=question, 
            top_k=4
        )
        
        # 2. Extract context and source citations
        context_text = "\n\n".join([chunk["content"] for chunk in retrieved_chunks])
        citations = [chunk["source_file"] for chunk in retrieved_chunks if "source_file" in chunk]

        # 3. Call LLM for RAG synthesis
        prompt = f"""
        Answer the following question using ONLY the provided context below.
        If the answer cannot be found in the context, state that clearly.

        Context:
        {context_text}

        Question: {question}
        """
        
        answer = await self._call_llm(prompt)

        return ChatQueryResponse(
            answer=answer,
            citations=list(set(citations))
        )

    async def propose_text_edit(
        self, 
        deal_id: UUID, 
        current_text: str, 
        instruction: str
    ) -> ProposeEditResponse:
        """
        Takes existing generated section content (e.g., solution pitch or scope)
        and streams an edited version matching human feedback.
        """
        prompt = f"""
        You are an expert sales strategist. Rewrite the original text based on the instruction.

        Original Text:
        {current_text}

        Instruction:
        {instruction}

        Provide ONLY the rewritten text without explanations or headers.
        """
        
        proposed_text = await self._call_llm(prompt)
        proposed_diff_id = uuid.uuid4()

        return ProposeEditResponse(
            proposed_diff_id=proposed_diff_id,
            current_text=current_text,
            proposed_text=proposed_text
        )

    async def _query_vector_store(
        self, 
        collection_name: str, 
        query_text: str, 
        top_k: int = 4
    ) -> List[Dict[str, Any]]:
        """Placeholder for PGVector collection retrieval."""
        logger.info(f"Querying vector collection '{collection_name}' for query: '{query_text}'")
        deal_id = collection_name.replace("deal_", "")
        return query_client_deal_docs(deal_id=deal_id, query=query_text, top_k=top_k)

    async def _call_llm(self, prompt: str) -> str:
        """Placeholder for Gemini LLM invocation."""
        return "This is an AI-generated synthesis based on your deal context and guidelines."