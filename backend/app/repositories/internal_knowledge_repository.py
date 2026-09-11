from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.knowledge import EnterpriseAsset
from app.schemas.knowledge import AssetCreate, AssetUpdate

class InternalKnowledgeRepository:
    """
    Repository for managing global enterprise assets and internal knowledge base operations.
    """
    
    def __init__(self, db: Session):
        self.db = db

    def create(self, asset_in: AssetCreate) -> EnterpriseAsset:
        db_asset = EnterpriseAsset(**asset_in.model_dump())
        self.db.add(db_asset)
        self.db.commit()
        self.db.refresh(db_asset)
        return db_asset

    def get_by_id(self, asset_id: int) -> Optional[EnterpriseAsset]:
        return self.db.query(EnterpriseAsset).filter(EnterpriseAsset.id == asset_id).first()

    def get_all(self, skip: int = 0, limit: int = 100, category: Optional[str] = None) -> List[EnterpriseAsset]:
        query = self.db.query(EnterpriseAsset)
        if category:
            query = query.filter(EnterpriseAsset.category == category)
        return query.order_by(EnterpriseAsset.created_at.desc()).offset(skip).limit(limit).all()

    def update(self, asset_id: int, asset_in: AssetUpdate) -> Optional[EnterpriseAsset]:
        db_asset = self.get_by_id(asset_id)
        if not db_asset:
            return None
            
        update_data = asset_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_asset, field, value)
            
        self.db.commit()
        self.db.refresh(db_asset)
        return db_asset

    def delete(self, asset_id: int) -> bool:
        db_asset = self.get_by_id(asset_id)
        if not db_asset:
            return False
            
        self.db.delete(db_asset)
        self.db.commit()
        return True

    def search_by_keyword(self, keyword: str) -> List[EnterpriseAsset]:
        """
        Performs a basic ILIKE search across title and content. 
        For advanced text search, consider migrating to PostgreSQL full-text search (tsvector).
        """
        search_term = f"%{keyword}%"
        return self.db.query(EnterpriseAsset).filter(
            (EnterpriseAsset.title.ilike(search_term)) | 
            (EnterpriseAsset.content.ilike(search_term))
        ).all()