export type Level = 'HIGH' | 'MEDIUM' | 'LOW'

// ---------- evidence layer
export type Source = {
  id: string
  title: string
  url?: string | null
  snippet: string
  tier: number // 1 filing, 2 company/IR, 3 reputable news, 4 other
  published_date?: string | null
  collected_by?: string
  query?: string
}
export type Fact = {
  id: string
  claim: string
  category: string
  value?: string | null
  period?: string | null
  source_ids: string[]
  confidence: Level
}
export type FactMap = Record<string, Fact>
export type SourceMap = Record<string, Source>

// ---------- plan
export type Hypothesis = { statement: string; why_it_matters: string; how_to_test: string }
export type ResearchPlan = {
  company_legal_name: string
  listing_status: 'listed' | 'private' | 'unknown'
  ticker_hint?: string | null
  regions: string[]
  sub_sector: string
  business_lines: string[]
  peers: string[]
  regulatory_regimes: string[]
  likely_attendee_roles: string[]
  hypotheses: Hypothesis[]
  known_unknowns: string[]
}

// ---------- financial snapshot (yfinance tool output; keys optional because private companies have none)
export type FinancialSnapshot = {
  availability?: 'available' | 'unavailable' | string
  symbol?: string
  company_name?: string
  currency?: string
  market_cap?: number | null
  raw_metrics?: Record<string, number | string | null>
  [key: string]: unknown
}

// ---------- strategic frameworks
export type SwotItem = { statement: string; impact: Level; fact_ids: string[] }
export type Swot = {
  strengths: SwotItem[]
  weaknesses: SwotItem[]
  opportunities: SwotItem[]
  threats: SwotItem[]
}
export type TowsMove = {
  quadrant: 'SO' | 'WO' | 'ST' | 'WT'
  move: string
  why_it_matters_for_meeting: string
  fact_ids: string[]
}
export type PorterForce = {
  force: 'RIVALRY' | 'NEW_ENTRANTS' | 'SUBSTITUTES' | 'BUYER_POWER' | 'SUPPLIER_POWER'
  rating: Level | 'INSUFFICIENT_EVIDENCE'
  rationale: string
  implication_for_deal: string
  fact_ids: string[]
}
export type PestleFactor = {
  dimension: 'POLITICAL' | 'ECONOMIC' | 'SOCIAL' | 'TECHNOLOGICAL' | 'LEGAL' | 'ENVIRONMENTAL'
  factor: string
  impact: Level
  timeframe: 'NOW' | 'WITHIN_12_MONTHS' | 'LONGER'
  fact_ids: string[]
}
export type StrategicFrameworks = { swot: Swot; tows: TowsMove[]; porter: PorterForce[]; pestle: PestleFactor[] }

// ---------- commercial frameworks
export type BuyingRole = 'ECONOMIC_BUYER' | 'CHAMPION' | 'TECHNICAL_EVALUATOR' | 'BLOCKER' | 'INFLUENCER' | 'UNKNOWN'
export type CommitteeMember = {
  role: string
  name?: string | null
  evidence_level: 'NAMED_WITH_SOURCES' | 'ROLE_ARCHETYPE'
  buying_role: BuyingRole
  likely_stance: 'SUPPORTIVE' | 'NEUTRAL' | 'SKEPTICAL' | 'UNKNOWN'
  influence: Level
  owns_kpis: string[]
  how_to_win_them: string
  fact_ids: string[]
}
export type MaturityDimension = {
  dimension: 'CLOUD' | 'DATA_ANALYTICS' | 'AI' | 'SECURITY' | 'ENGINEERING_DELIVERY' | 'CUSTOMER_EXPERIENCE'
  score_1_to_5?: number | null
  rationale: string
  fact_ids: string[]
}
export type PeerRow = {
  peer: string
  dimension: string
  target_position: 'AHEAD' | 'PARITY' | 'BEHIND' | 'UNKNOWN'
  comparison: string
  fact_ids: string[]
}
export type CommercialFrameworks = {
  buying_committee: CommitteeMember[]
  digital_maturity: MaturityDimension[]
  peer_benchmark: PeerRow[]
}

