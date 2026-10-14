import { useDispatch, useSelector } from 'react-redux'
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

import { logout } from '../features/auth/authSlice'
import type { AppDispatch, RootState } from '../app/store'

export function useAuthErrorInterceptor() {
  const dispatch = useDispatch<AppDispatch>()
  const navigate = useNavigate()
  const authError = useSelector((state: RootState) => state.auth.error)

  useEffect(() => {
    if (authError?.includes('session') || authError?.includes('expired') || authError?.includes('401')) {
      dispatch(logout())
      navigate('/login', { replace: true, state: { error: authError } })
    }
  }, [authError, dispatch, navigate])
}
