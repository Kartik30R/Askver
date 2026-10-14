import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.internal_knowledge import InternalKnowledgeAsset
from app.schemas.internal_knowledge import InternalKnowledgeCreate, InternalKnowledgeUpdate

logger = logging.getLogger(__name__)


class InternalKnowledgeRepository:
    """
    Repository for managing global enterprise assets and internal knowledge base operations.
    Fully aligned with InternalKnowledgeAsset ORM model.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, asset_in: InternalKnowledgeCreate) -> InternalKnowledgeAsset:
        db_asset = InternalKnowledgeAsset(**asset_in.model_dump())
        self.db.add(db_asset)
        await self.db.commit()
        await self.db.refresh(db_asset)
        logger.info(f"Created internal knowledge asset '{db_asset.id}' ({db_asset.title})")
        return db_asset

    async def get_by_id(self, asset_id: UUID) -> Optional[InternalKnowledgeAsset]:
        result = await self.db.execute(select(InternalKnowledgeAsset).where(InternalKnowledgeAsset.id == asset_id))
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        asset_type: Optional[str] = None,
        industry_tag: Optional[str] = None,
    ) -> List[InternalKnowledgeAsset]:
        query = select(InternalKnowledgeAsset)
        if asset_type:
            query = query.where(InternalKnowledgeAsset.asset_type == asset_type)
        if industry_tag:
            query = query.where(InternalKnowledgeAsset.industry_tag == industry_tag)
        query = query.order_by(desc(InternalKnowledgeAsset.created_at)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(self, asset_id: UUID, asset_in: InternalKnowledgeUpdate) -> Optional[InternalKnowledgeAsset]:
        db_asset = await self.get_by_id(asset_id)
        if not db_asset:
            return None

        update_data = asset_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_asset, field, value)

        await self.db.commit()
        await self.db.refresh(db_asset)
        logger.info(f"Updated internal knowledge asset '{asset_id}'")
        return db_asset

    async def delete(self, asset_id: UUID) -> bool:
        db_asset = await self.get_by_id(asset_id)
        if not db_asset:
            return False

        await self.db.delete(db_asset)
        await self.db.commit()
        logger.info(f"Deleted internal knowledge asset '{asset_id}'")
        return True

    async def search_by_keyword(self, keyword: str) -> List[InternalKnowledgeAsset]:
        """
        Performs an ILIKE search across title and summary.
        """
        search_term = f"%{keyword}%"
        result = await self.db.execute(
            select(InternalKnowledgeAsset).where(
                or_(
                    InternalKnowledgeAsset.title.ilike(search_term),
                    InternalKnowledgeAsset.summary.ilike(search_term),
                )
            )
        )
        return list(result.scalars().all())