import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'

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
  type LatestReportResponse,
} from './reportApi'
import {
  approveTextEdit,
  askDealQuery,
  proposeTextEdit,
  type ChatQueryResponse,
} from './chatApi'
import {
  getPipelineState,
  getPipelineStatus,
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
import PipelineFlow, { type PipelineNode } from '../../components/dashboard/PipelineFlow'
import ReportChatPanel from '../../components/dashboard/ReportChatPanel'
import HITLDrawer from '../../components/dashboard/HITLDrawer'
import NodeDetailTabs from '../../components/dashboard/NodeDetailTabs'
import ResearchPanel from '../../components/research/ResearchPanel'
import FrameworksPanel from '../../components/research/FrameworksPanel'
import InsightsPanel from '../../components/research/InsightsPanel'
import PainPointsPanel from '../../components/research/PainPointsPanel'
import SolutionFitPanel from '../../components/research/SolutionFitPanel'
import PlaybookView from '../../components/research/PlaybookView'
import ReviewPanel from '../../components/research/ReviewPanel'
import { EvidenceProvider } from '../../components/research/EvidenceContext'

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

  const { dealId } = useParams()
  const [viewMode, setViewMode] = useState<'pipeline' | 'tabs' | 'report_chat'>('pipeline')
  const [activeTabNode, setActiveTabNode] = useState('research')
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const [isDocumentsOpen, setIsDocumentsOpen] = useState(false)
  const [pipelineStatus, setPipelineStatus] = useState('UNKNOWN')
  const [dealDetails, setDealDetails] = useState<{ target_company?: string | null; target_industry?: string | null; meeting_objective?: string | null } | null>(null)
  const [isDeletingDeal, setIsDeletingDeal] = useState(false)
  const [isSubmittingReview, setIsSubmittingReview] = useState(false)
  const [reviewFeedback, setReviewFeedback] = useState('')
  const [documents, setDocuments] = useState<DealDocument[]>([])
  const [chatInput, setChatInput] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [documentCategory, setDocumentCategory] = useState('RFP')
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false)
  const [isUploadingDocument, setIsUploadingDocument] = useState(false)
  const [documentError, setDocumentError] = useState('')
  const [documentSuccess, setDocumentSuccess] = useState('')

  const getNodeStatus = (nodeId: string, fallback: PipelineNode['status'] = 'pending'): PipelineNode['status'] => {
    const nodeStatuses = pipelineState?.node_statuses ?? {}
    const raw = nodeStatuses[nodeId] ?? pipelineState?.[nodeId]
    if (raw === undefined || raw === null || raw === '') return fallback

    const value = String(raw).toLowerCase()
    if (value.includes('done') || value.includes('completed') || value.includes('approved') || value.includes('success')) return 'completed'
    if (value.includes('running') || value.includes('executing') || value.includes('active')) return 'running'
    if (value.includes('failed') || value.includes('error') || value.includes('rejected')) return 'failed'
    if (value.includes('paused') || value.includes('review') || value.includes('waiting') || value.includes('needs_revision')) return 'paused'
    return 'pending'
  }

  const nodes: PipelineNode[] = useMemo(
    () => [
      { id: 'research', label: 'Research', status: getNodeStatus('research', 'pending') },
      { id: 'frameworks', label: 'Frameworks', status: getNodeStatus('frameworks', 'pending') },
      { id: 'insights', label: 'Insights', status: getNodeStatus('insights', 'pending') },
      { id: 'pain_points', label: 'Pain Points', status: getNodeStatus('pain_points', 'pending') },
      { id: 'solution_fit', label: 'Solution Fit', status: getNodeStatus('solution_fit', 'pending') },
      { id: 'playbook', label: 'Playbook', status: getNodeStatus('playbook', 'pending') },
      { id: 'review', label: 'Review', status: getNodeStatus('review', pipelineState?.mandatory_review_checkpoint ? 'paused' : 'pending') },
    ],
    [pipelineState],
  )

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
      const candidate = detail && typeof detail === 'object' && 'deal' in detail && detail.deal && typeof detail.deal === 'object'
        ? (detail.deal as Record<string, unknown>)
        : (detail as Record<string, unknown>)

      setDealDetails({
        target_company: typeof candidate.target_company === 'string' ? candidate.target_company : null,
        target_industry: typeof candidate.target_industry === 'string' ? candidate.target_industry : null,
        meeting_objective: typeof candidate.meeting_objective === 'string' ? candidate.meeting_objective : null,
      })
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
        text: 'Choose a specific section before generating a revision.',
      }))
      return
    }

    const instruction = chatInput.trim() || 'Make this section more executive-ready and concise.'
    setChatInput('')
    dispatch(setChatLoading(true))

    try {
      const result = await proposeTextEdit(dealId, {
        section: selectedSection,
        instruction,
        current_text: reportMarkdown,
      }, accessToken)

      dispatch(setProposal(result))
      dispatch(addChatMessage({ role: 'assistant', text: `Draft revision created for ${selectedSection}. Review it and approve or reject the proposal below.` }))
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
        proposed_diff_id: proposal.proposed_diff_id ?? '',
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
      dispatch(addChatMessage({ role: 'assistant', text: error instanceof Error ? error.message : 'Unable to process the proposal decision.' }))
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

  const handleReviewApproval = async (status: 'approved' | 'needs_revision' | 'rejected') => {
    if (!dealId) return

    setIsSubmittingReview(true)
    try {
      await submitMandatoryReviewApproval(dealId, {
        checkpoint_status: status,
        feedback: reviewFeedback.trim() || undefined,
      }, accessToken)
      setReviewFeedback('')
      await loadPipelineState()
    } catch (error) {
      setDocumentError(error instanceof Error ? error.message : 'Unable to submit the review decision.')
    } finally {
      setIsSubmittingReview(false)
    }
  }

  const targetCompany = dealDetails?.target_company ?? pipelineState?.target_company ?? 'Company'
  const targetIndustry = dealDetails?.target_industry ?? pipelineState?.target_industry ?? 'Industry'
  const meetingObjective = dealDetails?.meeting_objective ?? pipelineState?.meeting_objective ?? 'Discuss strategic priorities'
  const statusBanner = pipelineState?.current_step ?? pipelineStatus

  const companyResearchPanel = pipelineState ? (
    <ResearchPanel state={pipelineState} />
  ) : (
    <div className="cosmic-card p-5 text-sm text-cosmic-muted">Research data is not available yet.</div>
  )

  const frameworkPanel = pipelineState ? (
    <FrameworksPanel state={pipelineState} />
  ) : (
    <div className="cosmic-card p-5 text-sm text-cosmic-muted">Framework data is not available yet.</div>
  )

  const insightPanel = pipelineState ? (
    <InsightsPanel state={pipelineState} />
  ) : (
    <div className="cosmic-card p-5 text-sm text-cosmic-muted">Insights are not available yet.</div>
  )

  const painPointsPanel = pipelineState ? (
    <PainPointsPanel state={pipelineState} />
  ) : (
    <div className="cosmic-card p-5 text-sm text-cosmic-muted">Pain points have not been generated yet.</div>
  )

  const solutionFitPanel = pipelineState ? (
    <SolutionFitPanel state={pipelineState} />
  ) : (
    <div className="cosmic-card p-5 text-sm text-cosmic-muted">Solution fit is not available yet.</div>
  )

  const playbookPanel = pipelineState ? (
    <PlaybookView
      playbook={pipelineState.meeting_playbook ?? {
        snapshot: { situation: '', why_now: '', opening_hook: '', meeting_goal: '', fact_ids: [] },
        agenda: [],
        talking_points: [],
        discovery_questions: [],
        objections: [],
        attendees: [],
        landmines: [],
        proof_points: [],
        pitch_and_ask: {
          pitch_60_seconds: '',
          pitch_3_minutes: '',
          the_ask: '',
          next_steps: [],
          follow_up_email_subject: '',
          follow_up_email_body: '',
          fact_ids: [],
          proof_asset_ids: [],
        },
        deal_risks: [],
        known_gaps: [],
        overall_confidence: 'MEDIUM',
      }}
      assets={pipelineState.matched_internal_assets ?? []}
    />
  ) : (
    <div className="cosmic-card p-5 text-sm text-cosmic-muted">No playbook has been generated yet.</div>
  )

  const reviewPanel = (
    <ReviewPanel
      state={pipelineState}
      reviewFeedback={reviewFeedback}
      setReviewFeedback={setReviewFeedback}
      isSubmittingReview={isSubmittingReview}
      onReviewApproval={handleReviewApproval}
    />
  )

  return (
    <EvidenceProvider facts={pipelineState?.facts} sources={pipelineState?.sources}>
      <div className="space-y-6 relative min-h-[calc(100vh-8rem)]">
        <DealDashboardHeader
          pipelineTitle={targetCompany}
          dealId={dealId}
          viewMode={viewMode}
          onChangeView={setViewMode}
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

        {viewMode === 'tabs' && (
          <NodeDetailTabs
            activeTabNode={activeTabNode}
            nodes={nodes}
            onSelectNode={setActiveTabNode}
            companyResearchPanel={companyResearchPanel}
            financialPanel={frameworkPanel}
            stakeholderPanel={insightPanel}
            prioritiesPainPointsPanel={painPointsPanel}
            solutionFitPanel={solutionFitPanel}
            cxoBriefPanel={playbookPanel}
            reviewFeedback={reviewFeedback}
            setReviewFeedback={setReviewFeedback}
            isSubmittingReview={isSubmittingReview}
            onReviewApproval={handleReviewApproval}
            pipelineState={pipelineState as Record<string, unknown> | null}
          />
        )}

        {viewMode === 'report_chat' && (
          <ReportChatPanel
            targetCompany={targetCompany}
            targetIndustry={targetIndustry}
            meetingObjective={meetingObjective}
            pipelineState={pipelineState as Record<string, unknown> | null}
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

        {viewMode === 'tabs' && activeTabNode === 'review' && reviewPanel}

        {isDrawerOpen && (
          <HITLDrawer
            dealId={dealId ?? ''}
            nodes={nodes}
            onClose={() => setIsDrawerOpen(false)}
            onInstructionSubmitted={() => void loadPipelineState()}
          />
        )}
      </div>
    </EvidenceProvider>
  )
}
