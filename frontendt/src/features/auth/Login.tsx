import React, { useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { useNavigate } from 'react-router-dom'
import { Sparkles, ArrowRight, ShieldCheck, Lock, Mail, User } from 'lucide-react'

import type { AppDispatch, RootState } from '../../app/store'
import { clearAuthError, loginUser, registerUser } from './authSlice'

export default function Login() {
  const [isRegister, setIsRegister] = useState(false)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const dispatch = useDispatch<AppDispatch>()
  const navigate = useNavigate()
  const { status, error } = useSelector((state: RootState) => state.auth)

  const isSubmitting = status === 'loading'

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    console.log('[🔐 Login] Form submitted', { isRegister, email })
    dispatch(clearAuthError())

    try {
      const resultAction = isRegister
        ? await dispatch(registerUser({ name, email, password }))
        : await dispatch(loginUser({ email, password }))

      console.log('[🔐 Login] Dispatch result:', resultAction)

      if (registerUser.fulfilled.match(resultAction) || loginUser.fulfilled.match(resultAction)) {
        console.log('[🔐 Login] Auth successful, navigating to /')
        navigate('/')
      } else if (registerUser.rejected.match(resultAction) || loginUser.rejected.match(resultAction)) {
        console.log('[🔐 Login] Auth rejected:', resultAction.payload)
      }
    } catch (err) {
      console.error('[🔐 Login] Unexpected error in handleSubmit:', err)
    }
  }

  return (
    <div className="min-h-screen bg-cosmic-bg text-cosmic-text flex items-center justify-center p-4 relative overflow-hidden">
      <div className="absolute top-1/4 left-1/3 w-96 h-96 bg-nagarro-green/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/3 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md relative z-10">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-cosmic-surface/80 border border-cosmic-border text-xs mb-4">
            <Sparkles className="w-3.5 h-3.5 text-nagarro-green animate-pulse" />
            <span className="text-cosmic-muted">Enterprise Deal Intelligence v1.0</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight">
            Ask<span className="text-nagarro-green">Ver</span>
          </h1>
          <p className="text-sm text-cosmic-muted mt-2">
            Autonomous Multi-Agent Strategy & RFP Intelligence
          </p>
        </div>

        <div className="cosmic-card p-8">
          <div className="flex bg-cosmic-bg/60 p-1 rounded-lg mb-6 border border-cosmic-border/50">
            <button
              type="button"
              onClick={() => setIsRegister(false)}
              className={`flex-1 py-2 text-xs font-semibold rounded-md transition-all ${
                !isRegister ? 'bg-nagarro-green text-black shadow-md' : 'text-cosmic-muted hover:text-white'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => setIsRegister(true)}
              className={`flex-1 py-2 text-xs font-semibold rounded-md transition-all ${
                isRegister ? 'bg-nagarro-green text-black shadow-md' : 'text-cosmic-muted hover:text-white'
              }`}
            >
              Register Account
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {isRegister && (
              <div>
                <label className="block text-xs font-medium text-cosmic-muted mb-1.5">Full Name</label>
                <div className="relative">
                  <User className="w-4 h-4 absolute left-3 top-3 text-cosmic-muted" />
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Kartik Rehan"
                    className="w-full bg-cosmic-bg/80 border border-cosmic-border rounded-lg pl-9 pr-4 py-2.5 text-sm text-white focus:outline-none focus:border-nagarro-green transition-colors"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-cosmic-muted mb-1.5">Work Email</label>
              <div className="relative">
                <Mail className="w-4 h-4 absolute left-3 top-3 text-cosmic-muted" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="consultant@nagarro.com"
                  className="w-full bg-cosmic-bg/80 border border-cosmic-border rounded-lg pl-9 pr-4 py-2.5 text-sm text-white focus:outline-none focus:border-nagarro-green transition-colors"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-cosmic-muted mb-1.5">Password</label>
              <div className="relative">
                <Lock className="w-4 h-4 absolute left-3 top-3 text-cosmic-muted" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full bg-cosmic-bg/80 border border-cosmic-border rounded-lg pl-9 pr-4 py-2.5 text-sm text-white focus:outline-none focus:border-nagarro-green transition-colors"
                />
              </div>
            </div>

            {error && <p className="text-sm text-red-400">{error}</p>}

            <button
              type="submit"
              disabled={isSubmitting}
              className="btn-nagarro w-full flex items-center justify-center gap-2 mt-6 disabled:opacity-70 disabled:cursor-not-allowed"
            >
              <span>{isSubmitting ? (isRegister ? 'Creating Account...' : 'Signing In...') : (isRegister ? 'Create Account' : 'Authenticate Workspace')}</span>
              <ArrowRight className="w-4 h-4 text-black" />
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-cosmic-border/50 text-center flex items-center justify-center gap-2 text-xs text-cosmic-muted">
            <ShieldCheck className="w-4 h-4 text-nagarro-green" />
            <span>Encrypted OAuth2 & JWT Session Security</span>
          </div>
        </div>
      </div>
    </div>
  )
}