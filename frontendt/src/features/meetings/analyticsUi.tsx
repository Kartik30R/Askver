import { createContext, useContext, useState } from 'react'
import type { ReactNode } from 'react'
import { AlertTriangle, ChevronDown, ShieldAlert, ShieldCheck } from 'lucide-react'

import type {
  AnalysisFinding,
  Basis,
  Confidence,
  Evidence,
  NeedItem,
  Severity,
} from './analysisTypes'

// ───────────────────────── Context (meeting links from evidence / ids) ─────────────────────────
export type AnalyticsContextValue = {
  meetingTitle: (meetingId: string) => string | null
  openMeeting: (meetingId: string) => void
}

export const AnalyticsContext = createContext<AnalyticsContextValue>({
  meetingTitle: () => null,
  openMeeting: () => undefined,
})

// ───────────────────────── Formatting ─────────────────────────
export const humanize = (value: string): string => {
  const text = value.replace(/_/g, ' ').toLowerCase()
  return text.charAt(0).toUpperCase() + text.slice(1)
}

export const formatDate = (iso: string | null | undefined): string => {
  if (!iso) return '—'
  const date = /^\d{4}-\d{2}-\d{2}$/.test(iso) ? new Date(`${iso}T00:00:00`) : new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}

export const formatDateTime = (iso: string | null | undefined): string => {
  if (!iso) return '—'
  const date = new Date(iso)
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleString()
}

// ───────────────────────── Tones ─────────────────────────
export type Tone = 'neutral' | 'green' | 'cyan' | 'amber' | 'orange' | 'red' | 'violet'

const TONE_CLASS: Record<Tone, string> = {
  neutral: 'border-cosmic-border bg-cosmic-bg/40 text-cosmic-muted',
  green: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300',
  cyan: 'border-cyan-500/40 bg-cyan-500/10 text-cyan-300',
  amber: 'border-amber-500/40 bg-amber-500/10 text-amber-300',
  orange: 'border-orange-500/40 bg-orange-500/10 text-orange-300',
  red: 'border-red-500/40 bg-red-500/10 text-red-300',
  violet: 'border-violet-500/40 bg-violet-500/10 text-violet-300',
}

export const TONE_FILL: Record<Tone, string> = {
  neutral: 'bg-slate-400',
  green: 'bg-emerald-400',
  cyan: 'bg-cyan-400',
  amber: 'bg-amber-400',
  orange: 'bg-orange-400',
  red: 'bg-red-400',
  violet: 'bg-violet-400',
}

const TONE_HEX: Record<Tone, string> = {
  neutral: '#94a3b8',
  green: '#6ee7b7',
  cyan: '#67e8f9',
  amber: '#fcd34d',
  orange: '#fdba74',
  red: '#fca5a5',
  violet: '#c4b5fd',
}

export const TONE_TEXT: Record<Tone, string> = {
  neutral: 'text-cosmic-muted',
  green: 'text-emerald-300',
  cyan: 'text-cyan-300',
  amber: 'text-amber-300',
  orange: 'text-orange-300',
  red: 'text-red-300',
  violet: 'text-violet-300',
}

export const severityTone = (value: Severity): Tone =>
  ({ LOW: 'cyan', MEDIUM: 'amber', HIGH: 'orange', CRITICAL: 'red' } as const)[value]

export const confidenceTone = (value: Confidence): Tone =>
  ({ LOW: 'amber', MEDIUM: 'cyan', HIGH: 'green' } as const)[value]

export const ratioTone = (ratio: number): Tone => (ratio >= 0.7 ? 'green' : ratio >= 0.45 ? 'amber' : 'red')

