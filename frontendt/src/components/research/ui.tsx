import type { ReactNode } from 'react'
import type { Level } from '../../features/workflow/researchTypes'

export type Tone = 'neutral' | 'green' | 'amber' | 'red' | 'cyan' | 'violet' | 'orange'

const TONE_CLASS: Record<Tone, string> = {
  neutral: 'bg-white/5 text-slate-300 border-white/10',
  green: 'bg-emerald-500/15 text-emerald-300 border-emerald-400/30',
  amber: 'bg-amber-500/15 text-amber-300 border-amber-400/30',
  red: 'bg-rose-500/15 text-rose-300 border-rose-400/30',
  cyan: 'bg-cyan-500/15 text-cyan-300 border-cyan-400/30',
  violet: 'bg-violet-500/15 text-violet-300 border-violet-400/30',
  orange: 'bg-orange-500/15 text-orange-300 border-orange-400/30',
}

export const humanize = (value: string): string =>
  value
    .toLowerCase()
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())

export function Pill({ tone = 'neutral', children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium leading-5 ${TONE_CLASS[tone]}`}
    >
      {children}
    </span>
  )
}

/** HIGH = good (confidence, evidence strength). */
export const qualityTone = (level?: string | null): Tone =>
  level === 'HIGH' ? 'green' : level === 'MEDIUM' ? 'amber' : level === 'LOW' ? 'red' : 'neutral'

/** HIGH = big/serious (impact, likelihood, severity). */
export const intensityTone = (level?: string | null): Tone =>
  level === 'HIGH' || level === 'CRITICAL' ? 'red' : level === 'MEDIUM' ? 'amber' : level === 'LOW' ? 'cyan' : 'neutral'

export function QualityPill({ level, prefix }: { level?: Level | string | null; prefix?: string }) {
  if (!level) return null
  return (
    <Pill tone={qualityTone(level)}>
      {prefix ? `${prefix} ` : ''}
      {humanize(level)}
    </Pill>
  )
}

export function IntensityPill({ level, prefix }: { level?: Level | string | null; prefix?: string }) {
  if (!level) return null
  return (
    <Pill tone={intensityTone(level)}>
      {prefix ? `${prefix} ` : ''}
      {humanize(level)}
    </Pill>
  )
}

export function Card({
  title,
  icon,
  right,
  children,
  className = '',
}: {
  title?: ReactNode
  icon?: ReactNode
  right?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={`cosmic-card rounded-2xl border border-white/10 bg-white/[0.03] p-4 sm:p-5 ${className}`}>
      {(title || right) && (
        <header className="mb-3 flex items-center justify-between gap-3">
          <h3 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-200">
            {icon}
            {title}
          </h3>
          {right}
        </header>
      )}
      {children}
    </section>
  )
}

export function Empty({ text }: { text: string }) {
  return <p className="rounded-xl border border-dashed border-white/10 px-4 py-6 text-center text-sm text-slate-400">{text}</p>
}

export function BulletList({ items, tone = 'text-slate-200' }: { items: string[]; tone?: string }) {
  if (!items.length) return null
  return (
    <ul className={`space-y-1.5 text-sm ${tone}`}>
      {items.map((item, i) => (
        <li key={`${i}-${item.slice(0, 24)}`} className="flex gap-2">
          <span className="mt-2 h-1 w-1 flex-none rounded-full bg-slate-500" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  )
}

export function Meter({ label, value, tone = 'cyan' }: { label: string; value: number; tone?: 'cyan' | 'green' | 'amber' }) {
  const pct = Math.max(0, Math.min(100, Math.round(value * 100)))
  const bar = tone === 'green' ? 'bg-emerald-400' : tone === 'amber' ? 'bg-amber-400' : 'bg-cyan-400'
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-slate-400">
        <span>{label}</span>
        <span>{pct}%</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
        <div className={`h-full rounded-full ${bar}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}
