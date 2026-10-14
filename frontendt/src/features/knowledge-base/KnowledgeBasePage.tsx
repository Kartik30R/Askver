import React, { useEffect, useMemo, useState } from 'react'
import { useSelector } from 'react-redux'
import { FileText, FileUp, ListFilter, Loader2, Trash2, CheckCircle2, UploadCloud } from 'lucide-react'

import type { RootState } from '../../app/store'
import { deleteKnowledgeAsset, listKnowledgeAssets, type KnowledgeAsset, uploadKnowledgeAsset } from './knowledgeApi'

const assetTypeOptions = ['CASE_STUDY', 'PROPOSAL', 'SOW', 'SUCCESS_STORY', 'PRESENTATION', 'SOLUTION_ACCELERATOR'] as const

export default function KnowledgeBasePage() {
  const accessToken = useSelector((state: RootState) => state.auth.accessToken)
  
  const [assets, setAssets] = useState<KnowledgeAsset[]>([])
  const [title, setTitle] = useState('')
  const [assetType, setAssetType] = useState<typeof assetTypeOptions[number]>(assetTypeOptions[0])
  const [industryTag, setIndustryTag] = useState('')
  const [technologyTags, setTechnologyTags] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  const summaryStats = useMemo(() => {
    return {
      total: assets.length,
      indexed: assets.filter((asset) => asset.indexing_status === 'INDEXED').length,
      processing: assets.filter((asset) => asset.indexing_status === 'PROCESSING').length,
    }
  }, [assets])

  const loadAssets = async () => {
    if (!accessToken) {
      console.warn('[📚 Knowledge] No access token available')
      return
    }

    setLoading(true)
    setError('')

    try {
      console.log('[📚 Knowledge] Loading assets...')
      const response = await listKnowledgeAssets({ accessToken })
      console.log('[📚 Knowledge] Loaded assets:', response)
      setAssets(response)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load knowledge base assets'
      console.error('[📚 Knowledge] Load error:', message)
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadAssets()
  }, [accessToken])

  const handleUpload = async (event: React.FormEvent) => {
    event.preventDefault()

    if (!accessToken) {
      setError('Not authenticated. Please sign in again.')
      return
    }

    if (!selectedFile) {
      setError('Please select a file to upload.')
      return
    }

    const formData = new FormData()
    formData.append('title', title)
    formData.append('asset_type', assetType)
    formData.append('industry_tag', industryTag)
    formData.append(
      'technology_tags',
      JSON.stringify(technologyTags.split(',').map((tag) => tag.trim()).filter(Boolean)),
    )
    formData.append('file', selectedFile)

    setUploading(true)
    setError('')
    setSuccessMessage('')

    try {
      console.log('[📚 Knowledge] Uploading asset:', { title, assetType, industryTag })
      const response = await uploadKnowledgeAsset(formData, accessToken)
      console.log('[📚 Knowledge] Upload response:', response)
      setSuccessMessage('Knowledge asset uploaded successfully.')
      setTitle('')
      setIndustryTag('')
      setTechnologyTags('')
      setSelectedFile(null)
      await loadAssets()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Upload failed'
      console.error('[📚 Knowledge] Upload error:', message)
      setError(message)
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (assetId: string) => {
    if (!accessToken) {
      setError('Not authenticated. Please sign in again.')
      return
    }

    try {
      console.log('[📚 Knowledge] Deleting asset:', assetId)
      await deleteKnowledgeAsset(assetId, accessToken)
      setSuccessMessage('Asset deleted successfully.')
      await loadAssets()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Delete failed'
      console.error('[📚 Knowledge] Delete error:', message)
      setError(message)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Knowledge Base</h1>
          <p className="text-sm text-cosmic-muted mt-1">Upload reusable proposal, case study, and solution assets for cross-deal retrieval.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="cosmic-card p-4">
          <div className="text-xs uppercase tracking-wide text-cosmic-muted">Total Assets</div>
          <div className="mt-3 text-3xl font-bold text-white">{summaryStats.total}</div>
        </div>
        <div className="cosmic-card p-4">
          <div className="text-xs uppercase tracking-wide text-cosmic-muted">Indexed</div>
          <div className="mt-3 text-3xl font-bold text-nagarro-green">{summaryStats.indexed}</div>
        </div>
        <div className="cosmic-card p-4">
          <div className="text-xs uppercase tracking-wide text-cosmic-muted">Processing</div>
          <div className="mt-3 text-3xl font-bold text-amber-400">{summaryStats.processing}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1.1fr_0.9fr] gap-6">
        <div className="cosmic-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <UploadCloud className="w-4 h-4 text-nagarro-green" />
            <h2 className="text-lg font-semibold text-white">Upload Knowledge Asset</h2>
          </div>

          <form onSubmit={handleUpload} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-cosmic-muted mb-1.5">Title</label>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
                placeholder="Customer Success Story - Retail Modernization"
                className="w-full bg-cosmic-bg border border-cosmic-border rounded-lg px-3 py-2 text-sm text-white focus:border-nagarro-green outline-none"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-cosmic-muted mb-1.5">Asset Type</label>
                <select
                  value={assetType}
                  onChange={(e) => setAssetType(e.target.value)}
                  className="w-full bg-cosmic-bg border border-cosmic-border rounded-lg px-3 py-2 text-sm text-white focus:border-nagarro-green outline-none"
                >
                  {assetTypeOptions.map((option) => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-cosmic-muted mb-1.5">Industry Tag</label>
                <input
                  value={industryTag}
                  onChange={(e) => setIndustryTag(e.target.value)}
                  placeholder="BFSI"
                  className="w-full bg-cosmic-bg border border-cosmic-border rounded-lg px-3 py-2 text-sm text-white focus:border-nagarro-green outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-cosmic-muted mb-1.5">Technology Tags</label>
              <input
                value={technologyTags}
                onChange={(e) => setTechnologyTags(e.target.value)}
                placeholder="React, Go, Postgres, AWS"
                className="w-full bg-cosmic-bg border border-cosmic-border rounded-lg px-3 py-2 text-sm text-white focus:border-nagarro-green outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-cosmic-muted mb-1.5">Upload File</label>
              <div className="border-2 border-dashed border-cosmic-border rounded-xl p-6 text-center bg-cosmic-bg/40 hover:border-nagarro-green/50 transition-colors">
                <FileUp className="w-8 h-8 text-nagarro-green mx-auto mb-2" />
                <input
                  type="file"
                  required
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  className="block w-full text-sm text-cosmic-muted file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-nagarro-green file:text-black hover:file:bg-nagarro-hover"
                />
                {selectedFile && <p className="mt-3 text-xs text-white">Selected: {selectedFile.name}</p>}
              </div>
            </div>

            {error && <p className="text-sm text-red-400">{error}</p>}
            {successMessage && <p className="text-sm text-nagarro-green">{successMessage}</p>}

            <button type="submit" disabled={uploading} className="btn-nagarro w-full flex items-center justify-center gap-2">
              {uploading ? <><Loader2 className="w-4 h-4 animate-spin" /> Uploading...</> : <><FileText className="w-4 h-4" /> Upload asset</>}
            </button>
          </form>
        </div>

        <div className="cosmic-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <ListFilter className="w-4 h-4 text-nagarro-green" />
            <h2 className="text-lg font-semibold text-white">Asset Library</h2>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12 text-cosmic-muted">
              <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading assets...
            </div>
          ) : assets.length === 0 ? (
            <div className="text-sm text-cosmic-muted py-10 text-center">No knowledge assets yet.</div>
          ) : (
            <div className="space-y-3 max-h-[620px] overflow-y-auto pr-1">
              {assets.map((asset) => (
                <div key={asset.id} className="border border-cosmic-border rounded-lg p-4 bg-cosmic-bg/50">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-xs font-medium uppercase tracking-wide text-nagarro-green">{asset.asset_type}</div>
                      <h3 className="mt-1 text-base font-semibold text-white">{asset.title}</h3>
                    </div>
                    <button
                      type="button"
                      onClick={() => void handleDelete(asset.id)}
                      className="text-cosmic-muted hover:text-red-400 transition-colors"
                      aria-label={`Delete ${asset.title}`}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>

                  <div className="mt-3 flex flex-wrap gap-2">
                    {asset.industry_tag && (
                      <span className="text-[10px] px-2 py-1 rounded-full bg-cosmic-border text-cosmic-muted">{asset.industry_tag}</span>
                    )}
                    {asset.technology_tags?.slice(0, 4).map((tag) => (
                      <span key={tag} className="text-[10px] px-2 py-1 rounded-full bg-cosmic-border/80 text-white">{tag}</span>
                    ))}
                  </div>

                  <div className="mt-4 flex items-center justify-between text-xs text-cosmic-muted">
                    <span className="flex items-center gap-1">
                      {asset.indexing_status === 'INDEXED' ? <CheckCircle2 className="w-3.5 h-3.5 text-nagarro-green" /> : <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-400" />}
                      {asset.indexing_status}
                    </span>
                    <span>{asset.file_type.toUpperCase()}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
