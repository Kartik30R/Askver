import React from 'react'
import { CheckCircle2, Clock, FileText, Loader2, Paperclip, Trash2, UploadCloud } from 'lucide-react'
import type { DealDocument } from '../../features/deals/dealsApi'

type DealDocumentsPanelProps = {
  dealId?: string
  documents: DealDocument[]
  isDocumentsOpen: boolean
  onToggleDocuments: () => void
  onDocumentUpload: (event: React.FormEvent) => Promise<void> | void
  onDocumentDelete: (documentId: string) => Promise<void> | void
  onSelectedFileChange: (file: File | null) => void
  isLoadingDocuments: boolean
  isUploadingDocument: boolean
  documentCategory: string
  onDocumentCategoryChange: (category: string) => void
  selectedFile: File | null
  documentError: string
  documentSuccess: string
  isDeletingDeal: boolean
  onDeleteDeal: () => Promise<void> | void
}

export default function DealDocumentsPanel({
  dealId,
  documents,
  isDocumentsOpen,
  onToggleDocuments,
  onDocumentUpload,
  onDocumentDelete,
  onSelectedFileChange,
  isLoadingDocuments,
  isUploadingDocument,
  documentCategory,
  onDocumentCategoryChange,
  selectedFile,
  documentError,
  documentSuccess,
  isDeletingDeal,
  onDeleteDeal,
}: DealDocumentsPanelProps) {
  return (
    <div className="cosmic-card p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <button
          type="button"
          onClick={onToggleDocuments}
          className="flex flex-1 items-center justify-between gap-3 text-left"
        >
          <div className="flex items-center gap-2">
            <Paperclip className="w-4 h-4 text-nagarro-green" />
            <h3 className="text-lg font-bold text-white">Client Documents</h3>
          </div>
          <span className="text-xs text-cosmic-muted">{isDocumentsOpen ? 'Collapse' : 'Expand'}</span>
        </button>

        <button
          type="button"
          onClick={() => void onDeleteDeal()}
          disabled={isDeletingDeal}
          className="inline-flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs font-medium text-red-300 transition hover:border-red-500/60 hover:text-red-200 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isDeletingDeal ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
          {isDeletingDeal ? 'Deleting...' : 'Delete deal'}
        </button>
      </div>

      {isDocumentsOpen && (
        <div className="grid grid-cols-1 xl:grid-cols-[0.9fr_1.1fr] gap-5">
          <form onSubmit={onDocumentUpload} className="space-y-4 rounded-xl border border-cosmic-border bg-cosmic-bg/40 p-4">
            <div>
              <label className="block text-xs font-medium text-cosmic-muted mb-1.5">Document Category</label>
              <select
                value={documentCategory}
                onChange={(event) => onDocumentCategoryChange(event.target.value)}
                className="w-full bg-cosmic-bg border border-cosmic-border rounded-lg px-3 py-2 text-sm text-white focus:border-nagarro-green outline-none"
              >
                <option value="RFP">RFP</option>
                <option value="RFI">RFI</option>
                <option value="BRD">BRD</option>
                <option value="ARCHITECTURE">ARCHITECTURE</option>
                <option value="SCOPE">SCOPE</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-cosmic-muted mb-1.5">Upload File</label>
              <div className="border-2 border-dashed border-cosmic-border rounded-xl p-5 text-center bg-cosmic-bg/40">
                <UploadCloud className="w-8 h-8 text-nagarro-green mx-auto mb-2" />
                <input
                  type="file"
                  onChange={(event) => onSelectedFileChange(event.target.files?.[0] || null)}
                  className="block w-full text-sm text-cosmic-muted file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-nagarro-green file:text-black hover:file:bg-nagarro-hover"
                />
                {selectedFile && <p className="mt-3 text-xs text-white">Selected: {selectedFile.name}</p>}
              </div>
            </div>

            {documentError && <p className="text-sm text-red-400">{documentError}</p>}
            {documentSuccess && <p className="text-sm text-nagarro-green">{documentSuccess}</p>}

            <button type="submit" disabled={isUploadingDocument} className="btn-nagarro w-full flex items-center justify-center gap-2">
              {isUploadingDocument ? <><Loader2 className="w-4 h-4 animate-spin" /> Uploading...</> : <><FileText className="w-4 h-4" /> Upload Document</>}
            </button>
          </form>

          <div className="space-y-3 rounded-xl border border-cosmic-border bg-cosmic-bg/40 p-4">
            <div className="flex items-center justify-between text-xs uppercase tracking-wide text-cosmic-muted">
              <span>Indexed Documents</span>
              <span>{documents.length}</span>
            </div>

            {isLoadingDocuments ? (
              <div className="flex items-center justify-center py-8 text-cosmic-muted">
                <Loader2 className="w-4 h-4 animate-spin mr-2" /> Loading...
              </div>
            ) : documents.length === 0 ? (
              <div className="text-sm text-cosmic-muted py-8 text-center">No documents uploaded yet for this deal.</div>
            ) : (
              documents.map((doc) => (
                <div key={doc.id} className="rounded-lg border border-cosmic-border bg-cosmic-surface/60 p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-[10px] uppercase tracking-wide text-nagarro-green">{doc.document_category}</div>
                      <div className="mt-1 text-sm font-semibold text-white">{doc.filename}</div>
                    </div>
                    <button
                      type="button"
                      onClick={() => void onDocumentDelete(doc.id)}
                      className="text-cosmic-muted hover:text-red-400 transition-colors"
                      aria-label={`Delete ${doc.filename}`}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>

                  <div className="mt-3 flex items-center justify-between text-[11px] text-cosmic-muted">
                    <span className="flex items-center gap-1">
                      {doc.indexing_status === 'INDEXED' ? <CheckCircle2 className="w-3.5 h-3.5 text-nagarro-green" /> : <Clock className="w-3.5 h-3.5 text-amber-400" />}
                      {doc.indexing_status}
                    </span>
                    <span>{doc.chunk_count} chunks</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
