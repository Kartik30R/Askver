from pathlib import Path  
import json
import os
import shutil
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.db.models.internal_knowledge import InternalKnowledgeAsset
from app.schemas.internal_knowledge import InternalKnowledgeResponse
from app.services.document_parser import parse_and_chunk_document
from app.services.vector_service import index_internal_knowledge_chunks

router = APIRouter(prefix="/knowledge-base", tags=["Knowledge Base"])

# Use relative path that resolves to absolute path on any OS (Windows/Unix)
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads/knowledge_base")).resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class UploadKnowledgeAssetResponse(BaseModel):
    status: str
    asset_id: UUID

    model_config = ConfigDict(from_attributes=True)


class DeleteKnowledgeAssetResponse(BaseModel):
    status: str
    message: str



@router.post("/", response_model=UploadKnowledgeAssetResponse, status_code=status.HTTP_201_CREATED)
async def upload_knowledge_asset(
    title: str = Form(...),
    asset_type: str = Form(..., description="CASE_STUDY, PROPOSAL, SOW, SUCCESS_STORY, SOLUTION_ACCELERATOR"),
    industry_tag: Optional[str] = Form(default=None),
    technology_tags: str = Form(default='[]', description="JSON list of tags e.g. ['React', 'Go']"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Uploads a global asset, parses text, and chunks into the shared knowledge base."""
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File name is required")

    try:
        parsed_tags = json.loads(technology_tags or "[]")
        if not isinstance(parsed_tags, list):
            raise ValueError("technology_tags must be a JSON array")
    except (TypeError, ValueError, json.JSONDecodeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="technology_tags must be a valid JSON array of strings",
        )

    # 1. Sanitize the filename to remove any Windows/Unix paths sent by Postman
    safe_filename = Path(file.filename).name

    # 2. Extract extension safely
    file_ext = safe_filename.rsplit(".", 1)[-1].lower() if "." in safe_filename else ""
    
    # 3. Build an OS-safe absolute path using pathlib
    # Prefix with a UUID so two uploads with the same name don't overwrite each other
    file_path_obj = UPLOAD_DIR / f"{uuid4().hex}_{safe_filename}"
    file_path = str(file_path_obj)  # Convert to string for Langchain/OS compatibility

    # 4. Save the file to disk
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    asset = InternalKnowledgeAsset(
        title=title,
        asset_type=asset_type,
        industry_tag=industry_tag,
        technology_tags=[str(tag).strip() for tag in parsed_tags if str(tag).strip()],
        file_path=file_path,
        file_type=file_ext,
        indexing_status="PROCESSING",
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)

    try:
        metadata = {
            "asset_id": str(asset.id),
            "asset_type": asset_type,
            "industry": industry_tag,
            "title": title,
        }
        
        # Parse and chunk using the safe file_path
        chunks = parse_and_chunk_document(file_path, file_ext, metadata)

        await index_internal_knowledge_chunks(
            "internal_company_knowledgebase",
            chunks,
            pre_delete_collection=False,
        )

        asset.indexing_status = "INDEXED"
        await db.commit()
        return UploadKnowledgeAssetResponse(status="success", asset_id=asset.id)

    except Exception as exc:
        asset.indexing_status = "FAILED"
        await db.commit()
        
        # Clean up the broken file so it doesn't take up disk space
        if file_path_obj.exists():
            file_path_obj.unlink()
            
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    
@router.get("/", response_model=list[InternalKnowledgeResponse])
async def list_knowledge_assets(
    asset_type: Optional[str] = None,
    industry: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """Lists global enterprise assets with optional filtering."""
    query = select(InternalKnowledgeAsset)
    if asset_type:
        query = query.where(InternalKnowledgeAsset.asset_type == asset_type)
    if industry:
        query = query.where(InternalKnowledgeAsset.industry_tag == industry)

    result = await db.execute(query.limit(limit))
    assets = result.scalars().all()
    return [InternalKnowledgeResponse.model_validate(asset) for asset in assets]


@router.get("/{asset_id}", response_model=InternalKnowledgeResponse)
async def get_knowledge_asset(asset_id: UUID, db: AsyncSession = Depends(get_db)):
    """Fetches metadata and parsing status for a specific knowledge asset."""
    result = await db.execute(select(InternalKnowledgeAsset).where(InternalKnowledgeAsset.id == asset_id))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return InternalKnowledgeResponse.model_validate(asset)


@router.delete("/{asset_id}", response_model=DeleteKnowledgeAssetResponse)
async def delete_knowledge_asset(asset_id: UUID, db: AsyncSession = Depends(get_db)):
    """Removes the asset record from PostgreSQL and its matching vector metadata."""
    result = await db.execute(select(InternalKnowledgeAsset).where(InternalKnowledgeAsset.id == asset_id))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    if os.path.exists(asset.file_path):
        os.remove(asset.file_path)

    # Raw SQL must be wrapped in text() on SQLAlchemy 2.x. Guard against the
    # LangChain tables not existing yet (nothing has been indexed).
    try:
        await db.execute(
            text(
                "DELETE FROM langchain_pg_embedding "
                "WHERE collection_id = (SELECT uuid FROM langchain_pg_collection "
                "WHERE name = 'internal_company_knowledgebase') "
                "AND cmetadata->>'asset_id' = :asset_id"
            ),
            {"asset_id": str(asset_id)},
        )
    except Exception:
        await db.rollback()
        raise

    await db.delete(asset)
    await db.commit()
    return DeleteKnowledgeAssetResponse(status="success", message="Asset and associated vectors deleted")