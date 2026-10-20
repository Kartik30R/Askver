import { useState } from 'react'
import { ChevronDown, ShieldAlert, ShieldCheck } from 'lucide-react'
import type { VerificationReport } from '../../features/workflow/researchTypes'
import { BulletList, Meter, QualityPill } from './ui'

export default function ConfidenceBanner({
  report,
  gaps,
}: {
  report: VerificationReport | null | undefined
  gaps: string[]
}) {
  const [open, setOpen] = useState(false)
  if (!report) return null
  const good = report.overall_confidence === 'HIGH'
  const Icon = good ? ShieldCheck : ShieldAlert
  const allGaps = gaps.length ? gaps : report.known_gaps

  return (
    <div
      className={`rounded-2xl border p-4 ${
        good ? 'border-emerald-400/20 bg-emerald-500/5' : report.overall_confidence === 'MEDIUM' ? 'border-amber-400/20 bg-amber-500/5' : 'border-rose-400/20 bg-rose-500/5'
      }`}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm text-slate-100">
          <Icon size={18} />
          <span className="font-semibold">Evidence confidence</span>
          <QualityPill level={report.overall_confidence} />
          <span className="text-xs text-slate-400">
            {report.scores.facts} facts · {report.scores.sources} sources
          </span>
        </div>
        {allGaps.length > 0 && (
          <button type="button" onClick={() => setOpen((v) => !v)} className="flex items-center gap-1 text-xs text-slate-300 hover:text-white">
            {allGaps.length} item{allGaps.length === 1 ? '' : 's'} to verify
            <ChevronDown size={14} className={open ? 'rotate-180 transition' : 'transition'} />
          </button>
        )}
      </div>
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        <Meter label="Topic coverage" value={report.scores.coverage} />
        <Meter label="Claims grounded in facts" value={report.scores.grounding} tone="green" />
        <Meter label="From reliable sources" value={report.scores.reliable_source_share} tone="amber" />
      </div>
      {open && (
        <div className="mt-4 border-t border-white/10 pt-3">
          <p className="mb-2 text-xs uppercase tracking-wide text-slate-400">Confirm these in the meeting</p>
          <BulletList items={allGaps} />
        </div>
      )}
    </div>
  )
}
