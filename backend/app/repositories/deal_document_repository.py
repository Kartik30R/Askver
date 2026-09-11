import logging
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.db.models.deal_document import DealDocument

logger = logging.getLogger(__name__)


class DealDocumentRepository:
    """
    Manages metadata and indexing status for client documents (RFPs, BRDs) 
    associated with specific deals.
    """
    def __init__(self, db: Session):
        self.db = db

    def create_document_record(
        self,
        deal_id: UUID,
        filename: str,
        file_path: str,
        file_type: str,
        document_category: str,
        vector_collection_name: str,
        file_size_bytes: Optional[int] = None
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
            chunk_count=0
        )
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def get_deal_documents(self, deal_id: UUID) -> List[DealDocument]:
        """Retrieves all documents associated with a specific deal."""
        return (
            self.db.query(DealDocument)
            .filter(DealDocument.deal_id == deal_id)
            .all()
        )

    def update_indexing_status(
        self, 
        document_id: UUID, 
        status: str, 
        chunk_count: int = 0
    ) -> Optional[DealDocument]:
        """Updates the status (e.g., PROCESSING, INDEXED) and total chunk count after PGVector insertion."""
        document = self.db.query(DealDocument).filter(DealDocument.id == document_id).first()
        if document:
            document.indexing_status = status
            document.chunk_count = chunk_count
            self.db.commit()
            self.db.refresh(document)
            logger.info(f"Document '{document_id}' status updated to '{status}' with {chunk_count} chunks.")
        return document