// ---------- insights
export type Insight = {
  headline: string
  so_what: string
  evidence_strength: Level
  linked_hypothesis?: string | null
  fact_ids: string[]
  unverified_figures: string[]
}
export type HypothesisVerdict = {
  statement: string
  verdict: 'SUPPORTED' | 'PARTIAL' | 'UNSUPPORTED' | 'CONTRADICTED' | 'UNTESTED'
  rationale: string
  fact_ids: string[]
}
export type ThesisPart = { text: string; fact_ids: string[] }
export type DealRiskItem = { risk: string; likelihood: Level; impact: Level; mitigation: string; fact_ids: string[] }
export type InsightSynthesis = {
  insights: Insight[]
  hypothesis_verdicts: HypothesisVerdict[]
  why_now: ThesisPart
  why_this_client: ThesisPart
  value_hypothesis: ThesisPart
  deal_risks: DealRiskItem[]
  validate_in_meeting: string[]
}

// ---------- gate / verifier
export type EvidenceReport = {
  counts: Record<string, number>
  weak: string[]
  fixable: string[]
  decision: 'PROCEED' | 'REFINE'
  pass: number
}
export type VerificationReport = {
  overall_confidence: Level
  scores: {
    coverage: number
    grounding: number
    high_confidence_share: number
    reliable_source_share: number
    facts: number
    sources: number
  }
  unverified_figures: string[]
  possible_conflicts: string[]
  known_gaps: string[]
}

// ---------- pain points (matches PainPointSchema)
export type PainPoint = {
  category: string
  description: string
  severity: 'HIGH' | 'MEDIUM' | 'LOW' | string
  impacted_business_area: string
  urgency?: 'NOW' | 'NEXT_12_MONTHS' | 'LATER' | string
  solution_themes?: string[]
  evidence_basis?: 'CLIENT_DOCUMENT' | 'PUBLIC_FACTS' | 'INFERRED'
  fact_ids?: string[]
  doc_evidence?: string[]
  linked_hypothesis?: string | null
}

// ---------- service mapping / assets (shape owned by existing node_5_6 schemas; keep loose)
export type MatchedAsset = {
  asset_id?: string
  asset_name?: string
  title?: string
  asset_type?: string
  relevance_reason?: string
  [key: string]: unknown
}
export type ServiceMapping = {
  client_need?: string
  proposed_service?: string
  business_value?: string
  supporting_proof_assets?: MatchedAsset[]
  [key: string]: unknown
}

// ---------- playbook
export type OneSlideSnapshot = { situation: string; why_now: string; opening_hook: string; meeting_goal: string; fact_ids: string[] }
export type AgendaItem = { minutes: number; topic: string; purpose: string }
export type TalkingPoint = {
  sequence: number
  headline: string
  point: string
  target_persona: string
  bridge_to_question?: number | null
  fact_ids: string[]
  proof_asset_ids: string[]
  unverified_figures: string[]
}
export type DiscoveryQuestion = {
  stage: 'SITUATION' | 'PROBLEM' | 'IMPACT' | 'VISION' | 'DECISION'
  question: string
  why_we_ask: string
  listen_for: string[]
  follow_up: string
  target_persona: string
  fact_ids: string[]
  unverified_figures: string[]
}
export type ObjectionItem = {
  objection: string
  likelihood: Level
  raised_by: string
  underlying_concern: string
  response: string
  proof_asset_ids: string[]
  fact_ids: string[]
  do_not_say?: string | null
  unverified_figures: string[]
}
export type AttendeePlaybook = {
  role: string
  name?: string | null
  evidence_level: 'NAMED_WITH_SOURCES' | 'ROLE_ARCHETYPE'
  buying_role: BuyingRole
  what_they_care_about: string[]
  approach: string
  best_questions_for_them: number[]
  fact_ids: string[]
}
export type Landmine = { topic: string; why: string; safer_framing: string; fact_ids: string[] }
export type ProofPoint = { pain_point: string; asset_id: string; how_to_use: string }
export type PitchAndAsk = {
  pitch_60_seconds: string
  pitch_3_minutes: string
  the_ask: string
  next_steps: string[]
  follow_up_email_subject: string
  follow_up_email_body: string
  fact_ids: string[]
  proof_asset_ids: string[]
}
export type MeetingPlaybook = {
  snapshot: OneSlideSnapshot
  agenda: AgendaItem[]
  talking_points: TalkingPoint[]
  discovery_questions: DiscoveryQuestion[]
  objections: ObjectionItem[]
  attendees: AttendeePlaybook[]
  landmines: Landmine[]
  proof_points: ProofPoint[]
  pitch_and_ask: PitchAndAsk
  deal_risks: string[]
  known_gaps: string[]
  overall_confidence: Level
}

export type PipelineProgress = { percent: number; phase: string; completed?: number; total?: number }
