"""
app/agents/meeting_analysis/state.py

LangGraph state for the per-meeting analysis graph.
Each analyzer node writes to its OWN key, so parallel fan-out needs no custom reducers
(only `warnings` is appended to by many nodes, so it uses operator.add).
"""
import operator
from typing import Annotated, Any, Optional, TypedDict

from app.schemas.meeting_analysis import (
    CompetitiveAnalysis,
    DiscoveryAnalysis,
    MeetingAnalysisResult,
    MeetingScorecard,
    MeetingSummary,
    MistakesAnalysis,
    NextActionsAnalysis,
    ObjectionAnalysis,
    PresentationAnalysis,
    SentimentAnalysis,
    StakeholderAnalysis,
)


class MeetingAnalysisState(TypedDict, total=False):
    # ── Inputs (filled by the service before invoking the graph) ──
    meeting_id: str
    deal_id: str
    owner_id: str
    title: str
    meeting_type: Optional[str]          # Customer Call / Board Review / Internal Alignment / QBR
    meeting_date: str
    attendees: Optional[str]
    objectives: Optional[str]
    notes: Optional[str]
    transcript_text: str

    # Optional supporting context
    deck_text: Optional[str]             # extracted text of presentation, with "--- Slide N ---" markers
    supporting_docs_text: Optional[str]  # customer notes, etc.
    deal_context: Optional[dict[str, Any]]  # CXO research brief: company, buyer priorities, hypotheses
    previous_meetings_digest: Optional[str]  # short digest of earlier meetings (open items, commitments)

    # ── Derived by preprocess ──
    transcript_stats: dict[str, Any]     # word_count, speakers, has_timestamps

    # ── Analyzer outputs (one key per node) ──
    summary: Optional[MeetingSummary]
    sentiment: Optional[SentimentAnalysis]
    mistakes: Optional[MistakesAnalysis]
    discovery: Optional[DiscoveryAnalysis]
    objections: Optional[ObjectionAnalysis]
    presentation: Optional[PresentationAnalysis]
    stakeholders: Optional[StakeholderAnalysis]
    competitive: Optional[CompetitiveAnalysis]

    # Second-stage outputs (depend on the above)
    scorecard: Optional[MeetingScorecard]
    next_actions: Optional[NextActionsAnalysis]

    # ── Bookkeeping ──
    warnings: Annotated[list[str], operator.add]
    unverified_quote_count: int
    result: Optional[MeetingAnalysisResult]
