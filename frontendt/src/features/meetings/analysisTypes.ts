/**
 * analysisTypes.ts
 *
 * One-to-one mirror of the backend Pydantic models:
 *   app/schemas/analysis_common.py
 *   app/schemas/meeting_analysis.py   (root: MeetingAnalysisResult)
 *   app/schemas/deal_analytics.py     (root: DealAnalyticsResult)
 *
 * Rules used to translate Python -> TypeScript
 *   - Enum                      -> string-literal union (same member names)
 *   - X | None / Optional[X]    -> X | null
 *   - fields with defaults      -> REQUIRED (the API always serialises them)
 *   - list[X]                   -> X[]
 *   - datetime / date           -> string (ISO 8601)
 *   - no index signatures, no Record<string, unknown>
 *
 * When a Python model changes, this file must change with it (ideally generate it
 * from /openapi.json with openapi-typescript and re-export the names below).
 */

// ───────────────────────── Shared enums (analysis_common.py) ─────────────────────────
export type AnalysisStatus = 'COMPLETED' | 'PARTIAL' | 'FAILED'
export type Basis = 'STATED' | 'INFERRED'
export type Confidence = 'LOW' | 'MEDIUM' | 'HIGH'
export type Severity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
export type Side = 'OUR_TEAM' | 'BUYER' | 'UNKNOWN'
export type EvidenceSource = 'TRANSCRIPT' | 'PRESENTATION' | 'NOTES' | 'RESEARCH' | 'PRIOR_MEETING'

export type MeetingType = 'Customer Call' | 'Board Review' | 'Internal Alignment' | 'QBR' | string

// ───────────────────────── Shared models ─────────────────────────
export interface Evidence {
  source: EvidenceSource
  quote: string
  speaker: string | null
  timestamp: string | null
  slide_number: number | null
  meeting_id: string | null
  /** Set by the backend pipeline: true only if the quote was found in the source text. */
  verified: boolean
}

/** Python: Finding. Base of every analytical finding. */
export interface AnalysisFinding {
  basis: Basis
  confidence: Confidence
  evidence: Evidence[]
}

// ───────────────────────── Meeting analysis: enums ─────────────────────────
export type ActionOrigin = 'AGREED' | 'AI_RECOMMENDED'
export type Sentiment = 'POSITIVE' | 'NEUTRAL' | 'MIXED' | 'NEGATIVE'
export type SignalDirection = 'POSITIVE' | 'NEGATIVE'
export type SignalCategory =
  | 'INTEREST'
  | 'PURCHASE_INTENT'
  | 'URGENCY'
  | 'TIME_INVESTMENT'
  | 'STAKEHOLDER_EXPANSION'
  | 'BUDGET'
  | 'TRUST'
  | 'HESITATION'
  | 'DISENGAGEMENT'
  | 'RESISTANCE'
export type SignalStage = 'WEAK_INTEREST' | 'EXPLORATORY' | 'ACTIVE_EVALUATION' | 'CONCRETE_COMMITMENT'
export type MistakeCategory =
  | 'MISSED_QUESTION'
  | 'POOR_ANSWER'
  | 'UNANSWERED_QUESTION'
  | 'WEAK_OBJECTION_HANDLING'
  | 'PITCH_OVER_DISCOVERY'
  | 'UNSUPPORTED_CLAIM'
  | 'MISSED_ROI'
  | 'DECISION_MAKER_NOT_IDENTIFIED'
  | 'WEAK_DIFFERENTIATION'
  | 'PREMATURE_PRICING'
  | 'NO_CLEAR_NEXT_STEP'
  | 'UNQUALIFIED_COMMITMENT'
  | 'OTHER'
export type DiscoveryDimension =
  | 'BUSINESS_PROBLEM'
  | 'BUSINESS_IMPACT'
  | 'CURRENT_SOLUTION'
  | 'DESIRED_OUTCOME'
  | 'QUANTIFIED_VALUE'
  | 'TECHNICAL_REQUIREMENTS'
  | 'DECISION_PROCESS'
  | 'BUDGET'
  | 'TIMELINE'
  | 'COMPETITION'
export type ObjectionCategory =
  | 'PRICE'
  | 'FUNCTIONALITY'
  | 'SECURITY'
  | 'IMPLEMENTATION'
  | 'INTEGRATION'
  | 'TRUST'
  | 'COMPETITION'
  | 'TIMING'
  | 'OTHER'
