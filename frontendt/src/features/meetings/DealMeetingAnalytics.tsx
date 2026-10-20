
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useSelector } from 'react-redux'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, BarChart3, MessagesSquare, Plus } from 'lucide-react'

import type { RootState } from '../../app/store'
import { fetchWithAuth } from '../../utils/fetchWithAuth'
import type { DealAnalyticsResult, MeetingAnalysisResult, MeetingRecord } from './analysisTypes'
import { AnalyticsContext, Notice } from './analyticsUi'
import type { AnalyticsContextValue } from './analyticsUi'
import { DealAnalyticsPanel, DealPulse } from './DealAnalyticsPanel'
import { MeetingAnalysisPanel } from './MeetingAnalysisPanel'
import type { LoadState } from './MeetingAnalysisPanel'
import { MeetingComposerModal } from './MeetingComposerModal'
import type { MeetingSubmission } from './MeetingComposerModal'
import { MeetingTimeline } from './MeetingTimeline'

type View = 'meeting' | 'deal'

// ───────────────────────── API ─────────────────────────
// Read  : GET  /deals/{dealId}/analytics/meetings/{meetingId}   -> MeetingAnalysisResult
//         GET  /deals/{dealId}/analytics/deal                    -> DealAnalyticsResult
// Run   : POST .../meetings/{meetingId}/run and POST .../deal/run (persisted-analytics backend).
//         If the run route does not exist yet, we fall back to the GET route (which runs the pipeline).
const errorText = (err: unknown, fallback: string): string => (err instanceof Error ? err.message : fallback)
const isNotFound = (err: unknown): boolean => err instanceof Error && /(^|\D)404(\D|$)|not found|not analy[sz]ed/i.test(err.message)
const isRouteMissing = (err: unknown): boolean => err instanceof Error && /(^|\D)(404|405)(\D|$)|method not allowed|not found/i.test(err.message)

