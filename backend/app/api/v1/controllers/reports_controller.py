from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.deal_service import DealService

router = APIRouter(prefix="/deals/{deal_id}/reports", tags=["Reports & Versioning"])


@router.get("/latest")
def get_latest_report(deal_id: UUID, db: Session = Depends(get_db)):
    """
    Returns the active version of the strategy brief/report from the LangGraph state.
    """
    deal_service = DealService(db)
    context = deal_service.get_deal_context(deal_id)
    
    if not context or not context.get("active_state"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="No active report state found for this deal."
        )
    
    return {
        "deal_metadata": context["deal_metadata"],
        "current_step": context["current_step"],
        "report_state": context["active_state"]
    }


@router.get("/versions")
def list_report_versions(deal_id: UUID, db: Session = Depends(get_db)):
    """
    Lists all historical snapshot versions for the deal's intelligence thread.
    """
    deal_service = DealService(db)
    # Assuming DealIntelligenceRepository has a method to fetch all snapshots
    snapshots = deal_service.intel_repo.get_deal_snapshots(deal_id)
    
    if not snapshots:
        return []
        
    return [
        {
            "snapshot_id": snap.id,
            "thread_id": snap.thread_id,
            "current_step": snap.current_step,
            "created_at": snap.created_at
        }
        for snap in snapshots
    ]


@router.get("/versions/{snapshot_id}")
def get_specific_version(deal_id: UUID, snapshot_id: UUID, db: Session = Depends(get_db)):
    """
    Fetches a specific historical snapshot version.
    """
    deal_service = DealService(db)
    snapshot = deal_service.intel_repo.get_snapshot_by_id(snapshot_id)
    
    if not snapshot or snapshot.deal_id != deal_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Snapshot not found for this deal."
        )
        
    return snapshot.snapshot_data


@router.post("/revert/{snapshot_id}")
def revert_to_version(deal_id: UUID, snapshot_id: UUID, db: Session = Depends(get_db)):
    """
    Rollbacks the active deal state to a previous version, creating a new head snapshot.
    """
    deal_service = DealService(db)
    target_snapshot = deal_service.intel_repo.get_snapshot_by_id(snapshot_id)
    
    if not target_snapshot or target_snapshot.deal_id != deal_id:
        raise HTTPException(status_code=404, detail="Target snapshot not found.")

    # Create a new snapshot based on the historical state to preserve the timeline
    new_snapshot = deal_service.intel_repo.save_intelligence_snapshot(
        deal_id=deal_id,
        thread_id=target_snapshot.thread_id,
        current_step=target_snapshot.current_step,
        snapshot_data=target_snapshot.snapshot_data
    )
    
    return {"status": "success", "message": f"Reverted to state from {target_snapshot.created_at}"}


@router.get("/export/markdown")
def export_markdown_report(deal_id: UUID, db: Session = Depends(get_db)):
    """
    Downloads the raw rendered Markdown report from the final state.
    """
    deal_service = DealService(db)
    context = deal_service.get_deal_context(deal_id)
    
    if not context or not context.get("active_state"):
        raise HTTPException(status_code=404, detail="Deal state not found")

    state = context["active_state"]
    # Look for the final report key; default to draft if final isn't ready
    markdown_content = state.get("final_report") or state.get("draft_proposal")
    
    if not markdown_content:
        markdown_content = "# Report Generation Incomplete\nThe report has not been generated yet."

    headers = {
        "Content-Disposition": f"attachment; filename=deal_{deal_id}_strategy_brief.md"
    }
    
    return Response(
        content=markdown_content, 
        media_type="text/markdown", 
        headers=headers
    )