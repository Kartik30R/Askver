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
