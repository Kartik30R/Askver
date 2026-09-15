import { createSlice } from '@reduxjs/toolkit'

const authSlice = createSlice({
  name: 'auth',
  initialState: { token: localStorage.getItem('access_token') || null },
  reducers: {
    setCredentials: (state, action) => { state.token = action.payload.access_token },
    logout: (state) => { state.token = null }
  }
})

export const { setCredentials, logout } = authSlice.actions
export const selectCurrentToken = (state: any) => state.auth.token
export default authSlice.reducer