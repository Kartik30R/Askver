import { createSlice, type PayloadAction } from '@reduxjs/toolkit'

export type WorkflowState = {
  pipelineState: any
  reportMarkdown: string
  chatMessages: Array<{ role: 'user' | 'assistant'; text: string }>
  chatLoading: boolean
  proposal: any
  selectedSection: string
}

const initialState: WorkflowState = {
  pipelineState: null,
  reportMarkdown: '',
  chatMessages: [],
  chatLoading: false,
  proposal: null,
  selectedSection: 'general',
}

const workflowSlice = createSlice({
  name: 'workflow',
  initialState,
  reducers: {
    setPipelineState(state, action: PayloadAction<any>) {
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
    setProposal(state, action: PayloadAction<any>) {
      state.proposal = action.payload
    },
    setSelectedSection(state, action: PayloadAction<string>) {
      state.selectedSection = action.payload
    },
  },
})

export const {
  setPipelineState,
  setReportMarkdown,
  addChatMessage,
  setChatLoading,
  setProposal,
  setSelectedSection,
} = workflowSlice.actions

export const selectReportMarkdown = (state: any) => state.workflow?.reportMarkdown ?? ''
export const selectChatMessages = (state: any) => state.workflow?.chatMessages ?? []
export const selectChatLoading = (state: any) => state.workflow?.chatLoading ?? false
export const selectWorkflowProposal = (state: any) => state.workflow?.proposal ?? null
export const selectWorkflowSelectedSection = (state: any) => state.workflow?.selectedSection ?? ''

export default workflowSlice.reducer
