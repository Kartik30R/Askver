import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, BigInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class InternalKnowledgeAsset(Base):
    """
    Stores metadata for global reusable enterprise assets
    (Proposals, Case Studies, SoWs, Success Stories, Accelerators).
    """
    __tablename__ = "internal_knowledge_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String(255), nullable=False, index=True)
    
    asset_type = Column(
        String(50), 
        nullable=False, 
        index=True
    )  # CASE_STUDY, PROPOSAL, SOW, SUCCESS_STORY, PRESENTATION, SOLUTION_ACCELERATOR
    
    industry_tag = Column(String(100), nullable=True, index=True)  # e.g., BFSI, Retail, Healthcare
    technology_tags = Column(JSONB, nullable=True)  # e.g., ["Flutter", "Go", "PostgreSQL", "AWS"]
    
    file_path = Column(String(512), nullable=False)
    file_type = Column(String(50), nullable=False)
    
    summary = Column(String(1000), nullable=True)
    vector_doc_id = Column(String(255), nullable=True, index=True)  # PGVector document ID reference
    indexing_status = Column(String(50), default="INDEXED", nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)