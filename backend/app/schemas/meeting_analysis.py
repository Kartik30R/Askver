"""
app/schemas/meeting_analysis.py

Pydantic models for the PER-MEETING analysis output.
Each section here is produced by one node in the meeting analysis graph.
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.analysis_common import Basis, Confidence, Evidence, Finding, Severity, Side


# ───────────────────────── A. Summary, outcomes, action items ─────────────────────────
class ActionOrigin(str, Enum):
    AGREED = "AGREED"                  # explicitly agreed in the meeting
    AI_RECOMMENDED = "AI_RECOMMENDED"  # suggested by the AI, not committed to


class ActionItem(Finding):
    description: str
    owner: str | None = None
    owner_side: Side = Side.UNKNOWN
    due_date: str | None = Field(default=None, description="As stated, e.g. 'next Friday' or '2026-11-02'")
    origin: ActionOrigin = ActionOrigin.AGREED


class Decision(Finding):
    decision: str
    made_by: str | None = None


class MeetingSummary(BaseModel):
    executive_summary: str = Field(description="4-6 sentences: what happened and where the deal stands")
    key_topics: list[str] = Field(default_factory=list)
    objectives_met: list[str] = Field(default_factory=list, description="Stated objectives that were achieved")
    objectives_missed: list[str] = Field(default_factory=list, description="Stated objectives not achieved")
    decisions: list[Decision] = Field(default_factory=list)
    our_commitments: list[ActionItem] = Field(default_factory=list, description="Deliverables WE promised")
    buyer_requests: list[ActionItem] = Field(default_factory=list, description="Information/materials the buyer asked for")
    buyer_commitments: list[ActionItem] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    next_meeting_requirements: list[str] = Field(default_factory=list)


# ───────────────────────── B. Sentiment and buying signals ─────────────────────────
class Sentiment(str, Enum):
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    MIXED = "MIXED"
    NEGATIVE = "NEGATIVE"


class SignalDirection(str, Enum):
    POSITIVE = "POSITIVE"  # moves the buyer closer to purchase
    NEGATIVE = "NEGATIVE"  # moves them away


class SignalCategory(str, Enum):
    INTEREST = "INTEREST"
    PURCHASE_INTENT = "PURCHASE_INTENT"
    URGENCY = "URGENCY"
    TIME_INVESTMENT = "TIME_INVESTMENT"
    STAKEHOLDER_EXPANSION = "STAKEHOLDER_EXPANSION"
    BUDGET = "BUDGET"
    TRUST = "TRUST"
    HESITATION = "HESITATION"
    DISENGAGEMENT = "DISENGAGEMENT"
    RESISTANCE = "RESISTANCE"


class SignalStage(str, Enum):
    WEAK_INTEREST = "WEAK_INTEREST"
    EXPLORATORY = "EXPLORATORY"
    ACTIVE_EVALUATION = "ACTIVE_EVALUATION"
    CONCRETE_COMMITMENT = "CONCRETE_COMMITMENT"


class BuyingSignal(Finding):
    direction: SignalDirection
    category: SignalCategory
    description: str
    strength: Severity = Field(default=Severity.MEDIUM, description="How strong the signal is (LOW..CRITICAL)")
    is_explicit_commitment: bool = Field(
        default=False, description="True for concrete commitments, False for polite interest"
    )


class SentimentAnalysis(BaseModel):
    overall_sentiment: Sentiment
    sentiment_rationale: str
    interest_level: Confidence = Field(description="LOW/MEDIUM/HIGH interest in the solution")
    purchase_intent: Confidence
    urgency: Confidence
    signal_stage: SignalStage
    signals: list[BuyingSignal] = Field(default_factory=list)
    moving_closer_summary: str = Field(description="What suggests the buyer is moving toward a purchase")
    moving_away_summary: str = Field(description="What suggests the opposite")


# ───────────────────────── C. Sales mistakes and missed opportunities ─────────────────────────
class MistakeCategory(str, Enum):
    MISSED_QUESTION = "MISSED_QUESTION"
    POOR_ANSWER = "POOR_ANSWER"
    UNANSWERED_QUESTION = "UNANSWERED_QUESTION"
    WEAK_OBJECTION_HANDLING = "WEAK_OBJECTION_HANDLING"
    PITCH_OVER_DISCOVERY = "PITCH_OVER_DISCOVERY"
    UNSUPPORTED_CLAIM = "UNSUPPORTED_CLAIM"
    MISSED_ROI = "MISSED_ROI"
    DECISION_MAKER_NOT_IDENTIFIED = "DECISION_MAKER_NOT_IDENTIFIED"
    WEAK_DIFFERENTIATION = "WEAK_DIFFERENTIATION"
    PREMATURE_PRICING = "PREMATURE_PRICING"
    NO_CLEAR_NEXT_STEP = "NO_CLEAR_NEXT_STEP"
    UNQUALIFIED_COMMITMENT = "UNQUALIFIED_COMMITMENT"
    OTHER = "OTHER"


class SalesMistake(Finding):
    category: MistakeCategory
    title: str
    what_happened: str
    why_it_matters: str
    what_to_do_instead: str
    better_example: str = Field(description="A concrete sentence/question the rep could have used")
    deal_impact: str
    severity: Severity = Severity.MEDIUM


class MistakesAnalysis(BaseModel):
    findings: list[SalesMistake] = Field(
        default_factory=list, description="Only evidence-supported mistakes. Each needs >=1 transcript quote."
    )
    strengths: list[str] = Field(default_factory=list, description="Things the team did well (evidence-based)")


# ───────────────────────── D. Customer needs and discovery ─────────────────────────
class NeedItem(Finding):
    description: str
    business_impact: str | None = None


class DiscoveryDimension(str, Enum):
    BUSINESS_PROBLEM = "BUSINESS_PROBLEM"
    BUSINESS_IMPACT = "BUSINESS_IMPACT"
    CURRENT_SOLUTION = "CURRENT_SOLUTION"
    DESIRED_OUTCOME = "DESIRED_OUTCOME"
    QUANTIFIED_VALUE = "QUANTIFIED_VALUE"
    TECHNICAL_REQUIREMENTS = "TECHNICAL_REQUIREMENTS"
    DECISION_PROCESS = "DECISION_PROCESS"
    BUDGET = "BUDGET"
    TIMELINE = "TIMELINE"
    COMPETITION = "COMPETITION"


class DiscoveryCoverageItem(BaseModel):
    dimension: DiscoveryDimension
    covered: bool
    note: str | None = None


class DiscoveryAnalysis(BaseModel):
    stated_needs: list[NeedItem] = Field(default_factory=list)
    inferred_needs: list[NeedItem] = Field(default_factory=list)
    current_solutions: list[NeedItem] = Field(default_factory=list, description="Incumbent tools/processes and limits")
    desired_outcomes: list[NeedItem] = Field(default_factory=list)
    quantified_value: list[NeedItem] = Field(default_factory=list, description="Numbers the buyer gave (cost, volume, savings)")
    requirements: list[NeedItem] = Field(default_factory=list, description="Technical / operational requirements")
    solution_gaps: list[NeedItem] = Field(default_factory=list, description="Needs our solution may not meet")
    unanswered_discovery_questions: list[str] = Field(default_factory=list)
    coverage: list[DiscoveryCoverageItem] = Field(default_factory=list)
    coverage_pct: int = Field(default=0, ge=0, le=100, description="Share of dimensions understood")


# ───────────────────────── E. Objections ─────────────────────────
class ObjectionCategory(str, Enum):
    PRICE = "PRICE"
    FUNCTIONALITY = "FUNCTIONALITY"
    SECURITY = "SECURITY"
    IMPLEMENTATION = "IMPLEMENTATION"
    INTEGRATION = "INTEGRATION"
    TRUST = "TRUST"
    COMPETITION = "COMPETITION"
    TIMING = "TIMING"
    OTHER = "OTHER"


class ObjectionStatus(str, Enum):
    RESOLVED = "RESOLVED"
    PARTIALLY_RESOLVED = "PARTIALLY_RESOLVED"
    UNRESOLVED = "UNRESOLVED"


class Objection(Finding):
    category: ObjectionCategory
    raised_by: str | None = None
    description: str
    severity: Severity = Severity.MEDIUM
    our_response: str | None = None
    status: ObjectionStatus
    status_rationale: str
    recommended_response: str
    follow_up: str | None = None


class ObjectionAnalysis(BaseModel):
    objections: list[Objection] = Field(default_factory=list)
    unresolved_count: int = 0


# ───────────────────────── F. Presentation effectiveness ─────────────────────────
class SlideIssueType(str, Enum):
    IRRELEVANT = "IRRELEVANT"
    INEFFECTIVE = "INEFFECTIVE"
    UNSUPPORTED_CLAIM = "UNSUPPORTED_CLAIM"
    MISSING_PROOF = "MISSING_PROOF"
    PROVOKED_QUESTION = "PROVOKED_QUESTION"
    STRONG = "STRONG"


class SlideFinding(Finding):
    slide_number: int | None = None
    issue_type: SlideIssueType
    description: str
    recommendation: str | None = None


class PresentationAnalysis(BaseModel):
    deck_provided: bool = False
    relevance_to_buyer_priorities: int | None = Field(default=None, ge=0, le=10)
    value_proposition_strength: int | None = Field(default=None, ge=0, le=10)
    differentiation_quality: int | None = Field(default=None, ge=0, le=10)
    slide_findings: list[SlideFinding] = Field(default_factory=list)
    missing_topics: list[str] = Field(default_factory=list)
    missing_proof_points: list[str] = Field(default_factory=list)
    roi_quantification_opportunities: list[str] = Field(default_factory=list)
    recommended_changes_for_next_deck: list[str] = Field(default_factory=list)
    summary: str = ""


# ───────────────────────── G. Stakeholders ─────────────────────────
class BuyingRole(str, Enum):
    ECONOMIC_BUYER = "ECONOMIC_BUYER"
    CHAMPION = "CHAMPION"
    TECHNICAL_EVALUATOR = "TECHNICAL_EVALUATOR"
    END_USER = "END_USER"
    PROCUREMENT = "PROCUREMENT"
    LEGAL_SECURITY = "LEGAL_SECURITY"
    BLOCKER = "BLOCKER"
    INFLUENCER = "INFLUENCER"
    UNKNOWN = "UNKNOWN"


class Stance(str, Enum):
    SUPPORTIVE = "SUPPORTIVE"
    NEUTRAL = "NEUTRAL"
    SKEPTICAL = "SKEPTICAL"
    RESISTANT = "RESISTANT"
    UNKNOWN = "UNKNOWN"


class RoleSource(str, Enum):
    CONFIRMED = "CONFIRMED"  # title/role stated in the meeting or attendee list
    INFERRED = "INFERRED"


class StakeholderProfile(Finding):
    name: str
    title: str | None = None
    side: Side = Side.BUYER
    buying_role: BuyingRole = BuyingRole.UNKNOWN
    role_source: RoleSource = RoleSource.INFERRED
    priorities: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    engagement_level: Confidence = Confidence.MEDIUM
    stance: Stance = Stance.UNKNOWN
    decision_authority: str | None = None
    influence_notes: str | None = None
    commitments: list[str] = Field(default_factory=list)
    engagement_strategy: str | None = None


class StakeholderAnalysis(BaseModel):
    stakeholders: list[StakeholderProfile] = Field(default_factory=list)
    missing_roles: list[BuyingRole] = Field(default_factory=list, description="Roles not seen yet")


# ───────────────────────── H. Competitive intelligence ─────────────────────────
class CompetitorMention(Finding):
    name: str
    context: str
    buyer_perception: str | None = None


class CompetitiveAnalysis(BaseModel):
    competitors: list[CompetitorMention] = Field(default_factory=list)
    buyer_evaluation_criteria: list[NeedItem] = Field(default_factory=list)
    our_apparent_strengths: list[NeedItem] = Field(default_factory=list)
    our_apparent_weaknesses: list[NeedItem] = Field(default_factory=list)
    claims_needing_evidence: list[str] = Field(default_factory=list)
    differentiation_opportunities: list[str] = Field(default_factory=list)
    questions_to_uncover_positioning: list[str] = Field(default_factory=list)


# ───────────────────────── I. Scorecard ─────────────────────────
class ScorecardMetricName(str, Enum):
    OVERALL_EFFECTIVENESS = "OVERALL_EFFECTIVENESS"
    BUYER_ENGAGEMENT = "BUYER_ENGAGEMENT"
    DISCOVERY_EFFECTIVENESS = "DISCOVERY_EFFECTIVENESS"
    VALUE_PROP_ALIGNMENT = "VALUE_PROP_ALIGNMENT"
    OBJECTION_HANDLING = "OBJECTION_HANDLING"
    COMPETITIVE_POSITIONING = "COMPETITIVE_POSITIONING"
    NEXT_STEP_CLARITY = "NEXT_STEP_CLARITY"


class ScorecardMetric(Finding):
    metric: ScorecardMetricName
    score: int = Field(ge=0, le=10)
    explanation: str


class MeetingScorecard(BaseModel):
    metrics: list[ScorecardMetric] = Field(default_factory=list)


# ───────────────────────── J. Recommended next actions ─────────────────────────
class NextAction(Finding):
    action: str
    rationale: str
    impact: Severity = Severity.MEDIUM
    urgency: Severity = Severity.MEDIUM
    suggested_owner: str | None = None
    origin: ActionOrigin = ActionOrigin.AI_RECOMMENDED


class NextActionsAnalysis(BaseModel):
    actions: list[NextAction] = Field(default_factory=list, description="Ranked: highest priority first")
    next_meeting_questions: list[str] = Field(default_factory=list)
    suggested_agenda: list[str] = Field(default_factory=list)


# ───────────────────────── Final assembled result ─────────────────────────
class AnalysisStatus(str, Enum):
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"   # some sections failed
    FAILED = "FAILED"


class MeetingAnalysisResult(BaseModel):
    """The object persisted (JSONB) against a meeting and fed into deal analytics."""

    meeting_id: str
    deal_id: str
    status: AnalysisStatus = AnalysisStatus.COMPLETED
    schema_version: str = "1.0"
    model_name: str | None = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    summary: Optional[MeetingSummary] = None
    scorecard: Optional[MeetingScorecard] = None
    sentiment: Optional[SentimentAnalysis] = None
    mistakes: Optional[MistakesAnalysis] = None
    discovery: Optional[DiscoveryAnalysis] = None
    objections: Optional[ObjectionAnalysis] = None
    presentation: Optional[PresentationAnalysis] = None
    stakeholders: Optional[StakeholderAnalysis] = None
    competitive: Optional[CompetitiveAnalysis] = None
    next_actions: Optional[NextActionsAnalysis] = None

    warnings: list[str] = Field(default_factory=list)
    unverified_quote_count: int = 0
