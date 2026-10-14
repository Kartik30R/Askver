import { fetchWithAuth } from '../../utils/fetchWithAuth'

export type PipelineStateResponse = {
  deal_id: string
  target_company?: string | null
  target_industry?: string | null
  meeting_objective?: string | null
  current_step?: string | null
  execution_paused_at?: string | null
  last_execution_resumption?: string | null
  pause_requested?: boolean
  manual_pause_at_node?: string | null
  dynamic_instructions?: string[] | null
  mandatory_review_checkpoint?: string | null
  human_approved?: boolean
  human_feedback?: string | null
  company_overview?: Record<string, unknown> | null
  financial_intelligence?: Record<string, unknown> | null
  stakeholder_intelligence?: Record<string, unknown> | null
  industry_analysis?: Record<string, unknown> | null
  priorities?: string[] | null
  detected_pain_points?: Array<Record<string, unknown>> | null
  service_mappings?: Array<Record<string, unknown>> | null
  matched_internal_assets?: Array<Record<string, unknown>> | null
  cxo_executive_brief?: Record<string, unknown> | null
  markdown_export?: string | null
  node_statuses?: Record<string, string>
  errors?: string[] | null
  [key: string]: unknown
}

export type MandatoryReviewApprovalPayload = {
  checkpoint_status: 'approved' | 'needs_revision' | 'rejected'
  feedback?: string | null
  custom_selected_assets?: string[] | null
  executive_brief_modifications?: Record<string, unknown> | null
}

export type ExecutionCheckpoint = {
  checkpoint_id: string
  node_name?: string | null
  current_step?: string | null
  timestamp?: string | null
  paused?: boolean
}

export async function getExecutionHistory(
  dealId: string,
  accessToken?: string | null,
): Promise<ExecutionCheckpoint[]> {
  const payload = await fetchWithAuth<ExecutionCheckpoint[] | { timeline?: ExecutionCheckpoint[] }>(
    `/deals/${dealId}/pipeline/execution/history`,
    {
      method: 'GET',
      accessToken: accessToken ?? undefined,
    },
  )

  if (Array.isArray(payload)) {
    return payload
  }

  if (payload && typeof payload === 'object' && Array.isArray(payload.timeline)) {
    return payload.timeline
  }

  return []
}

export async function resumeFromCheckpoint(
  dealId: string,
  checkpointId: string,
  accessToken?: string | null,
): Promise<{ success: boolean; message: string }> {
  return fetchWithAuth<{ success: boolean; message: string }>(
    `/deals/${dealId}/pipeline/execution/checkpoint/${checkpointId}/resume`,
    {
      method: 'POST',
      body: JSON.stringify({}),
      accessToken: accessToken ?? undefined,
    },
  )
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
