import { useEffect, useRef, useState } from 'react'
import { ExternalLink } from 'lucide-react'
import { resolveCitations, TIER_LABEL } from '../../features/workflow/citations'
import { useEvidence } from './EvidenceContext'
import { Pill } from './ui'

const tierTone = (tier: number) => (tier <= 1 ? 'green' : tier === 2 ? 'cyan' : tier === 3 ? 'amber' : 'neutral')

/** Numbered evidence chips. Click a chip to see the exact claim and the sources behind it. */
export default function Cite({ ids }: { ids?: string[] | null }) {
  const { facts, sources } = useEvidence()
  const [open, setOpen] = useState<number | null>(null)
  const ref = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    if (open === null) return
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(null)
    }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [open])

  const items = resolveCitations(ids, facts, sources)
  if (!items.length) return null

  return (
    <span ref={ref} className="relative ml-1 inline-flex flex-wrap items-center gap-1 align-middle">
      {items.map((c, i) => (
        <span key={c.factId} className="relative">
          <button
            type="button"
            onClick={() => setOpen(open === i ? null : i)}
            title={c.fact?.claim ?? 'Evidence not found'}
            className={`h-5 min-w-5 rounded-md border px-1 text-[10px] font-semibold leading-none transition ${
              c.fact
                ? 'border-cyan-400/30 bg-cyan-500/10 text-cyan-200 hover:bg-cyan-500/20'
                : 'border-rose-400/30 bg-rose-500/10 text-rose-300'
            }`}
          >
            {i + 1}
          </button>
          {open === i && (
            <span className="absolute left-0 top-6 z-30 block w-72 rounded-xl border border-white/10 bg-slate-900 p-3 text-left text-xs text-slate-200 shadow-2xl">
              {c.fact ? (
                <>
                  <span className="block text-[13px] leading-snug">{c.fact.claim}</span>
                  {(c.fact.value || c.fact.period) && (
                    <span className="mt-1 block text-slate-400">
                      {[c.fact.value, c.fact.period].filter(Boolean).join(' · ')}
                    </span>
                  )}
                  <span className="mt-2 block space-y-1.5">
                    {c.sources.map((s) => (
                      <span key={s.id} className="flex items-start justify-between gap-2">
                        <span className="min-w-0">
                          <span className="block truncate text-slate-300">{s.title}</span>
                          <Pill tone={tierTone(s.tier)}>{TIER_LABEL[s.tier] ?? 'Other'}</Pill>
                        </span>
                        {s.url && (
                          <a href={s.url} target="_blank" rel="noreferrer" className="mt-0.5 flex-none text-cyan-300 hover:text-cyan-200">
                            <ExternalLink size={13} />
                          </a>
                        )}
                      </span>
                    ))}
                  </span>
                </>
              ) : (
                <span>This citation ({c.factId}) is not in the evidence store.</span>
              )}
            </span>
          )}
        </span>
      ))}
    </span>
  )
}
