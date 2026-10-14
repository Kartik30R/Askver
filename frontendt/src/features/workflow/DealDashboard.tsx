import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import {
  BarChart3,
  DollarSign,
  TrendingUp,
  ShieldAlert,
  Activity,
  Gauge,
  Landmark,
  CheckCircle2,AlertTriangle
} from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import {
  deleteDeal,
  deleteDealDocument,
  getDealById,
  listDealDocuments,
  uploadDealDocument,
  type DealDocument,
} from '../deals/dealsApi'
import type { AppDispatch, RootState } from '../../app/store'
import {
  getLatestReport,
  getReportVersions,
  restoreReportVersion,
  type LatestReportResponse,
} from './reportApi'
import {
  approveTextEdit,
  askDealQuery,
  proposeTextEdit,
  type ChatQueryResponse,
} from './chatApi'
import {
  getExecutionHistory,
  getPipelineState,
  getPipelineStatus,
  resumeFromCheckpoint,
  submitMandatoryReviewApproval,
} from './workflowApi'
import {
  addChatMessage,
  selectChatLoading,
  selectChatMessages,
  selectReportMarkdown,
  selectWorkflowProposal,
  selectWorkflowSelectedSection,
  setChatLoading,
  setPipelineState,
  setProposal,
  setReportMarkdown,
  setSelectedSection,
} from './workflowSlice'
import DealDashboardHeader from '../../components/dashboard/DealDashboardHeader'
import DealDocumentsPanel from '../../components/dashboard/DealDocumentsPanel'
import PipelineFlow from '../../components/dashboard/PipelineFlow'
import ReportChatPanel from '../../components/dashboard/ReportChatPanel'
import HITLDrawer from '../../components/dashboard/HITLDrawer'
import NodeDetailTabs from '../../components/dashboard/NodeDetailTabs'