export type ObjectionStatus = 'RESOLVED' | 'PARTIALLY_RESOLVED' | 'UNRESOLVED'
export type SlideIssueType =
  | 'IRRELEVANT'
  | 'INEFFECTIVE'
  | 'UNSUPPORTED_CLAIM'
  | 'MISSING_PROOF'
  | 'PROVOKED_QUESTION'
  | 'STRONG'
export type BuyingRole =
  | 'ECONOMIC_BUYER'
  | 'CHAMPION'
  | 'TECHNICAL_EVALUATOR'
  | 'END_USER'
  | 'PROCUREMENT'
  | 'LEGAL_SECURITY'
  | 'BLOCKER'
  | 'INFLUENCER'
  | 'UNKNOWN'
export type Stance = 'SUPPORTIVE' | 'NEUTRAL' | 'SKEPTICAL' | 'RESISTANT' | 'UNKNOWN'
export type RoleSource = 'CONFIRMED' | 'INFERRED'
export type ScorecardMetricName =
  | 'OVERALL_EFFECTIVENESS'
  | 'BUYER_ENGAGEMENT'
  | 'DISCOVERY_EFFECTIVENESS'
  | 'VALUE_PROP_ALIGNMENT'
  | 'OBJECTION_HANDLING'
  | 'COMPETITIVE_POSITIONING'
  | 'NEXT_STEP_CLARITY'

// ───────────────────────── Meeting analysis: models ─────────────────────────
// A. Summary, outcomes, action items
export interface ActionItem extends AnalysisFinding {
  description: string
  owner: string | null
  owner_side: Side
  /** As stated in the meeting, e.g. "next Friday" or "2026-11-02". */
  due_date: string | null
  origin: ActionOrigin
}

export interface Decision extends AnalysisFinding {
  decision: string
  made_by: string | null
}

/** Python: MeetingSummary is a plain BaseModel (NOT a Finding). */
export interface MeetingSummary {
  executive_summary: string
  key_topics: string[]
  objectives_met: string[]
  objectives_missed: string[]
  decisions: Decision[]
  our_commitments: ActionItem[]
  buyer_requests: ActionItem[]
  buyer_commitments: ActionItem[]
  unresolved_questions: string[]
  next_meeting_requirements: string[]
}

// B. Sentiment and buying signals
export interface BuyingSignal extends AnalysisFinding {
  direction: SignalDirection
  category: SignalCategory
  description: string
  strength: Severity
  is_explicit_commitment: boolean
}

export interface SentimentAnalysis {
  overall_sentiment: Sentiment
  sentiment_rationale: string
  interest_level: Confidence
  purchase_intent: Confidence
  urgency: Confidence
  signal_stage: SignalStage
  signals: BuyingSignal[]
  moving_closer_summary: string
  moving_away_summary: string
}

// C. Sales mistakes
export interface SalesMistake extends AnalysisFinding {
  category: MistakeCategory
  title: string
  what_happened: string
  why_it_matters: string
  what_to_do_instead: string
  better_example: string
  deal_impact: string
  severity: Severity
}

export interface MistakesAnalysis {
  findings: SalesMistake[]
  strengths: string[]
}

// D. Discovery
export interface NeedItem extends AnalysisFinding {
  description: string
  business_impact: string | null
}

export interface DiscoveryCoverageItem {
  dimension: DiscoveryDimension
  covered: boolean
  note: string | null
}

export interface DiscoveryAnalysis {
  stated_needs: NeedItem[]
  inferred_needs: NeedItem[]
  current_solutions: NeedItem[]
  desired_outcomes: NeedItem[]
  quantified_value: NeedItem[]
  requirements: NeedItem[]
  solution_gaps: NeedItem[]
  unanswered_discovery_questions: string[]
  coverage: DiscoveryCoverageItem[]
  /** 0-100 */
  coverage_pct: number
}

// E. Objections
export interface Objection extends AnalysisFinding {
  category: ObjectionCategory
  raised_by: string | null
  description: string
  severity: Severity
  our_response: string | null
  status: ObjectionStatus
  status_rationale: string
  recommended_response: string
  follow_up: string | null
}

