import os
import shutil
import json
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from langchain_community.vectorstores import PGVector

from app.core.database import get_db
from app.models.internal_knowledge import InternalKnowledgeAsset
from app.services.document_parser import parse_and_chunk_document
from app.services.vector_service import get_embeddings_model, DATABASE_URL

router = APIRouter(prefix="/knowledge-base", tags=["Knowledge Base"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/uploads/knowledge_base")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/")
async def upload_knowledge_asset(
    title: str = Form(...),
    asset_type: str = Form(..., description="CASE_STUDY, PROPOSAL, SOW, SUCCESS_STORY, SOLUTION_ACCELERATOR"),
    industry_tag: str = Form(None),
    technology_tags: str = Form("[]", description="JSON list of tags e.g. ['React', 'Go']"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Uploads a global asset, parses text, and chunks into internal_company_knowledgebase."""
    file_ext = file.filename.split(".")[-1].lower()
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    tech_tags_list = json.loads(technology_tags)

    asset = InternalKnowledgeAsset(
        title=title,
        asset_type=asset_type,
        industry_tag=industry_tag,
        technology_tags=tech_tags_list,
        file_path=file_path,
        file_type=file_ext,
        indexing_status="PROCESSING"
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    try:
        metadata = {"asset_id": str(asset.id), "asset_type": asset_type, "industry": industry_tag, "title": title}
        chunks = parse_and_chunk_document(file_path, file_ext, metadata)

        PGVector.from_documents(
            embedding=get_embeddings_model(),
            documents=chunks,
            collection_name="internal_company_knowledgebase",
            connection_string=DATABASE_URL,
            pre_delete_collection=False
        )

        asset.indexing_status = "INDEXED"
        db.commit()
        return {"status": "success", "asset_id": asset.id}

    except Exception as e:
        asset.indexing_status = "FAILED"
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
def list_knowledge_assets(
    asset_type: Optional[str] = None,
    industry: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Lists indexed global enterprise assets with filtering."""
    query = db.query(InternalKnowledgeAsset)
    if asset_type:
        query = query.filter(InternalKnowledgeAsset.asset_type == asset_type)
    if industry:
        query = query.filter(InternalKnowledgeAsset.industry_tag == industry)
    
    assets = query.limit(limit).all()
    return assets

@router.get("/{asset_id}")
def get_knowledge_asset(asset_id: UUID, db: Session = Depends(get_db)):
    """Fetches metadata and parsing status for a specific global knowledge asset."""
    asset = db.query(InternalKnowledgeAsset).filter(InternalKnowledgeAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset

@router.delete("/{asset_id}")
def delete_knowledge_asset(asset_id: UUID, db: Session = Depends(get_db)):
    """Removes the asset record from PostgreSQL and purges its vectors from PGVector."""
    asset = db.query(InternalKnowledgeAsset).filter(InternalKnowledgeAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # 1. Delete physical file if exists
    if os.path.exists(asset.file_path):
        os.remove(asset.file_path)

    # 2. Delete from PGVector (Requires custom SQL or Langchain PGVector deletion logic based on metadata)
    db.execute(
        "DELETE FROM langchain_pg_embedding WHERE collection_id = (SELECT uuid FROM langchain_pg_collection WHERE name = 'internal_company_knowledgebase') AND cmetadata->>'asset_id' = :asset_id",
        {"asset_id": str(asset_id)}
    )
    
    # 3. Delete from DB
    db.delete(asset)
    db.commit()
    return {"status": "success", "message": "Asset and associated vectors deleted"}