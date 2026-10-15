import { useState } from 'react'
import { Sparkles, Upload, X } from 'lucide-react'

import type { MeetingType } from './analysisTypes'
import { Notice } from './analyticsUi'

export type MeetingFormState = {
  title: string
  meeting_date: string
  meeting_type: MeetingType
  attendees: string
  objectives: string
  notes: string
  transcript_text: string
  summary: string
}

export type MeetingSubmission = {
  form: MeetingFormState
  transcriptFile: File | null
  supportingFiles: File[]
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

const readTextFile = (file: File): Promise<string> =>
  new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result ?? ''))
    reader.onerror = () => reject(new Error(`Unable to read ${file.name}`))
    reader.readAsText(file)
  })

const inputClass =
  'w-full rounded-xl border border-cosmic-border bg-cosmic-bg px-3 py-2 text-sm text-white placeholder:text-cosmic-muted focus:border-nagarro-green/50 focus:outline-none focus:ring-2 focus:ring-nagarro-green/20'
const fileClass =
  'block w-full text-sm text-cosmic-muted file:mr-4 file:rounded-lg file:border-0 file:bg-nagarro-green file:px-4 file:py-2 file:text-sm file:font-semibold file:text-black hover:file:bg-nagarro-hover'
const labelClass = 'mb-2 block text-[10px] uppercase tracking-[0.18em]'

