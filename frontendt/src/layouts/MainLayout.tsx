import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import { LogOut, LayoutDashboard, FolderOpen } from 'lucide-react'

import type { AppDispatch } from '../app/store'
import { logoutUser } from '../features/auth/authApi'
import { logout } from '../features/auth/authSlice'

export const MainLayout = () => {
  const dispatch = useDispatch<AppDispatch>()
  const navigate = useNavigate()
  const location = useLocation()

  const handleLogout = async () => {
    try {
      await logoutUser()
    } catch {
      // Ignore server-side logout failure and still clear the client session.
    }

    dispatch(logout())
    navigate('/login')
  }

  const navItems = [
    { label: 'Active Deals', path: '/', icon: LayoutDashboard },
    { label: 'Knowledge Base', path: '/knowledge-base', icon: FolderOpen },
  ]

  return (
    <div className="min-h-screen bg-cosmic-bg text-cosmic-text flex">
      {/* Sidebar */}
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col justify-between border-r border-cosmic-border bg-cosmic-surface/80 p-5 backdrop-blur-lg md:flex">
        <div>
          <div className="mb-10 flex items-center gap-2">
            <div className="h-6 w-3 rounded-sm bg-nagarro-green" />
            <span className="text-xl font-bold tracking-wide">ASK<span className="text-nagarro-green">VER</span></span>
          </div>

          <nav className="space-y-2">
            {navItems.map(({ label, path, icon: Icon }) => {
              const active = location.pathname === path

              return (
                <button
                  key={path}
                  onClick={() => navigate(path)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                    active ? 'bg-cosmic-border/40 text-cosmic-text' : 'text-cosmic-muted hover:bg-cosmic-border hover:text-white'
                  }`}
                >
                  <Icon className="w-4 h-4 text-nagarro-green" />
                  {label}
                </button>
              )
            })}
          </nav>
        </div>

        <button 
          onClick={handleLogout}
          className="flex items-center gap-3 rounded-lg px-4 py-3 text-sm text-cosmic-muted transition-colors hover:bg-red-500/10 hover:text-white"
        >
          <LogOut className="w-4 h-4" />
          Sign Out
        </button>
      </aside>

      {/* Main Viewport */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* <header className="h-16 bg-cosmic-surface/50 backdrop-blur-md border-b border-cosmic-border px-8 flex items-center justify-between">
          <h2 className="text-sm font-medium text-cosmic-muted">Enterprise Assistant Workspace</h2>
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-nagarro-green animate-pulse" />
            <span className="text-xs text-cosmic-muted">LangGraph Pipeline Connected</span>
          </div>
        </header> */}

        <main className="flex-1 overflow-y-auto p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}