import { createAsyncThunk, createSlice, type PayloadAction } from '@reduxjs/toolkit'

import { ApiError, fetchCurrentUser, loginRequest, registerRequest, type AuthSession, type AuthUser } from './authApi'
import type { RootState } from '../../app/store'

const STORAGE_KEY = 'askver-auth'

export type AuthState = {
  user: AuthUser | null
  accessToken: string | null
  status: 'idle' | 'loading' | 'succeeded' | 'failed'
  refreshing: boolean
  error: string | null
}

const readStoredSession = (): Pick<AuthState, 'user' | 'accessToken'> => {
  if (typeof window === 'undefined') {
    return { user: null, accessToken: null }
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) {
      return { user: null, accessToken: null }
    }

    const parsed = JSON.parse(raw) as { user?: AuthUser | null; accessToken?: string | null }
    return {
      user: parsed.user ?? null,
      accessToken: parsed.accessToken ?? null,
    }
  } catch {
    return { user: null, accessToken: null }
  }
}

const persistSession = (user: AuthUser | null, accessToken: string | null) => {
  if (typeof window === 'undefined') {
    return
  }

  if (!user || !accessToken) {
    window.localStorage.removeItem(STORAGE_KEY)
    return
  }

  window.localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      user,
      accessToken,
    }),
  )
}

const defaultState: AuthState = {
  ...readStoredSession(),
  status: 'idle',
  refreshing: false,
  error: null,
}

export const loginUser = createAsyncThunk<AuthSession, { email: string; password: string }, { rejectValue: string }>(
  'auth/loginUser',
  async (payload, { rejectWithValue }) => {
    console.log('[🔐 authSlice] loginUser thunk invoked', payload)
    try {
      const result = await loginRequest(payload)
      console.log('[🔐 authSlice] loginUser success', result)
      return result
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Login failed'
      console.error('[🔐 authSlice] loginUser error:', message)
      return rejectWithValue(message)
    }
  },
)

export const registerUser = createAsyncThunk<AuthSession, { name: string; email: string; password: string }, { rejectValue: string }>(
  'auth/registerUser',
  async (payload, { rejectWithValue }) => {
    console.log('[🔐 authSlice] registerUser thunk invoked', payload)
    try {
      const result = await registerRequest(payload)
      console.log('[🔐 authSlice] registerUser success', result)
      return result
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Registration failed'
      console.error('[🔐 authSlice] registerUser error:', message)
      return rejectWithValue(message)
    }
  },
)

export const hydrateUserFromToken = createAsyncThunk<
  AuthUser | null,
  void,
  { state: RootState; rejectValue: { message: string; unauthorized: boolean } }
>(
  'auth/hydrateUserFromToken',
  async (_, { getState, rejectWithValue }) => {
    const accessToken = getState().auth.accessToken

    if (!accessToken) {
      return null
    }

    try {
      return await fetchCurrentUser(accessToken)
    } catch (error) {
      const status = error instanceof ApiError ? error.status : undefined
      return rejectWithValue({
        message: error instanceof Error ? error.message : 'Session check failed',
        unauthorized: status === 401 || status === 403,
      })
    }
  },
)

const authSlice = createSlice({
  name: 'auth',
  initialState: defaultState,
  reducers: {
    logout: (state) => {
      state.user = null
      state.accessToken = null
      state.status = 'idle'
      state.refreshing = false
      state.error = null
      persistSession(null, null)
    },
    clearAuthError: (state) => {
      state.error = null
    },
    setRefreshing: (state, action: PayloadAction<boolean>) => {
      state.refreshing = action.payload
      if (action.payload) {
        state.status = 'loading'
      }
    },
    establishSession: (state, action: PayloadAction<AuthSession>) => {
      state.user = action.payload.user
      state.accessToken = action.payload.access_token
      state.status = 'succeeded'
      state.refreshing = false
      state.error = null
      persistSession(action.payload.user, action.payload.access_token)
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(loginUser.pending, (state) => {
        state.status = 'loading'
        state.error = null
      })
      .addCase(loginUser.fulfilled, (state, action) => {
        state.user = action.payload.user
        state.accessToken = action.payload.access_token
        state.status = 'succeeded'
        state.error = null
        persistSession(action.payload.user, action.payload.access_token)
      })
      .addCase(loginUser.rejected, (state, action) => {
        state.status = 'failed'
        state.error = action.payload ?? 'Login failed'
      })
      .addCase(registerUser.pending, (state) => {
        state.status = 'loading'
        state.error = null
      })
      .addCase(registerUser.fulfilled, (state, action) => {
        state.user = action.payload.user
        state.accessToken = action.payload.access_token
        state.status = 'succeeded'
        state.error = null
        persistSession(action.payload.user, action.payload.access_token)
      })
      .addCase(registerUser.rejected, (state, action) => {
        state.status = 'failed'
        state.error = action.payload ?? 'Registration failed'
      })
      .addCase(hydrateUserFromToken.pending, (state) => {
        state.status = 'loading'
      })
      .addCase(hydrateUserFromToken.fulfilled, (state, action) => {
        if (!action.payload) {
          state.user = null
          state.accessToken = null
          state.status = 'succeeded'
          state.error = null
          persistSession(null, null)
          return
        }

        state.user = action.payload
        state.status = 'succeeded'
        state.error = null
      })
      .addCase(hydrateUserFromToken.rejected, (state, action) => {
        state.status = 'succeeded'
        if (action.payload?.unauthorized) {
          state.user = null
          state.accessToken = null
          state.error = action.payload.message
          persistSession(null, null)
          return
        }

        state.error = null
      })
  },
})

export const { logout, clearAuthError, setRefreshing, establishSession } = authSlice.actions
export default authSlice.reducer
