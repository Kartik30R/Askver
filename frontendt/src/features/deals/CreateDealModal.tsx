import React, { useState, useEffect, useRef } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { useNavigate } from 'react-router-dom'
import { Plus, FileUp, ArrowRight, Play, CheckCircle2, AlertCircle, Lock } from 'lucide-react'
import { createNewDeal, startDealWorkflow, setCurrentDraft, selectCurrentDraft, selectCreatingDeal, selectStartingPipeline, selectDealsError, clearError } from './dealsSlice'
import { uploadDealDocument } from './dealsApi'
import { type AppDispatch, type RootState } from '../../app/store'
import type { DealCreate } from './dealsApi'

interface CreateDealModalProps {
  isOpen: boolean
  onClose: () => void
}

type StepStatus = 'incomplete' | 'completed' | 'current'
type ResearchDepthOption = 'quick' | 'standard' | 'deep'

const DEAL_SETTINGS_STORAGE_KEY = 'askver-deal-settings'

const readStoredDealSettings = () => {
  try {
    if (typeof window === 'undefined') {
      return { researchDepth: 'standard' as ResearchDepthOption, meetingDurationMinutes: 45 }
    }

    const raw = window.localStorage.getItem(DEAL_SETTINGS_STORAGE_KEY)
    if (!raw) {
      return { researchDepth: 'standard' as ResearchDepthOption, meetingDurationMinutes: 45 }
    }

    const parsed = JSON.parse(raw) as { researchDepth?: string; meetingDurationMinutes?: number }
    const researchDepth = parsed.researchDepth === 'quick' || parsed.researchDepth === 'deep' ? parsed.researchDepth : 'standard'
    const meetingDurationMinutes = parsed.meetingDurationMinutes === 30 || parsed.meetingDurationMinutes === 45 || parsed.meetingDurationMinutes === 60 || parsed.meetingDurationMinutes === 90
      ? parsed.meetingDurationMinutes
      : 45

    return { researchDepth, meetingDurationMinutes }
  } catch {
    return { researchDepth: 'standard' as ResearchDepthOption, meetingDurationMinutes: 45 }
  }
}

