import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { Plus, Briefcase, Layers, Clock, PlayCircle } from 'lucide-react'
import CreateDealModal from './CreateDealModal'
import { fetchDeals, selectDeals, selectCurrentDraft, setCurrentDraft, selectDealsStatus } from './dealsSlice'
import { type AppDispatch } from '../../app/store'
import type { DealSummary } from './dealsSlice'

const statusConfig: Record<string, { color: string; label: string; icon: string }> = {
  CREATED: { color: 'bg-amber-500/20 border-amber-500/30 text-amber-300', label: 'Created', icon: '📝' },
  DRAFT: { color: 'bg-amber-500/20 border-amber-500/30 text-amber-300', label: 'Draft', icon: '📝' },
  RUNNING: { color: 'bg-blue-500/20 border-blue-500/30 text-blue-300', label: 'Running', icon: '⚙️' },
  PAUSED: { color: 'bg-yellow-500/20 border-yellow-500/30 text-yellow-300', label: 'Paused', icon: '⏸' },
  PAUSED_FOR_HUMAN_REVIEW: { color: 'bg-yellow-500/20 border-yellow-500/30 text-yellow-300', label: 'Paused', icon: '⏸' },
  AWAITING_REVIEW: { color: 'bg-purple-500/20 border-purple-500/30 text-purple-300', label: 'Review', icon: '👀' },
  COMPLETED: { color: 'bg-green-500/20 border-green-500/30 text-green-300', label: 'Completed', icon: '✓' },
  FAILED: { color: 'bg-red-500/20 border-red-500/30 text-red-300', label: 'Failed', icon: '✗' },
  REJECTED: { color: 'bg-red-500/20 border-red-500/30 text-red-300', label: 'Rejected', icon: '✗' },
}

const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString()
}

