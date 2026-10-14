import { useEffect, useRef } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'

import type { AppDispatch, RootState } from './app/store'
import { ProtectedRoute, PublicRoute } from './features/auth/ProtectedRoute'
import { hydrateUserFromToken } from './features/auth/authSlice'
import { refreshAccessToken } from './features/auth/authApi'
import { MainLayout } from './layouts/MainLayout'

import Login from './features/auth/Login'
import DealList from './features/deals/DealList'
import DealDashboard from './features/workflow/DealDashboard'
import KnowledgeBasePage from './features/knowledge-base/KnowledgeBasePage'

function AppRoutes() {
  const dispatch = useDispatch<AppDispatch>()
  const accessToken = useSelector((state: RootState) => state.auth.accessToken)
  const hasAttemptedInitialRefresh = useRef(false)

  useEffect(() => {
    if (accessToken) {
      void dispatch(hydrateUserFromToken())
      return
    }

    if (!hasAttemptedInitialRefresh.current && typeof document !== 'undefined' && document.cookie.includes('refresh_token=')) {
      hasAttemptedInitialRefresh.current = true
      void refreshAccessToken()
    }
  }, [accessToken, dispatch])

  useEffect(() => {
    if (!accessToken) {
      return undefined
    }

    const refreshInterval = window.setInterval(() => {
      void refreshAccessToken()
    }, 10 * 60 * 1000)

    return () => window.clearInterval(refreshInterval)
  }, [accessToken])

  return (
    <Routes>
      <Route
        path="/login"
        element={
          <PublicRoute>
            <Login />
          </PublicRoute>
        }
      />

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <MainLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DealList />} />
        <Route path="knowledge-base" element={<KnowledgeBasePage />} />
        <Route path="deals/:dealId" element={<DealDashboard />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  )
}

export default App