export interface ObjectionAnalysis {
  objections: Objection[]
  unresolved_count: number
}

// F. Presentation
export interface SlideFinding extends AnalysisFinding {
  slide_number: number | null
  issue_type: SlideIssueType
  description: string
  recommendation: string | null
}

export interface PresentationAnalysis {
  deck_provided: boolean
  /** 0-10 or null */
  relevance_to_buyer_priorities: number | null
  value_proposition_strength: number | null
  differentiation_quality: number | null
  slide_findings: SlideFinding[]
  missing_topics: string[]
  missing_proof_points: string[]
  roi_quantification_opportunities: string[]
  recommended_changes_for_next_deck: string[]
  summary: string
}

// G. Stakeholders
export interface StakeholderProfile extends AnalysisFinding {
  name: string
  title: string | null
  side: Side
  buying_role: BuyingRole
  role_source: RoleSource
  priorities: string[]
  concerns: string[]
  engagement_level: Confidence
  stance: Stance
  decision_authority: string | null
  influence_notes: string | null
  commitments: string[]
  engagement_strategy: string | null
}

export interface StakeholderAnalysis {
  stakeholders: StakeholderProfile[]
  missing_roles: BuyingRole[]
}

// H. Competitive intelligence
export interface CompetitorMention extends AnalysisFinding {
  name: string
  context: string
  buyer_perception: string | null
}

export interface CompetitiveAnalysis {
  competitors: CompetitorMention[]
  buyer_evaluation_criteria: NeedItem[]
  our_apparent_strengths: NeedItem[]
  our_apparent_weaknesses: NeedItem[]
  claims_needing_evidence: string[]
  differentiation_opportunities: string[]
  questions_to_uncover_positioning: string[]
}

// I. Scorecard
export interface ScorecardMetric extends AnalysisFinding {
  metric: ScorecardMetricName
  /** 0-10 */
  score: number
  explanation: string
}

export interface MeetingScorecard {
  metrics: ScorecardMetric[]
}

// J. Next actions
export interface NextAction extends AnalysisFinding {
  action: string
  rationale: string
  impact: Severity
  urgency: Severity
  suggested_owner: string | null
  origin: ActionOrigin
}

export interface NextActionsAnalysis {
  /** Ranked: highest priority first. */
  actions: NextAction[]
  next_meeting_questions: string[]
  suggested_agenda: string[]
}

/**
 * PENDING BACKEND: exposes MeetingAnalysisState.transcript_stats.
 * Marked optional on MeetingAnalysisResult until the backend adds it.
 */
export interface TranscriptStats {
  word_count: number
  speakers: string[]
  has_timestamps: boolean
}

export interface MeetingAnalysisResult {
  meeting_id: string
  deal_id: string
  status: AnalysisStatus
  schema_version: string
  model_name: string | null
  generated_at: string
  summary: MeetingSummary | null
  scorecard: MeetingScorecard | null
  sentiment: SentimentAnalysis | null
  mistakes: MistakesAnalysis | null
  discovery: DiscoveryAnalysis | null
  objections: ObjectionAnalysis | null
  presentation: PresentationAnalysis | null
  stakeholders: StakeholderAnalysis | null
  competitive: CompetitiveAnalysis | null
  next_actions: NextActionsAnalysis | null
  warnings: string[]
  unverified_quote_count: number
  /** PENDING BACKEND (see TranscriptStats). */
  transcript_stats?: TranscriptStats | null
}

// ───────────────────────── Deal analytics: enums ─────────────────────────
export type Trend = 'IMPROVING' | 'STABLE' | 'DECLINING' | 'STALLED' | 'INSUFFICIENT_DATA'
export type HealthDimensionName =
  | 'BUYER_ENGAGEMENT'
  | 'PROBLEM_CLARITY'
  | 'SOLUTION_FIT'
  | 'DECISION_MAKER_ACCESS'
  | 'BUDGET_READINESS'
  | 'COMPETITIVE_POSITION'
  | 'OBJECTION_RESOLUTION'
  | 'DECISION_PROCESS_CLARITY'
  | 'MOMENTUM_TIMELINE'
  | 'NEXT_STEP_EXECUTION'
