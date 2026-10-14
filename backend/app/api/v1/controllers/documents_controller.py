import os
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.db.models.deal import Deal
from app.db.models.deal_document import DealDocument
from app.schemas.deal_document import DealDocumentResponse
from app.services.document_service import DocumentService

router = APIRouter(prefix="/deals", tags=["Deal Documents"])


class UploadDealDocumentResponse(BaseModel):
    status: str
    document_id: UUID
    chunks_indexed: int
    indexing_status: str


class DeleteDealDocumentResponse(BaseModel):
    status: str
    message: str


@router.post("/{deal_id}/documents", response_model=dict)
async def upload_deal_document(
    deal_id: UUID,
    document_category: str = Form(..., description="RFP, RFI, BRD, ARCHITECTURE, SCOPE"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Uploads client RFPs/BRDs and chunks them into the isolated deal vector collection."""
    result = await db.execute(select(Deal).where(Deal.id == deal_id))
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    file_ext = file.filename.split(".")[-1].lower() if "." in (file.filename or "") else ""
    if file_ext not in ["pdf", "docx", "txt", "pptx"]:
        raise HTTPException(status_code=400, detail="Unsupported file format")

    doc_service = DocumentService(db)
    try:
        doc_record = await doc_service.upload_and_process_document(
            deal_id=deal_id,
            file=file,
            document_category=document_category,
        )
        return {
            "status": "success",
            "document_id": doc_record.id,
            "chunks_indexed": doc_record.chunk_count,
            "indexing_status": doc_record.indexing_status,
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve)) from ve
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Document processing failed: {str(exc)}") from exc


@router.get("/{deal_id}/documents", response_model=list[DealDocumentResponse])
async def list_deal_documents(deal_id: UUID, db: AsyncSession = Depends(get_db)):
    """Lists all uploaded client documents for a given deal."""
    result = await db.execute(select(DealDocument).where(DealDocument.deal_id == deal_id))
    docs = result.scalars().all()
    return [DealDocumentResponse.model_validate(doc) for doc in docs]


@router.delete("/{deal_id}/documents/{document_id}", response_model=DeleteDealDocumentResponse)
async def delete_deal_document(deal_id: UUID, document_id: UUID, db: AsyncSession = Depends(get_db)):
    """Deletes a deal document, removes the physical file, and purges corresponding vector chunks."""
    result = await db.execute(
        select(DealDocument).where(DealDocument.id == document_id, DealDocument.deal_id == deal_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except OSError:
            pass

    await db.execute(
        text(
            """
            DELETE FROM langchain_pg_embedding
            WHERE collection_id = (
                SELECT uuid
                FROM langchain_pg_collection
                WHERE name = :col_name
            )
            AND cmetadata->>'filename' = :filename
            """
        ),
        {"col_name": f"deal_{str(deal_id)}_docs", "filename": doc.filename},
    )

    await db.delete(doc)
    await db.commit()
    return {"status": "success", "message": "Document and associated vector chunks deleted"}