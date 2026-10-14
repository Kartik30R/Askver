# Knowledge Base API Integration

## Backend Contract

### Endpoints

#### 1. List Knowledge Assets
- **URL**: `POST /knowledge-base`
- **Request Body** (FormData):
  - `title` (string, required)
  - `asset_type` (string, required) - One of: `CASE_STUDY`, `PROPOSAL`, `SOW`, `SUCCESS_STORY`, `PRESENTATION`, `SOLUTION_ACCELERATOR`
  - `industry_tag` (string, optional)
  - `technology_tags` (JSON array stringified, optional) - e.g., `["React", "Go", "PostgreSQL"]`
  - `file` (File, required)

- **Response** (201 Created):
```typescript
{
  status: string
  asset_id: string (UUID)
}
```

#### 2. Upload Knowledge Asset
- **URL**: `GET /knowledge-base`
- **Query Parameters** (all optional):
  - `asset_type` - Filter by asset type
  - `industry` - Filter by industry tag
  - `limit` - Max results (default 100)

- **Response** (200 OK):
```typescript
[
  {
    id: string (UUID)
    title: string
    asset_type: string
    industry_tag: string | null
    technology_tags: string[] | null
    file_path: string
    file_type: string
    summary: string | null
    vector_doc_id: string | null
    indexing_status: 'INDEXED' | 'PROCESSING' | 'FAILED'
    created_at: string (ISO datetime)
    updated_at: string (ISO datetime)
  }
]
```

#### 3. Get Knowledge Asset by ID
- **URL**: `GET /knowledge-base/{asset_id}`
- **Response** (200 OK): Single `KnowledgeAsset` object (same as list response item)

#### 4. Delete Knowledge Asset
- **URL**: `DELETE /knowledge-base/{asset_id}`
- **Response** (200 OK):
```typescript
{
  status: string
  message: string
}
```

## Frontend Implementation

### Files Created/Updated

#### `knowledgeApi.ts`
- `listKnowledgeAssets(params?)` - List all assets with optional filtering
- `uploadKnowledgeAsset(formData, accessToken)` - Upload new asset
- `getKnowledgeAsset(assetId, accessToken)` - Get single asset
- `deleteKnowledgeAsset(assetId, accessToken)` - Delete asset

All functions accept `accessToken` from Redux auth state and pass it as Bearer token.

#### `KnowledgeBasePage.tsx`
- Updated to use Redux auth: `useSelector((state: RootState) => state.auth.accessToken)`
- All API calls now include access token
- Added proper error handling and debug logging
- Form validation and loading states
- Dependency on `accessToken` to reload assets when user logs in

### Type Contract

TypeScript types in `knowledgeApi.ts` match backend schema exactly:

```typescript
type KnowledgeAsset = {
  id: string
  title: string
  asset_type: 'CASE_STUDY' | 'PROPOSAL' | 'SOW' | 'SUCCESS_STORY' | 'PRESENTATION' | 'SOLUTION_ACCELERATOR'
  industry_tag: string | null
  technology_tags: string[] | null
  file_path: string
  file_type: string
  summary: string | null
  vector_doc_id: string | null
  indexing_status: 'INDEXED' | 'PROCESSING' | 'FAILED'
  created_at: string
  updated_at: string
}
```

## Authentication Flow

All knowledge base endpoints require valid JWT access token:

1. User logs in → Redux stores `accessToken`
2. KnowledgeBasePage reads `accessToken` from Redux
3. All API calls include `Authorization: Bearer {accessToken}` header
4. If 401/403 response → User is logged out and redirected to login
5. If token missing → Error message shown to user

## Debug Logging

All API calls log to browser console with `[📚 Knowledge]` prefix:

```typescript
[📚 Knowledge] GET /knowledge-base?limit=100
[📚 Knowledge] Loaded assets: [...]
[📚 Knowledge] POST /knowledge-base (multipart form)
[📚 Knowledge] Upload successful: { status: 'success', asset_id: '...' }
[📚 Knowledge] DELETE /knowledge-base/{id}
```

## Testing

### Test Upload Flow

1. Log in to the app
2. Navigate to "Knowledge Base"
3. Fill in form:
   - Title: "Customer Success Story - Retail"
   - Type: "SUCCESS_STORY"
   - Industry: "Retail"
   - Tags: "React, Go, AWS"
   - Select a PDF/DOC file
4. Click "Upload asset"
5. Check browser console for `[📚 Knowledge]` debug logs
6. After success, asset should appear in "Asset Library" list

### Test Delete Flow

1. In Asset Library, click trash icon on any asset
2. Asset should be removed from list
3. Check console for delete logs

### Test Session Expiry

1. Open DevTools → Application → localStorage
2. Delete `askver-auth` entry
3. Try to upload → Should show "Not authenticated" error
4. Should redirect to login automatically on next action

## Error Handling

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| "Cannot reach backend" | Backend not running | Start backend: `uvicorn app.main:app --host 127.0.0.1 --port 8000` |
| "Not authenticated" | No access token | Log in first |
| "Your session has expired" | Token is 401/403 | User automatically logged out and redirected |
| "technology_tags must be valid JSON array" | Invalid JSON format | Check comma-separated tech tags parsing |
| HTTP 500 | Backend error during file parsing/indexing | Check backend logs for stack trace |

## Configuration

### API Base URL

Set in `frontendt/.env`:
```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

Or environment variable when deploying to production.

## Next Steps

1. ✅ Knowledge base integration complete
2. Next: Integrate deals/deal document endpoints
3. Next: Integrate workflow/pipeline endpoints
4. Next: Integrate chat endpoints
