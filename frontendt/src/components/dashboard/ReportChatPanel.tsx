import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { MessageSquareCode, Send } from 'lucide-react'

type ChatMessage = {
  role: 'user' | 'assistant'
  text: string
}

type Proposal = {
  proposed_text: string
  proposed_diff_id?: string
}

type ReportChatPanelProps = {
  targetCompany: string
  targetIndustry: string
  meetingObjective: string
  pipelineState: Record<string, unknown> | null
  reportMarkdown: string
  chatMessages: ChatMessage[]
  chatLoading: boolean
  proposal: Proposal | null
  chatInput: string
  selectedSection: string
  onChatInputChange: (value: string) => void
  onChatSubmit: () => Promise<void> | void
  onGenerateRevision: () => Promise<void> | void
  onClearDraft: () => void
  onSectionChange: (value: string) => void
  onProposalDecision: (approved: boolean) => Promise<void> | void
}

export default function ReportChatPanel({
  targetCompany,
  targetIndustry,
  meetingObjective,
  pipelineState,
  reportMarkdown,
  chatMessages,
  chatLoading,
  proposal,
  chatInput,
  selectedSection,
  onChatInputChange,
  onChatSubmit,
  onGenerateRevision,
  onClearDraft,
  onSectionChange,
  onProposalDecision,
}: ReportChatPanelProps) {
  return (
    <div className="grid grid-cols-1 gap-6 h-[650px] lg:grid-cols-12">
      <div className="lg:col-span-7 cosmic-card p-6 flex flex-col min-h-0">
        <div className="mb-5 flex flex-col gap-3 border-b border-cosmic-border pb-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Latest strategy report</p>
              <h3 className="mt-2 text-2xl font-bold text-white">Executive Brief Preview</h3>
            </div>
            <div className="rounded-full border border-nagarro-green/30 bg-nagarro-green/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-nagarro-green">
              {targetCompany}
            </div>
          </div>
          <div className="flex flex-wrap gap-2 text-[10px] text-cosmic-muted">
            <span className="rounded-full border border-cosmic-border bg-cosmic-bg/60 px-2.5 py-1">Industry: {targetIndustry}</span>
            <span className="rounded-full border border-cosmic-border bg-cosmic-bg/60 px-2.5 py-1">Objective: {meetingObjective}</span>
            <span className="rounded-full border border-cosmic-border bg-cosmic-bg/60 px-2.5 py-1">Snapshot v{(pipelineState as Record<string, unknown> | null)?.version ?? 1}</span>
          </div>
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto pr-1">
          <div className="prose prose-invert max-w-none text-sm text-cosmic-text space-y-4">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{reportMarkdown || '# Report pending\n\nThe newest report has not been generated yet.'}</ReactMarkdown>
          </div>
        </div>
      </div>

      <div className="lg:col-span-5 cosmic-card flex flex-col min-h-0">
        <div className="border-b border-cosmic-border bg-cosmic-surface/60 p-4">
          <div className="mb-2 flex items-center justify-between gap-3">
            <span className="flex items-center gap-2 text-xs font-bold text-white">
              <MessageSquareCode className="w-4 h-4 text-nagarro-green" />
              AI Strategy Copilot
            </span>
            <span className="rounded-full border border-cosmic-border bg-cosmic-bg/60 px-2 py-0.5 text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">
              report-grounded
            </span>
          </div>
          <p className="text-[10px] uppercase tracking-[0.16em] text-cosmic-muted">Ask anything about the deal, brief, or workflow.</p>
        </div>

        <div className="flex-1 min-h-0 space-y-4 overflow-y-auto p-4 text-xs">
          {chatMessages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={message.role === 'user'
                ? 'bg-nagarro-green/10 text-white p-3 rounded-lg border border-nagarro-green/30 ml-6'
                : 'bg-cosmic-surface p-3 rounded-lg border border-cosmic-border mr-6'}
            >
              <p className="font-semibold mb-1 text-white">
                {message.role === 'user' ? 'User' : 'AI Assistant'}
              </p>
              <div className="text-cosmic-muted prose prose-invert prose-sm max-w-none [&_p]:mb-2 [&_ul]:my-2 [&_ol]:my-2 [&_li]:mb-1">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{String(message.text)}</ReactMarkdown>
              </div>
            </div>
          ))}

          {proposal && (
            <div className="bg-amber-950/20 border border-amber-500/40 rounded-lg p-3 mr-6 space-y-3">
              <p className="font-semibold text-amber-400 mb-2">Proposed Edit</p>
              <div className="text-cosmic-muted prose prose-invert prose-sm max-w-none [&_p]:mb-2 [&_ul]:my-2 [&_ol]:my-2 [&_li]:mb-1">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{String(proposal.proposed_text)}</ReactMarkdown>
              </div>
              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => void onProposalDecision(true)}
                  disabled={chatLoading}
                  className="flex-1 btn-nagarro text-xs py-2 disabled:opacity-50"
                >
                  Approve
                </button>
                <button
                  type="button"
                  onClick={() => void onProposalDecision(false)}
                  disabled={chatLoading}
                  className="flex-1 px-3 py-2 rounded-lg bg-cosmic-bg border border-cosmic-border text-xs text-cosmic-muted hover:text-white disabled:opacity-50"
                >
                  Reject
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="shrink-0 space-y-3 border-t border-cosmic-border bg-cosmic-bg/80 p-3">
          <div className="flex items-center gap-2 rounded-lg border border-cosmic-border bg-cosmic-surface px-2.5 py-1.5">
            <span className="text-[10px] uppercase tracking-[0.18em] text-cosmic-muted">Context</span>
            <select
              value={selectedSection || 'general'}
              onChange={(event) => onSectionChange(event.target.value)}
              className="flex-1 appearance-none rounded-md border border-cosmic-border bg-cosmic-bg px-2 py-1 text-xs text-white focus:outline-none focus:ring-1 focus:ring-nagarro-green"
            >
              <option value="general" className="bg-cosmic-surface text-white">General chat</option>
              <option value="cxo_executive_brief" className="bg-cosmic-surface text-white">CXO Executive Brief</option>
              <option value="financial_intelligence" className="bg-cosmic-surface text-white">Financial Intelligence</option>
              <option value="industry_analysis" className="bg-cosmic-surface text-white">Industry Analysis</option>
              <option value="priorities_and_pain_points" className="bg-cosmic-surface text-white">Priorities & Pain Points</option>
            </select>
          </div>
          <p className="text-[10px] leading-5 text-cosmic-muted">
            General chat uses the broader deal context. Choose a specific section to enable targeted revisions for that module.
          </p>

          <div className="flex items-center gap-2">
            <input
              type="text"
              value={chatInput}
              onChange={(event) => onChatInputChange(event.target.value)}
              placeholder="Ask about the report, the workflow, or request a rewrite..."
              className="flex-1 rounded-lg border border-cosmic-border bg-cosmic-surface px-3 py-2 text-xs text-white placeholder:text-cosmic-muted focus:border-nagarro-green focus:outline-none"
            />
            <button
              type="button"
              onClick={() => void onChatSubmit()}
              disabled={chatLoading}
              className="btn-nagarro rounded-lg p-2 disabled:opacity-50"
            >
              <Send className="w-4 h-4 text-black" />
            </button>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => void onGenerateRevision()}
              disabled={chatLoading || selectedSection === 'general'}
              title={selectedSection === 'general' ? 'Choose a specific section before generating a revision.' : undefined}
              className="btn-nagarro w-full text-xs py-2.5 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Generate revision
            </button>
            <button
              type="button"
              onClick={onClearDraft}
              className="w-full rounded-lg border border-cosmic-border bg-cosmic-surface px-3 py-2 text-xs text-cosmic-muted transition-colors hover:text-white"
            >
              Clear draft
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
