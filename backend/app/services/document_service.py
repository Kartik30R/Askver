import logging
import os
from uuid import UUID
from typing import List
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.repositories.deal_document_repository import DealDocumentRepository
from app.services.document_parser import parse_and_chunk_document
from app.services.vector_service import index_client_deal_chunks
from backend.app.db.models.deal_document import DealDocument

logger = logging.getLogger(__name__)

UPLOAD_DIR = "storage/uploads"


class DocumentService:
    """
    Handles file storage, parsing, vector embedding generation, 
    and document indexing state for client RFPs and BRDs.
    """
    def __init__(self, db: Session):
        self.db = db
        self.doc_repo = DealDocumentRepository(db)
        os.makedirs(UPLOAD_DIR, exist_ok=True)

    async def upload_and_process_document(
        self, 
        deal_id: UUID, 
        file: UploadFile, 
        document_category: str
    ) -> DealDocument:
        """
        Saves uploaded file to disk/storage, registers DB metadata, 
        and executes vector ingestion pipeline.
        """
        file_path = os.path.join(UPLOAD_DIR, f"{deal_id}_{file.filename}")
        
        # 1. Save file to disk
        content = await file.read()
        file_size = len(content)
        with open(file_path, "wb") as f:
            f.write(content)

        vector_collection_name = f"deal_{deal_id}_docs"
        file_type = file.filename.split(".")[-1].lower() if "." in file.filename else "unknown"

        # 2. Register document metadata in PostgreSQL
        doc_record = self.doc_repo.create_document_record(
            deal_id=deal_id,
            filename=file.filename,
            file_path=file_path,
            file_type=file_type,
            document_category=document_category,
            vector_collection_name=vector_collection_name,
            file_size_bytes=file_size
        )

        # 3. Process vector embeddings
        try:
            self.doc_repo.update_indexing_status(doc_record.id, "PROCESSING")
            chunk_count = await self._ingest_to_vector_store(file_path, vector_collection_name)
            doc_record = self.doc_repo.update_indexing_status(
                doc_record.id, 
                "INDEXED", 
                chunk_count=chunk_count
            )
        except Exception as e:
            logger.error(f"Failed to index document '{doc_record.id}': {str(e)}")
            self.doc_repo.update_indexing_status(doc_record.id, "FAILED")
            raise e

        return doc_record

    async def _ingest_to_vector_store(self, file_path: str, collection_name: str) -> int:
        """
        Extracts text, splits into chunks, computes embeddings, 
        and inserts into PGVector.
        """
        logger.info(f"Indexing '{file_path}' into collection '{collection_name}'")
        
        # Pipeline logic placeholder (e.g., PyPDF/LangChain recursive text split)
        file_type = file_path.split(".")[-1].lower()
    
        # 1. Chunk document
        chunks = parse_and_chunk_document(file_path, file_type)
        
        # 2. Vectorize into PGVector
        deal_id = collection_name.replace("deal_", "")
        index_client_deal_chunks(deal_id=deal_id, chunks=chunks)
    
        return len(chunks)

    def list_documents(self, deal_id: UUID) -> List[DealDocument]:
        """Retrieves all document records registered under a deal."""
        return self.doc_repo.get_deal_documents(deal_id)