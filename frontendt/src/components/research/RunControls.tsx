import { useState } from 'react'
import { Loader2, Play } from 'lucide-react'
import { Card } from './ui'

type Props = {
  mode: 'empty' | 'legacy'
  busy: boolean
  defaultDepth?: string | null
  defaultMinutes?: number | null
  onStart: (depth: 'quick' | 'standard' | 'deep', minutes: number) => Promise<void> | void
}

export default function RunControls({ mode, busy, defaultDepth, defaultMinutes, onStart }: Props) {
  const initial = defaultDepth === 'quick' || defaultDepth === 'deep' ? defaultDepth : 'standard'
  const [depth, setDepth] = useState<'quick' | 'standard' | 'deep'>(initial)
  const [minutes, setMinutes] = useState<number>(defaultMinutes ?? 45)

  return (
    <Card title={mode === 'legacy' ? 'This deal was researched with the previous engine' : 'Run deal research'}>
      <p className="text-sm text-slate-300">
        {mode === 'legacy'
          ? 'Re-run the research to get the evidence-backed playbook, frameworks, citations and confidence score. Your documents, meetings and analytics are not affected.'
          : 'Research the company, build the strategic analysis and prepare the meeting playbook.'}
      </p>
      <div className="mt-4 flex flex-wrap items-end gap-3">
        <label className="text-xs text-slate-400">
          Depth
          <select
            value={depth}
            onChange={(e) => setDepth(e.target.value as 'quick' | 'standard' | 'deep')}
            className="mt-1 block rounded-lg border border-white/10 bg-slate-950 px-3 py-2 text-sm text-slate-100"
          >
            <option value="quick">Quick (lowest cost)</option>
            <option value="standard">Standard</option>
            <option value="deep">Deep (most sources)</option>
          </select>
        </label>
        <label className="text-xs text-slate-400">
          Meeting length (min)
          <input
            type="number"
            min={15}
            max={180}
            value={minutes}
            onChange={(e) => setMinutes(Math.min(180, Math.max(15, Number(e.target.value) || 45)))}
            className="mt-1 block w-28 rounded-lg border border-white/10 bg-slate-950 px-3 py-2 text-sm text-slate-100"
          />
        </label>
        <button type="button" disabled={busy} onClick={() => void onStart(depth, minutes)} className="btn-nagarro flex items-center gap-2 disabled:opacity-50">
          {busy ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />} {mode === 'legacy' ? 'Re-run research' : 'Start research'}
        </button>
      </div>
    </Card>
  )
}
