import logging
from typing import Optional

from langchain_core.documents import Document
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.internal_knowledge_repository import InternalKnowledgeRepository
from app.services.vector_service import index_internal_knowledge_chunks

logger = logging.getLogger(__name__)


class InternalKnowledgeService:
    """
    Manages global company assets (case studies, whitepapers, accelerators)
    and handles their vector embeddings in PGVector.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.knowledge_repo = InternalKnowledgeRepository(db)

    async def list_assets(self, skip: int = 0, limit: int = 100, category: Optional[str] = None):
        return await self.knowledge_repo.get_all(skip=skip, limit=limit, asset_type=category)

    async def index_asset_text(self, title: str, content: str, asset_type: str, industry: Optional[str] = None):
        """Chunks and indexes raw internal asset text directly into the enterprise vector collection."""
        doc = Document(
            page_content=content,
            metadata={
                "title": title,
                "asset_type": asset_type,
                "industry": industry or "General",
            },
        )

        chunks = [
            Document(
                page_content=doc.page_content,
                metadata={**doc.metadata, "source": f"internal_asset::{title}"},
            )
        ]

        await index_internal_knowledge_chunks(
            "internal_company_knowledgebase",
            chunks,
            pre_delete_collection=False,
        )
        logger.info("Indexed internal asset '%s' into global vector store.", title)