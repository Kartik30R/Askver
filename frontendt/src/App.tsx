import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ProtectedRoute } from './features/auth/ProtectedRoute'
import { MainLayout } from './layouts/MainLayout'

// Feature Components
import Login from './features/auth/Login'
import DealList from './features/deals/DealList'
import DealDashboard from './features/workflow/DealDashboard'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<Login />} />

        {/* Protected App Routes */}
        <Route element={<ProtectedRoute />}>
          <Route element={<MainLayout />}>
            <Route path="/" element={<DealList />} />
            <Route path="/deals/:dealId" element={<DealDashboard />} />
          </Route>
        </Route>

        {/* Redirect unknown paths */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App