export default function CreateDealModal({ isOpen, onClose }: CreateDealModalProps) {
  const dispatch = useDispatch<AppDispatch>()
  const navigate = useNavigate()
  const currentDraft = useSelector(selectCurrentDraft)
  const accessToken = useSelector((state: RootState) => state.auth.accessToken)
  const creatingDeal = useSelector(selectCreatingDeal)
  const startingPipeline = useSelector(selectStartingPipeline)
  const error = useSelector(selectDealsError)

  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const [step, setStep] = useState(1)
  const [dealCreated, setDealCreated] = useState(false)
  const [docsUploaded, setDocsUploaded] = useState(false)
  const [formData, setFormData] = useState({
    title: '',
    target_company: '',
    target_industry: '',
    meeting_objective: '',
  })
  const [selectedDocs, setSelectedDocs] = useState<File[]>([])
  const [dragActive, setDragActive] = useState(false)
  const [isUploadingDocs, setIsUploadingDocs] = useState(false)
  const [formErrors, setFormErrors] = useState<Record<string, string>>({})
  const [researchDepth, setResearchDepth] = useState<ResearchDepthOption>(() => readStoredDealSettings().researchDepth)
  const [meetingDurationMinutes, setMeetingDurationMinutes] = useState<number>(() => readStoredDealSettings().meetingDurationMinutes)

  useEffect(() => {
    try {
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(DEAL_SETTINGS_STORAGE_KEY, JSON.stringify({ researchDepth, meetingDurationMinutes }))
      }
    } catch {
      // Ignore storage access failures and keep the values in memory.
    }
  }, [researchDepth, meetingDurationMinutes])

  // Determine starting step when modal opens or draft changes
  useEffect(() => {
    if (!isOpen) return

    if (currentDraft?.id) {
      // Deal already created, start at step 2
      setStep(2)
      setDealCreated(true)
      setFormData({
        title: currentDraft.title || '',
        target_company: currentDraft.target_company || '',
        target_industry: currentDraft.target_industry || '',
        meeting_objective: currentDraft.meeting_objective || '',
      })
    } else {
      // New deal, start at step 1
      setStep(1)
      setDealCreated(false)
      setFormData({
        title: '',
        target_company: '',
        target_industry: '',
        meeting_objective: '',
      })
    }
    setDocsUploaded(false)
    setSelectedDocs([])
    setFormErrors({})
    dispatch(clearError())
  }, [isOpen, currentDraft, dispatch])

  const validateStep1 = () => {
    const errors: Record<string, string> = {}

    if (!formData.title.trim()) errors.title = 'Deal title is required'
    if (!formData.target_company.trim()) errors.target_company = 'Company name is required'
    if (!formData.target_industry.trim()) errors.target_industry = 'Industry is required'
    if (!formData.meeting_objective.trim()) errors.meeting_objective = 'Meeting objective is required'

    setFormErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleCreateDeal = async () => {
    if (!validateStep1()) return
    if (dealCreated || creatingDeal) return // Prevent duplicate calls

    try {
      const dealData: DealCreate = {
        title: formData.title,
        target_company: formData.target_company,
        target_industry: formData.target_industry,
        meeting_objective: formData.meeting_objective,
      }

      const resultAction = await dispatch(createNewDeal(dealData))
      if (createNewDeal.fulfilled.match(resultAction)) {
        setDealCreated(true)
        // Auto-advance to step 2
        setTimeout(() => setStep(2), 300)
      }
    } catch (err) {
      console.error('Failed to create deal:', err)
    }
  }

  const handleFiles = async (incomingFiles: FileList | File[]) => {
    if (!currentDraft?.id) {
      setFormErrors({ submit: 'Deal must be created first. Please go back and complete step 1.' })
      return
    }

    if (isUploadingDocs) return // Prevent duplicate uploads

    const files = Array.from(incomingFiles)
    const allowedExtensions = ['pdf', 'docx', 'txt', 'pptx']
    const validFiles = files.filter((file) => {
      const ext = file.name.split('.').pop()?.toLowerCase() ?? ''
      return allowedExtensions.includes(ext)
    })

    if (!validFiles.length) {
      setFormErrors({ submit: 'Unsupported file type. Please upload PDF, DOCX, TXT, or PPTX files.' })
      return
    }

    setFormErrors({})
    setSelectedDocs(validFiles)
    setIsUploadingDocs(true)

    try {
      for (const file of validFiles) {
        const fd = new FormData()
        fd.append('document_category', 'RFP')
        fd.append('file', file)
        await uploadDealDocument(currentDraft.id, fd, accessToken)
      }

      setDocsUploaded(true)
      setFormErrors({})
    } catch (err) {
      console.error('Failed to upload documents:', err)
      setFormErrors({ submit: err instanceof Error ? err.message : 'Document upload failed.' })
    } finally {
      setIsUploadingDocs(false)
    }
  }

  const handleTriggerPipeline = async () => {
    if (!currentDraft?.id || startingPipeline) return

    try {
      const resultAction = await dispatch(startDealWorkflow({
        dealId: currentDraft.id,
        researchDepth,
        meetingDurationMinutes,
      }))
      if (startDealWorkflow.fulfilled.match(resultAction)) {
        // Clear draft and close modal
        dispatch(setCurrentDraft(null))
        onClose()
        // Navigate to deal dashboard
        navigate(`/deals/${currentDraft.id}`)
      }
    } catch (err) {
      console.error('Failed to trigger workflow:', err)
    }
  }

  const handleCancel = () => {
    onClose()
    // currentDraft stays in Redux for resuming later
  }

  const getStepStatus = (stepNum: number): StepStatus => {
    if (stepNum < step) return 'completed'
    if (stepNum === step) return 'current'
    return 'incomplete'
  }

  const getStepBadgeClass = (stepNum: number) => {
    const status = getStepStatus(stepNum)
    if (status === 'completed') return 'bg-nagarro-green/80 text-black font-bold'
    if (status === 'current') return 'bg-nagarro-green text-black font-bold'
    return 'text-cosmic-muted'
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="cosmic-card w-full max-w-2xl p-6 relative max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6 pb-4 border-b border-cosmic-border">
          <div>
            <h2 className="text-lg font-bold text-white">
              {dealCreated ? '📋 Complete Your Deal Setup' : '✨ Initiate Deal Intelligence'}
            </h2>
            {dealCreated && <p className="text-xs text-cosmic-muted mt-1">Deal created. Continue to upload documents.</p>}
          </div>

          {/* Step Indicators */}
          <div className="flex items-center gap-2 text-xs whitespace-nowrap">
            <span className={`px-2.5 py-1 rounded transition ${getStepBadgeClass(1)}`}>
              {getStepStatus(1) === 'completed' ? '✓' : '1'} Details
            </span>
            <span className="text-cosmic-muted">→</span>
            <span className={`px-2.5 py-1 rounded transition ${getStepBadgeClass(2)}`}>
              {getStepStatus(2) === 'completed' ? '✓' : '2'} Docs
            </span>
            <span className="text-cosmic-muted">→</span>
            <span className={`px-2.5 py-1 rounded transition ${getStepBadgeClass(3)}`}>
              {getStepStatus(3) === 'completed' ? '✓' : '3'} Execute
            </span>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-xs font-medium text-red-300">Error</p>
              <p className="text-xs text-red-300/80">{error}</p>
            </div>
          </div>
        )}

        {/* Step 1: Deal Details */}
        {step === 1 && (
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-cosmic-muted mb-1">Deal Title *</label>
              <input
                type="text"
                placeholder="e.g., Q4 2026 Financial Platform Migration"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                disabled={dealCreated}
                className={`w-full bg-cosmic-bg border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-nagarro-green transition disabled:opacity-50 disabled:cursor-not-allowed ${
                  formErrors.title ? 'border-red-500' : 'border-cosmic-border'
                }`}
              />
              {formErrors.title && <p className="text-xs text-red-400 mt-1">{formErrors.title}</p>}
            </div>

            <div>
              <label className="block text-xs font-medium text-cosmic-muted mb-1">Target Company Name *</label>
              <input
                type="text"
                placeholder="Acme Global Financials"
                value={formData.target_company}
                onChange={(e) => setFormData({ ...formData, target_company: e.target.value })}
                disabled={dealCreated}
                className={`w-full bg-cosmic-bg border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-nagarro-green transition disabled:opacity-50 disabled:cursor-not-allowed ${
                  formErrors.target_company ? 'border-red-500' : 'border-cosmic-border'
                }`}
              />
              {formErrors.target_company && <p className="text-xs text-red-400 mt-1">{formErrors.target_company}</p>}
            </div>

            <div>
              <label className="block text-xs font-medium text-cosmic-muted mb-1">Industry Sector *</label>
              <input
                type="text"
                placeholder="Banking & Financial Services"
                value={formData.target_industry}
                onChange={(e) => setFormData({ ...formData, target_industry: e.target.value })}
                disabled={dealCreated}
                className={`w-full bg-cosmic-bg border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-nagarro-green transition disabled:opacity-50 disabled:cursor-not-allowed ${
                  formErrors.target_industry ? 'border-red-500' : 'border-cosmic-border'
                }`}
              />
              {formErrors.target_industry && <p className="text-xs text-red-400 mt-1">{formErrors.target_industry}</p>}
            </div>

            <div>
              <label className="block text-xs font-medium text-cosmic-muted mb-1">Meeting Objective *</label>
              <textarea
                placeholder="What are the client's key expectations and priorities for this meeting?"
                value={formData.meeting_objective}
                onChange={(e) => setFormData({ ...formData, meeting_objective: e.target.value })}
                disabled={dealCreated}
                rows={3}
                className={`w-full bg-cosmic-bg border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-nagarro-green transition resize-none disabled:opacity-50 disabled:cursor-not-allowed ${
                  formErrors.meeting_objective ? 'border-red-500' : 'border-cosmic-border'
                }`}
              />
              {formErrors.meeting_objective && <p className="text-xs text-red-400 mt-1">{formErrors.meeting_objective}</p>}
            </div>

            {dealCreated && (
              <div className="p-3 bg-nagarro-green/10 border border-nagarro-green/30 rounded-lg flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-nagarro-green mt-0.5 flex-shrink-0" />
                <p className="text-xs text-nagarro-green">✓ Deal created successfully. Proceed to upload documents.</p>
              </div>
            )}

            <div className="flex justify-between gap-3 pt-4">
              <button
                onClick={handleCancel}
                className="px-4 py-2 text-xs text-cosmic-muted hover:text-white transition"
              >
                Cancel
              </button>
              {!dealCreated ? (
                <button
                  onClick={handleCreateDeal}
                  disabled={creatingDeal}
                  className="btn-nagarro text-xs flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {creatingDeal ? '⏳ Creating...' : 'Create Deal'}
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              ) : (
                <button
                  onClick={() => setStep(2)}
                  className="btn-nagarro text-xs flex items-center gap-1"
                >
                  Next: Documents
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>
        )}

        {/* Step 2: Document Upload */}
        {step === 2 && (
          <div className="space-y-4">
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
              <p className="text-xs text-blue-300">
                <strong>Optional:</strong> Upload RFP, BRD, or supporting documents. You can skip this and proceed to start the pipeline, or add documents later.
              </p>
            </div>

            <div
              onClick={() => !isUploadingDocs && fileInputRef.current?.click()}
              onKeyDown={(event) => {
                if (!isUploadingDocs && (event.key === 'Enter' || event.key === ' ')) {
                  event.preventDefault()
                  fileInputRef.current?.click()
                }
              }}
              onDragOver={(event) => {
                if (!isUploadingDocs) {
                  event.preventDefault()
                  setDragActive(true)
                }
              }}
              onDragLeave={() => setDragActive(false)}
              onDrop={(event) => {
                if (!isUploadingDocs) {
                  event.preventDefault()
                  setDragActive(false)
                  if (event.dataTransfer.files?.length) {
                    void handleFiles(event.dataTransfer.files)
                  }
                }
              }}
              role="button"
              tabIndex={0}
              className={`border-2 border-dashed rounded-xl p-8 text-center transition cursor-pointer ${
                isUploadingDocs
                  ? 'border-cosmic-border/50 bg-cosmic-bg/20 opacity-60'
                  : dragActive
                    ? 'border-nagarro-green bg-nagarro-green/10'
                    : docsUploaded
                      ? 'border-nagarro-green/50 bg-nagarro-green/5'
                      : 'border-cosmic-border hover:border-nagarro-green/50 bg-cosmic-bg/40'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.docx,.txt,.pptx"
                className="hidden"
                disabled={isUploadingDocs}
                onChange={(event) => {
                  if (event.target.files?.length) {
                    void handleFiles(event.target.files)
                  }
                  event.target.value = ''
                }}
              />

              <FileUp
                className={`w-10 h-10 mx-auto mb-2 ${
                  isUploadingDocs ? 'text-cosmic-muted' : docsUploaded ? 'text-nagarro-green' : 'text-nagarro-green'
                }`}
              />
              <p className="text-sm text-white font-medium">{isUploadingDocs ? 'Embedding documents...' : 'Drag and drop documents here'}</p>
              <p className="text-xs text-cosmic-muted mt-1">
                {currentDraft?.id ? `Vector Collection: deal_${currentDraft.id.slice(0, 8)}_docs` : 'Collection: pending'}
              </p>
              <p className="text-xs text-cosmic-muted mt-2">PDF, DOCX, TXT, PPTX • Max 10MB per file</p>

              {selectedDocs.length > 0 && (
                <div className="mt-3 space-y-1 text-left text-xs text-cosmic-muted">
                  {selectedDocs.slice(0, 3).map((file) => (
                    <div key={file.name} className="truncate text-white">
                      • {file.name} ({(file.size / 1024).toFixed(0)} KB)
                    </div>
                  ))}
                  {selectedDocs.length > 3 && <div>+ {selectedDocs.length - 3} more</div>}
                </div>
              )}

              {docsUploaded && (
                <p className="text-xs text-nagarro-green mt-3 font-medium">✓ {selectedDocs.length} documents indexed into vector store</p>
              )}
            </div>

            {formErrors.submit && (
              <div className="p-3 bg-red-500/20 border border-red-500/50 rounded-lg">
                <p className="text-xs text-red-300">{formErrors.submit}</p>
              </div>
            )}

            <div className="flex justify-between gap-3 pt-4">
              <button
                onClick={() => setStep(1)}
                disabled={isUploadingDocs}
                className="px-4 py-2 text-xs text-cosmic-muted hover:text-white transition disabled:opacity-50"
              >
                Back
              </button>
              <button
                onClick={() => setStep(3)}
                disabled={isUploadingDocs}
                className="btn-nagarro text-xs flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next: Execute
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Execute Pipeline */}
        {step === 3 && (
          <div className="space-y-4 text-center py-4">
            <CheckCircle2 className="w-12 h-12 text-nagarro-green mx-auto animate-bounce" />
            <h3 className="text-lg font-bold text-white">Ready to Launch Deal Analysis</h3>
            <p className="text-xs text-cosmic-muted max-w-xl mx-auto">
              8 specialized AI agents will asynchronously research the company, extract pain points, match internal proof assets, and synthesize a CXO-level executive brief.
            </p>

            <div className="bg-cosmic-bg/50 border border-cosmic-border/50 rounded-lg p-4 text-left mt-6 space-y-2">
              <p className="text-xs font-semibold text-white">Deal Summary</p>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <span className="text-cosmic-muted">Title</span>
                  <p className="text-white font-medium truncate">{formData.title}</p>
                </div>
                <div>
                  <span className="text-cosmic-muted">Company</span>
                  <p className="text-white font-medium truncate">{formData.target_company}</p>
                </div>
                <div className="col-span-2">
                  <span className="text-cosmic-muted">Industry</span>
                  <p className="text-white font-medium">{formData.target_industry}</p>
                </div>
              </div>
            </div>

            <div className="grid gap-4 pt-2 text-left">
              <div>
                <label className="block text-xs font-medium text-cosmic-muted mb-1">Research depth</label>
                <select
                  value={researchDepth}
                  onChange={(e) => setResearchDepth(e.target.value as ResearchDepthOption)}
                  className="w-full bg-cosmic-bg border border-cosmic-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-nagarro-green"
                >
                  <option value="quick">Quick</option>
                  <option value="standard">Standard</option>
                  <option value="deep">Deep</option>
                </select>
                <p className="mt-1 text-[11px] text-cosmic-muted">
                  Quick = fewer sources, fastest and cheapest. Standard = recommended. Deep = adds competitor analysis and more searching, uses more time and model calls.
                </p>
              </div>

              <div>
                <label className="block text-xs font-medium text-cosmic-muted mb-1">Meeting duration</label>
                <select
                  value={meetingDurationMinutes}
                  onChange={(e) => setMeetingDurationMinutes(Number(e.target.value))}
                  className="w-full bg-cosmic-bg border border-cosmic-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-nagarro-green"
                >
                  <option value={30}>30 minutes</option>
                  <option value={45}>45 minutes</option>
                  <option value={60}>60 minutes</option>
                  <option value={90}>90 minutes</option>
                </select>
              </div>
            </div>

            <div className="bg-nagarro-green/10 border border-nagarro-green/30 rounded-lg p-3 mt-4">
              <p className="text-xs text-nagarro-green">
                ✓ Deal is configured and ready. Pipeline execution cannot be undone. Documents are optional and can be added anytime.
              </p>
            </div>

            <div className="flex justify-center gap-3 pt-4">
              <button
                onClick={() => setStep(2)}
                disabled={startingPipeline}
                className="px-4 py-2 text-xs text-cosmic-muted hover:text-white transition disabled:opacity-50"
              >
                Back
              </button>
              <button
                onClick={handleTriggerPipeline}
                disabled={startingPipeline}
                className="btn-nagarro text-xs flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Play className="w-3.5 h-3.5 fill-black" />
                {startingPipeline ? 'Starting...' : 'Start Pipeline'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
