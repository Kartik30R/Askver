import { createAsyncThunk, createSlice, type PayloadAction } from '@reduxjs/toolkit'
import { createDeal, fetchUserDeals, startPipeline, type DealCreate, type DealSummary } from './dealsApi'
import type { RootState } from '../../app/store'

export type DealsState = {
  deals: DealSummary[]
  currentDraft: DealSummary | null
  status: 'idle' | 'loading' | 'succeeded' | 'failed'
  error: string | null
  creatingDeal: boolean
  startingPipeline: boolean
}

const initialState: DealsState = {
  deals: [],
  currentDraft: null,
  status: 'idle',
  error: null,
  creatingDeal: false,
  startingPipeline: false,
}

// ============================================================================
// ASYNC THUNKS
// ============================================================================

export const fetchDeals = createAsyncThunk<
  DealSummary[],
  void,
  { state: RootState; rejectValue: string }
>(
  'deals/fetchDeals',
  async (_, { getState, rejectWithValue }) => {
    const accessToken = getState().auth.accessToken

    if (!accessToken) {
      return rejectWithValue('Not authenticated')
    }

    try {
      const deals = await fetchUserDeals(accessToken)
      console.log('[💼 dealsSlice] fetchDeals success', deals)
      return deals
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch deals'
      console.error('[💼 dealsSlice] fetchDeals error:', message)
      return rejectWithValue(message)
    }
  },
)

export const createNewDeal = createAsyncThunk<
  DealSummary,
  DealCreate,
  { state: RootState; rejectValue: string }
>(
  'deals/createNewDeal',
  async (dealData, { getState, rejectWithValue }) => {
    const accessToken = getState().auth.accessToken

    if (!accessToken) {
      return rejectWithValue('Not authenticated')
    }

    try {
      const deal = await createDeal(dealData, accessToken)
      console.log('[💼 dealsSlice] createNewDeal success', deal)
      return deal
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to create deal'
      console.error('[💼 dealsSlice] createNewDeal error:', message)
      return rejectWithValue(message)
    }
  },
)

export const startDealWorkflow = createAsyncThunk<
  void,
  string | { dealId: string; researchDepth?: string; meetingDurationMinutes?: number },
  { state: RootState; rejectValue: string }
>(
  'deals/startDealWorkflow',
  async (payload, { getState, rejectWithValue }) => {
    const accessToken = getState().auth.accessToken

    if (!accessToken) {
      return rejectWithValue('Not authenticated')
    }

    const dealId = typeof payload === 'string' ? payload : payload.dealId
    const researchDepth = typeof payload === 'string' ? 'standard' : payload.researchDepth ?? 'standard'
    const meetingDurationMinutes = typeof payload === 'string' ? 45 : payload.meetingDurationMinutes ?? 45

    try {
      await startPipeline(dealId, accessToken, { researchDepth, meetingDurationMinutes })
      console.log('[💼 dealsSlice] startDealWorkflow success', dealId, { researchDepth, meetingDurationMinutes })
      return undefined
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to start workflow'
      console.error('[💼 dealsSlice] startDealWorkflow error:', message)
      return rejectWithValue(message)
    }
  },
)

// ============================================================================
// SLICE
// ============================================================================

const dealsSlice = createSlice({
  name: 'deals',
  initialState,
  reducers: {
    setCurrentDraft(state, action: PayloadAction<DealSummary | null>) {
      state.currentDraft = action.payload
    },
    clearError(state) {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchDeals.pending, (state) => {
        console.log('[💼 dealsSlice] fetchDeals.pending')
        state.status = 'loading'
        state.error = null
      })
      .addCase(fetchDeals.fulfilled, (state, action) => {
        console.log('[💼 dealsSlice] fetchDeals.fulfilled', action.payload)
        state.deals = action.payload
        state.status = 'succeeded'
        state.error = null
      })
      .addCase(fetchDeals.rejected, (state, action) => {
        console.log('[💼 dealsSlice] fetchDeals.rejected', action.payload)
        state.status = 'failed'
        state.error = action.payload ?? 'Failed to fetch deals'
      })
      .addCase(createNewDeal.pending, (state) => {
        console.log('[💼 dealsSlice] createNewDeal.pending')
        state.creatingDeal = true
        state.error = null
      })
      .addCase(createNewDeal.fulfilled, (state, action) => {
        console.log('[💼 dealsSlice] createNewDeal.fulfilled', action.payload)
        // Add newly created deal to the list
        const existingIndex = state.deals.findIndex(d => d.id === action.payload.id)
        if (existingIndex === -1) {
          state.deals = [action.payload, ...state.deals]
        } else {
          state.deals[existingIndex] = action.payload
        }
        // Keep it as current draft for continuing to next steps
        state.currentDraft = action.payload
        state.creatingDeal = false
        state.error = null
      })
      .addCase(createNewDeal.rejected, (state, action) => {
        console.log('[💼 dealsSlice] createNewDeal.rejected', action.payload)
        state.creatingDeal = false
        state.error = action.payload ?? 'Failed to create deal'
      })
      .addCase(startDealWorkflow.pending, (state) => {
        console.log('[💼 dealsSlice] startDealWorkflow.pending')
        state.startingPipeline = true
        state.error = null
      })
      .addCase(startDealWorkflow.fulfilled, (state) => {
        console.log('[💼 dealsSlice] startDealWorkflow.fulfilled')
        // Clear draft after starting workflow
        state.currentDraft = null
        state.startingPipeline = false
        state.error = null
      })
      .addCase(startDealWorkflow.rejected, (state, action) => {
        console.log('[💼 dealsSlice] startDealWorkflow.rejected', action.payload)
        state.startingPipeline = false
        state.error = action.payload ?? 'Failed to start workflow'
      })
  },
})

export const { setCurrentDraft, clearError } = dealsSlice.actions

// ============================================================================
// SELECTORS
// ============================================================================

export const selectDeals = (state: RootState) => state.deals?.deals ?? []
export const selectCurrentDraft = (state: RootState) => state.deals?.currentDraft ?? null
export const selectDealsStatus = (state: RootState) => state.deals?.status ?? 'idle'
export const selectDealsError = (state: RootState) => state.deals?.error ?? null
export const selectCreatingDeal = (state: RootState) => state.deals?.creatingDeal ?? false
export const selectStartingPipeline = (state: RootState) => state.deals?.startingPipeline ?? false

export default dealsSlice.reducer
