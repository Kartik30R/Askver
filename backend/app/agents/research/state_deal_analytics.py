"""
app/agents/deal_analytics/state.py

LangGraph state for the deal-level analytics graph.
"""
import operator
from typing import Annotated, Any, Optional, TypedDict

from app.schemas.deal_analytics import (
    BuyingCommittee,
    DealAnalyticsResult,
    DealCompetitivePositioning,
    DealHealth,
    DealStrategy,
    DealTimeline,
    ExecutionEffectiveness,
    MomentumAnalysis,
    RiskRegister,
    TrackersAnalysis,
    WinProbability,
)


class MeetingDigest(TypedDict, total=False):
    """One entry per analysed meeting (oldest first). `analysis` is MeetingAnalysisResult.model_dump(mode='json')."""

    meeting_id: str
    title: str
    meeting_type: Optional[str]
    meeting_date: str
    analysis: dict[str, Any]


class DealAnalyticsState(TypedDict, total=False):
    # ── Inputs ──
    deal_id: str
    owner_id: str
    latest_meeting_id: Optional[str]
    deal_profile: Optional[dict[str, Any]]       # company name, industry, deal size, stage, etc.
    research_brief: Optional[dict[str, Any]]     # the existing CXO research output
    meetings: list[MeetingDigest]                # all analysed meetings for the deal, oldest first
    previous_snapshot: Optional[dict[str, Any]]  # last DealAnalyticsResult.model_dump(), for deltas + stable risk keys
    snapshot_version: int

    # ── Stage 1 (parallel) ──
    health: Optional[DealHealth]
    momentum: Optional[MomentumAnalysis]
    risks: Optional[RiskRegister]
    buying_committee: Optional[BuyingCommittee]
    competitive: Optional[DealCompetitivePositioning]
    execution: Optional[ExecutionEffectiveness]
    trackers: Optional[TrackersAnalysis]

    # ── Stage 2+ (sequential, depend on stage 1) ──
    win_probability: Optional[WinProbability]
    strategy: Optional[DealStrategy]
    timeline: Optional[DealTimeline]

    # ── Bookkeeping ──
    warnings: Annotated[list[str], operator.add]
    result: Optional[DealAnalyticsResult]
