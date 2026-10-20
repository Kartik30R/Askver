import { useMemo, useState } from 'react'
import { ExternalLink } from 'lucide-react'
import type { PipelineStateResponse } from '../../features/workflow/workflowApi'
import { groupFactsByCategory, TIER_LABEL } from '../../features/workflow/citations'
import type { FinancialSnapshot } from '../../features/workflow/researchTypes'
import { BulletList, Card, Empty, Pill, QualityPill, humanize } from './ui'
import type { Tone } from './ui'

const VERDICT_TONE: Record<string, Tone> = {
  SUPPORTED: 'green',
  PARTIAL: 'amber',
  UNSUPPORTED: 'red',
  CONTRADICTED: 'red',
  UNTESTED: 'neutral',
}

const METRICS: Array<{ key: string; label: string; kind: 'money' | 'pct' | 'x' }> = [
  { key: 'total_revenue', label: 'Revenue (TTM)', kind: 'money' },
  { key: 'revenue_growth', label: 'Revenue growth', kind: 'pct' },
  { key: 'gross_margins', label: 'Gross margin', kind: 'pct' },
  { key: 'operating_margins', label: 'Operating margin', kind: 'pct' },
  { key: 'free_cashflow', label: 'Free cash flow', kind: 'money' },
  { key: 'return_on_equity', label: 'Return on equity', kind: 'pct' },
]

const money = (v: number, ccy: string) => {
  for (const [div, suf] of [[1e12, 'T'], [1e9, 'B'], [1e6, 'M']] as const) {
    if (Math.abs(v) >= div) return `${ccy} ${(v / div).toFixed(2)}${suf}`
  }
  return `${ccy} ${v.toLocaleString()}`
}

function FinancialCards({ fin }: { fin: FinancialSnapshot }) {
  const ccy = fin.currency ?? 'USD'
  const raw = fin.raw_metrics ?? {}
  const cells = METRICS.map((m) => {
    const v = raw[m.key]
    if (typeof v !== 'number') return null
    const text = m.kind === 'pct' ? `${(v * 100).toFixed(1)}%` : m.kind === 'money' ? money(v, ccy) : v.toFixed(2)
    return { label: m.label, text }
  }).filter((c): c is { label: string; text: string } => c !== null)
  if (typeof fin.market_cap === 'number') cells.unshift({ label: 'Market cap', text: money(fin.market_cap, ccy) })
  if (!cells.length) return <Empty text="No numeric financial metrics available." />
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {cells.map((c) => (
        <div key={c.label} className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
          <p className="text-[11px] uppercase tracking-wide text-slate-400">{c.label}</p>
          <p className="mt-1 text-lg font-semibold text-slate-50">{c.text}</p>
        </div>
      ))}
    </div>
  )
}

