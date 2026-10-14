from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.execution_history import ExecutionHistory


class ExecutionHistoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_checkpoint(
        self,
        deal_id: UUID,
        thread_id: str,
        checkpoint_id: str,
        node_name: Optional[str],
        current_step: str,
        snapshot_data: Dict[str, Any],
        version_number: int = 1,
        user_id: Optional[UUID] = None,
    ) -> ExecutionHistory:
        """Save execution checkpoint to history."""
        history = ExecutionHistory(
            deal_id=deal_id,
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            node_name=node_name,
            current_step=current_step,
            snapshot_data=snapshot_data,
            dynamic_instructions=snapshot_data.get("dynamic_instructions"),
            pause_requested=snapshot_data.get("pause_requested", False),
            version_number=version_number,
            created_by=user_id,
        )
        self.db.add(history)
        await self.db.commit()
        return history

    async def get_checkpoint(self, checkpoint_id: str, deal_id: UUID) -> Optional[ExecutionHistory]:
        """Get specific checkpoint."""
        result = await self.db.execute(
            select(ExecutionHistory).where(
                and_(
                    ExecutionHistory.checkpoint_id == checkpoint_id,
                    ExecutionHistory.deal_id == deal_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_deal_history(self, deal_id: UUID, limit: int = 100) -> List[ExecutionHistory]:
        """Get all checkpoints for a deal, newest first."""
        result = await self.db.execute(
            select(ExecutionHistory)
            .where(ExecutionHistory.deal_id == deal_id)
            .order_by(desc(ExecutionHistory.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_thread_checkpoints(self, thread_id: str, deal_id: UUID) -> List[ExecutionHistory]:
        """Get all checkpoints in a thread."""
        result = await self.db.execute(
            select(ExecutionHistory)
            .where(
                and_(
                    ExecutionHistory.thread_id == thread_id,
                    ExecutionHistory.deal_id == deal_id,
                )
            )
            .order_by(ExecutionHistory.created_at)
        )
        return list(result.scalars().all())

    async def get_latest_checkpoint(self, deal_id: UUID) -> Optional[ExecutionHistory]:
        """Get most recent checkpoint for a deal."""
        result = await self.db.execute(
            select(ExecutionHistory)
            .where(ExecutionHistory.deal_id == deal_id)
            .order_by(desc(ExecutionHistory.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_thread_at_checkpoint(self, thread_id: str) -> Optional[ExecutionHistory]:
        """Get latest checkpoint in thread."""
        result = await self.db.execute(
            select(ExecutionHistory)
            .where(ExecutionHistory.thread_id == thread_id)
            .order_by(desc(ExecutionHistory.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_all_threads(self, deal_id: UUID) -> List[tuple]:
        """List all unique threads (executions) for a deal with latest checkpoint."""
        result = await self.db.execute(
            select(
                ExecutionHistory.thread_id,
                ExecutionHistory.created_at,
                ExecutionHistory.current_step,
            )
            .where(ExecutionHistory.deal_id == deal_id)
            .distinct(ExecutionHistory.thread_id)
            .order_by(ExecutionHistory.thread_id, desc(ExecutionHistory.created_at))
        )
        return list(result.all())