export default function DealList() {
  const navigate = useNavigate()
  const dispatch = useDispatch<AppDispatch>()
  const deals = useSelector(selectDeals)
  const dealsStatus = useSelector(selectDealsStatus)
  const [isModalOpen, setIsModalOpen] = useState(false)

  useEffect(() => {
    dispatch(fetchDeals())
  }, [dispatch])

  // Refetch deals when modal closes (in case a new deal was created)
  useEffect(() => {
    if (!isModalOpen) {
      void dispatch(fetchDeals())
    }
  }, [isModalOpen, dispatch])

  const handleCreateNew = () => {
    dispatch(setCurrentDraft(null))
    setIsModalOpen(true)
  }

  const handleResumeDraft = (deal: DealSummary) => {
    dispatch(setCurrentDraft(deal))
    setIsModalOpen(true)
  }

  const handleViewDeal = (dealId: string) => {
    navigate(`/deals/${dealId}`)
  }

  const draftDeals = deals.filter((d) => ['DRAFT', 'CREATED'].includes(d.status) || !d.status)
  const activeDeal = deals.filter((d) => ['RUNNING', 'PAUSED', 'PAUSED_FOR_HUMAN_REVIEW', 'AWAITING_REVIEW'].includes(d.status))
  const completedDeals = deals.filter((d) => ['COMPLETED', 'REJECTED', 'FAILED'].includes(d.status))

  return (
    <div className="space-y-8">
      {/* Top Bar Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Deal Intelligence Center</h1>
          <p className="text-sm text-cosmic-muted mt-1">Manage active enterprise proposals and multi-agent workflows.</p>
        </div>
        <button onClick={handleCreateNew} className="btn-nagarro flex items-center gap-2">
          <Plus className="w-4 h-4 text-black" />
          <span>Create New Deal</span>
        </button>
      </div>

      {/* Loading State */}
      {dealsStatus === 'loading' && (
        <div className="text-center py-12">
          <div className="inline-block">
            <div className="w-8 h-8 border-2 border-nagarro-green border-t-transparent rounded-full animate-spin"></div>
          </div>
          <p className="text-cosmic-muted mt-3">Loading deals...</p>
        </div>
      )}

      {/* Draft Deals Section */}
      {draftDeals.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-cosmic-muted mb-3 uppercase tracking-wider">In Progress Drafts</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {draftDeals.map((deal) => (
              <div
                key={deal.id}
                className="cosmic-card p-4 border-l-4 border-l-amber-500/50 hover:border-l-amber-500 transition-all group"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-cosmic-border text-cosmic-muted">
                      {deal.target_industry}
                    </span>
                    <h3 className="text-base font-bold text-white mt-2 group-hover:text-nagarro-green transition-colors truncate">
                      {deal.title}
                    </h3>
                    <p className="text-xs text-cosmic-muted mt-1">{deal.target_company}</p>
                  </div>
                </div>

                <div className="space-y-2 pt-3 border-t border-cosmic-border/30">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-cosmic-muted">Status</span>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium border ${statusConfig.DRAFT.color}`}>
                      📝 Draft
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-cosmic-muted">Created</span>
                    <span className="text-white">{formatDate(deal.created_at)}</span>
                  </div>
                </div>

                <div className="flex gap-2 mt-4 pt-3 border-t border-cosmic-border/30">
                  <button
                    onClick={() => handleResumeDraft(deal)}
                    className="flex-1 px-3 py-1.5 text-xs font-medium text-black bg-nagarro-green hover:bg-nagarro-green/90 rounded transition"
                  >
                    Continue Setup
                  </button>
                  <button
                    onClick={() => handleViewDeal(deal.id)}
                    className="px-3 py-1.5 text-xs text-cosmic-muted hover:text-white border border-cosmic-border rounded transition"
                  >
                    View
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Active Deals Section */}
      {activeDeal.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-cosmic-muted mb-3 uppercase tracking-wider">Active Workflows</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {activeDeal.map((deal) => {
              const config = statusConfig[deal.status] || statusConfig.RUNNING
              return (
                <div
                  key={deal.id}
                  onClick={() => handleViewDeal(deal.id)}
                  className="cosmic-card p-5 cursor-pointer hover:border-nagarro-green/60 transition-all group"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${config.color}`}>
                        {config.icon} {config.label}
                      </span>
                      <h3 className="text-base font-bold text-white mt-2 group-hover:text-nagarro-green transition-colors truncate">
                        {deal.title}
                      </h3>
                      <p className="text-xs text-cosmic-muted mt-1">{deal.target_company}</p>
                    </div>
                  </div>

                  <div className="space-y-2 pt-3 border-t border-cosmic-border/30 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-2 text-cosmic-muted">
                        <Layers className="w-3.5 h-3.5 text-nagarro-green" />
                        Current Step:
                      </span>
                      <span className="text-white font-medium">Processing...</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-2 text-cosmic-muted">
                        <Clock className="w-3.5 h-3.5" />
                        Updated:
                      </span>
                      <span className="text-white">{formatDate(deal.updated_at)}</span>
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-cosmic-border/30">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleViewDeal(deal.id)
                      }}
                      className="w-full px-3 py-1.5 text-xs font-medium text-black bg-nagarro-green hover:bg-nagarro-green/90 rounded transition flex items-center justify-center gap-1"
                    >
                      <PlayCircle className="w-3.5 h-3.5" />
                      View Deal
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        </section>
      )}

      {/* Completed Deals Section */}
      {completedDeals.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-cosmic-muted mb-3 uppercase tracking-wider">Completed Deals</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {completedDeals.map((deal) => {
              const config = statusConfig[deal.status] || statusConfig.COMPLETED
              return (
                <div
                  key={deal.id}
                  onClick={() => handleViewDeal(deal.id)}
                  className="cosmic-card p-5 cursor-pointer hover:border-nagarro-green/60 transition-all group opacity-75 hover:opacity-100"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${config.color}`}>
                        {config.icon} {config.label}
                      </span>
                      <h3 className="text-base font-bold text-white mt-2 group-hover:text-nagarro-green transition-colors truncate">
                        {deal.title}
                      </h3>
                      <p className="text-xs text-cosmic-muted mt-1">{deal.target_company}</p>
                    </div>
                  </div>

                  <div className="space-y-2 pt-3 border-t border-cosmic-border/30 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-cosmic-muted">Industry:</span>
                      <span className="text-white">{deal.target_industry}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-2 text-cosmic-muted">
                        <Clock className="w-3.5 h-3.5" />
                        Completed:
                      </span>
                      <span className="text-white">{formatDate(deal.updated_at)}</span>
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-cosmic-border/30">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleViewDeal(deal.id)
                      }}
                      className="w-full px-3 py-1.5 text-xs font-medium text-white border border-cosmic-border hover:border-nagarro-green hover:text-nagarro-green rounded transition"
                    >
                      View Results
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        </section>
      )}

      {/* Empty State */}
      {deals.length === 0 && dealsStatus !== 'loading' && (
        <div className="cosmic-card p-12 text-center">
          <Briefcase className="w-12 h-12 text-cosmic-muted mx-auto mb-4 opacity-50" />
          <h3 className="text-lg font-semibold text-white mb-2">No Deals Yet</h3>
          <p className="text-sm text-cosmic-muted mb-6">Start by creating your first deal to begin the intelligence workflow.</p>
          <button onClick={handleCreateNew} className="btn-nagarro inline-flex items-center gap-2">
            <Plus className="w-4 h-4 text-black" />
            <span>Create Your First Deal</span>
          </button>
        </div>
      )}

      {/* Create Deal Modal */}
      <CreateDealModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
    </div>
  )
}