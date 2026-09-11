import os
import shutil
from uuid import UUID
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.deal import Deal
from app.models.deal_document import DealDocument
from app.schemas.deal import DealCreate
from app.services.deal_service import DealService
from app.services.document_parser import parse_and_chunk_document
from app.services.vector_service import index_client_deal_chunks

router = APIRouter(prefix="/deals", tags=["Deals"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/uploads/deals")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/")
def create_deal(
    deal_in: DealCreate, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Initializes a new deal record."""
    deal_service = DealService(db)
    return deal_service.create_new_deal(owner_id=current_user.id, deal_data=deal_in)

@router.get("/")
def list_user_deals(
    skip: int = 0, 
    limit: int = 50, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Retrieves all deals owned by the current user."""
    deals = db.query(Deal).filter(Deal.owner_id == current_user.id).offset(skip).limit(limit).all()
    return deals

@router.get("/{deal_id}")
def get_deal_details(deal_id: UUID, db: Session = Depends(get_db)):
    """Returns detailed metadata, status, and document summary for a specific deal."""
    deal_service = DealService(db)
    context = deal_service.get_deal_context(deal_id)
    if not context:
        raise HTTPException(status_code=404, detail="Deal not found")
    return context

@router.delete("/{deal_id}")
def delete_deal(deal_id: UUID, db: Session = Depends(get_db)):
    """Deletes a deal, its uploaded documents, and vector space."""
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    # Clean up isolated vector collection for this deal
    db.execute(
        "DELETE FROM langchain_pg_collection WHERE name = :collection_name",
        {"collection_name": f"deal_{str(deal_id)}_docs"}
    )
    db.delete(deal)
    db.commit()
    return {"status": "success", "message": "Deal and isolated vector space deleted"}

@router.post("/{deal_id}/documents")
async def upload_deal_document(
    deal_id: UUID,
    document_category: str = Form(..., description="RFP, RFI, BRD, ARCHITECTURE, SCOPE"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Uploads client RFPs/BRDs and chunks them into the isolated deal_{deal_id}_docs vector collection."""
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    file_ext = file.filename.split(".")[-1].lower()
    if file_ext not in ["pdf", "docx", "txt", "pptx"]:
        raise HTTPException(status_code=400, detail="Unsupported file format")

    file_path = os.path.join(UPLOAD_DIR, f"{deal_id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    deal_doc = DealDocument(
        deal_id=deal_id,
        filename=file.filename,
        file_path=file_path,
        file_type=file_ext,
        document_category=document_category,
        file_size_bytes=os.path.getsize(file_path),
        vector_collection_name=f"deal_{str(deal_id)}_docs",
        indexing_status="PROCESSING"
    )
    db.add(deal_doc)
    db.commit()
    db.refresh(deal_doc)

    try:
        metadata = {"deal_id": str(deal_id), "document_category": document_category, "filename": file.filename}
        chunks = parse_and_chunk_document(file_path, file_ext, metadata)
        index_client_deal_chunks(str(deal_id), chunks)

        deal_doc.chunk_count = len(chunks)
        deal_doc.indexing_status = "INDEXED"
        db.commit()
        return {"status": "success", "document_id": deal_doc.id, "chunks_indexed": len(chunks)}
    except Exception as e:
        deal_doc.indexing_status = "FAILED"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")

@router.get("/{deal_id}/documents")
def list_deal_documents(deal_id: UUID, db: Session = Depends(get_db)):
    """Lists all uploaded client documents for a given deal."""
    return db.query(DealDocument).filter(DealDocument.deal_id == deal_id).all()

@router.delete("/{deal_id}/documents/{document_id}")
def delete_deal_document(deal_id: UUID, document_id: UUID, db: Session = Depends(get_db)):
    """Deletes a deal document and cleans up corresponding vector chunks."""
    doc = db.query(DealDocument).filter(DealDocument.id == document_id, DealDocument.deal_id == deal_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    # Delete specific chunks from the deal's collection
    db.execute(
        "DELETE FROM langchain_pg_embedding WHERE collection_id = (SELECT uuid FROM langchain_pg_collection WHERE name = :col_name) AND cmetadata->>'filename' = :filename",
        {"col_name": f"deal_{str(deal_id)}_docs", "filename": doc.filename}
    )
    
    db.delete(doc)
    db.commit()
    return {"status": "success", "message": "Document and vector chunks deleted"}