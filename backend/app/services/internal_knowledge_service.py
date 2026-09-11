import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from langchain_core.documents import Document

from app.repositories.internal_knowledge_repository import InternalKnowledgeRepository
from app.schemas.internal_knowledge import InternalKnowledgeResponse
from app.services.vector_service import get_embeddings_model
from langchain_community.vectorstores import PGVector
import os

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/deal_db")


class InternalKnowledgeService:
    """
    Manages global company assets (case studies, whitepapers, accelerators)
    and handles their vector embeddings in PGVector.
    """
    def __init__(self, db: Session):
        self.db = db
        self.knowledge_repo = InternalKnowledgeRepository(db)

    def list_assets(self, skip: int = 0, limit: int = 100, category: Optional[str] = None):
        return self.knowledge_repo.get_all(skip=skip, limit=limit, category=category)

    def index_asset_text(self, title: str, content: str, asset_type: str, industry: Optional[str] = None):
        """
        Chunks and indexes raw internal asset text directly into the enterprise vector collection.
        """
        doc = Document(
            page_content=content,
            metadata={
                "title": title,
                "asset_type": asset_type,
                "industry": industry or "General"
            }
        )
        
        embeddings = get_embeddings_model()
        PGVector.from_documents(
            embedding=embeddings,
            documents=[doc],
            collection_name="internal_company_knowledgebase",
            connection_string=DATABASE_URL,
            pre_delete_collection=False
        )
        logger.info(f"Indexed internal asset '{title}' into global vector store.")