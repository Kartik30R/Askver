import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Deal(Base):
    __tablename__ = "deals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String(255), nullable=False)
    target_company = Column(String(255), nullable=False, index=True)
    target_industry = Column(String(100), nullable=False, index=True)
    meeting_objective = Column(Text, nullable=False)
    status = Column(
        String(50), 
        default="CREATED", 
        nullable=False, 
        index=True
    )  # CREATED, RUNNING, PAUSED_FOR_HUMAN_REVIEW, COMPLETED, FAILED
    
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    owner = relationship("User", back_populates="deals")
    intelligence_snapshots = relationship(
        "DealIntelligence", back_populates="deal", cascade="all, delete-orphan"
    )