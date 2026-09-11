import logging
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.deal import Deal

logger = logging.getLogger(__name__)


class DealRepository:
    """
    Data Access Layer for managing Deal entities in PostgreSQL.
    Focuses exclusively on CRUD operations for the `deals` table.
    """
    def __init__(self, db: Session):
        self.db = db

    def create_deal(
        self, 
        owner_id: UUID, 
        title: str, 
        target_company: str, 
        target_industry: str, 
        meeting_objective: str
    ) -> Deal:
        """Creates a new deal record assigned to a specific sales rep."""
        deal = Deal(
            owner_id=owner_id,
            title=title,
            target_company=target_company,
            target_industry=target_industry,
            meeting_objective=meeting_objective,
            status="CREATED"
        )
        self.db.add(deal)
        self.db.commit()
        self.db.refresh(deal)
        logger.info(f"Created deal '{deal.id}' for owner '{owner_id}'")
        return deal

    def get_deal_by_id(self, deal_id: UUID) -> Optional[Deal]:
        """Fetches a single deal by its primary key UUID."""
        return self.db.query(Deal).filter(Deal.id == deal_id).first()

    def list_deals_by_owner(
        self, 
        owner_id: UUID, 
        skip: int = 0, 
        limit: int = 20
    ) -> List[Deal]:
        """Retrieves a paginated list of deals owned by a specific user, ordered by creation date."""
        return (
            self.db.query(Deal)
            .filter(Deal.owner_id == owner_id)
            .order_by(desc(Deal.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_deal_status(self, deal_id: UUID, status: str) -> Optional[Deal]:
        """
        Updates the execution lifecycle status of a deal.
        Valid statuses: CREATED, RUNNING, PAUSED_FOR_HUMAN_REVIEW, COMPLETED, FAILED
        """
        deal = self.get_deal_by_id(deal_id)
        if deal:
            deal.status = status
            self.db.commit()
            self.db.refresh(deal)
            logger.info(f"Updated deal '{deal_id}' status to '{status}'")
        return deal

    def delete_deal(self, deal_id: UUID) -> bool:
        """Deletes a deal record. Foreign key cascades automatically remove linked documents and snapshots."""
        deal = self.get_deal_by_id(deal_id)
        if deal:
            self.db.delete(deal)
            self.db.commit()
            logger.info(f"Deleted deal '{deal_id}' and all associated records.")
            return True
        return False