/** Semantic tone for enum values that are not severities/confidences. */
const STATUS_TONE: Record<string, Tone> = {
  POSITIVE: 'green',
  COMPLETED: 'green',
  RESOLVED: 'green',
  SUPPORTIVE: 'green',
  IMPROVING: 'green',
  FULFILLED: 'green',
  CONFIRMED: 'green',
  ANSWERED: 'green',
  CONCRETE_COMMITMENT: 'green',
  AGREED: 'green',
  STRONG: 'green',
  ACTIVE_EVALUATION: 'cyan',
  STABLE: 'cyan',
  MITIGATING: 'cyan',
  OUR_TEAM: 'cyan',
  NEUTRAL: 'neutral',
  EXPLORATORY: 'neutral',
  UNKNOWN: 'neutral',
  INSUFFICIENT_DATA: 'neutral',
  ACCEPTED: 'neutral',
  AI_RECOMMENDED: 'violet',
  INFERRED: 'violet',
  NEW_INSIGHT: 'violet',
  MIXED: 'amber',
  STALLED: 'amber',
  PARTIAL: 'amber',
  PARTIALLY_RESOLVED: 'amber',
  SKEPTICAL: 'amber',
  WEAK_INTEREST: 'amber',
  OPEN: 'amber',
  UNVALIDATED: 'amber',
  PROVOKED_QUESTION: 'amber',
  NEGATIVE: 'red',
  FAILED: 'red',
  UNRESOLVED: 'red',
  RESISTANT: 'red',
  DECLINING: 'red',
  CONTRADICTED: 'red',
  OVERDUE: 'red',
  BLOCKER: 'red',
  IRRELEVANT: 'red',
  UNSUPPORTED_CLAIM: 'orange',
  MISSING_PROOF: 'orange',
  INEFFECTIVE: 'orange',
}

export const statusTone = (value: string): Tone => STATUS_TONE[value] ?? 'neutral'

// ───────────────────────── Atoms ─────────────────────────
export function Pill({ tone = 'neutral', children, icon }: { tone?: Tone; children: ReactNode; icon?: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] ${TONE_CLASS[tone]}`}
    >
      {icon}
      {children}
    </span>
  )
}

/** Pill whose label and colour come from an enum value. */
export function StatusPill({ value, prefix }: { value: string; prefix?: string }) {
  return (
    <Pill tone={statusTone(value)}>
      {prefix ? `${prefix} ` : ''}
      {humanize(value)}
    </Pill>
  )
}

export function SeverityPill({ value, prefix }: { value: Severity; prefix?: string }) {
  return (
    <Pill tone={severityTone(value)}>
      {prefix ? `${prefix} ` : ''}
      {humanize(value)}
    </Pill>
  )
}

export function ConfidencePill({ value, prefix = 'Confidence' }: { value: Confidence; prefix?: string }) {
  return (
    <Pill tone={confidenceTone(value)}>
      {humanize(value)} {prefix ? prefix.toLowerCase() : ''}
    </Pill>
  )
}

export function Label({ children }: { children: ReactNode }) {
  return <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">{children}</div>
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <Label>{label}</Label>
      <div className="mt-1.5 text-sm leading-6 text-cosmic-text">{children}</div>
    </div>
  )
}

export function Empty({ children }: { children: ReactNode }) {
  return (
    <p className="rounded-xl border border-dashed border-cosmic-border bg-cosmic-bg/20 px-3 py-3 text-xs text-cosmic-muted">
      {children}
    </p>
  )
}

export function Panel({
  title,
  icon,
  count,
  aside,
  children,
  className = '',
}: {
  title: string
  icon?: ReactNode
  count?: number
  aside?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={`cosmic-card p-5 ${className}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">
          {icon}
          <span>{title}</span>
          {count !== undefined && (
            <span className="rounded-full border border-cosmic-border bg-cosmic-bg/60 px-1.5 py-0.5 text-[10px] font-semibold text-nagarro-green">
              {count}
            </span>
          )}
        </div>
        {aside}
      </div>
      <div className="mt-4">{children}</div>
    </section>
  )
}

