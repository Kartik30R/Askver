import { AlertTriangle, CheckCircle2, Clock, Loader2 } from 'lucide-react'
import { LANE_LABEL, LANE_ORDER } from '../../features/workflow/pipelineNodes'
import type { PipelineLane } from '../../features/workflow/pipelineNodes'

export type PipelineNodeState = 'completed' | 'paused' | 'failed' | 'running' | 'pending'

export type PipelineNode = {
  id: string
  label: string
  status: PipelineNodeState
  lane?: PipelineLane
}

type PipelineFlowProps = {
  nodes: PipelineNode[]
  statusBanner: string
  onNodeClick: (nodeId: string) => void
  progress?: { percent: number; phase: string } | null
}

const STYLE: Record<PipelineNodeState, string> = {
  completed: 'border-emerald-400/30 bg-emerald-500/10 text-emerald-200',
  running: 'border-cyan-400/40 bg-cyan-500/10 text-cyan-200',
  paused: 'border-amber-400/40 bg-amber-500/10 text-amber-200',
  failed: 'border-rose-400/40 bg-rose-500/10 text-rose-200',
  pending: 'border-white/10 bg-white/[0.03] text-slate-400',
}

function StatusIcon({ status }: { status: PipelineNodeState }) {
  if (status === 'completed') return <CheckCircle2 size={14} />
  if (status === 'running') return <Loader2 size={14} className="animate-spin" />
  if (status === 'failed') return <AlertTriangle size={14} />
  return <Clock size={14} />
}

export default function PipelineFlow({ nodes, statusBanner, onNodeClick, progress }: PipelineFlowProps) {
  const lanes = LANE_ORDER.map((lane) => ({ lane, items: nodes.filter((n) => n.lane === lane) })).filter((l) => l.items.length)

  return (
    <div className="space-y-4">
      <div className="cosmic-card rounded-2xl border border-white/10 bg-white/[0.03] p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm text-slate-200">{statusBanner}</p>
          {progress && (
            <span className="text-xs text-slate-400">
              {progress.phase} · {progress.percent}%
            </span>
          )}
        </div>
        {progress && (
          <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/10">
            <div className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-violet-400 transition-all" style={{ width: `${progress.percent}%` }} />
          </div>
        )}
      </div>

      <div className="pipeline-flow-scroll flex items-stretch gap-3 overflow-x-auto pb-2">
        {lanes.map(({ lane, items }, i) => (
          <div key={lane} className="flex items-stretch gap-3">
            <div className="w-52 flex-none rounded-2xl border border-white/10 bg-white/[0.02] p-3">
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400">{LANE_LABEL[lane]}</p>
              <div className="space-y-2">
                {items.map((n) => (
                  <button
                    key={n.id}
                    type="button"
                    onClick={() => onNodeClick(n.id)}
                    className={`flex w-full items-center justify-between gap-2 rounded-xl border px-3 py-2 text-left text-xs transition hover:brightness-125 ${STYLE[n.status]}`}
                  >
                    <span className="truncate">{n.label}</span>
                    <StatusIcon status={n.status} />
                  </button>
                ))}
              </div>
            </div>
            {i < lanes.length - 1 && <div className="flex items-center text-slate-600">›</div>}
          </div>
        ))}
      </div>
    </div>
  )
}
