from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.research.graph_deal_analytics import run_deal_analytics
from app.agents.research.graph_meeting_analysis import run_meeting_analysis
from app.db.models.deal import Deal
from app.db.models.meeting import Meeting
from app.db.models.meeting_document import MeetingDocument
from app.repositories.meeting_repository import MeetingRepository
from app.schemas.deal_analytics import DealAnalyticsResult
from app.schemas.meeting_analysis import MeetingAnalysisResult
from app.services.deal_service import DealService
from app.services.meeting_service import MeetingService


class MeetingAnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.meeting_service = MeetingService(db)
        self.meeting_repo = MeetingRepository(db)
        self.deal_service = DealService(db)

    async def _latest_snapshot_data(self, deal_id: UUID) -> dict[str, Any]:
        snapshot = await self.deal_service.intel_repo.get_latest_intelligence_snapshot(deal_id)
        if snapshot is None:
            return {}
        data = snapshot.snapshot_data or {}
        return data if isinstance(data, dict) else {}

    async def _persist_meeting_analysis(self, *, deal_id: UUID, meeting_id: UUID, result: MeetingAnalysisResult) -> None:
        snapshot_data = await self._latest_snapshot_data(deal_id)
        meeting_map = snapshot_data.setdefault("meeting_analytics", {})
        if not isinstance(meeting_map, dict):
            meeting_map = {}
            snapshot_data["meeting_analytics"] = meeting_map
        meeting_map[str(meeting_id)] = result.model_dump(mode="json")

        latest_snapshot = await self.deal_service.intel_repo.get_latest_intelligence_snapshot(deal_id)
        thread_id = latest_snapshot.thread_id if latest_snapshot else f"deal_{deal_id}_analytics"
        await self.deal_service.intel_repo.save_intelligence_snapshot(
            deal_id=deal_id,
            thread_id=thread_id,
            current_step="MEETING_ANALYSIS_SAVED",
            snapshot_data=snapshot_data,
        )

    async def _persist_deal_analysis(self, *, deal_id: UUID, result: DealAnalyticsResult) -> None:
        snapshot_data = await self._latest_snapshot_data(deal_id)
        snapshot_data["deal_analytics"] = result.model_dump(mode="json")

        latest_snapshot = await self.deal_service.intel_repo.get_latest_intelligence_snapshot(deal_id)
        thread_id = latest_snapshot.thread_id if latest_snapshot else f"deal_{deal_id}_analytics"
        await self.deal_service.intel_repo.save_intelligence_snapshot(
            deal_id=deal_id,
            thread_id=thread_id,
            current_step="DEAL_ANALYSIS_SAVED",
            snapshot_data=snapshot_data,
        )

    async def _ensure_deal_access(self, deal_id: UUID, owner_id: UUID) -> Deal:
        deal = await self.db.get(Deal, deal_id)
        if deal is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
        if str(deal.owner_id) != str(owner_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this deal")
        return deal

    async def get_meeting_analysis(self, *, deal_id: UUID, meeting_id: UUID, owner_id: UUID) -> MeetingAnalysisResult:
        await self._ensure_deal_access(deal_id, owner_id)
        snapshot_data = await self._latest_snapshot_data(deal_id)
        meeting_map = snapshot_data.get("meeting_analytics") or {}
        if not isinstance(meeting_map, dict):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No persisted meeting analysis found.")
        payload = meeting_map.get(str(meeting_id))
        if payload is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No persisted meeting analysis found.")
        return MeetingAnalysisResult.model_validate(payload)

    async def get_deal_analysis(self, *, deal_id: UUID, owner_id: UUID) -> DealAnalyticsResult:
        await self._ensure_deal_access(deal_id, owner_id)
        snapshot_data = await self._latest_snapshot_data(deal_id)
        payload = snapshot_data.get("deal_analytics")
        if payload is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No persisted deal analysis found.")
        return DealAnalyticsResult.model_validate(payload)

    async def _meeting_supporting_docs_text(self, meeting_id: UUID) -> str | None:
        result = await self.db.execute(
            select(MeetingDocument)
            .where(MeetingDocument.meeting_id == meeting_id)
            .order_by(MeetingDocument.created_at.asc())
        )
        docs = result.scalars().all()
        if not docs:
            return None

        chunks: list[str] = []
        for doc in docs:
            text = self._read_document_text(doc)
            if text:
                chunks.append(f"--- {doc.original_filename} ---\n{text}")

        return "\n\n".join(chunks) if chunks else None

    def _read_document_text(self, doc: MeetingDocument) -> str | None:
        candidates: list[str] = []
        if doc.extracted_text_path:
            candidates.append(doc.extracted_text_path)
        if doc.storage_path:
            candidates.append(doc.storage_path)

        for candidate in candidates:
            path = Path(candidate)
            if not path.exists():
                continue
            try:
                if path.suffix.lower() in {".txt", ".md", ".csv", ".json"}:
                    return path.read_text(encoding="utf-8", errors="ignore")
                if path.suffix.lower() == ".pdf":
                    return ""  # PDF extraction is handled elsewhere; no text file exists yet.
                if path.suffix.lower() in {".docx", ".pptx"}:
                    return path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
        return None

    def _build_previous_meetings_digest(self, meetings: list[Meeting]) -> str:
        if not meetings:
            return "No previous meetings for this deal."

        entries: list[str] = []
        for meeting in meetings:
            summary = (meeting.summary or "No summary yet").strip().replace("\n", " ")
            entries.append(
                f"- {meeting.meeting_date.isoformat()} | {meeting.title} | {meeting.meeting_type or 'Meeting'}: {summary[:400]}"
            )
        return "\n".join(entries)

    async def analyze_meeting(self, *, deal_id: UUID, meeting_id: UUID, owner_id: UUID) -> MeetingAnalysisResult:
        await self._ensure_deal_access(deal_id, owner_id)
        meeting = await self.meeting_service.get_meeting_for_deal(deal_id, meeting_id, owner_id=owner_id)

        deal_context = await self.deal_service.get_deal_context(deal_id)
        research_brief = (deal_context or {}).get("active_state") or None

        prior_meetings = [
            item for item in await self.meeting_repo.list_for_deal(deal_id) if str(item.id) != str(meeting.id)
        ]
        previous_meetings_digest = self._build_previous_meetings_digest(prior_meetings)
        supporting_docs_text = await self._meeting_supporting_docs_text(meeting.id)

        result = await run_meeting_analysis(
            meeting=meeting,
            deck_text=None,
            supporting_docs_text=supporting_docs_text,
            deal_context=research_brief,
            previous_meetings_digest=previous_meetings_digest,
        )
        await self._persist_meeting_analysis(deal_id=deal_id, meeting_id=meeting_id, result=result)
        return result

    async def analyze_deal(self, *, deal_id: UUID, owner_id: UUID) -> DealAnalyticsResult:
        await self._ensure_deal_access(deal_id, owner_id)
        meetings = await self.meeting_repo.list_for_deal(deal_id)
        if not meetings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No meetings found for this deal to analyze.",
            )

        deal_context = await self.deal_service.get_deal_context(deal_id)
        research_brief = (deal_context or {}).get("active_state") or None
        deal_profile = {
            "deal_id": str(deal_id),
            "title": deal_context.get("deal", {}).get("title") if deal_context else None,
            "target_company": deal_context.get("deal", {}).get("target_company") if deal_context else None,
            "target_industry": deal_context.get("deal", {}).get("target_industry") if deal_context else None,
            "meeting_objective": deal_context.get("deal", {}).get("meeting_objective") if deal_context else None,
            "status": deal_context.get("deal", {}).get("status") if deal_context else None,
        }

        meeting_payload: list[dict[str, Any]] = []
        for meeting in meetings:
            previous_meetings = [item for item in meetings if str(item.id) != str(meeting.id)]
            supporting_docs_text = await self._meeting_supporting_docs_text(meeting.id)
            analysis_result = await run_meeting_analysis(
                meeting=meeting,
                deck_text=None,
                supporting_docs_text=supporting_docs_text,
                deal_context=research_brief,
                previous_meetings_digest=self._build_previous_meetings_digest(previous_meetings),
            )
            meeting_payload.append(
                {
                    "meeting_id": str(meeting.id),
                    "title": meeting.title,
                    "meeting_type": meeting.meeting_type,
                    "meeting_date": meeting.meeting_date.isoformat(),
                    "analysis": analysis_result.model_dump(mode="json"),
                }
            )

        previous_snapshot = None
        latest_snapshot = await self.deal_service.intel_repo.get_latest_intelligence_snapshot(deal_id)
        if latest_snapshot and isinstance(latest_snapshot.snapshot_data, dict):
            previous_snapshot = latest_snapshot.snapshot_data.get("deal_analytics")

        deal_analytics = await run_deal_analytics(
            deal_id=str(deal_id),
            owner_id=str(owner_id),
            meetings=sorted(meeting_payload, key=lambda item: item["meeting_date"]),
            deal_profile=deal_profile,
            research_brief=research_brief,
            previous_snapshot=previous_snapshot,
            latest_meeting_id=str(meetings[-1].id),
        )

        await self._persist_deal_analysis(deal_id=deal_id, result=deal_analytics)
        return deal_analytics
