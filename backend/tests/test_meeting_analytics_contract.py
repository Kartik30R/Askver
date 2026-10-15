from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.schemas.deal_analytics import DealAnalyticsResult
from app.schemas.meeting_analysis import MeetingAnalysisResult
from app.services.meeting_analytics_service import MeetingAnalyticsService


@pytest.mark.asyncio
async def test_analyze_meeting_returns_meeting_analysis_result(monkeypatch):
    service = MeetingAnalyticsService.__new__(MeetingAnalyticsService)
    meeting = SimpleNamespace(
        id=uuid4(),
        title="Discovery call",
        meeting_type="Customer Call",
        meeting_date=date(2026, 10, 15),
        summary="Strong discovery",
    )
    fake_db = SimpleNamespace(
        get=lambda *args, **kwargs: SimpleNamespace(owner_id=uuid4()),
        execute=lambda *args, **kwargs: SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [])),
    )
    service.db = fake_db
    service.meeting_service = SimpleNamespace(get_meeting_for_deal=lambda *args, **kwargs: meeting)
    service.meeting_repo = SimpleNamespace(list_for_deal=lambda *args, **kwargs: [])
    service.deal_service = SimpleNamespace(get_deal_context=lambda *args, **kwargs: {"active_state": {}})

    async def fake_run_meeting_analysis(**kwargs):
        return MeetingAnalysisResult(
            meeting_id=str(meeting.id),
            deal_id=str(uuid4()),
            summary=None,
            warnings=[],
        )

    monkeypatch.setattr(
        "app.services.meeting_analytics_service.run_meeting_analysis",
        fake_run_meeting_analysis,
    )

    result = await service.analyze_meeting(
        deal_id=uuid4(),
        meeting_id=meeting.id,
        owner_id=uuid4(),
    )

    assert isinstance(result, MeetingAnalysisResult)
    assert result.meeting_id == str(meeting.id)


@pytest.mark.asyncio
async def test_analyze_deal_returns_deal_analytics_result(monkeypatch):
    service = MeetingAnalyticsService.__new__(MeetingAnalyticsService)
    meeting = SimpleNamespace(
        id=uuid4(),
        title="Discovery call",
        meeting_type="Customer Call",
        meeting_date=date(2026, 10, 15),
        summary="Strong discovery",
    )
    fake_db = SimpleNamespace(
        get=lambda *args, **kwargs: SimpleNamespace(owner_id=uuid4()),
        execute=lambda *args, **kwargs: SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [])),
    )
    service.db = fake_db
    service.meeting_repo = SimpleNamespace(list_for_deal=lambda *args, **kwargs: [meeting])
    service.deal_service = SimpleNamespace(
        get_deal_context=lambda *args, **kwargs: {"active_state": {}, "deal": {}},
        intel_repo=SimpleNamespace(
            get_latest_intelligence_snapshot=lambda *args, **kwargs: None,
            save_intelligence_snapshot=lambda *args, **kwargs: None,
        ),
    )

    async def fake_run_meeting_analysis(**kwargs):
        return MeetingAnalysisResult(
            meeting_id=str(meeting.id),
            deal_id=str(uuid4()),
            summary=None,
            warnings=[],
        )

    async def fake_run_deal_analytics(**kwargs):
        return DealAnalyticsResult(
            deal_id=str(uuid4()),
            snapshot_version=1,
            meetings_analyzed=1,
            latest_meeting_id=str(meeting.id),
        )

    monkeypatch.setattr(
        "app.services.meeting_analytics_service.run_meeting_analysis",
        fake_run_meeting_analysis,
    )
    monkeypatch.setattr(
        "app.services.meeting_analytics_service.run_deal_analytics",
        fake_run_deal_analytics,
    )

    result = await service.analyze_deal(
        deal_id=uuid4(),
        owner_id=uuid4(),
    )

    assert isinstance(result, DealAnalyticsResult)
    assert result.meetings_analyzed == 1
