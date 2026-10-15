import React from 'react'
import {
  FileText,
  GitGraph,
  PanelTop,
  Sliders,
} from 'lucide-react'

export type ViewMode = 'pipeline' | 'tabs' | 'report_chat'

type DealDashboardHeaderProps = {
  pipelineTitle: string
  dealId?: string
  viewMode: ViewMode
  onChangeView: (mode: ViewMode) => void
  onOpenDrawer: () => void
}

export default function DealDashboardHeader({
  pipelineTitle,
  dealId,
  viewMode,
  onChangeView,
  onOpenDrawer,
}: DealDashboardHeaderProps) {
  return (
    <div className="cosmic-card p-4 flex flex-wrap items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        <div className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-ping" />
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            {pipelineTitle}
            <span className="text-xs font-mono font-normal text-cosmic-muted bg-cosmic-bg px-2 py-0.5 rounded border border-cosmic-border">
              {dealId ? `deal_${dealId.slice(0, 8)}` : 'deal_unknown'}
            </span>
          </h2>
        </div>
      </div>

      <div className="flex bg-cosmic-bg p-1 rounded-lg border border-cosmic-border">
        <button
          type="button"
          onClick={() => onChangeView('pipeline')}
          className={`flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
            viewMode === 'pipeline' ? 'bg-nagarro-green text-black' : 'text-cosmic-muted hover:text-white'
          }`}
        >
          <GitGraph className="w-3.5 h-3.5" />
          Pipeline Flow
        </button>
        <button
          type="button"
          onClick={() => onChangeView('tabs')}
          className={`flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
            viewMode === 'tabs' ? 'bg-nagarro-green text-black' : 'text-cosmic-muted hover:text-white'
          }`}
        >
          <PanelTop className="w-3.5 h-3.5" />
          Node Tabs
        </button>
        <button
          type="button"
          onClick={() => onChangeView('report_chat')}
          className={`flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
            viewMode === 'report_chat' ? 'bg-nagarro-green text-black' : 'text-cosmic-muted hover:text-white'
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          Report & AI Chat
        </button>
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onOpenDrawer}
          className="p-2 bg-cosmic-surface hover:bg-cosmic-border border border-cosmic-border rounded-lg text-nagarro-green relative transition-colors"
          title="Open Interactive HITL Instruction Drawer"
        >
          <Sliders className="w-4 h-4" />
          <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-nagarro-green animate-pulse" />
        </button>
      </div>
    </div>
  )
}
