import { useEffect, useMemo, useRef } from 'react'
import { ChevronLeft, ChevronRight, Plus } from 'lucide-react'

import type { MeetingRecord, MeetingTrendPoint } from './analysisTypes'
import { formatDate, Pill, ratioTone, statusTone, humanize, TONE_FILL } from './analyticsUi'

const clamp2: React.CSSProperties = {
  display: '-webkit-box',
  WebkitLineClamp: 2,
  WebkitBoxOrient: 'vertical',
  overflow: 'hidden',
}

/**
 * Horizontally slidable meeting timeline (oldest -> newest).
 * Scroll with the arrows, drag/trackpad, or the keyboard (cards are focusable buttons).
 */
export function MeetingTimeline({
  meetings,
  selectedId,
  onSelect,
  onAdd,
  trendPoints,
  loading,
}: {
  meetings: MeetingRecord[]
  selectedId: string | null
  onSelect: (meetingId: string) => void
  onAdd: () => void
  trendPoints: MeetingTrendPoint[]
  loading: boolean
}) {
  const railRef = useRef<HTMLDivElement>(null)
  const cardRefs = useRef<Record<string, HTMLButtonElement | null>>({})

  const trendById = useMemo(() => {
    const map: Record<string, MeetingTrendPoint> = {}
    trendPoints.forEach((point) => {
      map[point.meeting_id] = point
    })
    return map
  }, [trendPoints])

  useEffect(() => {
    if (!selectedId) return
    cardRefs.current[selectedId]?.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' })
  }, [selectedId])

  const scrollBy = (direction: 1 | -1) => {
    const rail = railRef.current
    if (!rail) return
    rail.scrollBy({ left: direction * Math.max(280, rail.clientWidth * 0.7), behavior: 'smooth' })
  }

  return (
    <div className="cosmic-card p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Meeting timeline</div>
          <span className="rounded-full border border-cosmic-border bg-cosmic-bg/60 px-1.5 py-0.5 text-[10px] font-semibold text-nagarro-green">{meetings.length}</span>
        </div>
        <div className="flex items-center gap-2">
          <button type="button" onClick={() => scrollBy(-1)} aria-label="Scroll timeline left" className="rounded-lg border border-cosmic-border bg-cosmic-bg/40 p-2 text-cosmic-muted transition-colors hover:border-nagarro-green/40 hover:text-white">
            <ChevronLeft className="h-4 w-4" />
          </button>
          <button type="button" onClick={() => scrollBy(1)} aria-label="Scroll timeline right" className="rounded-lg border border-cosmic-border bg-cosmic-bg/40 p-2 text-cosmic-muted transition-colors hover:border-nagarro-green/40 hover:text-white">
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div ref={railRef} className="pipeline-flow-scroll relative flex snap-x snap-mandatory gap-4 overflow-x-auto scroll-smooth pb-2 pt-1" role="listbox" aria-label="Meetings">
        {loading && !meetings.length && (
          <>
            {[0, 1, 2].map((index) => (
              <div key={index} className="h-[132px] w-[280px] flex-none animate-pulse rounded-2xl border border-cosmic-border bg-cosmic-bg/30" />
            ))}
          </>
        )}

        {meetings.map((meeting, index) => {
          const selected = meeting.id === selectedId
          const point = trendById[meeting.id]
          return (
            <div key={meeting.id} className="relative w-[280px] flex-none snap-center">
              {/* connector line through the nodes */}
              <div className="absolute left-0 right-[-16px] top-[7px] h-px bg-cosmic-border" aria-hidden />
              <div className={`relative z-10 mb-3 flex h-[15px] w-[15px] items-center justify-center rounded-full border-2 transition-all ${selected ? 'border-nagarro-green bg-nagarro-green shadow-[0_0_0_4px_rgba(110,231,183,0.18)]' : 'border-cosmic-border bg-cosmic-bg'}`} />
              <button
                type="button"
                role="option"
                aria-selected={selected}
                ref={(node) => {
                  cardRefs.current[meeting.id] = node
                }}
                onClick={() => onSelect(meeting.id)}
                className={`w-full rounded-2xl border p-4 text-left transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-nagarro-green focus:ring-offset-2 focus:ring-offset-cosmic-bg ${
                  selected
                    ? 'border-nagarro-green/60 bg-nagarro-green/5 shadow-[0_0_0_1px_rgba(110,231,183,0.2),0_0_24px_rgba(110,231,183,0.10)]'
                    : 'border-cosmic-border bg-cosmic-bg/30 hover:border-nagarro-green/30 hover:bg-cosmic-bg/50'
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[10px] uppercase tracking-[0.14em] text-cosmic-muted">
                    #{index + 1} · {meeting.meeting_type ?? 'Meeting'}
                  </span>
                  <span className="rounded-full border border-cosmic-border bg-cosmic-bg/40 px-2 py-0.5 text-[10px] text-cosmic-muted">{formatDate(meeting.meeting_date)}</span>
                </div>
                <div className="mt-2 text-sm font-semibold leading-5 text-white" style={clamp2}>
                  {meeting.title}
                </div>
                <div className="mt-2 truncate text-xs text-cosmic-muted">{meeting.attendees || 'No attendees listed'}</div>

                <div className="mt-3 flex min-h-[22px] flex-wrap items-center gap-1.5">
                  {point ? (
                    <>
                      {point.scorecard_overall !== null && (
                        <span className="inline-flex items-center gap-1.5 rounded-full border border-cosmic-border bg-cosmic-bg/60 px-2 py-0.5 text-[10px] font-semibold text-white">
                          <span className={`h-1.5 w-1.5 rounded-full ${TONE_FILL[ratioTone(point.scorecard_overall / 10)]}`} />
                          {point.scorecard_overall}/10
                        </span>
                      )}
                      {point.sentiment && <Pill tone={statusTone(point.sentiment)}>{humanize(point.sentiment)}</Pill>}
                      {point.unresolved_objections !== null && point.unresolved_objections > 0 && <Pill tone="orange">{point.unresolved_objections} open</Pill>}
                    </>
                  ) : (
                    <span className="text-[10px] text-cosmic-muted">Select to view analysis</span>
                  )}
                </div>
              </button>
            </div>
          )
        })}

        <div className="relative w-[200px] flex-none snap-center">
          <div className="absolute left-0 right-[60%] top-[7px] h-px bg-cosmic-border" aria-hidden />
          <div className="relative z-10 mb-3 h-[15px] w-[15px] rounded-full border-2 border-dashed border-cosmic-border bg-cosmic-bg" />
          <button
            type="button"
            onClick={onAdd}
            className="flex h-[132px] w-full flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-cosmic-border bg-cosmic-bg/20 text-cosmic-muted transition-all hover:border-nagarro-green/40 hover:text-nagarro-green"
          >
            <Plus className="h-5 w-5" />
            <span className="text-xs font-semibold uppercase tracking-[0.14em]">Add meeting</span>
          </button>
        </div>
      </div>
    </div>
  )
}