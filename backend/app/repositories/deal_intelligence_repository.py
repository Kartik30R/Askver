import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.models.deal_intelligence import DealIntelligence

logger = logging.getLogger(__name__)


class DealIntelligenceRepository:
    """
    Manages LangGraph state persistence, version-controlled snapshots, 
    and thread retrieval for the deal_intelligence table.
    """
    def __init__(self, db: Session):
        self.db = db

    def save_intelligence_snapshot(
        self, 
        deal_id: UUID, 
        thread_id: str, 
        current_step: str, 
        snapshot_data: Dict[str, Any]
    ) -> DealIntelligence:
        """Saves a new state dictionary and auto-increments the version number (v1 -> v2)."""
        latest_snapshot = self.get_latest_intelligence_snapshot(deal_id)
        next_version = (latest_snapshot.version + 1) if latest_snapshot else 1

        intelligence = DealIntelligence(
            deal_id=deal_id,
            version=next_version,
            thread_id=thread_id,
            current_step=current_step,
            snapshot_data=snapshot_data
        )
        self.db.add(intelligence)
        self.db.commit()
        self.db.refresh(intelligence)
        logger.info(f"Saved snapshot v{next_version} for deal '{deal_id}' at step '{current_step}'")
        return intelligence

    def get_latest_intelligence_snapshot(self, deal_id: UUID) -> Optional[DealIntelligence]:
        """Fetches the most recent snapshot for active UI rendering or execution resumption."""
        return (
            self.db.query(DealIntelligence)
            .filter(DealIntelligence.deal_id == deal_id)
            .order_by(desc(DealIntelligence.version))
            .first()
        )

    def get_snapshot_by_version(self, deal_id: UUID, version: int) -> Optional[DealIntelligence]:
        """Fetches a specific historical version for rollbacks or diff comparisons."""
        return (
            self.db.query(DealIntelligence)
            .filter(DealIntelligence.deal_id == deal_id, DealIntelligence.version == version)
            .first()
        )

    def list_all_snapshots(self, deal_id: UUID) -> List[DealIntelligence]:
        """Returns the full version history for a deal."""
        return (
            self.db.query(DealIntelligence)
            .filter(DealIntelligence.deal_id == deal_id)
            .order_by(desc(DealIntelligence.version))
            .all()
        )