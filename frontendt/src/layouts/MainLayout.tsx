import { Outlet, useNavigate } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import { logout } from '../features/auth/authSlice'
import { LogOut, LayoutDashboard, FileText } from 'lucide-react'

export const MainLayout = () => {
  const dispatch = useDispatch()
  const navigate = useNavigate()

  const handleLogout = () => {
    dispatch(logout())
    localStorage.removeItem('access_token')
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-cosmic-bg text-cosmic-text flex">
      {/* Sidebar */}
      <aside className="w-64 bg-cosmic-surface/80 backdrop-blur-lg border-r border-cosmic-border p-5 hidden md:flex flex-col justify-between">
        <div>
          <div className="flex items-center gap-2 mb-10">
            <div className="w-3 h-6 bg-nagarro-green rounded-sm" />
            <span className="text-xl font-bold tracking-wide">DEAL<span className="text-nagarro-green">INTEL</span></span>
          </div>

          <nav className="space-y-2">
            <button 
              onClick={() => navigate('/')} 
              className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium bg-cosmic-border/40 text-cosmic-text hover:bg-cosmic-border transition-colors"
            >
              <LayoutDashboard className="w-4 h-4 text-nagarro-green" />
              Active Deals
            </button>
          </nav>
        </div>

        <button 
          onClick={handleLogout}
          className="flex items-center gap-3 px-4 py-3 rounded-lg text-sm text-cosmic-muted hover:text-white hover:bg-red-500/10 transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Sign Out
        </button>
      </aside>

      {/* Main Viewport */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 bg-cosmic-surface/50 backdrop-blur-md border-b border-cosmic-border px-8 flex items-center justify-between">
          <h2 className="text-sm font-medium text-cosmic-muted">Enterprise Assistant Workspace</h2>
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-nagarro-green animate-pulse" />
            <span className="text-xs text-cosmic-muted">LangGraph Pipeline Connected</span>
          </div>
        </header>

        <main className="flex-1 p-8 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}