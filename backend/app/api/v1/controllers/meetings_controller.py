from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.api.deps import get_current_user
from app.core.database import get_db
from app.db.models.meeting_document import MeetingDocument
from app.db.models.user import User
from app.schemas.meeting import MeetingCreate, MeetingDocumentResponse, MeetingResponse, MeetingUpdate
from app.services.meeting_service import MeetingService

UPLOAD_DIR = Path("./storage/uploads/meeting_documents").resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/meetings", tags=["Meetings"])


@router.get("", response_model=list[MeetingResponse])
async def list_my_meetings(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    service = MeetingService(db)
    meetings = await service.list_meetings_for_owner(current_user.id, skip=skip, limit=limit)
    return [MeetingResponse.model_validate(meeting) for meeting in meetings]


@router.get("/deal/{deal_id}", response_model=list[MeetingResponse])
async def list_meetings_for_deal(
    deal_id: UUID,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    service = MeetingService(db)
    meetings = await service.list_meetings_for_deal(deal_id, owner_id=current_user.id, skip=skip, limit=limit)
    return [MeetingResponse.model_validate(meeting) for meeting in meetings]


@router.post("", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    payload: MeetingCreate,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    service = MeetingService(db)
    meeting = await service.create_meeting_for_deal(
        deal_id=payload.deal_id,
        owner_id=current_user.id,
        title=payload.title,
        meeting_date=payload.meeting_date,
        meeting_type=payload.meeting_type,
        attendees=payload.attendees,
        objectives=payload.objectives,
        notes=payload.notes,
        transcript_text=payload.transcript_text,
        summary=payload.summary,
    )
    return MeetingResponse.model_validate(meeting)


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting_id: UUID,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    service = MeetingService(db)
    meeting = await service.get_meeting(meeting_id, owner_id=current_user.id)
    return MeetingResponse.model_validate(meeting)


@router.patch("/{meeting_id}", response_model=MeetingResponse)
async def update_meeting(
    meeting_id: UUID,
    payload: MeetingUpdate,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    service = MeetingService(db)
    meeting = await service.get_meeting(meeting_id, owner_id=current_user.id)
    updated = await service.update_meeting_metadata(
        meeting,
        title=payload.title,
        meeting_date=payload.meeting_date,
        meeting_type=payload.meeting_type,
        attendees=payload.attendees,
        objectives=payload.objectives,
        notes=payload.notes,
        transcript_text=payload.transcript_text,
        summary=payload.summary,
    )
    return MeetingResponse.model_validate(updated)


@router.post("/{meeting_id}/documents", response_model=MeetingDocumentResponse)
async def upload_meeting_document(
    meeting_id: UUID,
    file: UploadFile = File(...),
    document_type: str = Form("supporting_document"),
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    service = MeetingService(db)
    await service.get_meeting(meeting_id, owner_id=current_user.id)

    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File name is required")

    safe_name = Path(file.filename).name
    file_path = UPLOAD_DIR / f"{meeting_id}_{uuid4().hex}_{safe_name}"
    content = await file.read()
    file_path.write_bytes(content)

    doc = MeetingDocument(
        meeting_id=meeting_id,
        document_type=document_type or "supporting_document",
        original_filename=safe_name,
        storage_path=str(file_path),
        mime_type=file.content_type,
        file_size_bytes=len(content),
        status="UPLOADED",
        extraction_status="PENDING",
        indexing_status="PENDING",
        uploaded_by_user_id=current_user.id,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    return MeetingDocumentResponse.model_validate(doc)


@router.delete("/{meeting_id}")
async def delete_meeting(
    meeting_id: UUID,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    service = MeetingService(db)
    meeting = await service.get_meeting(meeting_id, owner_id=current_user.id)
    await db.delete(meeting)
    await db.commit()
    return {"status": "success", "message": "Meeting deleted"}