export default function ResearchPanel({ state }: { state: PipelineStateResponse }) {
  const plan = state.research_plan
  const facts = state.facts
  const sources = state.sources
  const verdicts = new Map((state.insight_synthesis?.hypothesis_verdicts ?? []).map((v) => [v.statement.trim().toLowerCase(), v] as const))
  const byCategory = useMemo(() => groupFactsByCategory(facts), [facts])
  const categories = Object.keys(byCategory).sort()
  const [category, setCategory] = useState<string>('ALL')
  const shown = category === 'ALL' ? Object.values(facts ?? {}) : byCategory[category] ?? []
  const fin = state.financial_snapshot
  const sortedSources = Object.values(sources ?? {}).sort((a, b) => a.tier - b.tier)

  if (!plan && !Object.keys(facts ?? {}).length) {
    return <Empty text="Research has not produced evidence yet." />
  }

  return (
    <div className="space-y-5">
      {plan && (
        <Card title="Research plan">
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-400">Company</p>
              <p className="mt-1 text-sm text-slate-100">{plan.company_legal_name}</p>
              <p className="text-xs text-slate-400">
                {humanize(plan.listing_status)} · {plan.sub_sector}
              </p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-400">Regions</p>
              <p className="mt-1 text-sm text-slate-100">{plan.regions.join(', ') || '—'}</p>
              <p className="mt-2 text-xs uppercase tracking-wide text-slate-400">Business lines</p>
              <p className="mt-1 text-sm text-slate-100">{plan.business_lines.join(', ') || '—'}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-400">Benchmark peers</p>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {plan.peers.map((p) => (
                  <Pill key={p}>{p}</Pill>
                ))}
              </div>
              <p className="mt-2 text-xs uppercase tracking-wide text-slate-400">Regulation</p>
              <p className="mt-1 text-sm text-slate-100">{plan.regulatory_regimes.join(', ') || '—'}</p>
            </div>
          </div>
        </Card>
      )}

      {plan && plan.hypotheses.length > 0 && (
        <Card title="Deal hypotheses & what the evidence says">
          <ul className="space-y-3">
            {plan.hypotheses.map((h) => {
              const v = verdicts.get(h.statement.trim().toLowerCase())
              return (
                <li key={h.statement} className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-medium text-slate-50">{h.statement}</p>
                    <Pill tone={VERDICT_TONE[v?.verdict ?? 'UNTESTED']}>{humanize(v?.verdict ?? 'UNTESTED')}</Pill>
                  </div>
                  <p className="mt-1 text-xs text-slate-400">{v?.rationale ?? h.how_to_test}</p>
                </li>
              )
            })}
          </ul>
        </Card>
      )}

      <Card title="Financial snapshot" right={fin?.symbol ? <Pill tone="cyan">{fin.symbol}</Pill> : undefined}>
        {fin && fin.availability === 'available' ? (
          <FinancialCards fin={fin} />
        ) : (
          <Empty text="No verified market data (private company or not listed). Any financial figures appear only as sourced facts below." />
        )}
      </Card>

      <Card title="Evidence" right={<Pill>{Object.keys(facts ?? {}).length} facts</Pill>}>
        <div className="mb-3 flex flex-wrap gap-1.5">
          {['ALL', ...categories].map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setCategory(c)}
              className={`rounded-full border px-2.5 py-1 text-xs ${
                category === c ? 'border-cyan-400/40 bg-cyan-500/15 text-cyan-200' : 'border-white/10 text-slate-400 hover:bg-white/5'
              }`}
            >
              {c === 'ALL' ? 'All' : humanize(c)} {c !== 'ALL' && <span className="text-slate-500">{byCategory[c]?.length}</span>}
            </button>
          ))}
        </div>
        <ul className="divide-y divide-white/5">
          {shown.map((f) => (
            <li key={f.id} className="flex items-start justify-between gap-3 py-2.5 text-sm">
              <div className="min-w-0">
                <p className="text-slate-100">{f.claim}</p>
                <p className="mt-0.5 text-xs text-slate-500">
                  {[f.value, f.period].filter(Boolean).join(' · ')} {f.source_ids.length > 0 && `· ${f.source_ids.length} source${f.source_ids.length > 1 ? 's' : ''}`}
                </p>
              </div>
              <div className="flex flex-none items-center gap-1.5">
                <Pill>{humanize(f.category)}</Pill>
                <QualityPill level={f.confidence} />
              </div>
            </li>
          ))}
        </ul>
        {!shown.length && <Empty text="No facts in this category." />}
      </Card>

      <Card title="Sources" right={<Pill>{sortedSources.length}</Pill>}>
        <ul className="space-y-2">
          {sortedSources.map((s) => (
            <li key={s.id} className="flex items-start justify-between gap-3 text-sm">
              <div className="min-w-0">
                <p className="truncate text-slate-100">{s.title}</p>
                <p className="text-xs text-slate-500">{[TIER_LABEL[s.tier], s.published_date].filter(Boolean).join(' · ')}</p>
              </div>
              {s.url && (
                <a href={s.url} target="_blank" rel="noreferrer" className="flex-none text-cyan-300 hover:text-cyan-200">
                  <ExternalLink size={14} />
                </a>
              )}
            </li>
          ))}
        </ul>
        {!sortedSources.length && <Empty text="No sources recorded." />}
      </Card>

      {(state.research_gaps?.length ?? 0) > 0 && (
        <Card title="Research gaps">
          <BulletList items={state.research_gaps ?? []} tone="text-amber-200" />
        </Card>
      )}
    </div>
  )
}
