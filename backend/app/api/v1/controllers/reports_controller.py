from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.deal_service import DealService

router = APIRouter(prefix="/deals/{deal_id}/reports", tags=["Reports & Versioning"])


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


@router.get("/versions")
async def list_report_versions(deal_id: UUID, db: AsyncSession = Depends(get_db)):
    """Lists all historical snapshot versions for the deal."""
    deal_service = DealService(db)
    snapshots = await deal_service.intel_repo.get_deal_snapshots(deal_id)

    if not snapshots:
        return []

    return [
        {
            "snapshot_id": str(snap.id),
            "deal_id": str(snap.deal_id),
            "version": snap.version,
            "thread_id": snap.thread_id,
            "current_step": snap.current_step,
            "created_at": snap.created_at,
            "updated_at": snap.updated_at,
        }
        for snap in snapshots
    ]


@router.get("/versions/{snapshot_id}")
async def get_specific_version(deal_id: UUID, snapshot_id: UUID, db: AsyncSession = Depends(get_db)):
    """Fetches a specific historical snapshot version."""
    deal_service = DealService(db)
    snapshot = await deal_service.intel_repo.get_snapshot_by_id(snapshot_id)

    if not snapshot or snapshot.deal_id != deal_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Snapshot not found for this deal.",
        )

    return {
        "snapshot_id": str(snapshot.id),
        "deal_id": str(snapshot.deal_id),
        "version": snapshot.version,
        "thread_id": snapshot.thread_id,
        "current_step": snapshot.current_step,
        "snapshot_data": snapshot.snapshot_data,
        "created_at": snapshot.created_at,
        "updated_at": snapshot.updated_at,
    }


@router.post("/revert/{snapshot_id}")
async def revert_to_version(deal_id: UUID, snapshot_id: UUID, db: AsyncSession = Depends(get_db)):
    """Rolls back the active state to a saved snapshot."""
    deal_service = DealService(db)
    target_snapshot = await deal_service.intel_repo.get_snapshot_by_id(snapshot_id)

    if not target_snapshot or target_snapshot.deal_id != deal_id:
        raise HTTPException(status_code=404, detail="Target snapshot not found.")

    new_snapshot = await deal_service.intel_repo.save_intelligence_snapshot(
        deal_id=deal_id,
        thread_id=target_snapshot.thread_id,
        current_step=target_snapshot.current_step,
        snapshot_data=target_snapshot.snapshot_data,
    )

    return {
        "status": "success",
        "message": f"Reverted to snapshot {new_snapshot.version} from {target_snapshot.created_at}",
        "snapshot_id": str(new_snapshot.id),
    }


@router.get("/export/markdown")
async def export_markdown_report(deal_id: UUID, db: AsyncSession = Depends(get_db)):
    """Downloads the last markdown payload available for the deal."""
    deal_service = DealService(db)
    context = await deal_service.get_deal_context(deal_id)

    if not context or not context.get("active_state"):
        raise HTTPException(status_code=404, detail="Deal state not found")

    state = context["active_state"]
    markdown_content = (
        state.get("markdown_export")
        or state.get("final_report")
        or state.get("draft_proposal")
        or "# Report Generation Incomplete\nThe report has not been generated yet."
    )

    headers = {
        "Content-Disposition": f"attachment; filename=deal_{deal_id}_strategy_brief.md"
    }

    return Response(
        content=str(markdown_content),
        media_type="text/markdown",
        headers=headers,
    )