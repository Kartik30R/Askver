import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.deal_document import DealDocument

logger = logging.getLogger(__name__)


class DealDocumentRepository:
    """
    Manages metadata and indexing status for client documents (RFPs, BRDs)
    associated with specific deals.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_document_record(
        self,
        deal_id: UUID,
        filename: str,
        file_path: str,
        file_type: str,
        document_category: str,
        vector_collection_name: str,
        file_size_bytes: Optional[int] = None,
    ) -> DealDocument:
        """Registers a newly uploaded document before chunking begins."""
        document = DealDocument(
            deal_id=deal_id,
            filename=filename,
            file_path=file_path,
            file_type=file_type,
            document_category=document_category,
            file_size_bytes=file_size_bytes,
            vector_collection_name=vector_collection_name,
            indexing_status="PENDING",
            chunk_count=0,
        )
        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)
        return document

    async def get_deal_documents(self, deal_id: UUID) -> List[DealDocument]:
        """Retrieves all documents associated with a specific deal."""
        result = await self.db.execute(select(DealDocument).where(DealDocument.deal_id == deal_id))
        return list(result.scalars().all())

    async def update_indexing_status(
        self,
        document_id: UUID,
        status: str,
        chunk_count: int = 0,
    ) -> Optional[DealDocument]:
        """Updates the status and total chunk count after PGVector insertion."""
        result = await self.db.execute(select(DealDocument).where(DealDocument.id == document_id))
        document = result.scalar_one_or_none()
        if document:
            document.indexing_status = status
            document.chunk_count = chunk_count
            await self.db.commit()
            await self.db.refresh(document)
            logger.info(f"Document '{document_id}' status updated to '{status}' with {chunk_count} chunks.")
        return document