export default function DealMeetingAnalytics() {
  const navigate = useNavigate()
  const { dealId } = useParams()
  const accessToken = useSelector((state: RootState) => state.auth.accessToken)
  const token = accessToken ?? undefined

  const [meetings, setMeetings] = useState<MeetingRecord[]>([])
  const [meetingsLoading, setMeetingsLoading] = useState(true)
  const [pageError, setPageError] = useState<string | null>(null)

  const [view, setView] = useState<View>('meeting')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const [analyses, setAnalyses] = useState<Record<string, MeetingAnalysisResult>>({})
  const [analysisState, setAnalysisState] = useState<Record<string, LoadState>>({})
  const [analysisError, setAnalysisError] = useState<Record<string, string | null>>({})

  const [dealAnalysis, setDealAnalysis] = useState<DealAnalyticsResult | null>(null)
  const [dealState, setDealState] = useState<LoadState>('idle')
  const [dealError, setDealError] = useState<string | null>(null)

  const [composerOpen, setComposerOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [composerError, setComposerError] = useState<string | null>(null)

  const requested = useRef<Set<string>>(new Set())
  const detailRef = useRef<HTMLDivElement>(null)

  // Timeline is oldest -> newest (API returns newest first).
  const orderedMeetings = useMemo(
    () => [...meetings].sort((a, b) => a.meeting_date.localeCompare(b.meeting_date) || a.created_at.localeCompare(b.created_at)),
    [meetings],
  )
  const selectedMeeting = orderedMeetings.find((meeting) => meeting.id === selectedId) ?? null

  const contextValue = useMemo<AnalyticsContextValue>(
    () => ({
      meetingTitle: (id) => meetings.find((meeting) => meeting.id === id)?.title ?? null,
      openMeeting: (id) => {
        if (!meetings.some((meeting) => meeting.id === id)) return
        setSelectedId(id)
        setView('meeting')
        detailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      },
    }),
    [meetings],
  )

  // ── Loading ──
  const loadMeetings = useCallback(async (): Promise<MeetingRecord[]> => {
    if (!dealId) return []
    setMeetingsLoading(true)
    setPageError(null)
    try {
      const records = await fetchWithAuth<MeetingRecord[]>(`/meetings/deal/${dealId}`, { method: 'GET', accessToken: token })
      setMeetings(records)
      return records
    } catch (err) {
      setPageError(errorText(err, 'Unable to load meetings.'))
      setMeetings([])
      return []
    } finally {
      setMeetingsLoading(false)
    }
  }, [dealId, token])

  const fetchMeetingAnalysis = useCallback(
    async (meetingId: string, run: boolean) => {
      if (!dealId) return
      const base = `/deals/${dealId}/analytics/meetings/${meetingId}`
      setAnalysisState((prev) => ({ ...prev, [meetingId]: 'loading' }))
      setAnalysisError((prev) => ({ ...prev, [meetingId]: null }))
      try {
        let result: MeetingAnalysisResult
        if (run) {
          try {
            result = await fetchWithAuth<MeetingAnalysisResult>(`${base}/run`, { method: 'POST', accessToken: token })
          } catch (err) {
            if (!isRouteMissing(err)) throw err
            result = await fetchWithAuth<MeetingAnalysisResult>(base, { method: 'GET', accessToken: token })
          }
        } else {
          result = await fetchWithAuth<MeetingAnalysisResult>(base, { method: 'GET', accessToken: token })
        }
        setAnalyses((prev) => ({ ...prev, [meetingId]: result }))
        setAnalysisState((prev) => ({ ...prev, [meetingId]: 'idle' }))
      } catch (err) {
        if (!run && isNotFound(err)) {
          setAnalysisState((prev) => ({ ...prev, [meetingId]: 'missing' }))
        } else {
          setAnalysisState((prev) => ({ ...prev, [meetingId]: 'error' }))
          setAnalysisError((prev) => ({ ...prev, [meetingId]: errorText(err, 'Unable to load the meeting analysis.') }))
        }
      }
    },
    [dealId, token],
  )

  const fetchDealAnalysis = useCallback(
    async (run: boolean) => {
      if (!dealId) return
      const base = `/deals/${dealId}/analytics/deal`
      setDealState('loading')
      setDealError(null)
      try {
        let result: DealAnalyticsResult
        if (run) {
          try {
            result = await fetchWithAuth<DealAnalyticsResult>(`${base}/run`, { method: 'POST', accessToken: token })
          } catch (err) {
            if (!isRouteMissing(err)) throw err
            result = await fetchWithAuth<DealAnalyticsResult>(base, { method: 'GET', accessToken: token })
          }
        } else {
          result = await fetchWithAuth<DealAnalyticsResult>(base, { method: 'GET', accessToken: token })
        }
        setDealAnalysis(result)
        setDealState('idle')
      } catch (err) {
        if (!run && isNotFound(err)) {
          setDealState('missing')
          void fetchDealAnalysis(true)
        } else {
          setDealState('error')
          setDealError(errorText(err, 'Unable to load deal analytics.'))
        }
      }
    },
    [dealId, token],
  )

  // Initial load
  useEffect(() => {
    requested.current = new Set()
    setAnalyses({})
    setAnalysisState({})
    setAnalysisError({})
    setDealAnalysis(null)
    setDealState('idle')
    setSelectedId(null)
    void loadMeetings().then((records) => {
      const newest = [...records].sort((a, b) => b.meeting_date.localeCompare(a.meeting_date))[0]
      if (newest) setSelectedId(newest.id)
    })
    void fetchDealAnalysis(false)
  }, [dealId, token, loadMeetings, fetchDealAnalysis])

  // Load analysis the first time a meeting is selected (cached afterwards).
  useEffect(() => {
    if (!selectedId || requested.current.has(selectedId)) return
    requested.current.add(selectedId)
    void fetchMeetingAnalysis(selectedId, false)
  }, [selectedId, fetchMeetingAnalysis])

  // ── Create ──
  const handleCreate = async ({ form, supportingFiles }: MeetingSubmission): Promise<boolean> => {
    if (!dealId) return false
    setSaving(true)
    setComposerError(null)
    try {
      const created = await fetchWithAuth<MeetingRecord>('/meetings', {
        method: 'POST',
        accessToken: token,
        body: JSON.stringify({
          deal_id: dealId,
          title: form.title.trim(),
          meeting_date: form.meeting_date,
          meeting_type: form.meeting_type || 'Customer Call',
          attendees: form.attendees.trim() || null,
          objectives: form.objectives.trim() || null,
          notes: form.notes.trim() || null,
          transcript_text: form.transcript_text.trim(),
          summary: form.summary.trim() || null,
        }),
      })

      for (const file of supportingFiles) {
        const formData = new FormData()
        formData.append('file', file)
        formData.append('document_type', 'supporting_document')
        await fetchWithAuth(`/meetings/${created.id}/documents`, { method: 'POST', accessToken: token, body: formData })
      }

      await loadMeetings()
      requested.current.add(created.id)
      setSelectedId(created.id)
      setView('meeting')
      setComposerOpen(false)
      void fetchMeetingAnalysis(created.id, true).then(() => fetchDealAnalysis(true))
      return true
    } catch (err) {
      setComposerError(errorText(err, 'Unable to create the meeting.'))
      return false
    } finally {
      setSaving(false)
    }
  }

  const selectMeeting = (id: string) => {
    setSelectedId(id)
    setView('meeting')
  }

  const trendPoints = dealAnalysis?.momentum?.trend_points ?? []

  return (
    <AnalyticsContext.Provider value={contextValue}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => navigate(`/deals/${dealId ?? ''}`)}
              className="inline-flex items-center gap-2 rounded-lg border border-cosmic-border bg-cosmic-bg/40 px-3 py-2 text-xs text-cosmic-muted hover:text-white"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Back to deal
            </button>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white">Meeting Analysis</h1>
              <p className="mt-1 text-sm text-cosmic-muted">What happened in meetings, how the team performed, and what the deal signals are telling us.</p>
            </div>
          </div>
          <button type="button" onClick={() => setComposerOpen(true)} className="btn-nagarro inline-flex items-center gap-2">
            <Plus className="h-4 w-4 text-black" />
            Add meeting details
          </button>
        </div>

        {pageError && <Notice tone="red">{pageError}</Notice>}

        {/* Timeline */}
        <MeetingTimeline
          meetings={orderedMeetings}
          selectedId={view === 'meeting' ? selectedId : null}
          onSelect={selectMeeting}
          onAdd={() => setComposerOpen(true)}
          trendPoints={trendPoints}
          loading={meetingsLoading}
        />

        {/* Deal pulse */}
        <DealPulse analysis={dealAnalysis} meetingCount={meetings.length} state={dealState} onOpen={() => setView('deal')} />

        {/* View switch */}
        <div ref={detailRef} className="flex flex-wrap items-center gap-2 scroll-mt-4">
          <button type="button" onClick={() => setView('meeting')} className={`company-intel-tab ${view === 'meeting' ? 'active' : ''}`}>
            <MessagesSquare className="mr-2 h-3.5 w-3.5" />
            {selectedMeeting ? 'Selected meeting' : 'Meeting analysis'}
          </button>
          <button type="button" onClick={() => setView('deal')} className={`company-intel-tab ${view === 'deal' ? 'active' : ''}`}>
            <BarChart3 className="mr-2 h-3.5 w-3.5" />
            Overall deal analytics
          </button>
        </div>

        {/* Detail */}
        {view === 'meeting' ? (
          selectedMeeting ? (
            <MeetingAnalysisPanel
              key={selectedMeeting.id}
              meeting={selectedMeeting}
              analysis={analyses[selectedMeeting.id] ?? null}
              state={analysisState[selectedMeeting.id] ?? 'loading'}
              error={analysisError[selectedMeeting.id] ?? null}
              onRun={() => void fetchMeetingAnalysis(selectedMeeting.id, true).then(() => fetchDealAnalysis(true))}
            />
          ) : (
            <div className="cosmic-card p-12 text-center">
              <MessagesSquare className="mx-auto mb-4 h-12 w-12 text-cosmic-muted opacity-50" />
              <h3 className="text-lg font-semibold text-white">{meetingsLoading ? 'Loading meetings…' : 'No meetings yet'}</h3>
              <p className="mx-auto mt-2 max-w-md text-sm text-cosmic-muted">
                {meetingsLoading ? 'Fetching the meetings linked to this deal.' : 'Add the first meeting details, transcript, and supporting documents to start the analysis.'}
              </p>
            </div>
          )
        ) : (
          <DealAnalyticsPanel analysis={dealAnalysis} state={dealState} error={dealError} onRun={() => void fetchDealAnalysis(true)} meetingCount={meetings.length} />
        )}

        <MeetingComposerModal
          open={composerOpen}
          saving={saving}
          error={composerError}
          onClose={() => {
            setComposerOpen(false)
            setComposerError(null)
          }}
          onSubmit={handleCreate}
        />
      </div>
    </AnalyticsContext.Provider>
  )
}