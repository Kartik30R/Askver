import { CheckCircle2, Clock3, Loader2, MessageSquareCode, X } from 'lucide-react'
import type { PipelineStateResponse } from '../../features/workflow/workflowApi'

export default function ReviewPanel({
  state,
  reviewFeedback,
  setReviewFeedback,
  isSubmittingReview,
  onReviewApproval,
}: {
  state: PipelineStateResponse | null
  reviewFeedback: string
  setReviewFeedback: (value: string) => void
  isSubmittingReview: boolean
  onReviewApproval: (status: 'approved' | 'needs_revision' | 'rejected') => Promise<void>
}) {
  return (
    <div className="space-y-5">
      <div className="cosmic-card p-5 md:p-6">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Human review checkpoint</p>
            <h3 className="mt-2 text-2xl font-bold text-white">Review the final brief</h3>
          </div>
          <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-[10px] uppercase tracking-[0.14em] text-amber-300">
            <Clock3 className="h-3.5 w-3.5" />
            {String(state?.mandatory_review_checkpoint ?? 'pending')}
          </div>
        </div>

        <div className="mt-5 grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl border border-cosmic-border bg-cosmic-bg/40 p-4">
            <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Checkpoint</div>
            <div className="mt-2 text-lg font-semibold text-white">{String(state?.mandatory_review_checkpoint ?? 'pending')}</div>
          </div>
          <div className="rounded-2xl border border-cosmic-border bg-cosmic-bg/40 p-4">
            <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Approval</div>
            <div className="mt-2 text-lg font-semibold text-white">{state?.human_approved ? 'Approved' : 'Awaiting review'}</div>
          </div>
          <div className="rounded-2xl border border-cosmic-border bg-cosmic-bg/40 p-4">
            <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Feedback</div>
            <div className="mt-2 text-sm text-cosmic-muted">{String(state?.human_feedback ?? 'No feedback yet.')}</div>
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
  )
}
