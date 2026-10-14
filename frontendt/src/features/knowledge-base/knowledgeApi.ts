import { fetchWithAuth, getApiBaseUrl } from '../../utils/fetchWithAuth'

export type KnowledgeAsset = {
  id: string
  title: string
  asset_type: 'CASE_STUDY' | 'PROPOSAL' | 'SOW' | 'SUCCESS_STORY' | 'PRESENTATION' | 'SOLUTION_ACCELERATOR'
  industry_tag: string | null
  technology_tags: string[] | null
  file_path: string
  file_type: string
  summary: string | null
  vector_doc_id: string | null
  indexing_status: 'INDEXED' | 'PROCESSING' | 'FAILED'
  created_at: string
  updated_at: string
}

export type UploadKnowledgeAssetResponse = {
  status: string
  asset_id: string
}

export type DeleteKnowledgeAssetResponse = {
  status: string
  message: string
}

/**
 * List all knowledge base assets with optional filtering.
 * @param assetType - Filter by asset type (optional)
 * @param industry - Filter by industry tag (optional)
 * @param limit - Max results (default 100)
 * @param accessToken - JWT access token from Redux auth state
 */
export async function listKnowledgeAssets(params?: {
  assetType?: string
  industry?: string
  limit?: number
  accessToken?: string | null
}): Promise<KnowledgeAsset[]> {
  const queryParams = new URLSearchParams()
  if (params?.assetType) queryParams.append('asset_type', params.assetType)
  if (params?.industry) queryParams.append('industry', params.industry)
  if (params?.limit) queryParams.append('limit', String(params.limit))

  const query = queryParams.toString()
  const url = `/knowledge-base${query ? `?${query}` : ''}`

  console.log('[📚 Knowledge] GET', url)

  return fetchWithAuth<KnowledgeAsset[]>(url, {
    method: 'GET',
    accessToken: params?.accessToken ?? null,
  })
}

/**
 * Upload a knowledge base asset.
 * @param formData - FormData with title, asset_type, industry_tag, technology_tags, and file
 * @param accessToken - JWT access token from Redux auth state
 */
export async function uploadKnowledgeAsset(
  formData: FormData,
  accessToken?: string | null,
): Promise<UploadKnowledgeAssetResponse> {
  const baseUrl = getApiBaseUrl()
  const url = `${baseUrl}/knowledge-base`
  
  console.log('[📚 Knowledge] POST', url, '(multipart form)')

  // Don't set Content-Type for FormData - fetch will set it automatically with boundary
  const response = await fetch(url, {
    method: 'POST',
    credentials: 'include',
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
    body: formData,
  })

  if (response.status === 401 || response.status === 403) {
    throw new Error('Your session has expired. Please sign in again.')
  }

  if (!response.ok) {
    let message = `HTTP ${response.status}`
    try {
      const body = await response.json()
      if (typeof body?.detail === 'string') {
        message = body.detail
      } else if (Array.isArray(body?.detail)) {
        message = body.detail
          .map((d: unknown) => (typeof d === 'string' ? d : JSON.stringify(d)))
          .join('; ')
      }
    } catch {
      // Ignore JSON parse errors
    }
    throw new Error(message)
  }

  const data = (await response.json()) as UploadKnowledgeAssetResponse
  console.log('[📚 Knowledge] Upload successful:', data)
  return data
}

/**
 * Get a specific knowledge asset by ID.
 * @param assetId - UUID of the asset
 * @param accessToken - JWT access token from Redux auth state
 */
export async function getKnowledgeAsset(
  assetId: string,
  accessToken?: string | null,
): Promise<KnowledgeAsset> {
  const url = `/knowledge-base/${assetId}`
  console.log('[📚 Knowledge] GET', url)

  return fetchWithAuth<KnowledgeAsset>(url, {
    method: 'GET',
    accessToken: accessToken ?? null,
  })
}

/**
 * Delete a knowledge asset (removes file and vector embeddings).
 * @param assetId - UUID of the asset
 * @param accessToken - JWT access token from Redux auth state
 */
export async function deleteKnowledgeAsset(
  assetId: string,
  accessToken?: string | null,
): Promise<DeleteKnowledgeAssetResponse> {
  const url = `/knowledge-base/${assetId}`
  console.log('[📚 Knowledge] DELETE', url)

  return fetchWithAuth<DeleteKnowledgeAssetResponse>(url, {
    method: 'DELETE',
    accessToken: accessToken ?? null,
  })
}

