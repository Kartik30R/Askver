import { useEffect, useMemo, useState } from 'react'
import { useSelector } from 'react-redux'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  BarChart3,
  Briefcase,
  CheckCircle2,
  FileText,
  MessageSquareText,
  Plus,
  Sparkles,
  Upload,
  Video,
  X,
} from 'lucide-react'

import type { RootState } from '../../app/store'
import { fetchWithAuth } from '../../utils/fetchWithAuth'

type MeetingRecord = {
  id: string
  title: string
  meeting_date: string
  attendees?: string | null
  meeting_type?: string | null
  summary?: string | null
  transcript_text: string
  objectives?: string | null
  notes?: string | null
  created_at: string
  updated_at: string
}

type MeetingFormState = {
  title: string
  meeting_date: string
  meeting_type: string
  attendees: string
  objectives: string
  notes: string
  transcript_text: string
  summary: string
}

const emptyForm: MeetingFormState = {
  title: '',
  meeting_date: '',
  meeting_type: 'Customer Call',
  attendees: '',
  objectives: '',
  notes: '',
  transcript_text: '',
  summary: '',
}

export default function DealMeetingAnalytics() {
  const navigate = useNavigate()
  const { dealId } = useParams()
  const accessToken = useSelector((state: RootState) => state.auth.accessToken)
  const [showComposer, setShowComposer] = useState(false)
  const [meetings, setMeetings] = useState<MeetingRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState<MeetingFormState>(emptyForm)
  const [selectedMeetingId, setSelectedMeetingId] = useState<string | null>(null)

  const loadMeetings = async () => {
    if (!dealId) return

    setLoading(true)
    setError(null)

    try {
      const records = await fetchWithAuth<MeetingRecord[]>(`/meetings/deal/${dealId}`, {
        method: 'GET',
        accessToken: accessToken ?? undefined,
      })
      setMeetings(records)
      setSelectedMeetingId((existing) => existing ?? records[0]?.id ?? null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load meeting analytics.')
      setMeetings([])
      setSelectedMeetingId(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadMeetings()
  }, [dealId, accessToken])

  const selectedMeeting = meetings.find((meeting) => meeting.id === selectedMeetingId) ?? meetings[0] ?? null

  const overallWinProbability = useMemo(() => {
    if (!meetings.length) return 0
    const derived = meetings.map((meeting) => {
      const text = `${meeting.transcript_text} ${meeting.summary ?? ''}`.toLowerCase()
      const riskSignals = ['risk', 'concern', 'challenge', 'slow', 'security', 'budget', 'procurement', 'competition']
      const positiveSignals = ['aligned', 'strong', 'value', 'sponsor', 'buy-in', 'phased', 'clear', 'success']
      const positive = positiveSignals.filter((signal) => text.includes(signal)).length
      const negative = riskSignals.filter((signal) => text.includes(signal)).length
      return Math.max(40, Math.min(90, 50 + (positive * 6) - (negative * 4)))
    })

    return Math.round(derived.reduce((sum, value) => sum + value, 0) / derived.length)
  }, [meetings])

  const handleCreateMeeting = async () => {
    if (!dealId) return
    if (!form.title.trim() || !form.meeting_date || !form.transcript_text.trim()) {
      setError('Meeting title, date, and transcript are required.')
      return
    }

    setCreating(true)
    setError(null)

    try {
      const created = await fetchWithAuth<MeetingRecord>('/meetings', {
        method: 'POST',
        accessToken: accessToken ?? undefined,
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

      setForm(emptyForm)
      setShowComposer(false)
      setSelectedMeetingId(created.id)
      await loadMeetings()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to create meeting analysis.')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="space-y-6">
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

        <button
          type="button"
          onClick={() => setShowComposer(true)}
          className="btn-nagarro inline-flex items-center gap-2"
        >
          <Plus className="h-4 w-4 text-black" />
          Add meeting details
        </button>
      </div>

      {error && (
        <div className="rounded-2xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</div>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <div className="cosmic-card p-4">
          <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Meetings tracked</div>
          <div className="mt-3 text-3xl font-bold text-white">{meetings.length}</div>
        </div>
        <div className="cosmic-card p-4">
          <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Deal win signal</div>
          <div className="mt-3 text-3xl font-bold text-emerald-300">{overallWinProbability}%</div>
        </div>
        <div className="cosmic-card p-4">
          <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Meeting actions</div>
          <div className="mt-3 text-3xl font-bold text-cyan-300">{meetings.length ? meetings.reduce((sum, meeting) => sum + (meeting.objectives ? 1 : 0), 0) : 0}</div>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <aside className="cosmic-card p-4">
          <div className="mb-4 flex items-center justify-between">
            <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Deal timeline</div>
            <span className="text-xs text-cosmic-muted">Linked to deal</span>
          </div>

          {loading ? (
            <div className="text-sm text-cosmic-muted">Loading meeting timeline…</div>
          ) : (
            <div className="space-y-3">
              {meetings.map((meeting) => (
                <button
                  key={meeting.id}
                  type="button"
                  onClick={() => setSelectedMeetingId(meeting.id)}
                  className={`w-full rounded-2xl border p-4 text-left transition-all ${
                    selectedMeeting?.id === meeting.id
                      ? 'border-nagarro-green/60 bg-nagarro-green/5'
                      : 'border-cosmic-border bg-cosmic-bg/30 hover:border-cosmic-border/80'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-[10px] uppercase tracking-[0.12em] text-cosmic-muted">{meeting.meeting_type ?? 'Meeting'}</div>
                    <span className="rounded-full border border-cosmic-border bg-cosmic-bg/40 px-2 py-0.5 text-[10px] text-cosmic-muted">
                      {meeting.meeting_date}
                    </span>
                  </div>
                  <div className="mt-2 text-base font-semibold text-white">{meeting.title}</div>
                  <div className="mt-2 text-xs text-cosmic-muted">{meeting.attendees || 'No attendees listed'}</div>
                </button>
              ))}
            </div>
          )}
        </aside>

        <div className="space-y-6">
          {selectedMeeting ? (
            <>
              <div className="cosmic-card p-6">
                <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                  <div>
                    <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">{selectedMeeting.meeting_type ?? 'Meeting'}</div>
                    <h2 className="mt-3 text-2xl font-bold text-white">{selectedMeeting.title}</h2>
                    <div className="mt-2 text-sm text-cosmic-muted">{selectedMeeting.meeting_date}</div>
                  </div>
                  <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 text-xs text-emerald-300">
                    <BarChart3 className="h-3.5 w-3.5" />
                    Win signal {overallWinProbability}%
                  </div>
                </div>

                <div className="mt-6 rounded-2xl border border-cosmic-border bg-cosmic-bg/40 p-4 text-sm leading-7 text-cosmic-muted">
                  {selectedMeeting.summary || 'No summary recorded for this meeting yet.'}
                </div>
              </div>

              <div className="grid gap-6 lg:grid-cols-2">
                <div className="cosmic-card p-5">
                  <div className="mb-4 flex items-center gap-2 text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">
                    <MessageSquareText className="h-3.5 w-3.5 text-cyan-300" />
                    Transcript-driven signal
                  </div>
                  <p className="text-sm leading-7 text-cosmic-muted">{selectedMeeting.transcript_text}</p>
                </div>

                <div className="cosmic-card p-5">
                  <div className="mb-4 flex items-center gap-2 text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">
                    <Briefcase className="h-3.5 w-3.5 text-violet-300" />
                    Objectives
                  </div>
                  <div className="rounded-xl border border-cosmic-border bg-cosmic-bg/30 p-3 text-sm text-cosmic-muted">
                    {selectedMeeting.objectives || 'No meeting objectives captured.'}
                  </div>
                </div>
              </div>

              <div className="grid gap-6 lg:grid-cols-2">
                <div className="cosmic-card p-5">
                  <div className="mb-4 flex items-center gap-2 text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">
                    <Sparkles className="h-3.5 w-3.5 text-amber-300" />
                    Notes
                  </div>
                  <div className="rounded-xl border border-cosmic-border bg-cosmic-bg/30 p-3 text-sm text-cosmic-muted">
                    {selectedMeeting.notes || 'No supporting notes captured for this meeting.'}
                  </div>
                </div>

                <div className="cosmic-card p-5">
                  <div className="mb-4 flex items-center gap-2 text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">
                    <Video className="h-3.5 w-3.5 text-cyan-300" />
                    Attendees
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {selectedMeeting.attendees?.split(',').map((person) => person.trim()).filter(Boolean).map((person) => (
                      <span key={person} className="rounded-full border border-cosmic-border bg-cosmic-bg/40 px-3 py-1.5 text-xs text-cosmic-muted">
                        {person}
                      </span>
                    )) || <span className="text-sm text-cosmic-muted">No attendees recorded</span>}
                  </div>
                </div>
              </div>

              <div className="grid gap-6 lg:grid-cols-2">
                <div className="cosmic-card p-5">
                  <div className="mb-4 flex items-center gap-2 text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">
                    <FileText className="h-3.5 w-3.5 text-violet-300" />
                    Supporting artifacts
                  </div>
                  <div className="rounded-xl border border-cosmic-border bg-cosmic-bg/30 p-3 text-sm text-cosmic-muted">
                    No supporting documents are attached yet. Use the optional document upload when the meeting includes additional context.
                  </div>
                </div>

                <div className="cosmic-card p-5">
                  <div className="mb-4 flex items-center gap-2 text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-300" />
                    Meeting metadata
                  </div>
                  <ul className="space-y-2 text-sm text-cosmic-muted">
                    <li>Created: {selectedMeeting.created_at ? new Date(selectedMeeting.created_at).toLocaleString() : 'N/A'}</li>
                    <li>Updated: {selectedMeeting.updated_at ? new Date(selectedMeeting.updated_at).toLocaleString() : 'N/A'}</li>
                  </ul>
                </div>
              </div>
            </>
          ) : (
            <div className="cosmic-card p-12 text-center">
              <Sparkles className="mx-auto mb-4 h-12 w-12 text-cosmic-muted opacity-50" />
              <h3 className="text-lg font-semibold text-white">No meeting analysis yet</h3>
              <p className="mt-2 text-sm text-cosmic-muted">Add the first meeting details, transcript, and supporting documents to start the analysis.</p>
            </div>
          )}
        </div>
      </div>

      {showComposer && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4">
          <div className="w-full max-w-3xl rounded-3xl border border-cosmic-border bg-cosmic-surface p-6 shadow-2xl">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Add meeting details</div>
                <h3 className="mt-2 text-xl font-bold text-white">Create deal-linked meeting analysis</h3>
            <p className="mt-1 text-xs text-cosmic-muted">Transcript is required for analysis; supporting documents stay optional.</p>
              </div>
              <button type="button" onClick={() => setShowComposer(false)} className="rounded-lg border border-cosmic-border bg-cosmic-bg/40 p-2 text-cosmic-muted hover:text-white">
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-5">
              <div className="grid gap-4 md:grid-cols-2">
                <label className="block text-sm text-cosmic-muted">
                  <span className="mb-2 block text-[10px] uppercase tracking-[0.18em]">Meeting title</span>
                  <input
                    value={form.title}
                    onChange={(event) => setForm((prev) => ({ ...prev, title: event.target.value }))}
                    className="w-full rounded-xl border border-cosmic-border bg-cosmic-bg px-3 py-2 text-white placeholder:text-cosmic-muted"
                    placeholder="Discovery workshop - Finance team"
                  />
                </label>

                <label className="block text-sm text-cosmic-muted">
                  <span className="mb-2 block text-[10px] uppercase tracking-[0.18em]">Meeting type</span>
                  <select
                    value={form.meeting_type}
                    onChange={(event) => setForm((prev) => ({ ...prev, meeting_type: event.target.value }))}
                    className="w-full rounded-xl border border-cosmic-border bg-cosmic-bg px-3 py-2 text-white"
                  >
                    <option>Customer Call</option>
                    <option>Board Review</option>
                    <option>Internal Alignment</option>
                    <option>QBR</option>
                  </select>
                </label>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <label className="block text-sm text-cosmic-muted">
                  <span className="mb-2 block text-[10px] uppercase tracking-[0.18em]">Date</span>
                  <input
                    type="date"
                    value={form.meeting_date}
                    onChange={(event) => setForm((prev) => ({ ...prev, meeting_date: event.target.value }))}
                    className="w-full rounded-xl border border-cosmic-border bg-cosmic-bg px-3 py-2 text-white"
                  />
                </label>

                <label className="block text-sm text-cosmic-muted">
                  <span className="mb-2 block text-[10px] uppercase tracking-[0.18em]">Attendees</span>
                  <input
                    value={form.attendees}
                    onChange={(event) => setForm((prev) => ({ ...prev, attendees: event.target.value }))}
                    className="w-full rounded-xl border border-cosmic-border bg-cosmic-bg px-3 py-2 text-white"
                    placeholder="Names separated by comma"
                  />
                </label>
              </div>

              <div className="rounded-2xl border border-cyan-500/30 bg-cyan-500/5 p-4">
                <div className="mb-3 flex items-center justify-between gap-2 text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">
                  <span>Meeting transcript</span>
                  <span className="rounded-full border border-cyan-500/40 bg-cyan-500/10 px-2 py-0.5 text-[9px] font-medium text-cyan-300">Required</span>
                </div>

                <div className="space-y-4">
                  <label className="block text-sm text-cosmic-muted">
                    <span className="mb-2 block text-[10px] uppercase tracking-[0.18em]">Paste transcript text</span>
                    <textarea
                      rows={6}
                      required
                      value={form.transcript_text}
                      onChange={(event) => setForm((prev) => ({ ...prev, transcript_text: event.target.value }))}
                      className="w-full rounded-xl border border-cosmic-border bg-cosmic-bg px-3 py-2 text-white placeholder:text-cosmic-muted"
                      placeholder="Paste the meeting transcript, call recording notes, or detailed discussion summary. This is the primary input for analysis."
                    />
                  </label>

                  <div className="rounded-xl border border-dashed border-cyan-500/40 bg-cosmic-bg/20 p-4">
                    <div className="mb-2 flex items-center gap-2 text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">
                      <Upload className="h-3.5 w-3.5 text-nagarro-green" />
                      Or upload transcript file
                    </div>
                    <input
                      type="file"
                      accept=".txt,.md,.pdf,.doc,.docx,.rtf"
                      className="block w-full text-sm text-cosmic-muted file:mr-4 file:rounded-lg file:border-0 file:bg-nagarro-green file:px-4 file:py-2 file:text-sm file:font-semibold file:text-black hover:file:bg-nagarro-hover"
                    />
                    <p className="mt-2 text-xs text-cosmic-muted">You can upload a transcript document instead of pasting text directly.</p>
                  </div>
                </div>

                <p className="mt-3 text-xs text-cosmic-muted">Analysis is based on the transcript. Supporting files help enrich the context but are not the primary input.</p>
              </div>

              <div className="rounded-2xl border border-dashed border-cosmic-border bg-cosmic-bg/30 p-5">
                <div className="mb-2 flex items-center gap-2 text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">
                  <Upload className="h-3.5 w-3.5 text-nagarro-green" />
                  Supporting documents (optional)
                </div>
                <input type="file" multiple accept=".pdf,.doc,.docx,.ppt,.pptx,.txt,.md,.png,.jpg,.jpeg" className="block w-full text-sm text-cosmic-muted file:mr-4 file:rounded-lg file:border-0 file:bg-nagarro-green file:px-4 file:py-2 file:text-sm file:font-semibold file:text-black hover:file:bg-nagarro-hover" />
                <p className="mt-3 text-xs text-cosmic-muted">Optional: presentation decks, customer notes, screenshots, and other reference files that help explain the meeting context.</p>
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button type="button" onClick={() => setShowComposer(false)} className="rounded-xl border border-cosmic-border bg-cosmic-bg/40 px-4 py-2 text-sm text-cosmic-muted hover:text-white">
                Cancel
              </button>
              <button type="button" disabled={creating} onClick={handleCreateMeeting} className="btn-nagarro inline-flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-70">
                <Sparkles className="h-4 w-4 text-black" />
                {creating ? 'Saving…' : 'Start analysis'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
