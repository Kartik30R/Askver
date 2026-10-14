from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.execution_history_repository import ExecutionHistoryRepository
from app.repositories.deal_repository import DealRepository


class ExecutionHistoryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.history_repo = ExecutionHistoryRepository(db)
        self.deal_repo = DealRepository(db)

    async def save_execution_checkpoint(
        self,
        deal_id: UUID,
        thread_id: str,
        checkpoint_id: str,
        node_name: Optional[str],
        current_step: str,
        snapshot_data: Dict[str, Any],
        version_number: int = 1,
    ) -> Dict[str, Any]:
        """Save checkpoint to execution history."""
        await self.history_repo.save_checkpoint(
            deal_id=deal_id,
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            node_name=node_name,
            current_step=current_step,
            snapshot_data=snapshot_data,
            version_number=version_number,
        )
        return {
            "saved": True,
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def get_deal_timeline(self, deal_id: UUID) -> List[Dict[str, Any]]:
        """Get timeline of all executions/threads for a deal."""
        threads = await self.history_repo.list_all_threads(deal_id)
        timeline = []

        for thread_id, created_at, current_step in threads:
            checkpoints = await self.history_repo.get_thread_checkpoints(thread_id, deal_id)
            timeline.append({
                "thread_id": thread_id,
                "started_at": created_at.isoformat(),
                "latest_step": current_step,
                "checkpoint_count": len(checkpoints),
                "latest_checkpoint_id": checkpoints[-1].checkpoint_id if checkpoints else None,
            })

        return sorted(timeline, key=lambda x: x["started_at"], reverse=True)

    async def get_thread_history(self, thread_id: str, deal_id: UUID) -> List[Dict[str, Any]]:
        """Get all checkpoints in a thread with summary info."""
        checkpoints = await self.history_repo.get_thread_checkpoints(thread_id, deal_id)
        return [
            {
                "checkpoint_id": cp.checkpoint_id,
                "node_name": cp.node_name,
                "current_step": cp.current_step,
                "timestamp": cp.created_at.isoformat(),
                "paused": cp.pause_requested,
            }
            for cp in checkpoints
        ]

    async def get_checkpoint_state(
        self,
        deal_id: UUID,
        checkpoint_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get full state snapshot at specific checkpoint."""
        history = await self.history_repo.get_checkpoint(checkpoint_id, deal_id)
        if not history:
            return None

        return {
            "checkpoint_id": history.checkpoint_id,
            "thread_id": history.thread_id,
            "node_name": history.node_name,
            "current_step": history.current_step,
            "snapshot_data": history.snapshot_data,
            "timestamp": history.created_at.isoformat(),
        }

    async def prepare_resume_state(
        self,
        deal_id: UUID,
        checkpoint_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get state ready for resuming from a checkpoint."""
        history = await self.history_repo.get_checkpoint(checkpoint_id, deal_id)
        if not history:
            return None

        snapshot = history.snapshot_data or {}
        return {
            **snapshot,
            "resume_from_checkpoint": checkpoint_id,
            "previous_thread_id": history.thread_id,
        }
