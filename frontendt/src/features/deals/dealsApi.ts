import { fetchWithAuth, getApiBaseUrl } from '../../utils/fetchWithAuth'

// ============================================================================
// TYPES
// ============================================================================

export type DealCreate = {
  title: string
  target_company: string
  target_industry: string
  meeting_objective: string
}

export type ResearchDepth = 'quick' | 'standard' | 'deep'

export type StartPipelineOptions = {
  threadId?: string
  researchDepth?: ResearchDepth | string
  meetingDurationMinutes?: number
}

export type DealSummary = {
  id: string
  title: string
  target_company: string
  target_industry: string
  meeting_objective?: string
  status: string
  created_at: string
  updated_at: string
}

export type DocumentUploadResponse = {
  status: string
  document_id: string
  chunks_indexed: number
  indexing_status: string
}

export type DealDocument = {
  id: string
  filename: string
  document_category: string
  chunk_count: number
  indexing_status: string
  created_at: string
}

export type PipelineTriggerResponse = {
  status: string
  message: string
  thread_id?: string
}

// ============================================================================
// API FUNCTIONS
// ============================================================================

/**
 * Create a new deal in the backend
 */
export async function createDeal(
  dealData: DealCreate,
  accessToken: string | null,
): Promise<DealSummary> {
  console.log('[💼 Deals API] POST /deals', dealData)

  return fetchWithAuth<DealSummary>(
    '/deals',
    {
      method: 'POST',
      body: JSON.stringify(dealData),
      accessToken: accessToken ?? undefined,
    },
  )
}

/**
 * Fetch all deals for the current user
 */
export async function fetchUserDeals(
  accessToken: string | null,
  skip: number = 0,
  limit: number = 50,
): Promise<DealSummary[]> {
  console.log('[💼 Deals API] GET /deals')

  return fetchWithAuth<DealSummary[]>(
    `/deals?skip=${skip}&limit=${limit}`,
    {
      method: 'GET',
      accessToken: accessToken ?? undefined,
    },
  )
}

/**
 * Get a single deal by ID
 */
export async function getDealById(
  dealId: string,
  accessToken: string | null,
): Promise<DealSummary> {
  console.log('[💼 Deals API] GET /deals/{dealId}', dealId)

  return fetchWithAuth<DealSummary>(
    `/deals/${dealId}`,
    {
      method: 'GET',
      accessToken: accessToken ?? undefined,
    },
  )
}

/**
 * Delete a deal
 */
export async function deleteDeal(
  dealId: string,
  accessToken: string | null,
): Promise<{ status: string; message: string }> {
  console.log('[💼 Deals API] DELETE /deals/{dealId}', dealId)

  return fetchWithAuth(
    `/deals/${dealId}`,
    {
      method: 'DELETE',
      accessToken: accessToken ?? undefined,
    },
  )
}

/**
 * Upload a document for a deal (FormData)
 */
export async function uploadDealDocument(
  dealId: string,
  formData: FormData,
  accessToken: string | null,
): Promise<DocumentUploadResponse> {
  console.log('[💼 Deals API] POST /deals/{dealId}/documents', dealId)

  const baseUrl = getApiBaseUrl()
  const response = await fetch(`${baseUrl}/deals/${dealId}/documents`, {
    method: 'POST',
    credentials: 'include',
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
    body: formData,
  })

  if (response.status === 401 || response.status === 403) {
    throw new Error('Your session has expired. Please sign in again.')
  }

  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}`
    try {
      const body = await response.json()
      if (typeof body?.detail === 'string') {
        errorMessage = body.detail
      } else if (body?.message) {
        errorMessage = body.message
      }
    } catch {
      // Ignore JSON parsing errors
    }
    throw new Error(errorMessage)
  }

  const data = await response.json()
  console.log('[💼 Deals API] Document upload successful:', data)
  return data as DocumentUploadResponse
}

/**
 * List all documents for a deal
 */
export async function listDealDocuments(
  dealId: string,
  accessToken: string | null,
): Promise<DealDocument[]> {
  console.log('[💼 Deals API] GET /deals/{dealId}/documents', dealId)

  return fetchWithAuth<DealDocument[]>(
    `/deals/${dealId}/documents`,
    {
      method: 'GET',
      accessToken: accessToken ?? undefined,
    },
  )
}

/**
 * Delete a document from a deal
 */
export async function deleteDealDocument(
  dealId: string,
  documentId: string,
  accessToken: string | null,
): Promise<{ status: string; message: string }> {
  console.log('[💼 Deals API] DELETE /deals/{dealId}/documents/{documentId}', dealId, documentId)

  return fetchWithAuth(
    `/deals/${dealId}/documents/${documentId}`,
    {
      method: 'DELETE',
      accessToken: accessToken ?? undefined,
    },
  )
}

/**
 * Trigger the pipeline for a deal
 */
export async function startPipeline(
  dealId: string,
  accessToken: string | null,
  options: StartPipelineOptions = {},
): Promise<PipelineTriggerResponse> {
  const { threadId, researchDepth = 'standard', meetingDurationMinutes } = options
  console.log('[💼 Deals API] POST /deals/{dealId}/pipeline/trigger', dealId, { researchDepth, meetingDurationMinutes })

  const params = new URLSearchParams()
  if (threadId) {
    params.set('thread_id', threadId)
  }
  if (researchDepth) {
    params.set('research_depth', String(researchDepth).toLowerCase())
  }
  if (meetingDurationMinutes != null) {
    params.set('meeting_duration_minutes', String(meetingDurationMinutes))
  }

  const suffix = params.toString()

  return fetchWithAuth<PipelineTriggerResponse>(
    `/deals/${dealId}/pipeline/trigger${suffix ? `?${suffix}` : ''}`,
    {
      method: 'POST',
      accessToken: accessToken ?? undefined,
    },
  )
}
