import { createSlice, type PayloadAction } from '@reduxjs/toolkit'
import type { PipelineStateResponse } from './workflowApi'

export type WorkflowTab = 'playbook' | 'research' | 'frameworks' | 'insights' | 'pain_points' | 'solution_fit' | 'review'

export type WorkflowState = {
  pipelineState: PipelineStateResponse | null
  reportMarkdown: string
  chatMessages: Array<{ role: 'user' | 'assistant'; text: string }>
  chatLoading: boolean
  proposal: { proposed_text: string; proposed_diff_id?: string } | null
  selectedSection: string
  activeTab: WorkflowTab
  selectedAssetIds: string[] | null // null = reviewer has not changed the default (keep all)
}

const initialState: WorkflowState = {
  pipelineState: null,
  reportMarkdown: '',
  chatMessages: [],
  chatLoading: false,
  proposal: null,
  selectedSection: '',
  activeTab: 'playbook',
  selectedAssetIds: null,
}

const workflowSlice = createSlice({
  name: 'workflow',
  initialState,
  reducers: {
    setPipelineState(state, action: PayloadAction<PipelineStateResponse | null>) {
      state.pipelineState = action.payload
    },
    setReportMarkdown(state, action: PayloadAction<string>) {
      state.reportMarkdown = action.payload
    },
    addChatMessage(state, action: PayloadAction<{ role: 'user' | 'assistant'; text: string }>) {
      state.chatMessages.push(action.payload)
    },
    setChatLoading(state, action: PayloadAction<boolean>) {
      state.chatLoading = action.payload
    },
    setProposal(state, action: PayloadAction<WorkflowState['proposal']>) {
      state.proposal = action.payload
    },
    setSelectedSection(state, action: PayloadAction<string>) {
      state.selectedSection = action.payload
    },
    setActiveTab(state, action: PayloadAction<WorkflowTab>) {
      state.activeTab = action.payload
    },
    setSelectedAssetIds(state, action: PayloadAction<string[] | null>) {
      state.selectedAssetIds = action.payload
    },
    resetWorkflow() {
      return initialState // call when the route's dealId changes so one deal's data never shows on another
    },
  },
})

export const {
  setPipelineState, setReportMarkdown, addChatMessage, setChatLoading, setProposal,
  setSelectedSection, setActiveTab, setSelectedAssetIds, resetWorkflow,
} = workflowSlice.actions

type Root = { workflow: WorkflowState }
export const selectPipelineState = (state: Root) => state.workflow.pipelineState
export const selectReportMarkdown = (state: Root) => state.workflow.reportMarkdown
export const selectChatMessages = (state: Root) => state.workflow.chatMessages
export const selectChatLoading = (state: Root) => state.workflow.chatLoading
export const selectWorkflowProposal = (state: Root) => state.workflow.proposal
export const selectWorkflowSelectedSection = (state: Root) => state.workflow.selectedSection
export const selectActiveTab = (state: Root) => state.workflow.activeTab
export const selectSelectedAssetIds = (state: Root) => state.workflow.selectedAssetIds

export default workflowSlice.reducer