export function ItemCard({ children, tone }: { children: ReactNode; tone?: Tone }) {
  const border =
    tone === undefined || tone === 'neutral' ? 'border-cosmic-border' : TONE_CLASS[tone].split(' ')[0]
  return <div className={`rounded-xl border ${border} bg-cosmic-bg/30 p-4`}>{children}</div>
}

export function StringList({
  items,
  empty = 'Nothing recorded.',
  tone = 'green',
  ordered = false,
}: {
  items: string[]
  empty?: string
  tone?: Tone
  ordered?: boolean
}) {
  if (!items.length) return <Empty>{empty}</Empty>
  return (
    <ul className="space-y-2">
      {items.map((item, index) => (
        <li key={`${index}-${item.slice(0, 24)}`} className="flex gap-3 text-sm leading-6 text-cosmic-text">
          {ordered ? (
            <span className="mt-0.5 inline-flex h-5 w-5 flex-none items-center justify-center rounded-full border border-cosmic-border bg-cosmic-bg/60 text-[10px] font-semibold text-nagarro-green">
              {index + 1}
            </span>
          ) : (
            <span className={`mt-2 h-1.5 w-1.5 flex-none rounded-full ${TONE_FILL[tone]}`} />
          )}
          <span>{item}</span>
        </li>
      ))}
    </ul>
  )
}

export function Chips({ items, empty = 'None' }: { items: string[]; empty?: string }) {
  if (!items.length) return <span className="text-xs text-cosmic-muted">{empty}</span>
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item, index) => (
        <span
          key={`${index}-${item}`}
          className="rounded-full border border-cosmic-border bg-cosmic-bg/40 px-3 py-1 text-xs text-cosmic-text"
        >
          {item}
        </span>
      ))}
    </div>
  )
}

export function MeetingChips({ ids }: { ids: string[] }) {
  const { meetingTitle, openMeeting } = useContext(AnalyticsContext)
  if (!ids.length) return <span className="text-xs text-cosmic-muted">None</span>
  return (
    <div className="flex flex-wrap gap-1.5">
      {ids.map((id) => (
        <button key={id} type="button" className="source-chip" onClick={() => openMeeting(id)}>
          <span className="source-chip-domain">{meetingTitle(id) ?? id.slice(0, 8)}</span>
        </button>
      ))}
    </div>
  )
}

export function Notice({ tone, children, icon }: { tone: Tone; children: ReactNode; icon?: ReactNode }) {
  return (
    <div className={`flex items-start gap-3 rounded-xl border px-4 py-3 text-sm ${TONE_CLASS[tone]}`}>
      {icon ?? <AlertTriangle className="mt-0.5 h-4 w-4 flex-none" />}
      <div className="min-w-0 flex-1 leading-6">{children}</div>
    </div>
  )
}

export function Unavailable({ name, warnings }: { name: string; warnings: string[] }) {
  const related = warnings.filter((warning) => warning.toLowerCase().includes(name.toLowerCase()))
  return (
    <Notice tone="amber">
      <div className="font-semibold">{name} is unavailable</div>
      <div className="text-xs opacity-80">
        {related.length ? related.join(' · ') : 'This section failed or was not generated for this run.'}
      </div>
    </Notice>
  )
}

// ───────────────────────── Tabs ─────────────────────────
export function TabBar<T extends string>({
  tabs,
  active,
  onChange,
}: {
  tabs: ReadonlyArray<{ id: T; label: string; count?: number }>
  active: T
  onChange: (id: T) => void
}) {
  return (
    <div className="pipeline-flow-scroll flex gap-2 overflow-x-auto pb-1" role="tablist">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={active === tab.id}
          onClick={() => onChange(tab.id)}
          className={`company-intel-tab ${active === tab.id ? 'active' : ''}`}
        >
          {tab.label}
          {tab.count !== undefined && <span className="ml-2 text-[10px] opacity-70">{tab.count}</span>}
        </button>
      ))}
    </div>
  )
}

