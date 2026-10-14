import type { ReactNode } from 'react'
import { useSelector } from 'react-redux'
import { Navigate, useLocation } from 'react-router-dom'

import type { RootState } from '../../app/store'

type RouteWrapperProps = {
  children: ReactNode
}

export function ProtectedRoute({ children }: RouteWrapperProps) {
  const location = useLocation()
  const authStatus = useSelector((state: RootState) => state.auth.status)
  const isAuthenticated = useSelector((state: RootState) => Boolean(state.auth.accessToken))
  const isHydrating = authStatus === 'idle' || authStatus === 'loading'

  if (isHydrating && isAuthenticated) {
    return <div className="flex min-h-screen items-center justify-center"><div className="text-gray-500">Loading...</div></div>
  }

  if (!isAuthenticated && !isHydrating) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  return <>{children}</>
}

export function PublicRoute({ children }: RouteWrapperProps) {
  const authStatus = useSelector((state: RootState) => state.auth.status)
  const isAuthenticated = useSelector((state: RootState) => Boolean(state.auth.accessToken))
  const isHydrating = authStatus === 'idle' || authStatus === 'loading'

  if (isHydrating && isAuthenticated) {
    return <div className="flex min-h-screen items-center justify-center"><div className="text-gray-500">Loading...</div></div>
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}
