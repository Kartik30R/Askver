from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.db.models.deal import Deal
from app.db.models.user import User
from app.schemas.deals import DealCreate
from app.services.deal_service import DealService

router = APIRouter(prefix="/deals", tags=["Deals"])


@router.post("")
async def create_deal(
    deal_in: DealCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Initializes a new deal record."""
    deal_service = DealService(db)
    return await deal_service.create_new_deal(owner_id=current_user.id, deal_data=deal_in)


@router.get("")
async def list_user_deals(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves all deals owned by the current user."""
    result = await db.execute(
        select(Deal).where(Deal.owner_id == current_user.id).offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.get("/{deal_id}")
async def get_deal_details(
    deal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns the canonical deal metadata plus any cached workflow state for a specific deal."""
    deal_service = DealService(db)
    deal = await deal_service.get_deal(deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    if deal.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this deal")

    context = await deal_service.get_deal_context(deal_id)
    payload = {
        "id": str(deal.id),
        "title": deal.title,
        "target_company": deal.target_company,
        "target_industry": deal.target_industry,
        "meeting_objective": deal.meeting_objective,
        "status": deal.status,
        "owner_id": str(deal.owner_id),
        "created_at": deal.created_at,
        "updated_at": deal.updated_at,
    }

    if context and isinstance(context, dict):
        payload["active_state"] = context.get("active_state", {})

    return payload


@router.delete("/{deal_id}")
async def delete_deal(
    deal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deletes a deal and all linked workflow data for the current owner."""
    result = await db.execute(select(Deal).where(Deal.id == deal_id))
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    if deal.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this deal")

    collection_name = f"deal_{str(deal_id)}_docs"
    thread_id = f"deal_{str(deal_id)}"

    for table_name, params in (
        ("langchain_pg_collection", {"collection_name": collection_name}),
        ("langgraph_checkpoints", {"thread_id": thread_id}),
        ("langgraph_checkpoint_blobs", {"thread_id": thread_id}),
    ):
        table_exists = await db.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = :table_name
                )
                """
            ),
            {"table_name": table_name},
        )
        if not table_exists.scalar():
            continue

        if table_name == "langchain_pg_collection":
            await db.execute(
                text("DELETE FROM langchain_pg_collection WHERE name = :collection_name"),
                params,
            )
        else:
            await db.execute(
                text(f"DELETE FROM {table_name} WHERE thread_id = :thread_id"),
                params,
            )

    await db.delete(deal)
    await db.commit()
    return {"status": "success", "message": "Deal and related workflow data deleted"}