export type RiskCategory =
  | 'COMMERCIAL'
  | 'STAKEHOLDER'
  | 'COMPETITIVE'
  | 'TECHNICAL'
  | 'STRATEGIC_FIT'
  | 'EXECUTION'
  | 'PROCUREMENT'
  | 'TIMING'
export type RiskStatus = 'OPEN' | 'MITIGATING' | 'RESOLVED' | 'ACCEPTED'
export type TimelineEventType =
  | 'MEETING'
  | 'BUYING_SIGNAL'
  | 'RISK_OPENED'
  | 'RISK_RESOLVED'
  | 'STAKEHOLDER_CHANGE'
  | 'WIN_PROBABILITY_CHANGE'
  | 'COMMITMENT_FULFILLED'
  | 'COMMITMENT_MISSED'
  | 'STAGE_CHANGE'
  | 'CUSTOMER_DECISION'

// ───────────────────────── Deal analytics: models ─────────────────────────
// Deal health
export interface HealthDimension extends AnalysisFinding {
  dimension: HealthDimensionName
  /** 0-10 */
  score: number
  rationale: string
  missing_information: string[]
  source_meeting_ids: string[]
}

export interface DealHealth {
  dimensions: HealthDimension[]
  /** 0-100, computed in backend code (not by the LLM). */
  composite_score: number | null
  methodology_version: string
}

// Momentum
/** Python: plain BaseModel (NOT a Finding). */
export interface MeetingTrendPoint {
  meeting_id: string
  meeting_title: string
  meeting_date: string
  /** Free string in Python (copied from the meeting sentiment). */
  sentiment: string | null
  engagement: Confidence | null
  signal_stage: SignalStage | null
  scorecard_overall: number | null
  unresolved_objections: number | null
  discovery_coverage_pct: number | null
}

export interface MomentumAnalysis {
  overall_trend: Trend
  verdict: string
  engagement_trend: Trend
  sentiment_trend: Trend
  buying_signal_trend: Trend
  new_stakeholders_entered: string[]
  delays_or_missed_milestones: string[]
  /** One per meeting, oldest first. */
  trend_points: MeetingTrendPoint[]
}

// Risks
export interface RiskItem extends AnalysisFinding {
  risk_key: string
  category: RiskCategory
  title: string
  description: string
  severity: Severity
  status: RiskStatus
  first_seen_meeting_id: string | null
  last_seen_meeting_id: string | null
  occurrences: number
  mitigation: string | null
  suggested_owner: string | null
}

export interface RiskRegister {
  risks: RiskItem[]
  highest_priority_risk_key: string | null
}

// Buying committee
export interface CommitteeMember extends AnalysisFinding {
  name: string
  title: string | null
  buying_role: BuyingRole
  role_confirmed: boolean
  stance: Stance
  engagement: Confidence
  meetings_attended: number
  priorities: string[]
  concerns: string[]
  recommended_engagement: string | null
}

export interface BuyingCommittee {
  members: CommitteeMember[]
  economic_buyer_access: boolean
  technical_evaluator_access: boolean
  champion_identified: boolean
  champion_strength: Confidence | null
  procurement_involved: boolean
  security_legal_involved: boolean
  missing_roles: BuyingRole[]
  conflicting_priorities: string[]
  coverage_summary: string
  next_stakeholder_to_engage: string | null
}

// Competitive positioning
export interface DealCompetitor extends AnalysisFinding {
  name: string
  /** true = buyer named/evaluated them; false = hypothesis. */
  confirmed: boolean
  buyer_perception: string | null
  where_they_may_be_stronger: string[]
  where_we_are_stronger: string[]
}

export interface DealCompetitivePositioning {
  competitors: DealCompetitor[]
  evaluation_criteria: string[]
  strongest_differentiators: string[]
  competitive_gaps: string[]
  unresolved_competitive_questions: string[]
  recommended_positioning_changes: string[]
}

// Execution
export interface CommitmentRecord extends AnalysisFinding {
  commitment: string
  made_in_meeting_id: string
  owner: string | null
  due: string | null
  /** Free string in Python: FULFILLED | OPEN | OVERDUE | UNKNOWN. */
  status: string
}

export interface ExecutionEffectiveness {
  recurring_patterns: string[]
  repeated_mistake_categories: string[]
  improvements_over_time: string[]
  discovery_quality_trend: Trend
  follow_up_reliability_note: string
  commitments: CommitmentRecord[]
  /** 0-100 or null when there are no commitments. */
  commitment_reliability_pct: number | null
}

