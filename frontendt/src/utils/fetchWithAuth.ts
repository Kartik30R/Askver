import { refreshAccessToken } from '../features/auth/authApi'

const shouldAttemptRefresh = (path: string) => {
  const normalized = path.replace(/\?.*$/, '')
  return !['/auth/login', '/auth/register', '/auth/refresh', '/auth/logout'].includes(normalized)
}

/**
 * Environment-safe API base URL configuration.
 * Respects VITE_API_BASE_URL environment variable or defaults to 127.0.0.1:8000
 */
export const getApiBaseUrl = (): string => {
  const rawBase = (
    (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL)
      ? import.meta.env.VITE_API_BASE_URL
      : 'http://127.0.0.1:8000'
  ).replace(/\/+$/, '')

  return rawBase.endsWith('/api/v1') ? rawBase : `${rawBase}/api/v1`
}

/**
 * Custom fetch wrapper with:
 * - Automatic Bearer token injection from Redux auth state
 * - JSON/FormData handling
 * - Global 401 error detection and logout
 */
export async function fetchWithAuth<T>(
  path: string,
  init: RequestInit & { accessToken?: string | null } = {},
): Promise<T> {
  const { accessToken, ...restInit } = init
  const url = `${getApiBaseUrl()}${path}`
  const headers = new Headers(restInit.headers ?? {})

  // Auto-set Content-Type for JSON unless FormData
  if (!(restInit.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  // Inject access token
  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`)
  }

  const response = await fetch(url, {
    ...restInit,
    credentials: 'include',
    headers,
  })

  // 401 or 403 = session expired/invalid. Try a refresh once before forcing logout.
  if (shouldAttemptRefresh(path) && (response.status === 401 || response.status === 403)) {
    const refreshed = await refreshAccessToken()
    if (refreshed) {
      return fetchWithAuth<T>(path, {
        ...init,
        accessToken: refreshed.access_token,
      })
    }

    throw new Error('Your session has expired. Please sign in again.')
  }

  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}`

    try {
      const body = await response.json()
      if (typeof body?.detail === 'string') {
        errorMessage = body.detail
      } else if (Array.isArray(body?.detail)) {
        errorMessage = body.detail
          .map((d: unknown) => (typeof d === 'string' ? d : JSON.stringify(d)))
          .join('; ')
      } else if (body?.message) {
        errorMessage = body.message
      }
    } catch {
      // Ignore JSON parse errors
    }

    throw new Error(errorMessage)
  }

  // 204 No Content
  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}
