import { Navigate, Outlet } from 'react-router-dom'
import { useSelector } from 'react-redux'
import { selectCurrentToken } from './authSlice'

export const ProtectedRoute = () => {
  const token = useSelector(selectCurrentToken) || localStorage.getItem('access_token')

  if (!token) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}