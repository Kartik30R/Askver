import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, BigInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class DealDocument(Base):
    """
    Stores metadata for inbound client documents (RFP, RFI, BRD, Scope, Architecture)
    uploaded for a specific deal.
    """
    __tablename__ = "deal_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    deal_id = Column(UUID(as_uuid=True), ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True)
    
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_type = Column(String(50), nullable=False)  # pdf, docx, pptx, txt
    document_category = Column(
        String(50), 
        nullable=False, 
        default="RFP"
    )  # RFP, RFI, BRD, ARCHITECTURE, SCOPE, PRESENTATION
    
    file_size_bytes = Column(BigInteger, nullable=True)
    chunk_count = Column(Integer, default=0, nullable=False)
    vector_collection_name = Column(String(100), nullable=False)  # e.g., 'deal_{deal_id}_docs'
    indexing_status = Column(
        String(50), 
        default="PENDING", 
        nullable=False
    )  # PENDING, PROCESSING, INDEXED, FAILED
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    deal = relationship("Deal", back_populates="documents")