// Trackers
export interface TrackedQuestion extends AnalysisFinding {
  question: string
  asked_by: string | null
  first_raised_meeting_id: string | null
  /** Free string in Python: OPEN | ANSWERED. */
  status: string
  owner: string | null
}

export interface ResearchGap extends AnalysisFinding {
  hypothesis_from_research: string
  reality_from_meetings: string
  /** Free string in Python: CONFIRMED | CONTRADICTED | NEW_INSIGHT | UNVALIDATED. */
  verdict: string
}

export interface WarningSignal extends AnalysisFinding {
  title: string
  description: string
  severity: Severity
  is_disqualifying: boolean
  uncertainty_note: string | null
}

export interface TrackersAnalysis {
  unanswered_questions: TrackedQuestion[]
  research_gaps: ResearchGap[]
  warning_signals: WarningSignal[]
  signal_stage: SignalStage
}

// Win probability
export interface WinFactor extends AnalysisFinding {
  description: string
  impact: Severity
  source_meeting_ids: string[]
}

/** Python: plain BaseModel (NOT a Finding). */
export interface WinProbability {
  /** 0-100 */
  probability_pct: number
  previous_pct: number | null
  change_pct: number | null
  trend: Trend
  confidence: Confidence
  label: string
  rationale: string
  supporting_factors: WinFactor[]
  reducing_factors: WinFactor[]
  major_uncertainties: string[]
  conditions_to_improve: string[]
  conditions_to_decline: string[]
}

// Strategy
export interface StrategicAction extends AnalysisFinding {
  rank: number
  action: string
  rationale: string
  impact: Severity
  urgency: Severity
  linked_risk_keys: string[]
  suggested_owner: string | null
}

export interface DealStrategy {
  top_actions: StrategicAction[]
  highest_priority_risk_to_resolve: string | null
  next_stakeholder_to_engage: string | null
  questions_for_next_meeting: string[]
  documents_to_prepare: string[]
  objections_to_address_before_advancing: string[]
  presentation_changes: string[]
  negotiation_strategy: string | null
  suggested_next_meeting_agenda: string[]
  conditions_before_forecasting_close: string[]
}

// Timeline
export interface TimelineEvent {
  date: string
  meeting_id: string | null
  event_type: TimelineEventType
  title: string
  detail: string | null
}

export interface DealTimeline {
  /** Chronological, oldest first. */
  events: TimelineEvent[]
  what_changed_after_latest_meeting: string[]
  why_assessment_changed: string
}

/**
 * PENDING BACKEND: DealAnalyticsState.deal_profile exposed as a typed model.
 * Marked optional on DealAnalyticsResult until the backend adds it.
 */
export interface DealProfile {
  deal_id: string
  title: string | null
  target_company: string | null
  target_industry: string | null
  meeting_objective: string | null
  status: string | null
}

export interface DealAnalyticsResult {
  deal_id: string
  snapshot_version: number
  schema_version: string
  meetings_analyzed: number
  latest_meeting_id: string | null
  generated_at: string
  model_name: string | null
  win_probability: WinProbability | null
  health: DealHealth | null
  momentum: MomentumAnalysis | null
  risks: RiskRegister | null
  buying_committee: BuyingCommittee | null
  competitive: DealCompetitivePositioning | null
  execution: ExecutionEffectiveness | null
  trackers: TrackersAnalysis | null
  strategy: DealStrategy | null
  timeline: DealTimeline | null
  warnings: string[]
  /** PENDING BACKEND: add `status` (COMPLETED/PARTIAL/FAILED) to DealAnalyticsResult. */
  status?: AnalysisStatus
  /** PENDING BACKEND (see DealProfile). */
  deal_profile?: DealProfile | null
}

// ───────────────────────── Meeting CRUD record (MeetingResponse) ─────────────────────────
export type MeetingRecord = {
  id: string
  deal_id: string
  owner_id: string
  title: string
  meeting_date: string
  attendees: string | null
  meeting_type: MeetingType | null
  summary: string | null
  transcript_text: string
  objectives: string | null
  notes: string | null
  created_at: string
  updated_at: string
}