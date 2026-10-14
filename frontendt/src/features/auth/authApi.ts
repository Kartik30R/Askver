export type AuthUser = {
  id: string
  email: string
  name: string
  created_at: string
}

export type AuthSession = {
  access_token: string
  token_type: string
  user: AuthUser
}

export type LoginPayload = {
  email: string
  password: string
}

export type RegisterPayload = {
  name: string
  email: string
  password: string
}

export class ApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message)
    this.name = 'ApiError'
  }
}

const normalizeApiBaseUrl = (baseUrl?: string) => {
  const rawBase = (baseUrl ?? 'http://127.0.0.1:8000').replace(/\/+$/, '')
  return rawBase.endsWith('/api/v1') ? rawBase : `${rawBase}/api/v1`
}

const API_BASE_URL = normalizeApiBaseUrl(import.meta.env.VITE_API_BASE_URL)

let refreshRequest: Promise<AuthSession | null> | null = null

const shouldAttemptRefresh = (path: string) => {
  const normalized = path.replace(/\?.*$/, '')
  return !['/auth/login', '/auth/register', '/auth/refresh', '/auth/logout'].includes(normalized)
}

export async function refreshAccessToken(): Promise<AuthSession | null> {
  if (refreshRequest) {
    return refreshRequest
  }

  refreshRequest = (async () => {
    try {
      const { store } = await import('../../app/store')
      const { setRefreshing } = await import('./authSlice')
      store.dispatch(setRefreshing(true))

      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        if (typeof document !== 'undefined') {
          document.cookie = 'refresh_token=; Path=/; Max-Age=0; SameSite=Lax'
        }

        try {
          const { store } = await import('../../app/store')
          const { logout } = await import('./authSlice')
          store.dispatch(logout())
        } catch {
          // Ignore store dispatch issues when auth state is unavailable.
        }
        return null
      }

      const data = (await response.json()) as AuthSession

      try {
        const { store } = await import('../../app/store')
        const { establishSession } = await import('./authSlice')
        store.dispatch(establishSession(data))
      } catch {
        // Ignore store dispatch issues when auth state is unavailable.
      }

      return data
    } finally {
      try {
        const { store } = await import('../../app/store')
        const { setRefreshing } = await import('./authSlice')
        store.dispatch(setRefreshing(false))
      } catch {
        // Ignore store dispatch issues when auth state is unavailable.
      }
    }
  })()

  try {
    return await refreshRequest
  } finally {
    refreshRequest = null
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  accessToken?: string | null,
  opts: { treat401AsExpired?: boolean } = { treat401AsExpired: true },
): Promise<T> {
  const headers = new Headers(init.headers ?? {})

  if (!(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`)
  }

  const url = `${API_BASE_URL}${path}`

  let response: Response
  try {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 30000)

    response = await fetch(url, {
      ...init,
      credentials: 'include',
      headers,
      signal: controller.signal,
    })
    clearTimeout(timeout)
  } catch (networkError) {
    if (networkError instanceof TypeError && networkError.message.includes('Failed to fetch')) {
      throw new Error(
        `Cannot reach backend at ${API_BASE_URL}. Is it running? Try: http://127.0.0.1:8000`,
      )
    }
    throw new Error(
      `Network error: ${networkError instanceof Error ? networkError.message : String(networkError)}`,
    )
  }

  if (opts.treat401AsExpired && shouldAttemptRefresh(path) && (response.status === 401 || response.status === 403)) {
    const refreshed = await refreshAccessToken()
    if (refreshed) {
      return request<T>(path, init, refreshed.access_token, { ...opts, treat401AsExpired: false })
    }

    throw new ApiError('Your session has expired. Please sign in again.', response.status)
  }

  if (!response.ok) {
    let message = `HTTP ${response.status}`

    try {
      const body = await response.json()
      if (typeof body?.detail === 'string') {
        message = body.detail
      } else if (Array.isArray(body?.detail)) {
        message = body.detail.map((item: unknown) => (typeof item === 'string' ? item : JSON.stringify(item))).join(', ')
      } else if (body?.message) {
        message = body.message
      }
    } catch {
      // Ignore JSON parsing errors and fall back to the default message.
    }

    throw new ApiError(message, response.status)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

export async function loginRequest(payload: LoginPayload): Promise<AuthSession> {
  return request<AuthSession>(
    '/auth/login',
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    null,
    { treat401AsExpired: false },
  )
}

export async function registerRequest(payload: RegisterPayload): Promise<AuthSession> {
  return request<AuthSession>(
    '/auth/register',
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    null,
    { treat401AsExpired: false },
  )
}

export async function logoutUser(): Promise<void> {
  await request<void>('/auth/logout', {
    method: 'POST',
  })
}

export async function fetchCurrentUser(accessToken: string): Promise<AuthUser> {
  const data = await request<AuthUser | { user: AuthUser }>('/auth/me', {
    method: 'GET',
  }, accessToken)

  return 'user' in data ? data.user : data
}
