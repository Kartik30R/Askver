import { useCallback } from 'react'
import { useDispatch } from 'react-redux'
import { useNavigate } from 'react-router-dom'

import { logout } from '../features/auth/authSlice'
import type { AppDispatch } from '../app/store'

/**
 * Hook to wrap API calls and catch 401/403 auth errors.
 * Automatically logs out and navigates to login on session expiry.
 */
export function useAuthErrorHandler() {
  const dispatch = useDispatch<AppDispatch>()
  const navigate = useNavigate()

  return useCallback(
    async <T,>(promise: Promise<T>): Promise<T | null> => {
      try {
        return await promise
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error)

        // Check for auth error markers from backend
        if (message.includes('session') || message.includes('expired') || message.includes('401') || message.includes('Refresh token')) {
          dispatch(logout())
          navigate('/login', { replace: true, state: { error: message } })
          return null
        }

        // Re-throw for caller to handle
        throw error
      }
    },
    [dispatch, navigate],
  )
}
