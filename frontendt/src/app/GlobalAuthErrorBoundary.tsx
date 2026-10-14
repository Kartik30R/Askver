import type { ReactNode } from 'react'
import { useEffect } from 'react'
import { useDispatch } from 'react-redux'
import { useNavigate } from 'react-router-dom'

import { logout } from '../features/auth/authSlice'
import type { AppDispatch } from '../app/store'

export function GlobalAuthErrorBoundary({ children }: { children: ReactNode }) {
  const dispatch = useDispatch<AppDispatch>()
  const navigate = useNavigate()

  useEffect(() => {
    const handleAuthError = () => {
      // Dispatch logout to clear stale auth state
      dispatch(logout())
      // Redirect to login
      navigate('/login', { replace: true })
    }

    // Listen for auth-related messages or events
    const handleStorageChange = (event: StorageEvent) => {
      if (event.key === 'askver-auth' && !event.newValue) {
        // Session was cleared elsewhere
        handleAuthError()
      }
    }

    window.addEventListener('storage', handleStorageChange)

    return () => {
      window.removeEventListener('storage', handleStorageChange)
    }
  }, [dispatch, navigate])

  return <>{children}</>
}