// ───────────────────────── Charts ─────────────────────────
export function Ring({
  value,
  max = 100,
  size = 112,
  stroke = 9,
  tone,
  children,
}: {
  value: number
  max?: number
  size?: number
  stroke?: number
  tone?: Tone
  children?: ReactNode
}) {
  const ratio = Math.max(0, Math.min(1, max ? value / max : 0))
  const resolved = tone ?? ratioTone(ratio)
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius
  return (
    <div className="relative inline-flex flex-none items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90" role="img" aria-label={`${value} of ${max}`}>
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="rgba(148,163,184,0.16)" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={TONE_HEX[resolved]}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${circumference * ratio} ${circumference}`}
          style={{ transition: 'stroke-dasharray 600ms ease' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">{children}</div>
    </div>
  )
}

export function ScoreMeter({ score, max = 10, label }: { score: number | null; max?: number; label?: string }) {
  if (score === null) {
    return <span className="text-xs text-cosmic-muted">Not scored</span>
  }
  const ratio = Math.max(0, Math.min(1, score / max))
  return (
    <div className="flex items-center gap-3" role="meter" aria-valuemin={0} aria-valuemax={max} aria-valuenow={score} aria-label={label}>
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-700/40">
        <div className={`h-full rounded-full ${TONE_FILL[ratioTone(ratio)]}`} style={{ width: `${ratio * 100}%` }} />
      </div>
      <span className="w-12 text-right text-sm font-semibold tabular-nums text-white">
        {score}
        <span className="text-xs font-normal text-cosmic-muted">/{max}</span>
      </span>
    </div>
  )
}

export function Sparkline({
  values,
  max,
  label,
  tone = 'green',
}: {
  values: Array<number | null>
  max: number
  label: string
  tone?: Tone
}) {
  const width = 180
  const height = 44
  const pad = 6
  const step = values.length > 1 ? (width - pad * 2) / (values.length - 1) : 0
  const points = values.map((value, index) =>
    value === null ? null : { x: pad + index * step, y: height - pad - (Math.max(0, Math.min(max, value)) / max) * (height - pad * 2) },
  )
  const segments: string[] = []
  let current: string[] = []
  points.forEach((point) => {
    if (point) current.push(`${point.x},${point.y}`)
    else if (current.length) {
      segments.push(current.join(' '))
      current = []
    }
  })
  if (current.length) segments.push(current.join(' '))
  const last = [...values].reverse().find((value) => value !== null) ?? null
  return (
    <div>
      <div className="flex items-baseline justify-between gap-2">
        <Label>{label}</Label>
        <span className={`text-sm font-semibold tabular-nums ${TONE_TEXT[tone]}`}>{last === null ? '—' : last}</span>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} className="mt-1 h-11 w-full" role="img" aria-label={`${label} trend`} preserveAspectRatio="none">
        <line x1={pad} x2={width - pad} y1={height - pad} y2={height - pad} stroke="rgba(148,163,184,0.2)" />
        {segments.map((segment) => (
          <polyline key={segment} points={segment} fill="none" stroke={TONE_HEX[tone]} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
        ))}
        {points.map((point, index) =>
          point ? <circle key={index} cx={point.x} cy={point.y} r={3} fill={TONE_HEX[tone]} /> : null,
        )}
      </svg>
    </div>
  )
}

// ───────────────────────── Evidence + finding footer ─────────────────────────
export function EvidenceList({ evidence }: { evidence: Evidence[] }) {
  const { meetingTitle, openMeeting } = useContext(AnalyticsContext)
  if (!evidence.length) return <Empty>No supporting evidence was attached to this finding.</Empty>
  return (
    <ul className="space-y-3">
      {evidence.map((item, index) => (
        <li key={`${index}-${item.quote.slice(0, 20)}`} className="rounded-xl border border-cosmic-border bg-slate-950/40 p-3">
          <blockquote className="border-l-2 border-nagarro-green/50 pl-3 text-sm italic leading-6 text-cosmic-text">
            “{item.quote}”
          </blockquote>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Pill tone="neutral">{humanize(item.source)}</Pill>
            {item.speaker && <Pill tone="cyan">{item.speaker}</Pill>}
            {item.timestamp && <Pill tone="neutral">{item.timestamp}</Pill>}
            {item.slide_number !== null && <Pill tone="violet">Slide {item.slide_number}</Pill>}
            {item.meeting_id && (
              <button type="button" className="source-chip" onClick={() => openMeeting(item.meeting_id as string)}>
                <span className="source-chip-domain">{meetingTitle(item.meeting_id) ?? 'Open meeting'}</span>
              </button>
            )}
            {item.verified ? (
              <Pill tone="green" icon={<ShieldCheck className="h-3 w-3" />}>
                Verified quote
              </Pill>
            ) : (
              <Pill tone="amber" icon={<ShieldAlert className="h-3 w-3" />}>
                Unverified quote
              </Pill>
            )}
          </div>
        </li>
      ))}
    </ul>
  )
}

const basisTone = (basis: Basis): Tone => (basis === 'STATED' ? 'green' : 'violet')

/** Basis + confidence + expandable evidence. Rendered under every finding. */
export function FindingMeta({ finding }: { finding: AnalysisFinding }) {
  const [open, setOpen] = useState(false)
  const unverified = finding.evidence.filter((item) => !item.verified).length
  return (
    <div className="mt-3 border-t border-cosmic-border/60 pt-3">
      <div className="flex flex-wrap items-center gap-2">
        <Pill tone={basisTone(finding.basis)}>{finding.basis === 'STATED' ? 'Stated' : 'Inferred'}</Pill>
        <ConfidencePill value={finding.confidence} />
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          aria-expanded={open}
          className="ml-auto inline-flex items-center gap-1.5 rounded-full border border-cosmic-border bg-cosmic-bg/40 px-2.5 py-1 text-[11px] text-cosmic-muted transition-all duration-200 hover:border-nagarro-green/40 hover:text-white"
        >
          Evidence ({finding.evidence.length})
          {unverified > 0 && <span className="h-1.5 w-1.5 rounded-full bg-amber-400" title={`${unverified} unverified`} />}
          <ChevronDown className={`h-3 w-3 transition-transform ${open ? 'rotate-180' : ''}`} />
        </button>
      </div>
      {open && (
        <div className="mt-3">
          <EvidenceList evidence={finding.evidence} />
        </div>
      )}
    </div>
  )
}

// ───────────────────────── Shared blocks ─────────────────────────
export function NeedBlock({ title, items, icon }: { title: string; items: NeedItem[]; icon?: ReactNode }) {
  return (
    <Panel title={title} count={items.length} icon={icon}>
      {items.length ? (
        <div className="space-y-3">
          {items.map((item, index) => (
            <ItemCard key={`${index}-${item.description.slice(0, 24)}`}>
              <p className="text-sm leading-6 text-white">{item.description}</p>
              {item.business_impact && (
                <p className="mt-2 text-xs leading-5 text-cosmic-muted">
                  <span className="font-semibold text-cosmic-text">Business impact · </span>
                  {item.business_impact}
                </p>
              )}
              <FindingMeta finding={item} />
            </ItemCard>
          ))}
        </div>
      ) : (
        <Empty>Nothing identified.</Empty>
      )}
    </Panel>
  )
}

export function BoolRow({ label, value }: { label: string; value: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-xl border border-cosmic-border bg-cosmic-bg/30 px-3 py-2.5">
      <span className="text-sm text-cosmic-text">{label}</span>
      <Pill tone={value ? 'green' : 'red'}>{value ? 'Yes' : 'No'}</Pill>
    </div>
  )
}

export function SkeletonBlock({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-3" aria-busy="true">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="h-16 animate-pulse rounded-xl border border-cosmic-border bg-cosmic-bg/30" />
      ))}
    </div>
  )
}