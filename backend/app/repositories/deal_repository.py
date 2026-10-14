import logging
from typing import Optional, List
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.deal import Deal
from app.schemas.deals import DealCreate

logger = logging.getLogger(__name__)


class DealRepository:
    """
    Data Access Layer for managing Deal entities in PostgreSQL.
    Focuses exclusively on CRUD operations for the `deals` table.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_deal(self, owner_id: UUID, deal_in: DealCreate) -> Deal:
        """Creates a new deal record assigned to a specific sales rep using the DealCreate schema."""
        deal = Deal(
            owner_id=owner_id,
            title=deal_in.title,
            target_company=deal_in.target_company,
            target_industry=deal_in.target_industry,
            meeting_objective=deal_in.meeting_objective,
            status="CREATED"
        )
        self.db.add(deal)
        await self.db.commit()
        await self.db.refresh(deal)
        logger.info(f"Created deal '{deal.id}' for owner '{owner_id}'")
        return deal

    async def get_deal_by_id(self, deal_id: UUID) -> Optional[Deal]:
        """Fetches a single deal by its primary key UUID."""
        result = await self.db.execute(select(Deal).where(Deal.id == deal_id))
        return result.scalar_one_or_none()

    async def list_deals_by_owner(
        self,
        owner_id: UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Deal]:
        """Retrieves a paginated list of deals owned by a specific user, ordered by creation date."""
        result = await self.db.execute(
            select(Deal)
            .where(Deal.owner_id == owner_id)
            .order_by(desc(Deal.created_at))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_deal_status(self, deal_id: UUID, status: str) -> Optional[Deal]:
        """
        Updates the execution lifecycle status of a deal.
        Valid statuses: CREATED, RUNNING, PAUSED_FOR_HUMAN_REVIEW, COMPLETED, FAILED
        """
        deal = await self.get_deal_by_id(deal_id)
        if deal:
            deal.status = status
            await self.db.commit()
            await self.db.refresh(deal)
            logger.info(f"Updated deal '{deal_id}' status to '{status}'")
        return deal

    async def delete_deal(self, deal_id: UUID) -> bool:
        """Deletes a deal record. Foreign key cascades automatically remove linked documents and snapshots."""
        deal = await self.get_deal_by_id(deal_id)
        if deal:
            await self.db.delete(deal)
            await self.db.commit()
            logger.info(f"Deleted deal '{deal_id}' and all associated records.")
            return True
        return False