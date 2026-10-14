# Frontend Auth & Routing Architecture

## Overview

This document describes the Redux-based authentication and routing system, designed to integrate cleanly with the FastAPI backend while maintaining proper session management and user experience.

## Architecture

### Redux Auth State (`features/auth/authSlice.ts`)

The auth module manages:
- **User**: Current authenticated user (id, email, name, created_at)
- **Access Token**: JWT access token used in `Authorization: Bearer` header
- **Status**: Loading, idle, succeeded, or failed state
- **Error**: User-facing error messages

**Persistence**: Session data is stored in `localStorage` under the key `askver-auth` to survive page reloads.

### API Integration (`features/auth/authApi.ts`)

Provides typed async functions:
- `loginRequest(email, password)` → Returns `AuthSession` (token + user)
- `registerRequest(name, email, password)` → Returns `AuthSession`
- `logoutUser()` → Clears server-side session
- `fetchCurrentUser(accessToken)` → Validates token and returns current user

### Redux Async Thunks (`features/auth/authSlice.ts`)

**`loginUser`** - Thunk that calls `loginRequest` and updates Redux state on success/failure.

**`registerUser`** - Thunk that calls `registerRequest`, same lifecycle as login.

**`hydrateUserFromToken`** - Thunk that runs on app startup to restore session from stored token.
- Calls `/auth/me` to verify token validity
- If token is stale (401/403), clears session and redirects to login
- Used in `App.tsx` to hydrate auth on page load

### Route Guards (`features/auth/ProtectedRoute.tsx`)

**`<ProtectedRoute>`** - Wraps protected routes; redirects to `/login` if no access token.

**`<PublicRoute>`** - Wraps login/register; redirects to `/` if already authenticated.

### Global Error Handling

**`useAuthErrorHandler`** - Hook to wrap API calls and catch 401/403 errors, auto-logout.

**`useAuthErrorInterceptor`** - Hook that watches Redux `auth.error` and redirects on auth errors.

**`GlobalAuthErrorBoundary`** - Monitors localStorage changes to detect multi-tab logout.

## Routing Flow

```
┌─────────────────────────────┐
│   App.tsx                    │
│ ┌─────────────────────────┐  │
│ │ AppRoutes Component     │  │
│ │ - Dispatch              │  │
│ │   hydrateUserFromToken  │  │
│ │ - On first render       │  │
│ └─────────────────────────┘  │
└─────────────────────────────┘
          ↓
    ┌──────────────┐
    │ Auth stored? │
    └──────────────┘
      ↙     ↘
    Yes      No
    ↓        ↓
   OK    ┌────────────┐
         │    /login  │
         │ PublicRoute│
         └────────────┘
   
   ┌──────────────────────────┐
   │  Protected Routes        │
   │ - /                      │
   │ - /knowledge-base        │
   │ - /deals/:dealId         │
   │ ProtectedRoute wrapper   │
   └──────────────────────────┘
```

## API Error Handling

The backend returns errors with a `detail` field (Pydantic HTTPException). Examples:

```json
{
  "detail": "Incorrect email or password"
}

{
  "detail": "Email already registered"
}

{
  "detail": [
    {"field": "password", "msg": "Password too short"},
    {"field": "email", "msg": "Invalid format"}
  ]
}
```

`authApi.ts:request()` extracts and flattens these into user-facing error messages.

## Session Expiry Flow

1. **Backend**: Access token expires after 15 minutes (configurable in backend settings)
2. **Frontend**: Next API call returns 401/403
3. **`authApi.ts:request()`**: Throws `"Your session has expired. Please sign in again."`
4. **Component** (via `useAuthErrorHandler` or explicit try/catch): Catches error
5. **Redux**: Dispatch `logout()` → clears state and localStorage
6. **Router**: ProtectedRoute detects no token → redirects to `/login`

## Refresh Token Flow (Future)

The backend supports `/auth/refresh` endpoint:

