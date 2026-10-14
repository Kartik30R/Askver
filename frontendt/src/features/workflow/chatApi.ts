import { fetchWithAuth } from '../../utils/fetchWithAuth'

export type ChatQueryResponse = {
  deal_id: string
  answer: string
  citations?: string[]
}

export type ProposeEditResponse = {
  deal_id: string
  section?: string | null
  proposed_diff_id: string
  current_text: string
  proposed_text: string
  status: string
}

export type ApproveEditResponse = {
  deal_id: string
  proposed_diff_id: string
  approved: boolean
  status: string
  message: string
}

export async function askDealQuery(
  dealId: string,
  payload: { question: string },
  accessToken?: string | null,
): Promise<ChatQueryResponse> {
  return fetchWithAuth<ChatQueryResponse>(`/deals/${dealId}/chat/query`, {
    method: 'POST',
    body: JSON.stringify(payload),
    accessToken: accessToken ?? undefined,
  })
}

export async function proposeTextEdit(
  dealId: string,
  payload: { section?: string | null; instruction: string; current_text?: string | null },
  accessToken?: string | null,
): Promise<ProposeEditResponse> {
  return fetchWithAuth<ProposeEditResponse>(`/deals/${dealId}/chat/edit`, {
    method: 'POST',
    body: JSON.stringify(payload),
    accessToken: accessToken ?? undefined,
  })
}

export async function approveTextEdit(
  dealId: string,
  payload: { proposed_diff_id: string; approved: boolean },
  accessToken?: string | null,
): Promise<ApproveEditResponse> {
  return fetchWithAuth<ApproveEditResponse>(`/deals/${dealId}/chat/approve`, {
    method: 'POST',
    body: JSON.stringify(payload),
    accessToken: accessToken ?? undefined,
  })
}
