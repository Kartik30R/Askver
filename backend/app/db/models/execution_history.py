from sqlalchemy import Column, String, DateTime, Integer, JSON, Boolean, ForeignKey, LargeBinary
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid

from app.core.database import Base


class ExecutionHistory(Base):
    __tablename__ = "execution_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deal_id = Column(UUID(as_uuid=True), ForeignKey("deals.id"), nullable=False, index=True)
    thread_id = Column(String, nullable=False, index=True)
    checkpoint_id = Column(String, nullable=False, index=True)
    node_name = Column(String, nullable=True)
    current_step = Column(String, nullable=True)
    snapshot_data = Column(JSONB, nullable=True)
    dynamic_instructions = Column(JSON, nullable=True)
    pause_requested = Column(Boolean, default=False)
    version_number = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)

    def __repr__(self):
        return f"<ExecutionHistory deal_id={self.deal_id} checkpoint={self.checkpoint_id}>"
