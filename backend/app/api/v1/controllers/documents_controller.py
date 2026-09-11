import os
from uuid import UUID
from typing import List
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.deal_document import DealDocument
from app.services.document_service import DocumentService

router = APIRouter(prefix="/deals", tags=["Deal Documents"])


@router.post("/{deal_id}/documents")
async def upload_deal_document(
    deal_id: UUID,
    document_category: str = Form(..., description="RFP, RFI, BRD, ARCHITECTURE, SCOPE"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Uploads client RFPs/BRDs and chunks them into the isolated vector collection."""
    file_ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if file_ext not in ["pdf", "docx", "txt", "pptx"]:
        raise HTTPException(status_code=400, detail="Unsupported file format")

    doc_service = DocumentService(db)
    try:
        doc_record = await doc_service.upload_and_process_document(
            deal_id=deal_id,
            file=file,
            document_category=document_category
        )
        return {
            "status": "success",
            "document_id": doc_record.id,
            "chunks_indexed": doc_record.chunk_count,
            "indexing_status": doc_record.indexing_status
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")


@router.get("/{deal_id}/documents", response_model=List[dict])
def list_deal_documents(deal_id: UUID, db: Session = Depends(get_db)):
    """Lists all uploaded client documents for a given deal."""
    doc_service = DocumentService(db)
    docs = doc_service.list_documents(deal_id)
    return [
        {
            "document_id": d.id,
            "filename": d.filename,
            "category": d.document_category,
            "status": d.indexing_status,
            "chunk_count": d.chunk_count,
            "file_size_bytes": d.file_size_bytes,
            "created_at": d.created_at
        }
        for d in docs
    ]


@router.delete("/{deal_id}/documents/{document_id}")
def delete_deal_document(deal_id: UUID, document_id: UUID, db: Session = Depends(get_db)):
    """Deletes a deal document, removes physical file, and purges corresponding vector chunks."""
    doc = db.query(DealDocument).filter(DealDocument.id == document_id, DealDocument.deal_id == deal_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 1. Remove physical file
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    # 2. Purge chunks from PGVector collection
    db.execute(
        "DELETE FROM langchain_pg_embedding WHERE collection_id = (SELECT uuid FROM langchain_pg_collection WHERE name = :col_name) AND cmetadata->>'filename' = :filename",
        {"col_name": f"deal_{str(deal_id)}_docs", "filename": doc.filename}
    )
    
    # 3. Delete database record
    db.delete(doc)
    db.commit()
    return {"status": "success", "message": "Document and associated vector chunks deleted"}