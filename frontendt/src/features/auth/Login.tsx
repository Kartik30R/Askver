import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Sparkles, ArrowRight, ShieldCheck, Lock, Mail, User } from 'lucide-react'

export default function Login() {
  const [isRegister, setIsRegister] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // Simulated auth success
    localStorage.setItem('access_token', 'mock_jwt_token_12345')
    navigate('/')
  }

  return (
    <div className="min-h-screen bg-cosmic-bg text-cosmic-text flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background Glow Highlights */}
      <div className="absolute top-1/4 left-1/3 w-96 h-96 bg-nagarro-green/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/3 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md relative z-10">
        {/* Brand Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-cosmic-surface/80 border border-cosmic-border text-xs mb-4">
            <Sparkles className="w-3.5 h-3.5 text-nagarro-green animate-pulse" />
            <span className="text-cosmic-muted">Enterprise Deal Intelligence v1.0</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight">
            Nagarro <span className="text-nagarro-green">DealIntel</span>
          </h1>
          <p className="text-sm text-cosmic-muted mt-2">
            Autonomous Multi-Agent Strategy & RFP Intelligence
          </p>
        </div>

        {/* Auth Glass Card */}
        <div className="cosmic-card p-8">
          {/* Auth Mode Toggle */}
          <div className="flex bg-cosmic-bg/60 p-1 rounded-lg mb-6 border border-cosmic-border/50">
            <button
              onClick={() => setIsRegister(false)}
              className={`flex-1 py-2 text-xs font-semibold rounded-md transition-all ${
                !isRegister ? 'bg-nagarro-green text-black shadow-md' : 'text-cosmic-muted hover:text-white'
              }`}
            >
              Sign In
            </button>
            <button
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
                  placeholder="••••••••••••"
                  className="w-full bg-cosmic-bg/80 border border-cosmic-border rounded-lg pl-9 pr-4 py-2.5 text-sm text-white focus:outline-none focus:border-nagarro-green transition-colors"
                />
              </div>
            </div>

            <button type="submit" className="btn-nagarro w-full flex items-center justify-center gap-2 mt-6">
              <span>{isRegister ? 'Create Account' : 'Authenticate Workspace'}</span>
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