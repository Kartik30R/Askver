export type PipelineLane = 'plan' | 'research' | 'analysis' | 'fit' | 'review' | 'playbook'

export type PipelineNodeDef = { id: string; label: string; lane: PipelineLane }

export const PIPELINE_NODE_DEFS: PipelineNodeDef[] = [
  { id: 'research_planner', label: 'Research Planner', lane: 'plan' },

  { id: 'research_business_model', label: 'Business Model', lane: 'research' },
  { id: 'research_financial', label: 'Financials', lane: 'research' },
  { id: 'research_strategy', label: 'Strategy', lane: 'research' },
  { id: 'research_technology', label: 'Technology', lane: 'research' },
  { id: 'research_leadership', label: 'Leadership', lane: 'research' },
  { id: 'research_industry', label: 'Industry', lane: 'research' },
  { id: 'research_competitors', label: 'Competitors', lane: 'research' },
  { id: 'research_triggers', label: 'Triggers', lane: 'research' },
  { id: 'evidence_gate', label: 'Evidence Gate', lane: 'research' },

  { id: 'strategic_frameworks', label: 'Strategic Frameworks', lane: 'analysis' },
  { id: 'commercial_frameworks', label: 'Commercial Frameworks', lane: 'analysis' },
  { id: 'insight_synthesis', label: 'Insight Synthesis', lane: 'analysis' },
  { id: 'verifier', label: 'Verifier', lane: 'analysis' },

  { id: 'pain_point_detector', label: 'Pain Points', lane: 'fit' },
  { id: 'enterprise_rag', label: 'Asset Matching', lane: 'fit' },
  { id: 'service_mapper', label: 'Service Mapping', lane: 'fit' },

  { id: 'mandatory_review', label: 'Human Review', lane: 'review' },

  { id: 'playbook_questions', label: 'Questions & Objections', lane: 'playbook' },
  { id: 'playbook_room', label: 'Room Plan & Pitch', lane: 'playbook' },
  { id: 'playbook_assemble', label: 'Assemble Playbook', lane: 'playbook' },
  { id: 'report_indexing', label: 'Index Report', lane: 'playbook' },
]

export const LANE_LABEL: Record<PipelineLane, string> = {
  plan: '1 · Plan',
  research: '2 · Research (parallel)',
  analysis: '3 · Analyse',
  fit: '4 · Fit',
  review: '5 · Review',
  playbook: '6 · Playbook',
}

export const LANE_ORDER: PipelineLane[] = ['plan', 'research', 'analysis', 'fit', 'review', 'playbook']

/** Section headings produced by report_indexer.generate_markdown_report; used by the chat "section" picker. */
export const REPORT_SECTIONS = [
  'Executive Snapshot', 'Agenda', 'Talking Points', 'Discovery Questions', 'Objections & Responses',
  'Financial Snapshot', 'Strategic Insights', 'Pain Points', 'Attendees', 'Proof Points & Service Fit',
  'Pitch & Ask', 'Deal Risks', 'Known Gaps (verify in the room)',
]
