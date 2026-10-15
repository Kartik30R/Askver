"""
app/schemas/deal_analytics.py

Pydantic models for the DEAL-LEVEL analytics (synthesised across all meetings of a deal).
A new snapshot is generated after every meeting analysis; the previous snapshot is used to
compute deltas ("what changed after this meeting and why").
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.analysis_common import Confidence, Finding, Severity
from app.schemas.meeting_analysis import BuyingRole, SignalStage, Stance


class Trend(str, Enum):
    IMPROVING = "IMPROVING"
    STABLE = "STABLE"
    DECLINING = "DECLINING"
    STALLED = "STALLED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


# ───────────────────────── Deal health ─────────────────────────
class HealthDimensionName(str, Enum):
    BUYER_ENGAGEMENT = "BUYER_ENGAGEMENT"
    PROBLEM_CLARITY = "PROBLEM_CLARITY"
    SOLUTION_FIT = "SOLUTION_FIT"
    DECISION_MAKER_ACCESS = "DECISION_MAKER_ACCESS"
    BUDGET_READINESS = "BUDGET_READINESS"
    COMPETITIVE_POSITION = "COMPETITIVE_POSITION"
    OBJECTION_RESOLUTION = "OBJECTION_RESOLUTION"
    DECISION_PROCESS_CLARITY = "DECISION_PROCESS_CLARITY"
    MOMENTUM_TIMELINE = "MOMENTUM_TIMELINE"
    NEXT_STEP_EXECUTION = "NEXT_STEP_EXECUTION"


class HealthDimension(Finding):
    dimension: HealthDimensionName
    score: int = Field(ge=0, le=10)
    rationale: str
    missing_information: list[str] = Field(default_factory=list)
    source_meeting_ids: list[str] = Field(default_factory=list)


class DealHealth(BaseModel):
    dimensions: list[HealthDimension] = Field(default_factory=list)
    composite_score: Optional[float] = Field(default=None, description="Computed in code, not by the LLM (0-100)")
    methodology_version: str = "1.0"


# ───────────────────────── Momentum ─────────────────────────
class MeetingTrendPoint(BaseModel):
    meeting_id: str
    meeting_title: str
    meeting_date: str
    sentiment: str | None = None
    engagement: Confidence | None = None
    signal_stage: SignalStage | None = None
    scorecard_overall: int | None = None
    unresolved_objections: int | None = None
    discovery_coverage_pct: int | None = None


class MomentumAnalysis(BaseModel):
    overall_trend: Trend
    verdict: str = Field(description="Is the deal getting stronger, weaker or stuck - and why (2-4 sentences)")
    engagement_trend: Trend
    sentiment_trend: Trend
    buying_signal_trend: Trend
    new_stakeholders_entered: list[str] = Field(default_factory=list)
    delays_or_missed_milestones: list[str] = Field(default_factory=list)
    trend_points: list[MeetingTrendPoint] = Field(
        default_factory=list, description="One per meeting, oldest first. Copy values from the meeting analyses."
    )


# ───────────────────────── Risk register ─────────────────────────
class RiskCategory(str, Enum):
    COMMERCIAL = "COMMERCIAL"
    STAKEHOLDER = "STAKEHOLDER"
    COMPETITIVE = "COMPETITIVE"
    TECHNICAL = "TECHNICAL"
    STRATEGIC_FIT = "STRATEGIC_FIT"
    EXECUTION = "EXECUTION"
    PROCUREMENT = "PROCUREMENT"
    TIMING = "TIMING"


class RiskStatus(str, Enum):
    OPEN = "OPEN"
    MITIGATING = "MITIGATING"
    RESOLVED = "RESOLVED"
    ACCEPTED = "ACCEPTED"


class RiskItem(Finding):
    risk_key: str = Field(
        description="Stable snake_case identifier, e.g. 'economic_buyer_not_engaged'. "
        "REUSE the key from the previous register if the same risk persists."
    )
    category: RiskCategory
    title: str
    description: str
    severity: Severity
    status: RiskStatus = RiskStatus.OPEN
    first_seen_meeting_id: str | None = None
    last_seen_meeting_id: str | None = None
    occurrences: int = Field(default=1, description="Number of meetings where it showed up (one risk, not many)")
    mitigation: str | None = None
    suggested_owner: str | None = None


class RiskRegister(BaseModel):
    risks: list[RiskItem] = Field(default_factory=list)
    highest_priority_risk_key: str | None = None


# ───────────────────────── Buying committee ─────────────────────────
class CommitteeMember(Finding):
    name: str
    title: str | None = None
    buying_role: BuyingRole = BuyingRole.UNKNOWN
    role_confirmed: bool = False
    stance: Stance = Stance.UNKNOWN
    engagement: Confidence = Confidence.MEDIUM
    meetings_attended: int = 0
    priorities: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    recommended_engagement: str | None = None


class BuyingCommittee(BaseModel):
    members: list[CommitteeMember] = Field(default_factory=list)
    economic_buyer_access: bool = False
    technical_evaluator_access: bool = False
    champion_identified: bool = False
    champion_strength: Optional[Confidence] = None
    procurement_involved: bool = False
    security_legal_involved: bool = False
    missing_roles: list[BuyingRole] = Field(default_factory=list)
    conflicting_priorities: list[str] = Field(default_factory=list)
    coverage_summary: str = ""
    next_stakeholder_to_engage: str | None = None


# ───────────────────────── Competitive positioning ─────────────────────────
class DealCompetitor(Finding):
    name: str
    confirmed: bool = Field(description="True if the buyer actually named/evaluated them; False = hypothesis")
    buyer_perception: str | None = None
    where_they_may_be_stronger: list[str] = Field(default_factory=list)
    where_we_are_stronger: list[str] = Field(default_factory=list)


class DealCompetitivePositioning(BaseModel):
    competitors: list[DealCompetitor] = Field(default_factory=list)
    evaluation_criteria: list[str] = Field(default_factory=list)
    strongest_differentiators: list[str] = Field(default_factory=list)
    competitive_gaps: list[str] = Field(default_factory=list)
    unresolved_competitive_questions: list[str] = Field(default_factory=list)
    recommended_positioning_changes: list[str] = Field(default_factory=list)


# ───────────────────────── Sales execution ─────────────────────────
class CommitmentRecord(Finding):
    commitment: str
    made_in_meeting_id: str
    owner: str | None = None
    due: str | None = None
    status: str = Field(description="FULFILLED | OPEN | OVERDUE | UNKNOWN (based on later meetings)")


class ExecutionEffectiveness(BaseModel):
    recurring_patterns: list[str] = Field(
        default_factory=list, description="Patterns that repeat across meetings, not one-off critiques"
    )
    repeated_mistake_categories: list[str] = Field(default_factory=list)
    improvements_over_time: list[str] = Field(default_factory=list)
    discovery_quality_trend: Trend = Trend.INSUFFICIENT_DATA
    follow_up_reliability_note: str = ""
    commitments: list[CommitmentRecord] = Field(default_factory=list)
    commitment_reliability_pct: Optional[int] = Field(default=None, ge=0, le=100)


# ───────────────────────── Trackers / warnings ─────────────────────────
class TrackedQuestion(Finding):
    question: str
    asked_by: str | None = None
    first_raised_meeting_id: str | None = None
    status: str = Field(description="OPEN | ANSWERED")
    owner: str | None = None


class ResearchGap(Finding):
    hypothesis_from_research: str
    reality_from_meetings: str
    verdict: str = Field(description="CONFIRMED | CONTRADICTED | NEW_INSIGHT | UNVALIDATED")


class WarningSignal(Finding):
    title: str
    description: str
    severity: Severity
    is_disqualifying: bool = False
    uncertainty_note: str | None = None


class TrackersAnalysis(BaseModel):
    unanswered_questions: list[TrackedQuestion] = Field(default_factory=list)
    research_gaps: list[ResearchGap] = Field(default_factory=list)
    warning_signals: list[WarningSignal] = Field(default_factory=list)
    signal_stage: SignalStage = SignalStage.EXPLORATORY


# ───────────────────────── Win probability ─────────────────────────
class WinFactor(Finding):
    description: str
    impact: Severity = Severity.MEDIUM
    source_meeting_ids: list[str] = Field(default_factory=list)


class WinProbability(BaseModel):
    probability_pct: int = Field(ge=0, le=100)
    previous_pct: Optional[int] = None
    change_pct: Optional[int] = None
    trend: Trend = Trend.INSUFFICIENT_DATA
    confidence: Confidence = Confidence.LOW
    label: str = "AI-estimated win probability (not a calibrated forecast)"
    rationale: str
    supporting_factors: list[WinFactor] = Field(default_factory=list)
    reducing_factors: list[WinFactor] = Field(default_factory=list)
    major_uncertainties: list[str] = Field(default_factory=list)
    conditions_to_improve: list[str] = Field(default_factory=list)
    conditions_to_decline: list[str] = Field(default_factory=list)


# ───────────────────────── Strategy ─────────────────────────
class StrategicAction(Finding):
    rank: int
    action: str
    rationale: str
    impact: Severity
    urgency: Severity
    linked_risk_keys: list[str] = Field(default_factory=list)
    suggested_owner: str | None = None


class DealStrategy(BaseModel):
    top_actions: list[StrategicAction] = Field(default_factory=list, description="Max 5, ranked")
    highest_priority_risk_to_resolve: str | None = None
    next_stakeholder_to_engage: str | None = None
    questions_for_next_meeting: list[str] = Field(default_factory=list)
    documents_to_prepare: list[str] = Field(default_factory=list)
    objections_to_address_before_advancing: list[str] = Field(default_factory=list)
    presentation_changes: list[str] = Field(default_factory=list)
    negotiation_strategy: str | None = None
    suggested_next_meeting_agenda: list[str] = Field(default_factory=list)
    conditions_before_forecasting_close: list[str] = Field(default_factory=list)


# ───────────────────────── Timeline ─────────────────────────
class TimelineEventType(str, Enum):
    MEETING = "MEETING"
    BUYING_SIGNAL = "BUYING_SIGNAL"
    RISK_OPENED = "RISK_OPENED"
    RISK_RESOLVED = "RISK_RESOLVED"
    STAKEHOLDER_CHANGE = "STAKEHOLDER_CHANGE"
    WIN_PROBABILITY_CHANGE = "WIN_PROBABILITY_CHANGE"
    COMMITMENT_FULFILLED = "COMMITMENT_FULFILLED"
    COMMITMENT_MISSED = "COMMITMENT_MISSED"
    STAGE_CHANGE = "STAGE_CHANGE"
    CUSTOMER_DECISION = "CUSTOMER_DECISION"


class TimelineEvent(BaseModel):
    date: str
    meeting_id: str | None = None
    event_type: TimelineEventType
    title: str
    detail: str | None = None


class DealTimeline(BaseModel):
    events: list[TimelineEvent] = Field(default_factory=list, description="Chronological, oldest first")
    what_changed_after_latest_meeting: list[str] = Field(default_factory=list)
    why_assessment_changed: str = ""


# ───────────────────────── Final snapshot ─────────────────────────
class DealAnalyticsResult(BaseModel):
    """Persisted (JSONB) per deal; each regeneration is a new versioned snapshot."""

    deal_id: str
    snapshot_version: int = 1
    schema_version: str = "1.0"
    meetings_analyzed: int = 0
    latest_meeting_id: str | None = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    model_name: str | None = None

    win_probability: Optional[WinProbability] = None
    health: Optional[DealHealth] = None
    momentum: Optional[MomentumAnalysis] = None
    risks: Optional[RiskRegister] = None
    buying_committee: Optional[BuyingCommittee] = None
    competitive: Optional[DealCompetitivePositioning] = None
    execution: Optional[ExecutionEffectiveness] = None
    trackers: Optional[TrackersAnalysis] = None
    strategy: Optional[DealStrategy] = None
    timeline: Optional[DealTimeline] = None

    warnings: list[str] = Field(default_factory=list)
