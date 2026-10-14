# Integration Steps: Replacing Ad-Hoc Auth with Redux

## What Changed

### Before
- Direct fetch calls in Login.tsx without async thunks
- Manual state management with useState
- No global request middleware
- No automatic session restoration on page load
- 401 errors not handled consistently

### After
- Redux async thunks (`loginUser`, `registerUser`, `hydrateUserFromToken`)
- Automatic JWT token injection in all requests
- Global 401 → logout → redirect to login flow
- Session restored from localStorage on app startup
- Typed, reusable auth hooks and selectors

## Files to Update for Feature Screens

When building new protected features (deals, knowledge base, etc.) that call backend APIs:

### 1. Import the access token

```typescript
import { useSelector } from 'react-redux'
import type { RootState } from '../../app/store'

const accessToken = useSelector((state: RootState) => state.auth.accessToken)
```

### 2. Use `fetchWithAuth` for API calls

```typescript
import { fetchWithAuth } from '../../utils/fetchWithAuth'

const data = await fetchWithAuth('/deals', {
  method: 'GET',
  accessToken,
})
```

### 3. Add auth error interception (optional but recommended)

```typescript
import { useAuthErrorHandler } from '../../app/useAuthErrorHandler'

const handleAuthError = useAuthErrorHandler()

const result = await handleAuthError(
  fetchWithAuth('/deals', { accessToken })
)
if (!result) return // Already handling redirect to login
```

### Profile Screen Example

```tsx
import { useSelector } from 'react-redux'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchWithAuth } from '../../utils/fetchWithAuth'
import { useAuthErrorHandler } from '../../app/useAuthErrorHandler'
import type { RootState } from '../../app/store'

export function ProfilePage() {
  const navigate = useNavigate()
  const accessToken = useSelector((state: RootState) => state.auth.accessToken)
  const user = useSelector((state: RootState) => state.auth.user)
  const handleAuthError = useAuthErrorHandler()

  const [profile, setProfile] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!accessToken) return

    const load = async () => {
      try {
        // Example: custom profile endpoint
        const data = await handleAuthError(
          fetchWithAuth('/users/profile', { 
            method: 'GET',
            accessToken 
          })
        )
        
        if (data) setProfile(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load profile')
      }
    }

    void load()
  }, [accessToken, handleAuthError])

  if (!user) return <p>Loading...</p>
  if (error) return <p className="text-red-500">{error}</p>

  return (
    <div>
      <h1>{user.name}</h1>
      <p>{user.email}</p>
      {profile && <pre>{JSON.stringify(profile, null, 2)}</pre>}
    </div>
  )
}
```

## Testing the Auth Flow

### 1. Register a new user

- Go to http://localhost:5173/login
- Switch to "Register Account"
- Fill in name, email, password
- Click create
- Should redirect to `/` (deal list)

### 2. Test session persistence

- Register/login successfully
- Refresh page (`Ctrl+R`)
- Should see the app without re-entering credentials
- Check browser DevTools → Application → localStorage → `askver-auth`

### 3. Test logout

- Click "Sign Out" in sidebar
- Should redirect to login
- Refresh page
- Should stay on login (session cleared)

### 4. Test session expiry

- Open DevTools Console
- Run: `localStorage.removeItem('askver-auth')`
- Refresh page
- Should redirect to login

### 5. Test wrong credentials

- Go to login
- Enter invalid email/password
- Should show error message
- Should stay on login (no redirect)

## Environment Configuration

Create `.env` in workspace root or frontend root:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

Or in production:

```env
VITE_API_BASE_URL=https://api.example.com/api/v1
```

The `fetchWithAuth` utility will respect this via:
- `import.meta.env.VITE_API_BASE_URL` if set
- Fallback: `http://localhost:8000/api/v1`

## Common Issues & Fixes

### Q: "Cannot find module authSlice"
**A**: Make sure all files are created in the correct path:
- `src/features/auth/authSlice.ts`
- `src/features/auth/authApi.ts`
- `src/features/auth/ProtectedRoute.tsx`
- `src/app/store.ts`

### Q: Button disabled but no loading state text
**A**: Check selector usage:
```tsx
const { status, error } = useSelector((state: RootState) => state.auth)
// status is: 'idle' | 'loading' | 'succeeded' | 'failed'
```

### Q: "Bearer token not found in headers"
**A**: Pass `accessToken` explicitly:
```tsx
const accessToken = useSelector((state: RootState) => state.auth.accessToken)
await fetchWithAuth('/endpoint', { accessToken })
```

### Q: Getting redirected to login even after successful login
**A**: Check that:
1. Backend returns `{ "access_token": "...", "user": {...} }`
2. Redux action payload matches this shape
3. `ProtectedRoute` checks `state.auth.accessToken` (not null/undefined)

## Next Steps

1. ✅ Auth slice and routing implemented
2. ✅ Protected routes guarding protected pages
3. ✅ Session restoration on app load
4. Next: Integrate other features (deals, documents, chat) with auth
   - Update existing `deals/dealsApi.ts` to use `fetchWithAuth`
   - Update existing `workflow/reportApi.ts`, `chatApi.ts` to use `fetchWithAuth`
   - Test end-to-end login → deal creation → upload → chat flow

## Architecture Diagram

```
┌──────────────────────────────────────────┐
│         React App (main.tsx)             │
│        ┌────────────────────────┐        │
│        │  Provider (Redux Store)│        │
│        │  ┌──────────────────┐  │        │
│        │  │ auth reducer     │  │        │
│        │  └──────────────────┘  │        │
│        └────────────────────────┘        │
│              ↓                            │
│        ┌────────────────────────┐        │
│        │  BrowserRouter         │        │
│        │  - AppRoutes (hydrate) │        │
│        │  - PublicRoute(/login)│        │
│        │  - ProtectedRoute(/)   │        │
│        └────────────────────────┘        │
└──────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────┐
│         Redux Auth State                 │
│  - user: AuthUser | null                 │
│  - accessToken: string | null            │
│  - status: 'idle' | 'loading' | ...     │
│  - error: string | null                  │
└──────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────┐
│      Route Guards & Hooks                │
│  - ProtectedRoute: checks accessToken    │
│  - useAuthErrorHandler: wraps API calls  │
│  - useSelector: read auth state          │
│  - useDispatch: dispatch thunks          │
└──────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────┐
│         API Utilities                    │
│  - fetchWithAuth: injects Bearer token   │
│  - login/register requests               │
│  - Error extraction & 401 handling       │
└──────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────┐
│         FastAPI Backend                  │
│  - /auth/login                           │
│  - /auth/register                        │
│  - /auth/logout                          │
│  - /auth/me                              │
│  - Protected endpoints (require token)   │
└──────────────────────────────────────────┘
```
