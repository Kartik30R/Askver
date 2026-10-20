import { fetchWithAuth } from '../../utils/fetchWithAuth'
import type {
  CommercialFrameworks,
  EvidenceReport,
  FactMap,
  FinancialSnapshot,
  InsightSynthesis,
  MatchedAsset,
  MeetingPlaybook,
  PainPoint,
  PipelineProgress,
  ResearchPlan,
  ServiceMapping,
  SourceMap,
  StrategicFrameworks,
  VerificationReport,
} from './researchTypes'

export type PipelineStateResponse = {
  deal_id: string
  target_company?: string | null
  target_industry?: string | null
  meeting_objective?: string | null
  research_depth?: string | null
  meeting_duration_minutes?: number | null
  current_step?: string | null
  execution_paused_at?: string | null
  last_execution_resumption?: string | null
  pause_requested?: boolean
  manual_pause_at_node?: string | null
  dynamic_instructions?: Array<string | Record<string, unknown>> | null
  mandatory_review_checkpoint?: string | null
  human_approved?: boolean
  human_feedback?: string | null

  research_plan?: ResearchPlan | null
  facts?: FactMap | null
  sources?: SourceMap | null
  research_gaps?: string[] | null
  financial_snapshot?: FinancialSnapshot | null
  strategic_frameworks?: StrategicFrameworks | null
  commercial_frameworks?: CommercialFrameworks | null
  evidence_report?: EvidenceReport | null
  insight_synthesis?: InsightSynthesis | null
  verification_report?: VerificationReport | null

  priorities?: string[] | null
  detected_pain_points?: PainPoint[] | null
  service_mappings?: ServiceMapping[] | null
  matched_internal_assets?: MatchedAsset[] | null

  meeting_playbook?: MeetingPlaybook | null
  cxo_executive_brief?: Record<string, unknown> | null // back-compat only, do not render
  markdown_export?: string | null

  progress?: PipelineProgress | null
  node_statuses?: Record<string, string>
  errors?: string[] | null
  // legacy deals (pre-upgrade snapshots) may still carry these; only used to detect "legacy"
  company_research?: unknown
  [key: string]: unknown
}

export type MandatoryReviewApprovalPayload = {
  checkpoint_status: 'approved' | 'needs_revision' | 'rejected'
  feedback?: string | null
  custom_selected_assets?: string[] | null
}

export type DynamicInstructionPayload = {
  instructions: string[]
  apply_to_node?: string | null
  target_nodes?: string[] | null
  rerun_from_node?: string | null
  priority?: number
}

export async function getPipelineState(
  dealId: string,
  accessToken?: string | null,
): Promise<PipelineStateResponse> {
  return fetchWithAuth<PipelineStateResponse>(
    `/deals/${dealId}/pipeline/state`,
    {
      method: 'GET',
      accessToken: accessToken ?? undefined,
    },
  )
}

export async function getPipelineStatus(
  dealId: string,
  accessToken?: string | null,
): Promise<{ deal_id: string; status: string }> {
  return fetchWithAuth<{ deal_id: string; status: string }>(
    `/deals/${dealId}/pipeline/status`,
    {
      method: 'GET',
      accessToken: accessToken ?? undefined,
    },
  )
}

export async function submitMandatoryReviewApproval(
  dealId: string,
  payload: MandatoryReviewApprovalPayload,
  accessToken?: string | null,
): Promise<{ success: boolean; message: string; status?: string; should_run?: boolean }> {
  return fetchWithAuth<{ success: boolean; message: string; status?: string; should_run?: boolean }>(
    `/deals/${dealId}/pipeline/hitl/mandatory-review/approve`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
      accessToken: accessToken ?? undefined,
    },
  )
}

export async function submitDynamicInstruction(
  dealId: string,
  payload: DynamicInstructionPayload,
  accessToken?: string | null,
): Promise<{ success: boolean; message: string; should_run?: boolean; target_nodes?: string[] | null; rerun_from_node?: string | null }> {
  return fetchWithAuth<{ success: boolean; message: string; should_run?: boolean; target_nodes?: string[] | null; rerun_from_node?: string | null }>(
    `/deals/${dealId}/pipeline/hitl/dynamic-instruction`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
      accessToken: accessToken ?? undefined,
    },
  )
}
