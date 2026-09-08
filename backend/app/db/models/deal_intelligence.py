import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class DealIntelligence(Base):
    __tablename__ = "deal_intelligence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    deal_id = Column(UUID(as_uuid=True), ForeignKey("deals.id"), nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    
    # Stores the complete output dictionary corresponding to DealIntelligenceState
    snapshot_data = Column(JSONB, nullable=False)
    
    thread_id = Column(String(255), nullable=False, index=True)  # LangGraph Thread ID
    current_step = Column(String(100), nullable=False, default="INIT")
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship
    deal = relationship("Deal", back_populates="intelligence_snapshots")