import React from 'react'
import { CheckCircle2, Clock, Loader2, MessageSquareCode, X } from 'lucide-react'
import type { PipelineNode } from './PipelineFlow'

type NodeDetailTabsProps = {
  activeTabNode: string
  nodes: PipelineNode[]
  onSelectNode: (nodeId: string) => void
  companyResearchPanel: React.ReactNode
  financialPanel: React.ReactNode
  stakeholderPanel: React.ReactNode
  prioritiesPainPointsPanel: React.ReactNode
  industryPanel: React.ReactNode
  solutionFitPanel: React.ReactNode
  cxoBriefPanel: React.ReactNode
  reviewFeedback: string
  setReviewFeedback: (value: string) => void
  isSubmittingReview: boolean
  onReviewApproval: (status: 'approved' | 'needs_revision' | 'rejected') => Promise<void>
  pipelineState: Record<string, unknown> | null
}

export default function NodeDetailTabs({
  activeTabNode,
  nodes,
  onSelectNode,
  companyResearchPanel,
  financialPanel,
  stakeholderPanel,
  prioritiesPainPointsPanel,
  industryPanel,
  solutionFitPanel,
  cxoBriefPanel,
  reviewFeedback,
  setReviewFeedback,
  isSubmittingReview,
  onReviewApproval,
  pipelineState,
}: NodeDetailTabsProps) {
  return (
    <div className="cosmic-card overflow-hidden">
      <div className="flex items-center bg-cosmic-bg border-b border-cosmic-border overflow-x-auto">
        {nodes.map((node) => (
          <button
            key={node.id}
            type="button"
            onClick={() => onSelectNode(node.id)}
            className={`flex items-center gap-2 px-4 py-3 text-xs font-medium border-r border-cosmic-border whitespace-nowrap transition-all ${
              activeTabNode === node.id
                ? 'bg-cosmic-surface text-nagarro-green border-t-2 border-t-nagarro-green'
                : 'text-cosmic-muted hover:text-white hover:bg-cosmic-surface/50'
            }`}
          >
            {node.status === 'completed' && <CheckCircle2 className="w-3.5 h-3.5 text-nagarro-green" />}
            {node.status === 'paused' && <Clock className="w-3.5 h-3.5 text-amber-400" />}
            {node.label}
          </button>
        ))}
      </div>

      <div className="p-6">
        {activeTabNode === 'company_research' ? (
          <div className="max-w-none text-sm">{companyResearchPanel}</div>
        ) : activeTabNode === 'financial_intelligence' ? (
          <div className="max-w-none text-sm">{financialPanel}</div>
        ) : activeTabNode === 'stakeholder_intel' ? (
          <div className="max-w-none text-sm">{stakeholderPanel}</div>
        ) : activeTabNode === 'pain_point_detector' ? (
          <div className="max-w-none text-sm">{prioritiesPainPointsPanel}</div>
        ) : activeTabNode === 'industry_analysis' ? (
          <div className="max-w-none text-sm">{industryPanel}</div>
        ) : activeTabNode === 'service_mapper' ? (
          <div className="max-w-none text-sm">{solutionFitPanel}</div>
        ) : activeTabNode === 'cxo_brief_generator' ? (
          <div className="max-w-none text-sm">{cxoBriefPanel}</div>
        ) : activeTabNode === 'human_review_gate' ? (
          <div className="max-w-none text-sm">
            <div className="space-y-5">
              <div className="cosmic-card p-5 md:p-6">
                <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
                  <div>
                    <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Human review checkpoint</div>
                    <h3 className="mt-2 text-2xl font-bold text-white">Review and approve the final brief</h3>
                  </div>
                  <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-[10px] uppercase tracking-[0.14em] text-amber-300">
                    <Clock className="h-3.5 w-3.5" />
                    {String((pipelineState as Record<string, unknown> | null)?.mandatory_review_checkpoint ?? 'pending')}
                  </div>
                </div>

                <div className="mt-5 grid gap-4 md:grid-cols-3">
                  <div className="rounded-2xl border border-cosmic-border bg-cosmic-bg/40 p-4">
                    <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Checkpoint</div>
                    <div className="mt-2 text-lg font-semibold text-white">{String((pipelineState as Record<string, unknown> | null)?.mandatory_review_checkpoint ?? 'pending')}</div>
                  </div>
                  <div className="rounded-2xl border border-cosmic-border bg-cosmic-bg/40 p-4">
                    <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Approval</div>
                    <div className="mt-2 text-lg font-semibold text-white">{(pipelineState as Record<string, unknown> | null)?.human_approved ? 'Approved' : 'Awaiting review'}</div>
                  </div>
                  <div className="rounded-2xl border border-cosmic-border bg-cosmic-bg/40 p-4">
                    <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Feedback</div>
                    <div className="mt-2 text-sm text-cosmic-muted">{String((pipelineState as Record<string, unknown> | null)?.human_feedback ?? 'No feedback yet.')}</div>
                  </div>
                </div>

                <div className="mt-6 space-y-3">
                  <label className="block text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Reviewer notes</label>
                  <textarea
                    value={reviewFeedback}
                    onChange={(event) => setReviewFeedback(event.target.value)}
                    rows={4}
                    className="w-full rounded-2xl border border-cosmic-border bg-cosmic-bg/40 px-3 py-3 text-sm text-white placeholder:text-cosmic-muted focus:border-nagarro-green focus:outline-none"
                    placeholder="Add notes, revision requests, or approval rationale..."
                  />
                </div>

                <div className="mt-5 flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={() => void onReviewApproval('approved')}
                    disabled={isSubmittingReview}
                    className="inline-flex items-center gap-2 rounded-xl bg-nagarro-green px-4 py-2 text-sm font-semibold text-black transition hover:bg-nagarro-hover disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isSubmittingReview ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                    Approve brief
                  </button>
                  <button
                    type="button"
                    onClick={() => void onReviewApproval('needs_revision')}
                    disabled={isSubmittingReview}
                    className="inline-flex items-center gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-2 text-sm font-semibold text-amber-200 transition hover:border-amber-500/60 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isSubmittingReview ? <Loader2 className="h-4 w-4 animate-spin" /> : <MessageSquareCode className="h-4 w-4" />}
                    Request revision
                  </button>
                  <button
                    type="button"
                    onClick={() => void onReviewApproval('rejected')}
                    disabled={isSubmittingReview}
                    className="inline-flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm font-semibold text-red-200 transition hover:border-red-500/60 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isSubmittingReview ? <Loader2 className="h-4 w-4 animate-spin" /> : <X className="h-4 w-4" />}
                    Reject
                  </button>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="prose prose-invert max-w-none text-sm">
            {companyResearchPanel}
          </div>
        )}
      </div>
    </div>
  )
}