1. Backend stores `refresh_token` in httponly cookie
2. When access token expires, call `/auth/refresh`
3. Backend validates refresh token and returns new access token
4. No need to re-login if refresh token is still valid

To implement: Create `refreshAccessToken` thunk in `authSlice.ts` and call it on 401 before logout.

## Multi-Tab Session Sync

If user logs out in one tab:

1. **Tab A**: Calls `/auth/logout` → clears localStorage
2. **Tab B**: `GlobalAuthErrorBoundary` detects storage change
3. **Result**: Auto-logout in all tabs, redirect to login

## Usage Examples

### Login/Register Component

```tsx
import { useDispatch, useSelector } from 'react-redux'
import { loginUser, registerUser } from './authSlice'
import type { AppDispatch, RootState } from '../../app/store'

export function LoginForm() {
  const dispatch = useDispatch<AppDispatch>()
  const { status, error } = useSelector((state: RootState) => state.auth)

  const handleLogin = async () => {
    const result = await dispatch(loginUser({ email: 'user@example.com', password: 'pass' }))
    
    if (loginUser.fulfilled.match(result)) {
      // Success - App.tsx routes to /
    }
  }

  return (
    <form>
      {error && <p>{error}</p>}
      <button disabled={status === 'loading'}>
        {status === 'loading' ? 'Signing in...' : 'Sign In'}
      </button>
    </form>
  )
}
```

### Protected Screen with API Calls

```tsx
import { useSelector } from 'react-redux'
import { useAuthErrorHandler } from '../../app/useAuthErrorHandler'
import type { RootState } from '../../app/store'

export function DealList() {
  const accessToken = useSelector((state: RootState) => state.auth.accessToken)
  const handleAuthError = useAuthErrorHandler()

  const loadDeals = async () => {
    try {
      const deals = await handleAuthError(
        fetchWithAuth('/deals', { accessToken })
      )
      if (!deals) return // Already redirected to login
      setDeals(deals)
    } catch (err) {
      // Handle non-auth errors
      setError(err instanceof Error ? err.message : 'Failed to load')
    }
  }

  useEffect(() => {
    void loadDeals()
  }, [])
}
```

### Logout

```tsx
import { useDispatch } from 'react-redux'
import { logout } from '../features/auth/authSlice'
import { logoutUser } from '../features/auth/authApi'

export function Navbar() {
  const dispatch = useDispatch()
  const navigate = useNavigate()

  const handleLogout = async () => {
    try {
      await logoutUser() // Server-side logout
    } catch {
      // Ignore server error, still clear client session
    }
    
    dispatch(logout())
    navigate('/login')
  }

  return <button onClick={handleLogout}>Sign Out</button>
}
```

## Backend Contract (DO NOT CHANGE)

These endpoints must remain stable for frontend to function:

- **POST** `/api/v1/auth/register` → `TokenResponse { access_token, user: UserResponse }`
- **POST** `/api/v1/auth/login` → `TokenResponse { access_token, user: UserResponse }`
- **POST** `/api/v1/auth/logout` → `{ message: "Logged out successfully" }`
- **GET** `/api/v1/auth/me` (requires `Authorization: Bearer {token}`) → `{ user: UserResponse }`
- **POST** `/api/v1/auth/refresh` (cookie-based) → `TokenResponse`

All auth errors must respond with `{ "detail": "<error message>" }` or array of detail objects.

## Debugging

### Check stored session

```typescript
const session = JSON.parse(localStorage.getItem('askver-auth') ?? '{}')
console.log(session.user, session.accessToken)
```

### Monitor Redux state

```typescript
// In browser DevTools Redux extension
// Watch `auth.status`, `auth.error`, `auth.accessToken`
```

### Test 401 redirect

```typescript
// Manually expire token in localStorage
localStorage.setItem('askver-auth', '{}')
// Refresh page or navigate - should go to login
```