export function MeetingComposerModal({
  open,
  saving,
  error,
  onClose,
  onSubmit,
}: {
  open: boolean
  saving: boolean
  error: string | null
  onClose: () => void
  /** Resolve true when the meeting was created (the modal then resets itself). */
  onSubmit: (submission: MeetingSubmission) => Promise<boolean>
}) {
  const [form, setForm] = useState<MeetingFormState>(emptyForm)
  const [transcriptFile, setTranscriptFile] = useState<File | null>(null)
  const [supportingFiles, setSupportingFiles] = useState<File[]>([])
  const [localError, setLocalError] = useState<string | null>(null)

  if (!open) return null

  const update = <K extends keyof MeetingFormState>(key: K, value: MeetingFormState[K]) => setForm((prev) => ({ ...prev, [key]: value }))

  const handleTranscriptFile = async (file: File | undefined) => {
    if (!file) return
    const canReadText =
      file.type.startsWith('text/') ||
      /\.(txt|md|csv|json|rtf)$/i.test(file.name) ||
      file.type.includes('json') ||
      file.type.includes('xml')
    if (!canReadText) {
      setLocalError('Please paste the transcript text or upload a plain-text transcript file (.txt, .md, .csv, .json, .rtf).')
      return
    }
    try {
      const text = await readTextFile(file)
      setTranscriptFile(file)
      setForm((prev) => ({ ...prev, transcript_text: text || prev.transcript_text }))
      setLocalError(null)
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : 'Unable to read transcript file.')
    }
  }

  const submit = async () => {
    const transcript = form.transcript_text.trim() || (transcriptFile ? (await readTextFile(transcriptFile)).trim() : '')
    if (!form.title.trim() || !form.meeting_date || !transcript) {
      setLocalError('Meeting title, date, and transcript are required.')
      return
    }
    setLocalError(null)
    const created = await onSubmit({ form: { ...form, transcript_text: transcript }, transcriptFile, supportingFiles })
    if (created) {
      setForm(emptyForm)
      setTranscriptFile(null)
      setSupportingFiles([])
    }
  }

  const shownError = localError ?? error

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/70 p-4 backdrop-blur-sm sm:items-center" role="dialog" aria-modal="true" aria-label="Create deal-linked meeting analysis">
      <div className="my-auto w-full max-w-3xl rounded-3xl border border-cosmic-border bg-cosmic-surface p-6 shadow-2xl">
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Add meeting details</div>
            <h3 className="mt-2 text-xl font-bold text-white">Create deal-linked meeting analysis</h3>
            <p className="mt-1 text-xs text-cosmic-muted">Transcript is required for analysis; supporting documents stay optional.</p>
          </div>
          <button type="button" onClick={onClose} aria-label="Close" className="rounded-lg border border-cosmic-border bg-cosmic-bg/40 p-2 text-cosmic-muted hover:text-white">
            <X className="h-4 w-4" />
          </button>
        </div>

        {shownError && (
          <div className="mb-5">
            <Notice tone="red">{shownError}</Notice>
          </div>
        )}

        <div className="space-y-5">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block text-cosmic-muted">
              <span className={labelClass}>Meeting title</span>
              <input value={form.title} onChange={(event) => update('title', event.target.value)} className={inputClass} placeholder="Discovery workshop - Finance team" />
            </label>
            <label className="block text-cosmic-muted">
              <span className={labelClass}>Meeting type</span>
              <select value={form.meeting_type} onChange={(event) => update('meeting_type', event.target.value)} className={inputClass}>
                <option>Customer Call</option>
                <option>Board Review</option>
                <option>Internal Alignment</option>
                <option>QBR</option>
              </select>
            </label>
            <label className="block text-cosmic-muted">
              <span className={labelClass}>Date</span>
              <input type="date" value={form.meeting_date} onChange={(event) => update('meeting_date', event.target.value)} className={inputClass} />
            </label>
            <label className="block text-cosmic-muted">
              <span className={labelClass}>Attendees</span>
              <input value={form.attendees} onChange={(event) => update('attendees', event.target.value)} className={inputClass} placeholder="Names separated by comma" />
            </label>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <label className="block text-cosmic-muted">
              <span className={labelClass}>Objectives (optional)</span>
              <textarea rows={2} value={form.objectives} onChange={(event) => update('objectives', event.target.value)} className={inputClass} placeholder="What did you want out of this meeting?" />
            </label>
            <label className="block text-cosmic-muted">
              <span className={labelClass}>Notes (optional)</span>
              <textarea rows={2} value={form.notes} onChange={(event) => update('notes', event.target.value)} className={inputClass} placeholder="Anything the transcript does not capture" />
            </label>
          </div>

          <div className="rounded-2xl border border-cyan-500/30 bg-cyan-500/5 p-4">
            <div className="mb-3 flex items-center justify-between gap-2 text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">
              <span>Meeting transcript</span>
              <span className="rounded-full border border-cyan-500/40 bg-cyan-500/10 px-2 py-0.5 text-[9px] font-medium text-cyan-300">Required</span>
            </div>
            <div className="space-y-4">
              <label className="block text-cosmic-muted">
                <span className={labelClass}>Paste transcript text</span>
                <textarea
                  rows={6}
                  required
                  value={form.transcript_text}
                  onChange={(event) => update('transcript_text', event.target.value)}
                  className={inputClass}
                  placeholder="Paste the meeting transcript, call recording notes, or detailed discussion summary. This is the primary input for analysis."
                />
              </label>
              <div className="rounded-xl border border-dashed border-cyan-500/40 bg-cosmic-bg/20 p-4">
                <div className="mb-2 flex items-center gap-2 text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">
                  <Upload className="h-3.5 w-3.5 text-nagarro-green" />
                  Or upload transcript file
                </div>
                <input type="file" accept=".txt,.md,.csv,.json,.rtf" onChange={(event) => void handleTranscriptFile(event.target.files?.[0])} className={fileClass} />
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
            <input type="file" multiple accept=".pdf,.doc,.docx,.ppt,.pptx,.txt,.md,.png,.jpg,.jpeg" onChange={(event) => setSupportingFiles(Array.from(event.target.files ?? []))} className={fileClass} />
            <p className="mt-3 text-xs text-cosmic-muted">Optional: presentation decks, customer notes, screenshots, and other reference files that help explain the meeting context.</p>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button type="button" onClick={onClose} className="rounded-xl border border-cosmic-border bg-cosmic-bg/40 px-4 py-2 text-sm text-cosmic-muted hover:text-white">
            Cancel
          </button>
          <button type="button" disabled={saving} onClick={() => void submit()} className="btn-nagarro inline-flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-black" />
            {saving ? 'Saving…' : 'Start analysis'}
          </button>
        </div>
      </div>
    </div>
  )
}