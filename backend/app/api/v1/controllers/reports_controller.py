from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.deal_service import DealService

router = APIRouter(prefix="/deals/{deal_id}/reports", tags=["Reports"])


@router.get("/latest")
async def get_latest_report(deal_id: UUID, db: AsyncSession = Depends(get_db)):
    """Returns the newest persisted workflow snapshot for the deal."""
    deal_service = DealService(db)
    snapshot = await deal_service.intel_repo.get_latest_intelligence_snapshot(deal_id)

    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active report state found for this deal.",
        )

    return {
        "deal_id": str(deal_id),
        "version": snapshot.version,
        "thread_id": snapshot.thread_id,
        "current_step": snapshot.current_step,
        "snapshot_data": snapshot.snapshot_data,
        "created_at": snapshot.created_at,
        "updated_at": snapshot.updated_at,
    }


@router.get("/export/markdown")
async def export_markdown_report(deal_id: UUID, db: AsyncSession = Depends(get_db)):
    """Downloads the last markdown payload available for the deal."""
    deal_service = DealService(db)
    context = await deal_service.get_deal_context(deal_id)

    if not context or not context.get("active_state"):
        raise HTTPException(status_code=404, detail="Deal state not found")

    state = context["active_state"]
    markdown_content = state.get("markdown_export") or state.get("final_report") or state.get("draft_proposal")
    if not markdown_content:
        meeting_playbook = state.get("meeting_playbook") or {}
        if meeting_playbook:
            markdown_content = "# Executive Snapshot\n\n" + (meeting_playbook.get("executive_snapshot") or "")
        else:
            raise HTTPException(status_code=404, detail="No report available yet")

    headers = {
        "Content-Disposition": f"attachment; filename=deal_{deal_id}_strategy_brief.md"
    }

    return Response(
        content=str(markdown_content),
        media_type="text/markdown",
        headers=headers,
    )