export default function DealDashboard() {
  const dispatch = useDispatch<AppDispatch>()
  const navigate = useNavigate()
  const accessToken = useSelector((state: RootState) => state.auth.accessToken)
  const pipelineState = useSelector((state: RootState) => state.workflow.pipelineState)
  const reportMarkdown = useSelector((state: RootState) => selectReportMarkdown(state))
  const chatMessages = useSelector((state: RootState) => selectChatMessages(state))
  const chatLoading = useSelector((state: RootState) => selectChatLoading(state))
  const proposal = useSelector((state: RootState) => selectWorkflowProposal(state))
  const selectedSection = useSelector((state: RootState) => selectWorkflowSelectedSection(state))

  // Top-level View Mode: 'pipeline' | 'tabs' | 'report_chat'
  const [viewMode, setViewMode] = useState<'pipeline' | 'tabs' | 'report_chat'>('pipeline')

  // Selected node for Chrome Tabs view
  const [activeTabNode, setActiveTabNode] = useState('company_research')

  // VS Code Drawer Toggle
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)

  // Version Control Checkpoint Dropdown state
  const [selectedCheckpoint, setSelectedCheckpoint] = useState('latest')
  const [checkpointOptions, setCheckpointOptions] = useState<Array<{ value: string; label: string }>>([
    { value: 'latest', label: 'Head (Latest Checkpoint)' },
  ])
  const [isDocumentsOpen, setIsDocumentsOpen] = useState(false)
  const [pipelineStatus, setPipelineStatus] = useState('UNKNOWN')
  const [dealDetails, setDealDetails] = useState<{ target_company?: string | null; target_industry?: string | null; meeting_objective?: string | null } | null>(null)
  const [intelTab, setIntelTab] = useState<'overview' | 'financial' | 'business' | 'leadership' | 'digital' | 'technology' | 'news'>('overview')
  const [painPointFilter, setPainPointFilter] = useState<'ALL' | 'HIGH' | 'MEDIUM' | 'LOW'>('ALL')
  const [industryFilter, setIndustryFilter] = useState<'ALL' | 'TRENDS' | 'RISKS' | 'REGULATORY' | 'BENCHMARKS'>('ALL')
  const [industryExpanded, setIndustryExpanded] = useState<Record<string, boolean>>({})
  const [selectedCitationKey, setSelectedCitationKey] = useState<string | null>(null)
  const [sourceDrawerOpen, setSourceDrawerOpen] = useState(false)
  const [selectedStakeholderRole, setSelectedStakeholderRole] = useState('CEO')
  const [stakeholderCompareMode, setStakeholderCompareMode] = useState(false)
  const [isDeletingDeal, setIsDeletingDeal] = useState(false)
  const [isSubmittingReview, setIsSubmittingReview] = useState(false)
  const [reviewFeedback, setReviewFeedback] = useState('')
  const [coveredTalkingPoints, setCoveredTalkingPoints] = useState<Record<number, boolean>>({})

  const { dealId } = useParams()
  const [documents, setDocuments] = useState<DealDocument[]>([])
  const [chatInput, setChatInput] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [documentCategory, setDocumentCategory] = useState('RFP')
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false)
  const [isUploadingDocument, setIsUploadingDocument] = useState(false)
  const [documentError, setDocumentError] = useState('')
  const [documentSuccess, setDocumentSuccess] = useState('')

  const loadDocuments = async () => {
    if (!dealId) return

    setIsLoadingDocuments(true)
    setDocumentError('')

    try {
      const response = await listDealDocuments(dealId, accessToken)
      setDocuments(response)
    } catch (error) {
      setDocumentError(error instanceof Error ? error.message : 'Unable to load documents')
    } finally {
      setIsLoadingDocuments(false)
    }
  }

  const loadDealMeta = async () => {
    if (!dealId) return

    try {
      const detail = await getDealById(dealId, accessToken)
      const candidate = 
        detail && typeof detail === 'object' && 'deal' in detail && detail.deal && typeof detail.deal === 'object'
          ? detail.deal as Record<string, unknown>
          : detail as Record<string, unknown>

      const payload = {
        target_company: typeof candidate.target_company === 'string' ? candidate.target_company : null,
        target_industry: typeof candidate.target_industry === 'string' ? candidate.target_industry : null,
        meeting_objective: typeof candidate.meeting_objective === 'string' ? candidate.meeting_objective : null,
      }
      setDealDetails(payload)
    } catch {
      setDealDetails(null)
    }
  }

  const loadPipelineState = async () => {
    if (!dealId) return

    try {
      const state = await getPipelineState(dealId, accessToken)
      dispatch(setPipelineState(state))

      const statusResponse = await getPipelineStatus(dealId, accessToken)
      setPipelineStatus(statusResponse.status)
    } catch {
      dispatch(setPipelineState(null))
      setPipelineStatus('UNKNOWN')
    }
  }

  const loadExecutionHistory = async () => {
    if (!dealId) {
      setCheckpointOptions([{ value: 'latest', label: 'Head (Latest Version)' }])
      setSelectedCheckpoint('latest')
      return
    }

    try {
      const reportVersions = await getReportVersions(dealId, accessToken)
      const options = [
        { value: 'latest', label: 'Head (Latest Version)' },
        ...reportVersions.map((version) => ({
          value: version.snapshot_id,
          label: `Version ${version.version} · ${new Date(version.updated_at ?? Date.now()).toLocaleString([], {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          })}`,
        })),
      ]
      setCheckpointOptions(options)
      if (!selectedCheckpoint || selectedCheckpoint === 'latest' || !options.some((option) => option.value === selectedCheckpoint)) {
        setSelectedCheckpoint('latest')
      }
    } catch {
      try {
        const history = await getExecutionHistory(dealId, accessToken)
        const options = [
          { value: 'latest', label: 'Head (Latest Version)' },
          ...history.map((checkpoint) => ({
            value: checkpoint.checkpoint_id,
            label: `${checkpoint.current_step || checkpoint.node_name || 'Checkpoint'} · ${new Date(checkpoint.timestamp ?? Date.now()).toLocaleString([], {
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })}`,
          })),
        ]
        setCheckpointOptions(options)
        if (!selectedCheckpoint || selectedCheckpoint === 'latest' || !options.some((option) => option.value === selectedCheckpoint)) {
          setSelectedCheckpoint('latest')
        }
      } catch {
        setCheckpointOptions([{ value: 'latest', label: 'Head (Latest Version)' }])
        setSelectedCheckpoint('latest')
      }
    }
  }

  const loadLatestReport = async () => {
    if (!dealId) return

    try {
      const response = await getLatestReport(dealId, accessToken)
      const state = response.snapshot_data as LatestReportResponse['snapshot_data']
      const markdown =
        (state?.markdown_export as string | undefined) ||
        (typeof state?.cxo_executive_brief === 'string' ? state.cxo_executive_brief : undefined) ||
        '# Report not available\n\nThe report has not been generated yet.'
      dispatch(setReportMarkdown(markdown))
    } catch {
      dispatch(setReportMarkdown('# Report not available\n\nThe report has not been generated yet.'))
    }
  }

  const handleChatSubmit = async () => {
    if (!dealId || !chatInput.trim()) return

    const userMessage = chatInput.trim()
    dispatch(addChatMessage({ role: 'user', text: userMessage }))
    setChatInput('')
    dispatch(setChatLoading(true))

    try {
      const response: ChatQueryResponse = await askDealQuery(dealId, { question: userMessage }, accessToken)
      dispatch(addChatMessage({ role: 'assistant', text: response.answer }))
    } catch (error) {
      dispatch(addChatMessage({ role: 'assistant', text: error instanceof Error ? error.message : 'Unable to answer this question.' }))
    } finally {
      dispatch(setChatLoading(false))
    }
  }

  const handleProposedEdit = async () => {
    if (!dealId) return

    if (!selectedSection || selectedSection === 'general') {
      dispatch(addChatMessage({
        role: 'assistant',
        text: 'Choose a specific section first. Revision generation only works when the chat context is scoped to a section like the executive brief or financial intelligence.',
      }))
      return
    }

    const instruction = chatInput.trim() || 'Make this section more executive-ready and concise.'
    const targetSection = selectedSection
    setChatInput('')
    dispatch(setChatLoading(true))

    try {
      const result = await proposeTextEdit(dealId, {
        section: targetSection,
        instruction,
        current_text: reportMarkdown,
      }, accessToken)
      dispatch(setProposal(result))
      dispatch(addChatMessage({ role: 'assistant', text: `Draft revision created for ${targetSection}. Review it and approve or reject the proposal below.` }))
    } catch (error) {
      dispatch(addChatMessage({ role: 'assistant', text: error instanceof Error ? error.message : 'Unable to generate a proposal.' }))
    } finally {
      dispatch(setChatLoading(false))
    }
  }

  const handleProposalDecision = async (approved: boolean) => {
    if (!dealId || !proposal) return

    dispatch(setChatLoading(true))

    try {
      const result = await approveTextEdit(dealId, {
        proposed_diff_id: proposal.proposed_diff_id,
        approved,
      }, accessToken)

      dispatch(addChatMessage({
        role: 'assistant',
        text: result.approved
          ? `Approved proposal ${result.proposed_diff_id}. The edit can now be applied to the ${selectedSection || 'report'} section.`
          : `Rejected proposal ${result.proposed_diff_id}. The draft was discarded and can be revised.`,
      }))
      dispatch(setProposal(null))
    } catch (error) {
      dispatch(addChatMessage({
        role: 'assistant',
        text: error instanceof Error ? error.message : 'Unable to process the proposal decision.',
      }))
    } finally {
      dispatch(setChatLoading(false))
    }
  }

  useEffect(() => {
    if (!selectedSection) {
      dispatch(setSelectedSection('general'))
    }
  }, [dispatch, selectedSection])

  useEffect(() => {
    void loadDocuments()
    void loadDealMeta()
    void loadPipelineState()
    void loadExecutionHistory()
    void loadLatestReport()
  }, [dealId, accessToken])

  const handleDocumentUpload = async (event: React.FormEvent) => {
    event.preventDefault()

    if (!dealId || !selectedFile) {
      setDocumentError('Please select a document to upload.')
      return
    }

    const formData = new FormData()
    formData.append('document_category', documentCategory)
    formData.append('file', selectedFile)

    setIsUploadingDocument(true)
    setDocumentError('')
    setDocumentSuccess('')

    try {
      await uploadDealDocument(dealId, formData, accessToken)
      setDocumentSuccess('Document uploaded successfully.')
      setSelectedFile(null)
      await loadDocuments()
    } catch (error) {
      setDocumentError(error instanceof Error ? error.message : 'Upload failed')
    } finally {
      setIsUploadingDocument(false)
    }
  }

  const handleDocumentDelete = async (documentId: string) => {
    if (!dealId) return

    try {
      await deleteDealDocument(dealId, documentId, accessToken)
      setDocumentSuccess('Document removed.')
      await loadDocuments()
    } catch (error) {
      setDocumentError(error instanceof Error ? error.message : 'Delete failed')
    }
  }

  const handleDeleteDeal = async () => {
    if (!dealId) return

    const shouldDelete = window.confirm('Delete this deal and all associated workflow data? This action cannot be undone.')
    if (!shouldDelete) return

    setIsDeletingDeal(true)

    try {
      await deleteDeal(dealId, accessToken)
      navigate('/deals')
    } catch (error) {
      setDocumentError(error instanceof Error ? error.message : 'Unable to delete this deal.')
    } finally {
      setIsDeletingDeal(false)
    }
  }

  const handleRestoreCheckpoint = async () => {
    if (!dealId || !selectedCheckpoint || selectedCheckpoint === 'latest') return

    try {
      await restoreReportVersion(dealId, selectedCheckpoint, accessToken)
      setSelectedCheckpoint('latest')
      await loadPipelineState()
      await loadLatestReport()
      await loadExecutionHistory()
    } catch (error) {
      try {
        await resumeFromCheckpoint(dealId, selectedCheckpoint, accessToken)
        setSelectedCheckpoint('latest')
        await loadPipelineState()
        await loadLatestReport()
        await loadExecutionHistory()
      } catch (fallbackError) {
        setDocumentError(fallbackError instanceof Error ? fallbackError.message : 'Unable to restore this version.')
      }
    }
  }

  const handleReviewApproval = async (status: 'approved' | 'needs_revision' | 'rejected') => {
    if (!dealId) return

    setIsSubmittingReview(true)

    try {
      await submitMandatoryReviewApproval(
        dealId,
        {
          checkpoint_status: status,
          feedback: reviewFeedback.trim() || undefined,
        },
        accessToken,
      )
      setReviewFeedback('')
      await loadPipelineState()
    } catch (error) {
      setDocumentError(error instanceof Error ? error.message : 'Unable to submit the review decision.')
    } finally {
      setIsSubmittingReview(false)
    }
  }

  const nodeAliases: Record<string, string[]> = {
    company_research: ['company_research', 'company_overview'],
    financial_intelligence: ['financial_intelligence', 'financial_intel'],
    stakeholder_intel: ['stakeholder_intel', 'stakeholder_intelligence', 'stakeholder_analysis'],
    industry_analysis: ['industry_analysis'],
    pain_point_detector: ['pain_point_detector', 'detected_pain_points', 'priorities_and_pain_points', 'priorities'],
    enterprise_rag_matcher: ['enterprise_rag_matcher', 'matched_internal_assets', 'service_mappings', 'enterprise_rag'],
    service_mapper: ['service_mapper', 'service_mappings'],
    human_review_gate: ['human_review_gate', 'mandatory_review', 'mandatory_review_checkpoint', 'human_feedback', 'human_approved'],
    cxo_brief_generator: ['cxo_brief_generator', 'cxo_brief', 'cxo_executive_brief'],
  }

  const getNodeAliasValue = (nodeId: string): unknown => {
    const aliases = nodeAliases[nodeId] ?? [nodeId]
    for (const alias of aliases) {
      const value = pipelineState?.[alias]
      if (value !== undefined && value !== null) return value
    }
    return undefined
  }

  const nodeStatusMap = pipelineState?.node_statuses ?? {}
  const resolveNodeStatus = (nodeId: string, fallback: 'completed' | 'paused' | 'pending' | 'failed' | 'running') => {
    const aliases = nodeAliases[nodeId] ?? [nodeId]
    const rawStatus =
      aliases
        .map((alias) => nodeStatusMap[alias])
        .find((value) => value !== undefined && value !== null)
      ?? (nodeId === 'human_review_gate'
        ? nodeStatusMap.mandatory_review ?? pipelineState?.mandatory_review_checkpoint
        : undefined)
      ?? (nodeId === 'cxo_brief_generator' ? nodeStatusMap.cxo_brief ?? nodeStatusMap.cxo_brief_generator : undefined)
      ?? (nodeId === 'enterprise_rag_matcher' ? nodeStatusMap.enterprise_rag ?? nodeStatusMap.enterprise_rag_matcher : undefined)
      ?? (nodeStatusMap[nodeId] ?? getNodeAliasValue(nodeId))

    if (rawStatus === undefined || rawStatus === null || rawStatus === '') return fallback

    const normalized = String(rawStatus).toLowerCase()
    if (normalized.includes('completed') || normalized.includes('success') || normalized.includes('approved')) return 'completed'
    if (normalized.includes('failed') || normalized.includes('error') || normalized.includes('rejected')) return 'failed'
    if (normalized.includes('running') || normalized.includes('started') || normalized.includes('executing')) return 'running'
    if (normalized.includes('paused') || normalized.includes('review') || normalized.includes('awaiting') || normalized.includes('needs_revision')) return 'paused'
    return 'pending'
  }

  const humanizeLabel = (value: string) => value
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())

  const formatValueForMarkdown = (value: unknown, key?: string): string => {
    if (value == null) {
      return key ? `- **${humanizeLabel(key)}**: Not available` : 'Not available'
    }

    if (typeof value === 'string') {
      return value.trim() || (key ? `- **${humanizeLabel(key)}**: Empty` : 'Empty')
    }

    if (typeof value === 'number' || typeof value === 'boolean') {
      return key ? `- **${humanizeLabel(key)}**: ${String(value)}` : String(value)
    }

    if (Array.isArray(value)) {
      if (value.length === 0) {
        return key ? `- **${humanizeLabel(key)}**: No items` : 'No items'
      }

      return value
        .map((item, index) => {
          const nextKey = key ? `${key} ${index + 1}` : `Item ${index + 1}`
          return typeof item === 'object' && item !== null
            ? `### ${humanizeLabel(nextKey)}\n${formatValueForMarkdown(item, nextKey)}`
            : `- **${humanizeLabel(nextKey)}**: ${String(item)}`
        })
        .join('\n')
    }

    if (typeof value === 'object') {
      const entries = Object.entries(value as Record<string, unknown>)
      if (entries.length === 0) {
        return key ? `- **${humanizeLabel(key)}**: No data` : 'No data'
      }

      return entries
        .map(([entryKey, entryValue]) => {
          if (typeof entryValue === 'object' && entryValue !== null && !Array.isArray(entryValue)) {
            return `### ${humanizeLabel(entryKey)}\n${formatValueForMarkdown(entryValue, entryKey)}`
          }
          return `- **${humanizeLabel(entryKey)}**: ${String(entryValue)}`
        })
        .join('\n')
    }

    return String(value)
  }

  const asStringList = (value: unknown) => {
    if (Array.isArray(value)) return value.map((item) => String(item)).filter(Boolean)
    if (typeof value === 'string') return [value]
    return []
  }

  const renderNodeTemplate = (nodeId: string, data: unknown) => {
    if (!data) {
      return `### ${humanizeLabel(nodeId)}\n- **Status**: ${resolveNodeStatus(nodeId, 'pending')}\n\nNo data is available for this stage yet.`
    }

    if (nodeId === 'company_research') {
      const overview = (data as Record<string, unknown>)?.overview as Record<string, unknown> | undefined
      const summary = (overview?.summary as Record<string, unknown>) ?? {}
      const headline = String(summary.headline ?? 'Company overview')
      const narrative = String(summary.detailed_narrative ?? '')
      const leadership = Array.isArray((data as Record<string, unknown>)?.leadership_team)
        ? (data as Record<string, unknown>).leadership_team as Array<Record<string, unknown>>
        : []

      return [
        `# ${String((pipelineState?.financial_intelligence as Record<string, unknown>)?.company_name ?? 'Company')}`,
        '',
        `## ${headline}`,
        '',
        narrative || 'No summary narrative available yet.',
        '',
        '### Leadership team',
        ...leadership.slice(0, 5).map((person) => `- **${person.name ?? 'Team member'}** — ${person.role ?? 'Leadership role'}`),
      ].join('\n')
    }

    if (nodeId === 'financial_intelligence') {
      const financial = data as Record<string, unknown>
      const metrics = Array.isArray(financial.metric_scores) ? financial.metric_scores : []
      const metricLines = (metrics as Array<Record<string, unknown>>)
        .slice(0, 5)
        .map((metric) => `- **${metric.metric_name ?? 'Metric'}**: ${metric.value ?? 'n/a'} (${metric.score_100 ?? 'n/a'} / 100)`) 

      return [
        `# ${String(financial.company_name ?? 'Financial intelligence')}`,
        '',
        `**Market**: ${String(financial.market ?? 'n/a')}  |  **Status**: ${String(financial.status ?? 'n/a')}`,
        '',
        `> ${String(financial.ai_summary ?? 'No summary available.')}`,
        '',
        ...metricLines,
      ].join('\n')
    }

    if (nodeId === 'stakeholder_intel') {
      const stakeholders = Array.isArray((data as Record<string, unknown>)?.personas)
        ? ((data as Record<string, unknown>).personas as Array<Record<string, unknown>>) ?? []
        : []

      return [
        '## Stakeholder intelligence',
        '',
        ...stakeholders.slice(0, 6).map((persona) => [
          `### ${String(persona.role ?? 'Stakeholder')}`,
          ...asStringList(persona.likely_goals).map((item) => `- Goal: ${item}`),
          ...asStringList(persona.likely_concerns).map((item) => `- Concern: ${item}`),
          '',
        ].join('\n')),
      ].join('\n')
    }

    if (nodeId === 'industry_analysis') {
      const trends = Array.isArray((data as Record<string, unknown>)?.major_trends)
        ? ((data as Record<string, unknown>).major_trends as Array<Record<string, unknown>>) ?? []
        : []
      const risks = Array.isArray((data as Record<string, unknown>)?.risks_and_challenges)
        ? ((data as Record<string, unknown>).risks_and_challenges as Array<Record<string, unknown>>) ?? []
        : []

      return [
        '## Industry analysis',
        '',
        '### Major trends',
        ...trends.slice(0, 3).map((item) => `- **${String(item.headline ?? 'Trend')}**: ${String(item.detailed_narrative ?? '')}`),
        '',
        '### Risks and challenges',
        ...risks.slice(0, 3).map((item) => `- **${String(item.headline ?? 'Risk')}**: ${String(item.detailed_narrative ?? '')}`),
      ].join('\n')
    }

    if (nodeId === 'pain_point_detector') {
      const painPoints = Array.isArray(data) ? data as Array<Record<string, unknown>> : Array.isArray((data as Record<string, unknown>)?.detected_pain_points) ? ((data as Record<string, unknown>).detected_pain_points as Array<Record<string, unknown>>) : []
      const priorities = Array.isArray((data as Record<string, unknown>)?.priorities) ? ((data as Record<string, unknown>).priorities as string[]) : Array.isArray(data) ? [] : asStringList((data as Record<string, unknown>)?.priorities)

      return [
        '## Priorities and pain points',
        '',
        '### Strategic priorities',
        ...priorities.slice(0, 5).map((item) => `- ${item}`),
        '',
        '### Pain points',
        ...painPoints.slice(0, 5).map((item) => `- **${String(item.category ?? 'Pain point')}** (${String(item.severity ?? 'MEDIUM')}): ${String(item.description ?? '')}`),
      ].join('\n')
    }

    if (nodeId === 'service_mapper' || nodeId === 'enterprise_rag_matcher') {
      const entries = Array.isArray(data) ? data as Array<Record<string, unknown>> : Array.isArray((data as Record<string, unknown>)?.service_mappings) ? ((data as Record<string, unknown>).service_mappings as Array<Record<string, unknown>>) : []

      return [
        '## Service mapping',
        '',
        ...entries.slice(0, 4).map((item) => [
          `### ${String(item.recommended_offering ?? 'Recommended offering')}`,
          `**Client need**: ${String(item.client_need ?? '')}`,
          `**Business impact**: ${String(item.expected_business_impact ?? '')}`,
          ...((item.supporting_proof_assets as Array<Record<string, unknown>> | undefined) ?? []).slice(0, 2).map((asset) => `- **${String(asset.asset_name ?? 'Asset')}** — ${String(asset.summary ?? '')}`),
          '',
        ].join('\n')),
      ].join('\n')
    }

    if (nodeId === 'human_review_gate') {
      const checkpoint = (pipelineState?.mandatory_review_checkpoint as string | undefined) ?? 'pending'
      const approved = Boolean(pipelineState?.human_approved)
      return [
        '## Human review gate',
        '',
        `**Checkpoint status**: ${checkpoint}`,
        `**Approval status**: ${approved ? 'Approved' : 'Awaiting approval'}`,
        pipelineState?.human_feedback ? `**Feedback**: ${pipelineState.human_feedback}` : '',
      ].join('\n')
    }

    if (nodeId === 'cxo_brief_generator') {
      const brief = data as Record<string, unknown>
      const talkingPoints = asStringList(brief?.talking_points)
      const objections = Array.isArray(brief?.objections_and_responses) ? (brief.objections_and_responses as Array<Record<string, unknown>>) : []

      return [
        '## CXO executive brief',
        '',
        `> ${String(brief?.executive_summary ?? 'Executive summary unavailable.')}`,
        '',
        '### Talking points',
        ...talkingPoints.slice(0, 5).map((item) => `- ${item}`),
        '',
        '### Objections and responses',
        ...objections.slice(0, 3).map((item) => `- **${String(item.objection ?? 'Objection')}** → ${String(item.response ?? '')}`),
      ].join('\n')
    }

    return formatValueForMarkdown(data, nodeId)
  }

  const companyResearchData = (pipelineState?.company_overview ?? null) as Record<string, unknown> | null
  const normalizeDisplayValue = (...values: Array<string | null | undefined>) => {
    const cleaned = values
      .map((value) => typeof value === 'string' ? value.trim() : '')
      .find((value) => value.length > 0 && !['unknown company', 'unknown industry', 'no objective captured yet', 'n/a', 'na'].includes(value.toLowerCase()))

    return cleaned ?? 'Not available'
  }

  const getFirstAvailableValue = (...values: Array<string | null | undefined>) => {
    for (const value of values) {
      if (typeof value === 'string' && value.trim()) {
        const trimmed = value.trim()
        const normalized = trimmed.toLowerCase()
        if (!['unknown company', 'unknown industry', 'no objective captured yet', 'n/a', 'na'].includes(normalized)) {
          return trimmed
        }
      }
    }
    return 'Not available'
  }

  const targetCompany = getFirstAvailableValue(
    dealDetails?.target_company ?? undefined,
    pipelineState?.target_company ?? undefined,
    typeof (companyResearchData as Record<string, unknown> | null)?.company_name === 'string' ? String((companyResearchData as Record<string, unknown>).company_name) : undefined,
    typeof (companyResearchData as Record<string, unknown> | null)?.overview === 'object' && companyResearchData?.overview
      ? String(((companyResearchData.overview as Record<string, unknown>)?.company_name) ?? '')
      : undefined,
  )
  const targetIndustry = getFirstAvailableValue(
    dealDetails?.target_industry ?? undefined,
    pipelineState?.target_industry ?? undefined,
    typeof (companyResearchData as Record<string, unknown> | null)?.industry === 'string' ? String((companyResearchData as Record<string, unknown>).industry) : undefined,
    typeof (companyResearchData as Record<string, unknown> | null)?.overview === 'object' && companyResearchData?.overview
      ? String(((companyResearchData.overview as Record<string, unknown>)?.industry) ?? '')
      : undefined,
  )
  const meetingObjective = getFirstAvailableValue(
    dealDetails?.meeting_objective ?? undefined,
    pipelineState?.meeting_objective ?? undefined,
  )

  const asRecord = (value: unknown): Record<string, unknown> => {
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      return value as Record<string, unknown>
    }
    return {}
  }

  const asArray = (value: unknown): Array<Record<string, unknown>> => {
    if (Array.isArray(value)) {
      return value.filter(Boolean) as Array<Record<string, unknown>>
    }
    return []
  }

  const getSourceTone = (sourceType: string | undefined) => {
    switch (sourceType) {
      case 'FINANCIAL_API':
        return { label: 'Financial Data', badge: 'bg-nagarro-green/10 border-nagarro-green/30 text-nagarro-green', icon: 'database' }
      case 'TAVILY_WEB':
      case 'WEB_SEARCH':
        return { label: 'Web Source', badge: 'bg-cyan-500/10 border-cyan-500/30 text-cyan-300', icon: 'globe' }
      default:
        return { label: String(sourceType ?? 'Source'), badge: 'bg-slate-500/10 border-slate-500/30 text-slate-300', icon: 'link' }
    }
  }

  const listAllCitations = (): Array<Record<string, unknown>> => {
    const citations: Array<Record<string, unknown>> = []
    const seen = new Set<string>()

    const walk = (value: unknown) => {
      if (!value) return
      if (Array.isArray(value)) {
        value.forEach(walk)
        return
      }
      if (typeof value !== 'object') return

      const record = value as Record<string, unknown>
      if (Array.isArray(record.citations)) {
        record.citations.forEach((item) => {
          const citation = item as Record<string, unknown>
          const key = `${String(citation.url ?? citation.title ?? 'citation')}::${String(citation.source_type ?? 'source')}`
          if (!seen.has(key)) {
            seen.add(key)
            citations.push(citation)
          }
        })
      }

      Object.values(record).forEach(walk)
    }

    walk(companyResearchData)
    return citations
  }

  const sourceEntries = listAllCitations()
  const sourceCount = sourceEntries.length
  const financialSourceCount = sourceEntries.filter((item) => String(item.source_type ?? '').toUpperCase() === 'FINANCIAL_API').length
  const webSourceCount = sourceEntries.filter((item) => ['TAVILY_WEB', 'WEB_SEARCH'].includes(String(item.source_type ?? '').toUpperCase())).length

  const renderCitationChips = (citations: unknown, narrativeKey: string) => {
    const list = asArray(citations)
    if (!list.length) return null

    const renderSourceChip = (citation: Record<string, unknown>, index: number) => {
      const sourceType = String(citation.source_type ?? 'SOURCE')
      const badge = getSourceTone(sourceType)
      const key = `${narrativeKey}-${index}-${String(citation.url ?? citation.title ?? 'source')}`
      const chipIsOpen = selectedCitationKey === key
      const domain = typeof citation.url === 'string' && citation.url.trim() ? new URL(citation.url).hostname.replace(/^www\./, '') : 'Source data'

      return (
        <div key={key} className="relative">
          <button
            type="button"
            onClick={() => setSelectedCitationKey(chipIsOpen ? null : key)}
            className="source-chip"
            aria-label={`View citation ${index + 1} for ${citation.title ?? 'source'}`}
          >
            <span className="source-chip-number">[{index + 1}]</span>
            <span className="source-chip-domain">
              <span className="inline-flex items-center gap-1.5">
                {badge.icon === 'database' ? '🗄' : badge.icon === 'globe' ? '🌐' : '🔗'}
                {domain}
              </span>
            </span>
            <span className={`source-chip-badge ${badge.badge}`}>{badge.label}</span>
          </button>

          {chipIsOpen && (
            <div className="source-popover">
              <div className="mb-2 flex items-center justify-between gap-2">
                <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Source {index + 1}</div>
                <button
                  type="button"
                  onClick={() => setSelectedCitationKey(null)}
                  className="text-cosmic-muted hover:text-white"
                  aria-label="Close citation details"
                >
                  ✕
                </button>
              </div>

              <div className="mb-2 text-sm font-semibold text-white">
                {typeof citation.url === 'string' && citation.url.trim() ? (
                  <a href={citation.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-nagarro-green hover:text-nagarro-hover">
                    {String(citation.title ?? 'Source title')}
                    <span aria-hidden="true">↗</span>
                  </a>
                ) : (
                  <span>{String(citation.title ?? 'Source data')}</span>
                )}
                {typeof citation.url === 'string' && citation.url.trim() ? (
                  <span className="mt-1 block text-[11px] text-cosmic-muted">{domain}</span>
                ) : (
                  <span className="mt-1 block text-[11px] text-cosmic-muted">Source data (no public link)</span>
                )}
              </div>

              <div className={`mb-2 inline-flex rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-[0.18em] ${badge.badge}`}>
                {badge.label}
              </div>

              <blockquote className="rounded-xl border border-cosmic-border bg-cosmic-bg/40 p-3 text-sm leading-6 text-cosmic-text">
                <div className="mb-1 text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Excerpt from source</div>
                “{String(citation.snippet ?? citation.summary ?? 'No excerpt available for this source.') }”
              </blockquote>

              {typeof citation.url === 'string' && citation.url.trim() && (
                <a href={citation.url} target="_blank" rel="noopener noreferrer" className="mt-3 inline-flex items-center gap-1 text-xs text-nagarro-green hover:text-nagarro-hover">
                  Open source ↗
                </a>
              )}
            </div>
          )}
        </div>
      )
    }

    return (
      <div className="mt-4 space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Sources ({list.length})</span>
          {list.map(renderSourceChip)}
        </div>
      </div>
    )
  }

  const clampNarrative = (label: string, text: string, key: string) => {
    const isExpanded = Boolean((window as Window & { __companyNarrativeExpanded?: Record<string, boolean> }).__companyNarrativeExpanded?.[key])
    const previewText = text.length > 160 && !isExpanded ? `${text.slice(0, 160)}...` : text

    return (
      <div>
        <p className="text-sm leading-6 text-cosmic-muted whitespace-pre-line break-words">
          {previewText || 'No narrative provided.'}
        </p>
        {text.length > 160 && (
          <button
            type="button"
            className="mt-2 text-xs font-medium text-nagarro-green hover:text-nagarro-hover"
            aria-expanded={isExpanded}
            onClick={() => {
              const map = (window as Window & { __companyNarrativeExpanded?: Record<string, boolean> }).__companyNarrativeExpanded ?? {}
              map[key] = !isExpanded
              ;(window as Window & { __companyNarrativeExpanded?: Record<string, boolean> }).__companyNarrativeExpanded = map
              setSelectedCitationKey((current) => current)
            }}
          >
            {isExpanded ? 'Read less' : 'Read more'}
          </button>
        )}
      </div>
    )
  }

  const overview = asRecord(companyResearchData?.overview)
  const summary = asRecord(overview.summary)
  const businessModel = asRecord(overview.business_model)
  const revenueStreams = asArray(overview.revenue_streams)
  const leadership = asArray(companyResearchData?.leadership_team)
  const initiatives = asArray(companyResearchData?.digital_initiatives)
  const techInvestments = asArray(companyResearchData?.technology_investments)
  const news = asArray(companyResearchData?.recent_news_and_m_and_a)
  const financialData = (pipelineState?.financial_intelligence as Record<string, unknown> | undefined) ?? {}
  const financialMetrics = Array.isArray(financialData.metric_scores)
    ? (financialData.metric_scores as Array<Record<string, unknown>>)
    : []

  const parseOverallScore = (value: unknown) => {
    const raw = String(value ?? '0/10')
    const match = raw.match(/\d+(?:\.\d+)?/)
    return match ? Number(match[0]) : 0
  }

  const getScoreBandColor = (score: number) => {
    if (score >= 80) return '#6EE7B7'
    if (score >= 60) return '#5BC0EB'
    if (score >= 40) return '#FBBF24'
    return '#FB7185'
  }

  const formatMetricValue = (metric: Record<string, unknown>) => {
    const metricName = String(metric.metric_name ?? '')
    const value = metric.value

    if (typeof value === 'number') {
      if (metricName.toLowerCase().includes('growth') || metricName.toLowerCase().includes('margin') || metricName.toLowerCase().includes('return') || metricName.toLowerCase().includes('ratio')) {
        if (Math.abs(value) <= 1) {
          return `${(value * 100).toFixed(1)}%`
        }
      }

      if (Math.abs(value) >= 1_000_000_000) {
        return `$${(value / 1_000_000_000).toFixed(2)}B`
      }
      if (Math.abs(value) >= 1_000_000) {
        return `$${(value / 1_000_000).toFixed(2)}M`
      }
      if (Math.abs(value) >= 1_000) {
        return `$${(value / 1_000).toFixed(2)}K`
      }
      return Number.isInteger(value) ? String(value) : value.toFixed(2)
    }

    return typeof value === 'string' ? value : 'N/A'
  }

  const getMetricIcon = (metricName: string) => {
    const normalized = metricName.toLowerCase()
    if (normalized.includes('revenue')) return <TrendingUp className="h-4 w-4" />
    if (normalized.includes('margin')) return <BarChart3 className="h-4 w-4" />
    if (normalized.includes('debt')) return <Landmark className="h-4 w-4" />
    if (normalized.includes('return') || normalized.includes('equity')) return <Gauge className="h-4 w-4" />
    if (normalized.includes('cash') || normalized.includes('free')) return <DollarSign className="h-4 w-4" />
    if (normalized.includes('price') || normalized.includes('pe')) return <Activity className="h-4 w-4" />
    return <ShieldAlert className="h-4 w-4" />
  }

  const stakeholderPanel = (() => {
    const stakeholderData = asRecord(pipelineState?.stakeholder_intelligence ?? getNodeAliasValue('stakeholder_intel'))
    const personas = Array.isArray(stakeholderData.personas)
      ? (stakeholderData.personas as Array<Record<string, unknown>>)
      : []

    const personaRoleDisplay = (role: string) => {
      const normalized = role.toUpperCase()
      const fullNames: Record<string, string> = {
        CEO: 'Chief Executive Officer',
        CFO: 'Chief Financial Officer',
        CTO: 'Chief Technology Officer',
        CIO: 'Chief Information Officer',
        CISO: 'Chief Information Security Officer',
        CDO: 'Chief Data Officer',
      }
      return `${normalized} - ${fullNames[normalized] ?? humanizeLabel(normalized)}`
    }

    const selectedPersona = personas.find((person) => String(person.role ?? '').toUpperCase() === selectedStakeholderRole.toUpperCase()) ?? personas[0] ?? null

    if (!personas.length) {
      return (
        <div className="cosmic-card p-5 md:p-6 text-sm text-cosmic-muted">
          Stakeholder intelligence is not available yet.
        </div>
      )
    }

    const renderList = (items: unknown[], tone: 'green' | 'amber' | 'cyan') => {
      const list = Array.isArray(items) ? items.filter((item): item is string => typeof item === 'string' && item.trim().length > 0) : []
      const accentClass = tone === 'green'
        ? 'border-nagarro-green/30 bg-nagarro-green/10 text-nagarro-green'
        : tone === 'amber'
          ? 'border-amber-500/30 bg-amber-500/10 text-amber-300'
          : 'border-cyan-500/30 bg-cyan-500/10 text-cyan-300'

      return (
        <div className="space-y-2">
          {list.length ? list.map((item, index) => (
            <div key={`${tone}-${item}-${index}`} className="flex items-start gap-3 rounded-xl border border-cosmic-border bg-cosmic-bg/40 p-3">
              <div className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border ${accentClass}`}>
                <span className="text-[10px] font-bold">•</span>
              </div>
              <p className="text-sm leading-6 text-cosmic-muted">{item}</p>
            </div>
          )) : (
            <div className="rounded-xl border border-cosmic-border bg-cosmic-bg/40 p-3 text-sm text-cosmic-muted">
              No data captured for this section.
            </div>
          )}
        </div>
      )
    }

    if (stakeholderCompareMode) {
      return (
        <div className="space-y-6">
          <div className="cosmic-card p-5 md:p-6">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-violet-500/30 bg-violet-500/10 text-violet-300">
                  <BarChart3 className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Stakeholders</div>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <h3 className="text-2xl font-bold text-white">Compare stakeholder priorities</h3>
                    <span className="inline-flex items-center rounded-full border border-nagarro-green/30 bg-nagarro-green/10 px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-nagarro-green">
                      AI-generated
                    </span>
                  </div>
                </div>
              </div>

              <button
                type="button"
                onClick={() => setStakeholderCompareMode(false)}
                className="rounded-full border border-cosmic-border bg-cosmic-bg/40 px-3 py-1.5 text-[10px] uppercase tracking-[0.12em] text-cosmic-muted hover:text-white"
              >
                Back to persona
              </button>
            </div>
          </div>

          <div className="cosmic-card overflow-hidden p-0">
            <div className="overflow-x-auto">
              <table className="min-w-full border-separate border-spacing-0 text-left">
                <thead>
                  <tr>
                    <th className="border-b border-r border-cosmic-border bg-cosmic-bg/50 px-4 py-3 text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">
                      Theme
                    </th>
                    {personas.map((person) => (
                      <th key={String(person.role ?? 'role')} className="border-b border-r border-cosmic-border bg-cosmic-bg/50 px-4 py-3 text-left">
                        <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">{String(person.role ?? 'Role')}</div>
                        <div className="mt-1 text-sm font-semibold text-white">{personaRoleDisplay(String(person.role ?? 'Role'))}</div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[
                    { key: 'likely_goals', label: 'Likely Goals', accent: 'green' },
                    { key: 'likely_concerns', label: 'Likely Concerns', accent: 'amber' },
                    { key: 'business_drivers', label: 'Business Drivers', accent: 'cyan' },
                  ].map((row) => (
                    <tr key={row.key}>
                      <td className="border-b border-r border-cosmic-border bg-cosmic-bg/30 px-4 py-4 align-top text-sm font-semibold text-white">
                        {row.label}
                      </td>
                      {personas.map((person) => {
                        const items = Array.isArray(person[row.key as keyof typeof person])
                          ? (person[row.key as keyof typeof person] as unknown[]).filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
                          : []
                        return (
                          <td key={`${String(person.role ?? 'role')}-${row.key}`} className="border-b border-r border-cosmic-border bg-cosmic-bg/20 px-4 py-4 align-top">
                            <ul className="space-y-2 text-sm leading-6 text-cosmic-muted">
                              {items.length ? items.map((item, index) => (
                                <li key={`${row.key}-${String(person.role ?? 'role')}-${index}`} className="flex items-start gap-2">
                                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-nagarro-green" />
                                  <span>{item}</span>
                                </li>
                              )) : <li className="text-cosmic-muted">—</li>}
                            </ul>
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )
    }

    return (
      <div className="space-y-6">
        <div className="cosmic-card p-5 md:p-6">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-violet-500/30 bg-violet-500/10 text-violet-300">
                <BarChart3 className="h-5 w-5" />
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Stakeholder intelligence</div>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <h3 className="text-2xl font-bold text-white">Who do we talk to and what do they care about?</h3>
                  <span className="inline-flex items-center rounded-full border border-nagarro-green/30 bg-nagarro-green/10 px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-nagarro-green">
                    AI-generated
                  </span>
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={() => setStakeholderCompareMode(true)}
              className="rounded-full border border-cosmic-border bg-cosmic-bg/40 px-3 py-1.5 text-[10px] uppercase tracking-[0.12em] text-cosmic-muted hover:text-white"
            >
              Compare
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-5 xl:grid-cols-[0.8fr_1.2fr]">
          <div className="cosmic-card p-4 md:p-5">
            <div className="mb-4 flex items-center justify-between gap-2">
              <div>
                <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Persona list</div>
                <h4 className="mt-1 text-lg font-bold text-white">Executive map</h4>
              </div>
            </div>

            <div className="space-y-2">
              {personas.map((person) => {
                const role = String(person.role ?? 'Role')
                const isSelected = selectedPersona && String(selectedPersona.role ?? '').toUpperCase() === role.toUpperCase()
                return (
                  <button
                    key={role}
                    type="button"
                    onClick={() => setSelectedStakeholderRole(role)}
                    className={`w-full rounded-2xl border p-3 text-left transition-all ${
                      isSelected
                        ? 'border-violet-500/40 bg-violet-500/10 text-white'
                        : 'border-cosmic-border bg-cosmic-bg/40 text-cosmic-muted hover:text-white'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-xs font-semibold uppercase tracking-[0.12em] text-violet-300">{role}</span>
                      <span className="text-[10px] uppercase tracking-[0.12em] text-cosmic-muted">{role === 'CEO' ? 'Leader' : role === 'CFO' ? 'Finance' : role === 'CTO' ? 'Technology' : role === 'CIO' ? 'IT' : role === 'CISO' ? 'Security' : 'Data'}</span>
                    </div>
                    <div className="mt-2 text-sm font-medium">{personaRoleDisplay(role)}</div>
                  </button>
                )
              })}
            </div>
          </div>

          <div className="cosmic-card p-5 md:p-6">
            {selectedPersona ? (
              <>
                <div className="mb-5 flex items-center justify-between gap-3">
                  <div>
                    <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Selected persona</div>
                    <h4 className="mt-1 text-2xl font-bold text-white">{personaRoleDisplay(String(selectedPersona.role ?? 'Role'))}</h4>
                  </div>
                  <span className="inline-flex items-center rounded-full border border-violet-500/30 bg-violet-500/10 px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-violet-300">
                    {String(selectedPersona.role ?? 'Role')}
                  </span>
                </div>

                <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
                  <div className="rounded-2xl border border-nagarro-green/30 bg-nagarro-green/10 p-4">
                    <div className="mb-3 flex items-center gap-2">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full border border-nagarro-green/30 bg-nagarro-green/10 text-nagarro-green">
                        <CheckCircle2 className="h-4 w-4" />
                      </div>
                      <h5 className="text-sm font-semibold uppercase tracking-[0.12em] text-nagarro-green">Likely Goals</h5>
                    </div>
                    {renderList(Array.isArray(selectedPersona.likely_goals) ? selectedPersona.likely_goals as string[] : [], 'green')}
                  </div>

                  <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4">
                    <div className="mb-3 flex items-center gap-2">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full border border-amber-500/30 bg-amber-500/10 text-amber-300">
                        <AlertTriangle className="h-4 w-4" />
                      </div>
                      <h5 className="text-sm font-semibold uppercase tracking-[0.12em] text-amber-300">Likely Concerns</h5>
                    </div>
                    {renderList(Array.isArray(selectedPersona.likely_concerns) ? selectedPersona.likely_concerns as string[] : [], 'amber')}
                  </div>

                  <div className="rounded-2xl border border-cyan-500/30 bg-cyan-500/10 p-4">
                    <div className="mb-3 flex items-center gap-2">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full border border-cyan-500/30 bg-cyan-500/10 text-cyan-300">
                        <TrendingUp className="h-4 w-4" />
                      </div>
                      <h5 className="text-sm font-semibold uppercase tracking-[0.12em] text-cyan-300">Business Drivers</h5>
                    </div>
                    {renderList(Array.isArray(selectedPersona.business_drivers) ? selectedPersona.business_drivers as string[] : [], 'cyan')}
                  </div>
                </div>
              </>
            ) : (
              <div className="text-sm text-cosmic-muted">No stakeholder profile available yet.</div>
            )}
          </div>
        </div>
      </div>
    )
  })()

  const companyResearchPanel = (() => {
    const hasCoreDealMetadata =
      targetCompany !== 'Not available' ||
      targetIndustry !== 'Not available' ||
      meetingObjective !== 'Not available'

    if (!companyResearchData && !hasCoreDealMetadata) {
      return (
        <div className="space-y-4">
          <div className="cosmic-card p-6">
            <p className="text-sm text-cosmic-muted">Company research data is not available yet.</p>
          </div>
        </div>
      )
    }

    const renderSectionCard = (title: string, accent: string, children: React.ReactNode, icon: string) => (
      <div className={`cosmic-card ${accent} p-5 md:p-6`}>
        <div className="mb-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-cosmic-border bg-cosmic-bg/40 text-base shadow-sm">
              {icon}
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Profile</div>
              <h3 className="mt-1 text-xl font-bold text-white">{title}</h3>
            </div>
          </div>
        </div>
        {children}
      </div>
    )

    const overviewNarrative = String((summary as Record<string, unknown>)?.detailed_narrative ?? (overview as Record<string, unknown>)?.summary ?? '')
    const businessNarrative = String((businessModel as Record<string, unknown>)?.detailed_narrative ?? '')
    const companyHeadquarters = String((companyResearchData?.headquarters ?? 'Not disclosed') || 'Not disclosed')
    const employeeCount = String((companyResearchData?.employee_count_estimate ?? 'Not disclosed') || 'Not disclosed')

    const financialSnippet = String((companyResearchData as Record<string, unknown>)?.financial_overview ?? '')
    const parseFinancialKpis = () => {
      const match = financialSnippet.match(/Market Cap[:\s]*INR\s*([0-9.,\s]+(?:lakh|crore|thousand|million|billion)?)|Market Cap[:\s]*([0-9.,\s]+(?:lakh|crore|thousand|million|billion)?)/i)
      const revenueMatch = financialSnippet.match(/Total Revenue[:\s]*INR\s*([0-9.,\s]+(?:lakh|crore|thousand|million|billion)?)|Total Revenue[:\s]*([0-9.,\s]+(?:lakh|crore|thousand|million|billion)?)/i)
      const growthMatch = financialSnippet.match(/Revenue Growth[:\s]*([0-9.,%\s]+(?:%|percent)?)/i)
      const marginMatch = financialSnippet.match(/Operating Margin[:\s]*([0-9.,%\s]+(?:%|percent)?)/i)
      const scoreMatch = financialSnippet.match(/Quality Score[:\s]*([0-9]+\s*\/\s*[0-9]+)/i)

      return {
        marketCap: match ? match[1] || match[2] || 'N/A' : null,
        totalRevenue: revenueMatch ? revenueMatch[1] || revenueMatch[2] || 'N/A' : null,
        revenueGrowth: growthMatch ? growthMatch[1]?.trim() : null,
        operatingMargin: marginMatch ? marginMatch[1]?.trim() : null,
        qualityScore: scoreMatch ? scoreMatch[1]?.trim() : null,
      }
    }

    const kpis = parseFinancialKpis()
    const hasKpiData = Object.values(kpis).some(Boolean)

    return (
      <div className="space-y-6 pb-4">
        <div className="cosmic-card sticky top-4 z-10 p-4 md:p-5">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2 text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">
                <span className="inline-flex items-center gap-1 rounded-full border border-nagarro-green/40 bg-nagarro-green/10 px-2 py-0.5 text-nagarro-green">Company Intelligence</span>
                <span className="inline-flex items-center gap-1">
                  <span aria-hidden="true">📍</span>
                  {companyHeadquarters}
                </span>
              </div>
              <h2 className="mt-3 bg-gradient-to-r from-nagarro-green via-nagarro-green to-cyan-300 bg-clip-text text-2xl font-bold tracking-tight text-transparent md:text-3xl">
                {targetCompany}
              </h2>
            </div>

            <div className="flex flex-col gap-2 md:flex-row md:items-center">
              <button
                type="button"
                onClick={() => setSourceDrawerOpen(true)}
                className="btn-nagarro"
              >
                All Sources
              </button>
            </div>
          </div>

          <div className="mt-4 flex flex-col gap-3 border-t border-cosmic-border pt-4 md:flex-row md:items-center md:justify-between">
            <div className="flex flex-wrap items-center gap-2 text-xs text-cosmic-muted">
              <span className="inline-flex items-center gap-1 rounded-full border border-cosmic-border bg-cosmic-bg/40 px-2 py-1">{sourceCount} total sources</span>
              <span className="inline-flex items-center gap-1 rounded-full border border-cosmic-border bg-cosmic-bg/40 px-2 py-1">{financialSourceCount} Financial API</span>
              <span className="inline-flex items-center gap-1 rounded-full border border-cosmic-border bg-cosmic-bg/40 px-2 py-1">{webSourceCount} Web</span>
              <span className="text-nagarro-green">All insights are traceable to the cited sources.</span>
            </div>

            <label className="flex min-w-[220px] max-w-[320px] items-center gap-2 rounded-xl border border-cosmic-border bg-cosmic-bg/40 px-3 py-2 text-sm text-cosmic-muted">
              <span aria-hidden="true">⌕</span>
              <input
                type="text"
                placeholder="Filter within company profile"
                className="w-full border-0 bg-transparent text-sm text-white placeholder:text-cosmic-muted focus:outline-none"
                aria-label="Filter company profile"
              />
            </label>
          </div>
        </div>

        <div className="flex gap-2 overflow-x-auto pb-1 [scrollbar-width:none] [-ms-overflow-style:none]">
          {[
            ['overview', 'Overview'],
            ['business', 'Business Model & Revenue'],
            ['leadership', 'Leadership'],
            ['digital', 'Digital Initiatives'],
            ['technology', 'Technology'],
            ['news', 'News & M&A'],
          ].map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => setIntelTab(id as typeof intelTab)}
              className={`company-intel-tab ${intelTab === id ? 'active' : ''}`}
            >
              {label}
            </button>
          ))}
        </div>

        {intelTab === 'overview' && (
          <div className="space-y-6">
            <div className="cosmic-card p-5 md:p-6">
              <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
                <div className="flex-1">
                  <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Executive summary</div>
                  <h3 className="mt-3 bg-gradient-to-r from-nagarro-green via-nagarro-green to-cyan-300 bg-clip-text text-3xl font-bold text-transparent">
                    {targetCompany}
                  </h3>
                  <p className="mt-4 max-w-3xl text-base leading-7 text-cosmic-muted">
                    {overviewNarrative || 'No executive summary is available for this company profile yet.'}
                  </p>
                  {renderCitationChips(summary.citations ?? overview.citations ?? [], 'overview-summary')}
                </div>

                <div className="min-w-[220px] rounded-2xl border border-cosmic-border bg-cosmic-bg/40 p-4 md:w-[260px]">
                  <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Meeting objective</div>
                  <div className="mt-2 text-sm font-medium leading-6 text-white">{meetingObjective}</div>
                  <div className="mt-4 text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Industry</div>
                  <div className="mt-2 text-sm font-medium text-nagarro-green">{targetIndustry}</div>
                </div>
              </div>
            </div>

            {hasKpiData && (
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5">
                {[
                  { label: 'Market Cap', value: kpis.marketCap ? `INR ${kpis.marketCap}` : 'N/A', accent: 'bg-nagarro-green/10 text-nagarro-green border-nagarro-green/30', icon: '💰' },
                  { label: 'Total Revenue', value: kpis.totalRevenue ? `INR ${kpis.totalRevenue}` : 'N/A', accent: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30', icon: '📊' },
                  { label: 'Revenue Growth', value: kpis.revenueGrowth ? `${kpis.revenueGrowth}` : 'N/A', accent: 'bg-violet-500/10 text-violet-300 border-violet-500/30', icon: '📈' },
                  { label: 'Operating Margin', value: kpis.operatingMargin ? `${kpis.operatingMargin}` : 'N/A', accent: 'bg-amber-500/10 text-amber-300 border-amber-500/30', icon: '⚖' },
                  { label: 'Quality Score', value: kpis.qualityScore || 'N/A', accent: 'bg-slate-500/10 text-slate-300 border-slate-500/30', icon: '★' },
                ].map((item) => (
                  <div key={item.label} className={`rounded-2xl border p-4 ${item.accent}`}>
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">{item.label}</div>
                      <span className="text-xl" aria-hidden="true">{item.icon}</span>
                    </div>
                    <div className="mt-3 text-xl font-bold tracking-tight text-white tabular-nums">{item.value}</div>
                  </div>
                ))}
              </div>
            )}

          </div>
        )}

        {intelTab === 'business' && (
          <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
            {renderSectionCard('Business model', 'border-l border-l-nagarro-green/80', (
              <>
                <div className="text-lg font-semibold text-white">{String((businessModel as Record<string, unknown>)?.headline ?? 'Business model')}</div>
                <p className="mt-3 text-sm leading-6 text-cosmic-muted">{String((businessModel as Record<string, unknown>)?.detailed_narrative ?? 'No business model narrative provided.')}</p>
                {renderCitationChips((businessModel as Record<string, unknown>)?.citations ?? [], 'business-model-detailed')}
              </>
            ), '🏢')}

            {renderSectionCard('Revenue mix', 'border-l border-l-cyan-400/80', (
              <div className="space-y-3">
                {revenueStreams.length ? revenueStreams.map((stream, index) => (
                  <div key={`${String(stream.headline ?? 'stream')}-${index}`} className="rounded-xl border border-cosmic-border bg-cosmic-bg/40 p-3">
                    <div className="flex items-center justify-between gap-3">
                      <div className="font-semibold text-white">{String(stream.headline ?? 'Revenue stream')}</div>
                      <span className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">{String(stream.category ?? 'Core')}</span>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-cosmic-muted">{String(stream.detailed_narrative ?? '')}</p>
                    {renderCitationChips(stream.citations ?? [], `revenue-mix-${index}`)}
                  </div>
                )) : <p className="text-sm text-cosmic-muted">No revenue stream data is available.</p>}
              </div>
            ), '📊')}
          </div>
        )}

        {intelTab === 'leadership' && (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {leadership.length ? leadership.map((person, index) => {
              const personRecord = asRecord(person)
              const initials = String(personRecord.name ?? 'LM').split(' ').slice(0, 2).map((part) => part[0] ?? '').join('').toUpperCase() || 'LM'
              const palette = ['from-nagarro-green/80 to-cyan-400/70', 'from-cyan-500/80 to-violet-500/70', 'from-violet-500/80 to-nagarro-green/70', 'from-amber-500/80 to-nagarro-green/70']
              return (
                <div key={`${String(personRecord.name ?? 'leader')}-${index}`} className="cosmic-card border-l border-l-violet-400/80 p-5">
                  <div className="flex items-start gap-4">
                    <div className={`flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br ${palette[index % palette.length]} text-sm font-bold text-white`}>
                      {initials}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="text-lg font-bold text-white">{String(personRecord.name ?? 'Leadership member')}</div>
                      <div className="mt-1 text-sm text-nagarro-green">{String(personRecord.role ?? 'Role unavailable')}</div>
                    </div>
                  </div>
                  <p className="mt-4 text-sm leading-6 text-cosmic-muted">{String(personRecord.background ?? 'No background provided.')}</p>
                </div>
              )
            }) : <div className="cosmic-card p-5 text-sm text-cosmic-muted">Leadership data is not available.</div>}
          </div>
        )}

        {intelTab === 'digital' && (
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            {initiatives.length ? initiatives.map((initiative, index) => {
              const item = asRecord(initiative)
              const status = String(item.status ?? 'Planned').toLowerCase()
              const priority = String(item.perceived_priority ?? 'MEDIUM').toUpperCase()
              const statusClass = status.includes('complete') ? 'border-nagarro-green/30 bg-nagarro-green/10 text-nagarro-green' : status.includes('progress') ? 'border-amber-500/30 bg-amber-500/10 text-amber-300' : 'border-cyan-500/30 bg-cyan-500/10 text-cyan-300'
              const priorityClass = priority === 'HIGH' ? 'border-rose-500/30 bg-rose-500/10 text-rose-300' : priority === 'MEDIUM' ? 'border-amber-500/30 bg-amber-500/10 text-amber-300' : 'border-slate-500/30 bg-slate-500/10 text-slate-300'

              return (
                <div key={`${String(item.initiative_name ?? 'initiative')}-${index}`} className="cosmic-card border-l border-l-violet-400/80 p-5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="text-lg font-semibold text-white">{String(item.initiative_name ?? 'Initiative')}</div>
                    <div className="flex gap-2">
                      <span className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-[0.18em] ${statusClass}`}>{String(item.status ?? 'Planned')}</span>
                      <span className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-[0.18em] ${priorityClass}`}>{priority}</span>
                    </div>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-cosmic-muted">{String((item.description as Record<string, unknown>)?.detailed_narrative ?? item.description ?? 'No description available.')}</p>
                  {renderCitationChips(item.citations ?? [], `digital-${index}`)}
                </div>
              )
            }) : <div className="cosmic-card p-5 text-sm text-cosmic-muted">No digital initiatives data available.</div>}
          </div>
        )}

        {intelTab === 'technology' && (
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            {techInvestments.length ? techInvestments.map((item, index) => {
              const entry = asRecord(item)
              const category = String(entry.category ?? 'Other')
              const kindClass = category.toLowerCase().includes('cloud') ? 'border-cyan-500/30 bg-cyan-500/10 text-cyan-300' : category.toLowerCase().includes('ai') || category.toLowerCase().includes('ml') ? 'border-violet-500/30 bg-violet-500/10 text-violet-300' : 'border-slate-500/30 bg-slate-500/10 text-slate-300'
              return (
                <div key={`${String(entry.technology_stack ?? 'technology')}-${index}`} className="cosmic-card border-l border-l-cyan-400/80 p-5">
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-lg font-semibold text-white">{String(entry.technology_stack ?? 'Technology stack')}</div>
                    <span className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-[0.18em] ${kindClass}`}>{category}</span>
                  </div>
                  <div className="mt-3 text-sm text-cosmic-muted">
                    <span className="text-cosmic-muted">Vendor / Tool:</span>{' '}
                    <span className="text-white">{String(entry.vendor_or_tool ?? 'Not disclosed')}</span>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-cosmic-muted">{String((entry.details as Record<string, unknown>)?.detailed_narrative ?? 'No details provided.')}</p>
                  {renderCitationChips(entry.citations ?? [], `technology-${index}`)}
                </div>
              )
            }) : <div className="cosmic-card p-5 text-sm text-cosmic-muted">No technology investments data available.</div>}
          </div>
        )}

        {intelTab === 'news' && (
          <div className="cosmic-card p-5 md:p-6">
            <div className="relative space-y-5 before:absolute before:left-[10px] before:top-2 before:h-[calc(100%-0.75rem)] before:w-px before:bg-cosmic-border">
              {news.length ? news.map((story, index) => {
                const item = asRecord(story)
                const category = String(item.category ?? 'Update')
                const categoryClass = category.toLowerCase().includes('acquisition') ? 'border-violet-500/30 bg-violet-500/10 text-violet-300' : category.toLowerCase().includes('partnership') ? 'border-nagarro-green/30 bg-nagarro-green/10 text-nagarro-green' : category.toLowerCase().includes('investment') ? 'border-cyan-500/30 bg-cyan-500/10 text-cyan-300' : 'border-amber-500/30 bg-amber-500/10 text-amber-300'
                return (
                  <div key={`${String(item.headline ?? 'news')}-${index}`} className="relative pl-8">
                    <div className="absolute left-0 top-2 h-5 w-5 rounded-full border border-nagarro-green/40 bg-nagarro-green/20 shadow-[0_0_18px_rgba(110,231,183,0.4)]" />
                    <div className="rounded-2xl border border-cosmic-border bg-cosmic-bg/40 p-4">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="text-lg font-semibold text-white">{String(item.headline ?? 'News headline')}</div>
                        <span className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-[0.18em] ${categoryClass}`}>{category}</span>
                      </div>
                      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-cosmic-muted">
                        <span>{String(item.date_or_period ?? item.date ?? 'Date not disclosed')}</span>
                        <span>•</span>
                        <span>{String(item.source ?? 'Source not disclosed')}</span>
                      </div>
                      <p className="mt-3 text-sm leading-6 text-cosmic-muted">{String((item.details as Record<string, unknown>)?.detailed_narrative ?? item.summary ?? 'No narrative provided.')}</p>
                      {renderCitationChips(item.citations ?? [], `news-${index}`)}
                    </div>
                  </div>
                )
              }) : <div className="text-sm text-cosmic-muted">No recent news or M&A data available.</div>}
            </div>
          </div>
        )}

        {sourceDrawerOpen && (
          <div className="fixed inset-0 z-50 flex items-end justify-end bg-black/50 backdrop-blur-sm md:items-stretch">
            <div className="cosmic-card h-full w-full max-w-xl overflow-auto rounded-l-2xl rounded-r-none border-l border-l-nagarro-green/60 p-0" aria-label="All sources drawer">
              <div className="flex items-center justify-between border-b border-cosmic-border px-5 py-4">
                <div>
                  <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Provenance</div>
                  <h3 className="mt-1 text-xl font-bold text-white">All Sources</h3>
                </div>
                <button type="button" onClick={() => setSourceDrawerOpen(false)} className="text-cosmic-muted hover:text-white" aria-label="Close sources drawer">
                  ✕
                </button>
              </div>

              <div className="space-y-4 p-5">
                {sourceEntries.length ? Object.entries(
                  sourceEntries.reduce<Record<string, Array<Record<string, unknown>>>>((groups, item) => {
                    const sourceType = String(item.source_type ?? 'SOURCE')
                    groups[sourceType] = groups[sourceType] ?? []
                    groups[sourceType].push(item)
                    return groups
                  }, {})
                ).map(([type, items]) => (
                  <div key={type} className="rounded-2xl border border-cosmic-border bg-cosmic-bg/40 p-4">
                    <div className="mb-3 flex items-center justify-between gap-3">
                      <div className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-[0.18em] ${getSourceTone(type).badge}`}>
                        {getSourceTone(type).label}
                      </div>
                      <span className="text-xs text-cosmic-muted">{items.length} claims</span>
                    </div>
                    <div className="space-y-3">
                      {items.map((item, index) => (
                        <div key={`${String(item.url ?? item.title ?? 'source')}-${index}`} className="rounded-xl border border-cosmic-border bg-cosmic-bg/30 p-3">
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0 flex-1">
                              <div className="text-sm font-semibold text-white">
                                {typeof item.url === 'string' && item.url.trim() ? (
                                  <a href={item.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-nagarro-green hover:text-nagarro-hover">
                                    {String(item.title ?? 'Source title')}
                                    <span aria-hidden="true">↗</span>
                                  </a>
                                ) : (
                                  <span>{String(item.title ?? 'Source data')}</span>
                                )}
                              </div>
                              {typeof item.url === 'string' && item.url.trim() ? (
                                <div className="mt-1 text-[11px] text-cosmic-muted">{new URL(item.url).hostname.replace(/^www\./, '')}</div>
                              ) : (
                                <div className="mt-1 text-[11px] text-cosmic-muted">Source data (no public link)</div>
                              )}
                            </div>
                          </div>
                          <blockquote className="mt-2 rounded-lg border border-cosmic-border bg-cosmic-bg/20 p-2 text-xs leading-5 text-cosmic-muted">
                            “{String(item.snippet ?? 'No excerpt available.') }”
                          </blockquote>
                        </div>
                      ))}
                    </div>
                  </div>
                )) : <div className="rounded-2xl border border-cosmic-border bg-cosmic-bg/40 p-5 text-sm text-cosmic-muted">No citation metadata available for this company profile.</div>}
              </div>
            </div>
          </div>
        )}
      </div>
    )
  })()

  const financialPanel = (() => {
    const overallScoreValue = parseOverallScore(financialData.overall_score_10)
    const overallPercent = Math.min(100, Math.max(0, overallScoreValue * 10))
    const overallColor = overallPercent >= 80 ? '#6EE7B7' : overallPercent >= 60 ? '#5BC0EB' : overallPercent >= 40 ? '#FBBF24' : '#FB7185'
    const radarData = financialMetrics.slice(0, 8).map((metric) => ({
      label: String(metric.metric_name ?? 'Metric'),
      score: Number(metric.score_100 ?? 0),
    }))
    const sortedMetrics = [...financialMetrics].sort((left, right) => Number(right.score_100 ?? 0) - Number(left.score_100 ?? 0))
    const concerns = Array.isArray(financialData.financial_concerns)
      ? (financialData.financial_concerns as string[]).filter((item) => typeof item === 'string' && item.trim())
      : []

    return (
      <div className="space-y-6">
        <div className="cosmic-card p-5 md:p-6">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-cyan-500/30 bg-cyan-500/10 text-cyan-300">
                <BarChart3 className="h-5 w-5" />
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Financial intelligence</div>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <h3 className="text-2xl font-bold text-white">{String(financialData.company_name ?? targetCompany)}</h3>
                  <span className="inline-flex items-center rounded-full border border-cosmic-border bg-cosmic-bg/40 px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-cosmic-muted">
                    {String(financialData.symbol ?? 'N/A')}
                  </span>
                  <span className="inline-flex items-center rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-cyan-300">
                    {String(financialData.market_cap_category ?? 'Unknown')}
                  </span>
                  <span className="inline-flex items-center rounded-full border border-nagarro-green/30 bg-nagarro-green/10 px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-nagarro-green">
                    {String(financialData.status ?? 'not_listed')}
                  </span>
                  <span className="inline-flex items-center rounded-full border border-cosmic-border bg-cosmic-bg/40 px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-cosmic-muted">
                    {String(financialData.availability ?? 'unavailable')}
                  </span>
                  <span className="inline-flex items-center rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-cyan-300">
                    Source: {String(financialData.data_source ?? 'yfinance')}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-[0.9fr_1.1fr]">
          <div className="cosmic-card p-5 md:p-6">
            <div className="mx-auto flex max-w-[260px] flex-col items-center justify-center">
              <div className="relative h-40 w-40">
                <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90">
                  <circle cx="60" cy="60" r="46" stroke="rgba(148,163,184,0.18)" strokeWidth="12" fill="transparent" />
                  <circle
                    cx="60"
                    cy="60"
                    r="46"
                    stroke={overallColor}
                    strokeWidth="12"
                    strokeLinecap="round"
                    fill="transparent"
                    strokeDasharray={289}
                    strokeDashoffset={289 - (289 * overallPercent) / 100}
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                  <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Overall score</div>
                  <div className="mt-1 text-4xl font-bold leading-none text-white" style={{ color: overallColor }}>{overallScoreValue.toFixed(1)}</div>
                  <div className="mt-1 text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">/ 10</div>
                </div>
              </div>
              <p className="mt-5 text-sm leading-6 text-cosmic-muted text-center">{String(financialData.ai_summary ?? 'No financial summary available.')}</p>
            </div>
          </div>

          <div className="cosmic-card p-5 md:p-6">
            <div className="mb-4 flex items-center justify-between gap-2">
              <div>
                <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Performance profile</div>
                <h4 className="mt-1 text-lg font-bold text-white">Metric score radar</h4>
              </div>
              <span className="rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-cyan-300">0-100</span>
            </div>
            <div className="h-[260px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData} outerRadius="72%">
                  <PolarGrid stroke="rgba(148,163,184,0.3)" />
                  <PolarAngleAxis dataKey="label" tick={{ fill: '#D3DCE5', fontSize: 11 }} />
                  <PolarRadiusAxis domain={[0, 100]} tickCount={5} tick={{ fill: '#8BA0B3', fontSize: 10 }} />
                  <Radar dataKey="score" stroke="#6EE7B7" fill="#6EE7B7" fillOpacity={0.2} />
                  <Tooltip
                    formatter={(value) => [`${Number(value).toFixed(0)}/100`, 'Score']}
                    contentStyle={{
                      backgroundColor: '#0B1220',
                      border: '1px solid rgba(110, 231, 183, 0.25)',
                      borderRadius: '12px',
                      color: '#E5F9F0',
                    }}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {financialMetrics.map((metric, index) => {
            const score = Number(metric.score_100 ?? 0)
            const score10 = parseOverallScore(metric.score_10)
            const accent = score >= 80 ? 'border-nagarro-green/50 bg-nagarro-green/5' : score >= 60 ? 'border-cyan-500/40 bg-cyan-500/5' : score >= 40 ? 'border-amber-500/40 bg-amber-500/5' : 'border-rose-500/40 bg-rose-500/5'
            const valueText = typeof metric.value === 'number'
              ? Number(metric.value).toLocaleString(undefined, { maximumFractionDigits: 2 })
              : typeof metric.value === 'string' ? metric.value : 'N/A'

            return (
              <div key={`${String(metric.metric_name ?? 'metric')}-${index}`} className={`rounded-2xl border p-4 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_0_20px_rgba(110,231,183,0.12)] ${accent}`}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Metric</div>
                    <div className="mt-2 text-lg font-bold text-white">{String(metric.metric_name ?? 'Metric')}</div>
                  </div>
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-cosmic-border bg-cosmic-bg/40 text-nagarro-green">
                    {getMetricIcon(String(metric.metric_name ?? 'Metric'))}
                  </div>
                </div>

                <div className="mt-4 text-2xl font-bold tracking-tight text-white tabular-nums">{valueText}</div>

                <div className="mt-3 flex items-center justify-between gap-3">
                  <span className="inline-flex rounded-full border border-cosmic-border bg-cosmic-bg/40 px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-cosmic-muted">
                    {score}/100 · {Number.isFinite(score10) ? `${score10}/10` : 'N/A'}
                  </span>
                  <span className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">{String(metric.status ?? 'available')}</span>
                </div>

                <div className="mt-4 h-1.5 w-full overflow-hidden rounded-full bg-cosmic-bg/60">
                  <div className="h-full rounded-full" style={{ width: `${Math.min(100, Math.max(0, score))}%`, backgroundColor: getScoreBandColor(score) }} />
                </div>

                <p className="mt-3 text-sm leading-6 text-cosmic-muted">{String(metric.rationale ?? 'No rationale available.')}</p>
              </div>
            )
          })}
        </div>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <div className="cosmic-card p-5 md:p-6">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Performance ranking</div>
                <h4 className="mt-1 text-lg font-bold text-white">Metric score comparison</h4>
              </div>
              <span className="inline-flex items-center rounded-full border border-cosmic-border bg-cosmic-bg/40 px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-cosmic-muted">Sorted descending</span>
            </div>

            <div className="h-[280px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={sortedMetrics.map((metric) => ({ name: String(metric.metric_name ?? 'Metric'), value: Number(metric.score_100 ?? 0) }))} margin={{ top: 10, right: 10, left: 0, bottom: 24 }}>
                  <CartesianGrid stroke="rgba(148,163,184,0.18)" vertical={false} />
                  <XAxis dataKey="name" tick={{ fill: '#D3DCE5', fontSize: 10 }} interval={0} angle={-18} textAnchor="end" height={48} />
                  <YAxis domain={[0, 100]} tick={{ fill: '#8BA0B3', fontSize: 10 }} />
                  <Tooltip
                    formatter={(value) => [`${Number(value).toFixed(0)}/100`, 'Score']}
                    contentStyle={{ backgroundColor: '#0B1220', border: '1px solid rgba(110, 231, 183, 0.25)', borderRadius: '12px', color: '#E5F9F0' }}
                  />
                  <Bar dataKey="value" radius={[8, 8, 0, 0]} fill="#5BC0EB" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="cosmic-card border-l border-l-amber-400/80 bg-amber-500/5 p-5 md:p-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-300">
                <AlertTriangle className="h-5 w-5" />
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Financial concerns</div>
                <h4 className="mt-1 text-lg font-bold text-white">Risk watchlist</h4>
              </div>
            </div>

            <div className="mt-4 space-y-3">
              {concerns.length ? concerns.map((item, idx) => (
                <div key={`${String(item)}-${idx}`} className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-3">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" />
                    <p className="text-sm leading-6 text-amber-100">{String(item)}</p>
                  </div>
                </div>
              )) : (
                <div className="rounded-2xl border border-cosmic-border bg-cosmic-bg/40 p-3 text-sm leading-6 text-cosmic-muted">
                  No major financial concerns flagged. Metrics not reported for banks (for example free cash flow) are not scored.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    )
  })()

  const prioritiesPainPointsPanel = (() => {
    const priorityList = Array.isArray(pipelineState?.priorities)
      ? pipelineState.priorities.filter((item: { trim: () => { (): any; new(): any; length: number } }): item is string => typeof item === 'string' && item.trim().length > 0)
      : []

    const painPoints = Array.isArray(pipelineState?.detected_pain_points)
      ? pipelineState.detected_pain_points.filter((item: any): item is Record<string, unknown> => Boolean(item) && typeof item === 'object')
      : []

    const severityCounts: Record<'HIGH' | 'MEDIUM' | 'LOW', number> = { HIGH: 0, MEDIUM: 0, LOW: 0 }
    painPoints.forEach((point: { severity: any }) => {
      const severity = String(point.severity ?? '').toUpperCase()
      if (severity === 'HIGH' || severity === 'MEDIUM' || severity === 'LOW') {
        severityCounts[severity as 'HIGH' | 'MEDIUM' | 'LOW'] += 1
      }
    })

    const maxSeverityCount = Math.max(1, ...Object.values(severityCounts))
    const filteredPainPoints = painPointFilter === 'ALL'
      ? painPoints
      : painPoints.filter((point: { severity: any }) => String(point.severity ?? '').toUpperCase() === painPointFilter)

    const severityStyles: Record<'HIGH' | 'MEDIUM' | 'LOW', string> = {
      HIGH: 'border-rose-500/30 bg-rose-500/10 text-rose-300',
      MEDIUM: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
      LOW: 'border-slate-500/30 bg-slate-500/10 text-slate-300',
    }

    return (
      <div className="space-y-6">
        <div className="cosmic-card p-5 md:p-6">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-300">
                <AlertTriangle className="h-5 w-5" />
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Priorities & pain points</div>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <h3 className="text-2xl font-bold text-white">Client action priorities</h3>
                  <span className="inline-flex items-center rounded-full border border-nagarro-green/30 bg-nagarro-green/10 px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-nagarro-green">
                    AI-generated
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-5 xl:grid-cols-[0.9fr_1.1fr]">
          <div className="cosmic-card p-5 md:p-6">
            <div className="mb-4 flex items-center justify-between gap-2">
              <div>
                <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Strategic priorities</div>
                <h4 className="mt-1 text-lg font-bold text-white">What the client needs to fix</h4>
              </div>
            </div>

            <div className="space-y-3">
              {priorityList.length ? priorityList.map((item: string | number | boolean | React.ReactElement<any, string | React.JSXElementConstructor<any>> | Iterable<React.ReactNode> | React.ReactPortal | null | undefined, index: number) => (
                <div key={`${item}-${index}`} className="rounded-2xl border border-cosmic-border bg-cosmic-bg/40 p-3">
                  <div className="flex items-start gap-3">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-nagarro-green/30 bg-nagarro-green/10 text-sm font-bold text-nagarro-green">
                      {index + 1}
                    </div>
                    <p className="text-sm leading-6 text-cosmic-muted">{item}</p>
                  </div>
                </div>
              )) : (
                <div className="rounded-2xl border border-cosmic-border bg-cosmic-bg/40 p-4 text-sm text-cosmic-muted">
                  No strategic priorities are available yet.
                </div>
              )}
            </div>
          </div>

          <div className="cosmic-card bg-amber-500/5 p-5 md:p-6">
            <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Summary</div>
                <h4 className="mt-1 text-lg font-bold text-white">Pain point distribution</h4>
              </div>
              <div className="inline-flex items-center gap-2 rounded-full border border-cosmic-border bg-cosmic-bg/40 px-2 py-1 text-[10px] uppercase tracking-[0.12em] text-cosmic-muted">
                Total: <span className="text-white">{painPoints.length}</span>
              </div>
            </div>

            <div className="h-2.5 w-full overflow-hidden rounded-full bg-cosmic-bg/60">
              <div className="flex h-full w-full overflow-hidden rounded-full">
                {(['HIGH', 'MEDIUM', 'LOW'] as const).map((level) => (
                  <div
                    key={level}
                    className={level === 'HIGH' ? 'bg-rose-400' : level === 'MEDIUM' ? 'bg-amber-400' : 'bg-slate-400'}
                    style={{ width: `${(severityCounts[level] / maxSeverityCount) * 100}%` }}
                  />
                ))}
              </div>
            </div>

            <div className="mt-4 grid grid-cols-3 gap-3">
              {(['HIGH', 'MEDIUM', 'LOW'] as const).map((level) => (
                <div key={level} className={`rounded-xl border p-3 ${severityStyles[level]}`}>
                  <div className="text-[10px] uppercase tracking-[0.18em]">{level}</div>
                  <div className="mt-2 text-xl font-bold text-white">{severityCounts[level]}</div>
                </div>
              ))}
            </div>

            <div className="mt-5 flex flex-wrap gap-2">
              {(['ALL', 'HIGH', 'MEDIUM', 'LOW'] as const).map((level) => (
                <button
                  key={level}
                  type="button"
                  onClick={() => setPainPointFilter(level)}
                  className={`rounded-full border px-2.5 py-1.5 text-[10px] uppercase tracking-[0.12em] transition-all ${
                    painPointFilter === level
                      ? 'border-nagarro-green/40 bg-nagarro-green/10 text-nagarro-green'
                      : 'border-cosmic-border bg-cosmic-bg/40 text-cosmic-muted hover:text-white'
                  }`}
                >
                  {level}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="cosmic-card p-5 md:p-6">
          <div className="mb-4 flex items-center justify-between gap-2">
            <div>
              <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Pain points</div>
              <h4 className="mt-1 text-lg font-bold text-white">Issue inventory</h4>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            {filteredPainPoints.length ? filteredPainPoints.map((point: { severity: any; description: any; category: any; impacted_business_area: any }, index: any) => {
              const severity = String(point.severity ?? 'MEDIUM').toUpperCase()
              const severityClass = severityStyles[severity as 'HIGH' | 'MEDIUM' | 'LOW'] ?? severityStyles.MEDIUM
              const description = String(point.description ?? 'No description provided.')

              return (
                <div key={`${String(point.category ?? 'pain-point')}-${index}`} className="rounded-2xl border border-cosmic-border bg-cosmic-bg/40 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-lg font-semibold text-white">{String(point.category ?? 'Pain point')}</div>
                    <span className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] ${severityClass}`}>
                      {severity}
                    </span>
                  </div>

                  <p className="mt-3 text-sm leading-6 text-cosmic-muted">
                    {description.length > 180 ? `${description.slice(0, 180)}...` : description}
                  </p>

                  <div className="mt-4 flex items-center justify-between gap-2">
                    <span className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Impacted area</span>
                    <span className="inline-flex rounded-full border border-cosmic-border bg-cosmic-bg/40 px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-white">
                      {String(point.impacted_business_area ?? 'Not specified')}
                    </span>
                  </div>
                </div>
              )
            }) : (
              <div className="col-span-full rounded-2xl border border-cosmic-border bg-cosmic-bg/40 p-5 text-sm text-cosmic-muted">
                No pain points match the selected severity filter.
              </div>
            )}
          </div>
        </div>
      </div>
    )
  })()

  const industryPanel = (() => {
    const industryData = asRecord(pipelineState?.industry_analysis)
    const sections = [
      { key: 'TRENDS', title: 'Major Trends', icon: '📈', accent: 'border-l border-l-nagarro-green/80', badge: 'bg-nagarro-green/10 border-nagarro-green/30 text-nagarro-green', items: asArray(industryData.major_trends) },
      { key: 'RISKS', title: 'Risks & Challenges', icon: '⚠️', accent: 'border-l border-l-rose-400/80', badge: 'bg-rose-500/10 border-rose-500/30 text-rose-300', items: asArray(industryData.risks_and_challenges) },
      { key: 'REGULATORY', title: 'Regulatory & Compliance', icon: '🛡️', accent: 'border-l border-l-amber-400/80', badge: 'bg-amber-500/10 border-amber-500/30 text-amber-300', items: asArray(industryData.regulatory_compliance) },
      { key: 'BENCHMARKS', title: 'Technology Benchmarks', icon: '🔧', accent: 'border-l border-l-cyan-400/80', badge: 'bg-cyan-500/10 border-cyan-500/30 text-cyan-300', items: asArray(industryData.technology_benchmarks) },
    ] as const

    const visibleSections = industryFilter === 'ALL'
      ? sections
      : sections.filter((section) => section.key === industryFilter)

    const renderHighlightedText = (value: string) => {
      const tokens = value.split(/(\d+(?:\.\d+)?%)/g)
      return tokens.map((token, index) => {
        if (/^\d+(?:\.\d+)?%$/.test(token)) {
          return (
            <span key={`${token}-${index}`} className="rounded border border-cyan-500/30 bg-cyan-500/10 px-1 text-cyan-200">
              {token}
            </span>
          )
        }
        return <React.Fragment key={`${token}-${index}`}>{token}</React.Fragment>
      })
    }

    return (
      <div className="space-y-6">
        <div className="cosmic-card p-5 md:p-6">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-cyan-500/30 bg-cyan-500/10 text-cyan-300">
                <BarChart3 className="h-5 w-5" />
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Industry analysis</div>
                <h3 className="mt-2 text-2xl font-bold text-white">What market forces affect this deal?</h3>
              </div>
            </div>
          </div>

          <div className="mt-5 flex flex-wrap gap-2">
            {(['ALL', 'TRENDS', 'RISKS', 'REGULATORY', 'BENCHMARKS'] as const).map((filter) => (
              <button
                key={filter}
                type="button"
                onClick={() => setIndustryFilter(filter)}
                className={`rounded-full border px-2.5 py-1.5 text-[10px] uppercase tracking-[0.12em] transition-all ${
                  industryFilter === filter
                    ? 'border-nagarro-green/40 bg-nagarro-green/10 text-nagarro-green'
                    : 'border-cosmic-border bg-cosmic-bg/40 text-cosmic-muted hover:text-white'
                }`}
              >
                {filter === 'ALL' ? 'All' : filter === 'TRENDS' ? 'Trends' : filter === 'RISKS' ? 'Risks' : filter === 'REGULATORY' ? 'Regulatory' : 'Benchmarks'}
              </button>
            ))}
          </div>
        </div>

        {visibleSections.map((section) => (
          <div key={section.key} className={`cosmic-card ${section.accent} p-5 md:p-6`}>
            <div className="mb-4 flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-cosmic-border bg-cosmic-bg/40 text-lg">
                  {section.icon}
                </div>
                <div>
                  <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Section</div>
                  <h4 className="mt-1 text-lg font-bold text-white">{section.title}</h4>
                </div>
              </div>
              <span className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] ${section.badge}`}>
                {section.items.length} items
              </span>
            </div>

            <div className="space-y-3">
              {section.items.length ? section.items.map((item, index) => {
                const story = String((item as Record<string, unknown>).detailed_narrative ?? 'No narrative provided.')
                const key = `${section.key}-${String((item as Record<string, unknown>).headline ?? 'item')}-${index}`
                const isExpanded = Boolean(industryExpanded[key])
                const previewText = story.length > 180 && !isExpanded ? `${story.slice(0, 180)}...` : story

                return (
                  <div key={key} className="rounded-2xl border border-cosmic-border bg-cosmic-bg/40 p-4">
                    <div className="text-lg font-semibold text-white">{String((item as Record<string, unknown>).headline ?? 'Industry development')}</div>
                    <p className="mt-3 text-sm leading-6 text-cosmic-muted">
                      {renderHighlightedText(previewText)}
                    </p>
                    {story.length > 180 && (
                      <button
                        type="button"
                        className="mt-2 text-xs font-medium text-nagarro-green hover:text-nagarro-hover"
                        aria-expanded={isExpanded}
                        onClick={() => setIndustryExpanded((current) => ({ ...current, [key]: !isExpanded }))}
                      >
                        {isExpanded ? 'Read less' : 'Read more'}
                      </button>
                    )}
                    {renderCitationChips((item as Record<string, unknown>).citations ?? [], key)}
                  </div>
                )
              }) : (
                <div className="rounded-2xl border border-cosmic-border bg-cosmic-bg/40 p-4 text-sm text-cosmic-muted">
                  No items available for this section yet.
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    )
  })()

  const solutionFitPanel = (() => {
    const serviceMappings = asArray(pipelineState?.service_mappings)
    const matchedAssets = asArray(pipelineState?.matched_internal_assets)

    if (!serviceMappings.length && !matchedAssets.length) {
      return (
        <div className="cosmic-card p-5 md:p-6 text-sm text-cosmic-muted">
          Solution-fit intelligence is not available yet.
        </div>
      )
    }

    return (
      <div className="space-y-6">
        <div className="cosmic-card p-5 md:p-6">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
                <CheckCircle2 className="h-5 w-5" />
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Solution fit</div>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <h3 className="text-2xl font-bold text-white">How do our offerings map to the client's problems?</h3>
                  <span className="inline-flex items-center rounded-full border border-nagarro-green/30 bg-nagarro-green/10 px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-nagarro-green">
                    AI-generated
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="space-y-5">
            {serviceMappings.length ? serviceMappings.map((mapping, index) => {
              const service = asRecord(mapping)
              const proofAssets = asArray(service.supporting_proof_assets)
              return (
                <div key={`${String(service.recommended_offering ?? 'offering')}-${index}`} className="cosmic-card border-l border-l-emerald-500/80 p-5 md:p-6">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Mapping {index + 1}</div>
                      <h4 className="mt-2 text-xl font-bold text-white">{String(service.recommended_offering ?? 'Recommended offering')}</h4>
                    </div>
                    <span className="inline-flex rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-emerald-300">
                      {String(service.detected_bottleneck ?? 'Capability fit')}
                    </span>
                  </div>

                  <div className="mt-5 grid grid-cols-1 gap-4 xl:grid-cols-2">
                    <div className="rounded-2xl border border-cosmic-border bg-cosmic-bg/40 p-4">
                      <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Client need</div>
                      <p className="mt-2 text-sm leading-6 text-cosmic-muted">{String(service.client_need ?? 'No client need captured.')}</p>
                    </div>
                    <div className="rounded-2xl border border-cosmic-border bg-cosmic-bg/40 p-4">
                      <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Expected business impact</div>
                      <p className="mt-2 text-sm leading-6 text-cosmic-muted">{String(service.expected_business_impact ?? 'No impact estimate captured.')}</p>
                    </div>
                  </div>

                  <div className="mt-5">
                    <div className="mb-3 text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Supporting proof assets</div>
                    <div className="space-y-3">
                      {proofAssets.length ? proofAssets.map((asset, assetIndex) => {
                        const assetRecord = asRecord(asset)
                        const score = Number(assetRecord.relevance_score ?? 0)
                        return (
                          <div key={`${String(assetRecord.asset_name ?? 'proof')}-${assetIndex}`} className="rounded-2xl border border-cosmic-border bg-cosmic-bg/40 p-4">
                            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                              <div>
                                <div className="text-base font-semibold text-white">{String(assetRecord.asset_name ?? 'Proof asset')}</div>
                                <div className="mt-1 text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">{String(assetRecord.asset_type ?? 'CASE_STUDY')}</div>
                              </div>
                              <span className="inline-flex rounded-full border border-nagarro-green/30 bg-nagarro-green/10 px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-nagarro-green">
                                {score.toFixed(0)}% relevance
                              </span>
                            </div>
                            <p className="mt-3 text-sm leading-6 text-cosmic-muted">{String(assetRecord.summary ?? 'No summary available.')}</p>
                            {Array.isArray(assetRecord.key_metrics_achieved) && assetRecord.key_metrics_achieved.length > 0 && (
                              <div className="mt-3 flex flex-wrap gap-2">
                                {assetRecord.key_metrics_achieved.map((metric, metricIndex) => (
                                  <span key={`${String(metric)}-${metricIndex}`} className="rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-cyan-300">
                                    {String(metric)}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        )
                      }) : (
                        <div className="rounded-2xl border border-cosmic-border bg-cosmic-bg/40 p-4 text-sm text-cosmic-muted">
                          No supporting proof assets are attached to this recommendation yet.
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )
            }) : (
              <div className="cosmic-card p-5 md:p-6 text-sm text-cosmic-muted">
                No service mappings are available for this deal yet.
              </div>
            )}
          </div>

          <div className="space-y-5">
            <div className="cosmic-card p-5 md:p-6">
              <div className="mb-4 flex items-center justify-between gap-3">
                <div>
                  <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Internal proof library</div>
                  <h4 className="mt-1 text-lg font-bold text-white">Matched assets</h4>
                </div>
                <span className="inline-flex items-center rounded-full border border-cosmic-border bg-cosmic-bg/40 px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-cosmic-muted">
                  {matchedAssets.length} assets
                </span>
              </div>

              <div className="space-y-3">
                {matchedAssets.length ? matchedAssets.map((asset, index) => {
                  const assetRecord = asRecord(asset)
                  const score = Number(assetRecord.relevance_score ?? 0)
                  return (
                    <div key={`${String(assetRecord.asset_name ?? 'internal-asset')}-${index}`} className="rounded-2xl border border-cosmic-border bg-cosmic-bg/40 p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="text-base font-semibold text-white">{String(assetRecord.asset_name ?? 'Matched asset')}</div>
                          <div className="mt-1 text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">{String(assetRecord.asset_type ?? 'CASE_STUDY')}</div>
                        </div>
                        <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-emerald-300">
                          {score.toFixed(0)}%
                        </span>
                      </div>
                      <p className="mt-3 text-sm leading-6 text-cosmic-muted">{String(assetRecord.summary ?? 'No summary available.')}</p>
                      {Array.isArray(assetRecord.key_metrics_achieved) && assetRecord.key_metrics_achieved.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {assetRecord.key_metrics_achieved.map((metric, metricIndex) => (
                            <span key={`${String(metric)}-${metricIndex}`} className="rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-cyan-300">
                              {String(metric)}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  )
                }) : (
                  <div className="rounded-2xl border border-cosmic-border bg-cosmic-bg/40 p-4 text-sm text-cosmic-muted">
                    No matched internal assets are available for this deal yet.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  })()

  const cxoBriefPanel = (() => {
    const brief = asRecord(pipelineState?.cxo_executive_brief ?? getNodeAliasValue('cxo_brief_generator'))
    const executiveSummary = String(brief.executive_summary ?? 'Executive summary is not available yet.')
    const executivePitch = String(brief.executive_pitch ?? 'No executive pitch available yet.')
    const talkingPoints = Array.isArray(brief.talking_points) ? brief.talking_points.filter((item): item is string => typeof item === 'string' && item.trim().length > 0) : []
    const questionsToAsk = Array.isArray(brief.questions_to_ask) ? brief.questions_to_ask.filter((item): item is string => typeof item === 'string' && item.trim().length > 0) : []
    const objections = Array.isArray(brief.objections_and_responses) ? brief.objections_and_responses.filter((item): item is Record<string, unknown> => typeof item === 'object' && item !== null) : []
    const [openObjection, setOpenObjection] = useState<number | null>(0)

    const copyText = async (text: string, label: string) => {
      try {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(text)
        } else {
          const textArea = document.createElement('textarea')
          textArea.value = text
          textArea.style.position = 'fixed'
          textArea.style.opacity = '0'
          document.body.appendChild(textArea)
          textArea.focus()
          textArea.select()
          document.execCommand('copy')
          document.body.removeChild(textArea)
        }
        setDocumentSuccess(`${label} copied to clipboard.`)
      } catch {
        setDocumentError(`Unable to copy ${label.toLowerCase()} automatically.`)
      }
    }

    const fullBriefText = [
      `Executive Summary\n${executiveSummary}\n\n`,
      `Executive Pitch\n${executivePitch}\n\n`,
      'Talking Points\n' + talkingPoints.map((point, index) => `${index + 1}. ${point}`).join('\n') + '\n\n',
      'Questions to Ask\n' + questionsToAsk.map((question, index) => `${index + 1}. ${question}`).join('\n') + '\n\n',
      'Objections & Responses\n' + objections.map((entry, index) => `${index + 1}. ${String(entry.objection ?? 'Objection')}: ${String(entry.response ?? '')}`).join('\n'),
    ].join('\n')

    return (
      <div className="space-y-6 print-shell">
        <div className="cosmic-card p-5 md:p-6 print-card">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
                <CheckCircle2 className="h-5 w-5" />
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">CXO brief</div>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <h3 className="text-2xl font-bold text-white">What do I say in the meeting?</h3>
                  <span className="inline-flex items-center rounded-full border border-nagarro-green/30 bg-nagarro-green/10 px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-nagarro-green">
                    AI-generated
                  </span>
                </div>
              </div>
            </div>

            <div className="print-hide flex flex-wrap items-center gap-2">
              <button type="button" onClick={() => void copyText(fullBriefText, 'Full brief')} className="btn-nagarro text-xs px-3 py-2">Copy full brief</button>
              <button type="button" onClick={() => window.print()} className="rounded-xl border border-cosmic-border bg-cosmic-bg/40 px-3 py-2 text-xs font-medium text-white hover:border-nagarro-green/40 hover:text-nagarro-green">Print / Export PDF</button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="cosmic-card p-5 md:p-6 print-card">
            <div className="mb-3 flex items-center justify-between gap-3 print-hide">
              <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Executive summary</div>
              <button type="button" onClick={() => void copyText(executiveSummary, 'Executive summary')} className="rounded-lg border border-cosmic-border bg-cosmic-bg/40 px-2.5 py-1.5 text-[10px] uppercase tracking-[0.12em] text-cosmic-muted hover:text-white">Copy</button>
            </div>
            <h4 className="text-3xl font-bold leading-tight text-white">{targetCompany}</h4>
            <p className="mt-4 text-base leading-7 text-cosmic-muted">{executiveSummary}</p>
          </div>

          <div className="cosmic-card p-5 md:p-6 print-card">
            <div className="mb-3 flex items-center justify-between gap-3 print-hide">
              <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Executive pitch</div>
              <button type="button" onClick={() => void copyText(executivePitch, 'Executive pitch')} className="rounded-lg border border-cosmic-border bg-cosmic-bg/40 px-2.5 py-1.5 text-[10px] uppercase tracking-[0.12em] text-cosmic-muted hover:text-white">Copy</button>
            </div>
            <p className="text-xl leading-9 text-cosmic-text print:text-slate-900">{executivePitch}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
          <div className="cosmic-card p-5 md:p-6 print-card">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Talking points</div>
                <h4 className="mt-1 text-xl font-bold text-white">Message sequence</h4>
              </div>
            </div>

            <div className="space-y-3">
              {talkingPoints.length ? talkingPoints.map((point, index) => {
                const isChecked = Boolean(coveredTalkingPoints[index])
                return (
                  <div key={`${point}-${index}`} className={`rounded-2xl border p-3 transition-all ${isChecked ? 'border-nagarro-green/30 bg-nagarro-green/10' : 'border-cosmic-border bg-cosmic-bg/40'}`}>
                    <div className="flex items-start gap-3">
                      <button
                        type="button"
                        aria-label={`Mark talking point ${index + 1} as covered`}
                        onClick={() => setCoveredTalkingPoints((current) => ({ ...current, [index]: !current[index] }))}
                        className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition-all ${isChecked ? 'border-nagarro-green bg-nagarro-green text-black' : 'border-cosmic-border bg-cosmic-bg/40 text-cosmic-muted'}`}
                      >
                        {isChecked && <CheckCircle2 className="h-3.5 w-3.5" />}
                      </button>
                      <div className="flex-1">
                        <div className="mb-1 text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Point {index + 1}</div>
                        <p className="text-sm leading-6 text-cosmic-muted">{point}</p>
                      </div>
                    </div>
                  </div>
                )
              }) : (
                <div className="rounded-2xl border border-cosmic-border bg-cosmic-bg/40 p-4 text-sm text-cosmic-muted">No talking points available yet.</div>
              )}
            </div>
          </div>

          <div className="cosmic-card p-5 md:p-6 print-card">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Questions to ask</div>
                <h4 className="mt-1 text-xl font-bold text-white">Discovery prompts</h4>
              </div>
            </div>

            <div className="space-y-3">
              {questionsToAsk.length ? questionsToAsk.map((question, index) => (
                <div key={`${question}-${index}`} className="rounded-2xl border border-cosmic-border bg-cosmic-bg/40 p-3">
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Question {index + 1}</div>
                    <button type="button" onClick={() => void copyText(question, `Question ${index + 1}`)} className="rounded-lg border border-cosmic-border bg-cosmic-bg/40 px-2 py-1 text-[10px] uppercase tracking-[0.12em] text-cosmic-muted hover:text-white print-hide">Copy</button>
                  </div>
                  <p className="text-sm leading-6 text-cosmic-muted">{question}</p>
                </div>
              )) : (
                <div className="rounded-2xl border border-cosmic-border bg-cosmic-bg/40 p-4 text-sm text-cosmic-muted">No discovery questions available yet.</div>
              )}
            </div>
          </div>
        </div>

        <div className="cosmic-card p-5 md:p-6 print-card">
          <div className="mb-4">
            <div className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Objections & responses</div>
            <h4 className="mt-1 text-xl font-bold text-white">Response framework</h4>
          </div>

          <div className="space-y-3">
            {objections.length ? objections.map((entry, index) => {
              const isOpen = openObjection === index
              const objectionText = String(entry.objection ?? 'Objection')
              const responseText = String(entry.response ?? 'No response available.')
              return (
                <div key={`${objectionText}-${index}`} className="overflow-hidden rounded-2xl border border-cosmic-border bg-cosmic-bg/40">
                  <button
                    type="button"
                    onClick={() => setOpenObjection(isOpen ? null : index)}
                    className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
                  >
                    <div className="flex items-center gap-3">
                      <span className="flex h-8 w-8 items-center justify-center rounded-full border border-rose-500/30 bg-rose-500/10 text-rose-300">!</span>
                      <span className="text-sm font-semibold text-white">{objectionText}</span>
                    </div>
                    <span className="text-xs uppercase tracking-[0.12em] text-cosmic-muted">{isOpen ? 'Hide' : 'Show'}</span>
                  </button>

                  {isOpen && (
                    <div className="border-t border-cosmic-border bg-cosmic-bg/30 p-4">
                      <div className="mb-2 flex items-center gap-2 text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">
                        <span className="flex h-6 w-6 items-center justify-center rounded-full border border-nagarro-green/30 bg-nagarro-green/10 text-nagarro-green">✓</span>
                        Response
                      </div>
                      <p className="text-sm leading-7 text-cosmic-muted">{responseText}</p>
                    </div>
                  )}
                </div>
              )
            }) : (
              <div className="rounded-2xl border border-cosmic-border bg-cosmic-bg/40 p-4 text-sm text-cosmic-muted">No objection-response pairs available yet.</div>
            )}
          </div>
        </div>
      </div>
    )
  })()

  const activeNodeMarkdown = (() => {
    if (!pipelineState) {
      return '### Pipeline state not available\nThe workflow has not started yet or the backend has not returned state data.'
    }

    if (activeTabNode === 'company_research') {
      return companyResearchPanel as unknown as string
    }

    if (activeTabNode === 'financial_intelligence') {
      return financialPanel as unknown as string
    }

    if (activeTabNode === 'stakeholder_intel') {
      return stakeholderPanel as unknown as string
    }

    if (activeTabNode === 'pain_point_detector') {
      return prioritiesPainPointsPanel as unknown as string
    }

    if (activeTabNode === 'industry_analysis') {
      return industryPanel as unknown as string
    }

    if (activeTabNode === 'service_mapper') {
      return solutionFitPanel as unknown as string
    }

    const rawNodeData = getNodeAliasValue(activeTabNode)
    return renderNodeTemplate(activeTabNode, rawNodeData)
  })()

  const nodes = [
    { id: 'company_research', label: 'Company Research', status: resolveNodeStatus('company_research', 'pending') },
    { id: 'financial_intelligence', label: 'Financial Intel', status: resolveNodeStatus('financial_intelligence', 'pending') },
    { id: 'stakeholder_intel', label: 'Stakeholder Analysis', status: resolveNodeStatus('stakeholder_intel', 'pending') },
    { id: 'industry_analysis', label: 'Industry Analysis', status: resolveNodeStatus('industry_analysis', 'pending') },
    { id: 'pain_point_detector', label: 'Pain Point Detector', status: resolveNodeStatus('pain_point_detector', 'pending') },
    { id: 'service_mapper', label: 'Solution Fit', status: resolveNodeStatus('service_mapper', 'pending') },
    { id: 'human_review_gate', label: 'Human Review Gate', status: resolveNodeStatus('human_review_gate', pipelineState?.mandatory_review_checkpoint === 'approved' ? 'completed' : 'paused') },
    { id: 'cxo_brief_generator', label: 'CXO Brief', status: resolveNodeStatus('cxo_brief_generator', 'pending') },
  ]

  const statusBanner = (() => {
    if (pipelineState?.current_step) return pipelineState.current_step
    if (pipelineStatus && pipelineStatus !== 'UNKNOWN') return pipelineStatus
    return 'WAITING_FOR_DATA'
  })()

  const pipelineTitle = (() => {
    const companyName = (pipelineState?.financial_intelligence as Record<string, unknown> | undefined)?.company_name
    return companyName ? String(companyName) : 'Deal Pipeline'
  })()

  return (
    <div className="space-y-6 relative min-h-[calc(100vh-8rem)]">
      <DealDashboardHeader
        pipelineTitle={pipelineTitle}
        dealId={dealId}
        viewMode={viewMode}
        selectedCheckpoint={selectedCheckpoint}
        checkpointOptions={checkpointOptions}
        onChangeView={setViewMode}
        onSelectedCheckpointChange={setSelectedCheckpoint}
        onRestoreCheckpoint={handleRestoreCheckpoint}
        onOpenDrawer={() => setIsDrawerOpen(true)}
      />

      <DealDocumentsPanel
        dealId={dealId}
        documents={documents}
        isDocumentsOpen={isDocumentsOpen}
        onToggleDocuments={() => setIsDocumentsOpen((prev) => !prev)}
        onDocumentUpload={handleDocumentUpload}
        onDocumentDelete={handleDocumentDelete}
        onSelectedFileChange={setSelectedFile}
        isLoadingDocuments={isLoadingDocuments}
        isUploadingDocument={isUploadingDocument}
        documentCategory={documentCategory}
        onDocumentCategoryChange={setDocumentCategory}
        selectedFile={selectedFile}
        documentError={documentError}
        documentSuccess={documentSuccess}
        isDeletingDeal={isDeletingDeal}
        onDeleteDeal={handleDeleteDeal}
      />

      {/* ========================================================================================= */}
      {/* VIEW 1: GITLAB-STYLE PIPELINE FLOW CARDS */}
      {/* ========================================================================================= */}
      {viewMode === 'pipeline' && (
        <PipelineFlow
          nodes={nodes}
          statusBanner={statusBanner}
          onNodeClick={(nodeId) => {
            setActiveTabNode(nodeId)
            setViewMode('tabs')
          }}
        />
      )}

      {/* ========================================================================================= */}
      {/* VIEW 2: CHROME-STYLE TABS VIEW */}
      {/* ========================================================================================= */}
      {viewMode === 'tabs' && (
        <NodeDetailTabs
          activeTabNode={activeTabNode}
          nodes={nodes}
          onSelectNode={(nodeId) => setActiveTabNode(nodeId)}
          companyResearchPanel={companyResearchPanel}
          financialPanel={financialPanel}
          stakeholderPanel={stakeholderPanel}
          prioritiesPainPointsPanel={prioritiesPainPointsPanel}
          industryPanel={industryPanel}
          solutionFitPanel={solutionFitPanel}
          cxoBriefPanel={cxoBriefPanel}
          reviewFeedback={reviewFeedback}
          setReviewFeedback={setReviewFeedback}
          isSubmittingReview={isSubmittingReview}
          onReviewApproval={handleReviewApproval}
          pipelineState={pipelineState}
        />
      )}

      {/* ========================================================================================= */}
      {/* VIEW 3: STRATEGY REPORT & AI CHAT (SPLIT SCREEN) */}
      {/* ========================================================================================= */}
      {viewMode === 'report_chat' && (
        <ReportChatPanel
          targetCompany={targetCompany}
          targetIndustry={targetIndustry}
          meetingObjective={meetingObjective}
          pipelineState={pipelineState}
          reportMarkdown={reportMarkdown}
          chatMessages={chatMessages}
          chatLoading={chatLoading}
          proposal={proposal}
          chatInput={chatInput}
          selectedSection={selectedSection || 'general'}
          onChatInputChange={setChatInput}
          onChatSubmit={handleChatSubmit}
          onGenerateRevision={handleProposedEdit}
          onClearDraft={() => {
            setChatInput('')
            dispatch(setProposal(null))
          }}
          onSectionChange={(value) => dispatch(setSelectedSection(value))}
          onProposalDecision={handleProposalDecision}
        />
      )}

      {/* ========================================================================================= */}
      {/* VS CODE-STYLE RIGHT SIDE DRAWER (HITL DYNAMIC INSTRUCTION & STEERING) */}
      {/* ========================================================================================= */}
      {isDrawerOpen && <HITLDrawer nodes={nodes} onClose={() => setIsDrawerOpen(false)} />}
    </div>
  )
}