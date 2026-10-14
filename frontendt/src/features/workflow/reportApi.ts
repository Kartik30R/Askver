import { fetchWithAuth } from '../../utils/fetchWithAuth'

export type LatestReportResponse = {
  deal_id: string
  version: number
  thread_id: string
  current_step: string | null
  snapshot_data: Record<string, unknown>
  created_at: string
  updated_at: string
}

export type ReportVersionResponse = {
  snapshot_id: string
  deal_id: string
  version: number
  thread_id: string
  current_step: string | null
  snapshot_data: Record<string, unknown>
  created_at: string
  updated_at: string
}

export async function getLatestReport(
  dealId: string,
  accessToken?: string | null,
): Promise<LatestReportResponse> {
  return fetchWithAuth<LatestReportResponse>(
    `/deals/${dealId}/reports/latest`,
    {
      method: 'GET',
      accessToken: accessToken ?? undefined,
    },
  )
}

export async function getReportVersions(
  dealId: string,
  accessToken?: string | null,
): Promise<ReportVersionResponse[]> {
  return fetchWithAuth<ReportVersionResponse[]>(`/deals/${dealId}/reports/versions`, {
    method: 'GET',
    accessToken: accessToken ?? undefined,
  })
}

export async function restoreReportVersion(
  dealId: string,
  snapshotId: string,
  accessToken?: string | null,
): Promise<{ status: string; message: string; snapshot_id?: string }> {
  return fetchWithAuth<{ status: string; message: string; snapshot_id?: string }>(
    `/deals/${dealId}/reports/revert/${snapshotId}`,
    {
      method: 'POST',
      body: JSON.stringify({}),
      accessToken: accessToken ?? undefined,
    },
  )
}
