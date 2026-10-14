import React from 'react'
import { AlertTriangle, Pause, Play, Sliders, X } from 'lucide-react'
import type { PipelineNode } from './PipelineFlow'

type HITLDrawerProps = {
  nodes: PipelineNode[]
  onClose: () => void
}

export default function HITLDrawer({ nodes, onClose }: HITLDrawerProps) {
  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/50 backdrop-blur-xs flex justify-end">
      <div className="w-full max-w-md bg-cosmic-surface border-l border-cosmic-border h-full flex flex-col shadow-2xl animate-in slide-in-from-right duration-200">
        <div className="p-4 border-b border-cosmic-border flex items-center justify-between bg-cosmic-bg/80">
          <div className="flex items-center gap-2">
            <Sliders className="w-4 h-4 text-nagarro-green" />
            <h3 className="text-sm font-bold text-white">HITL Pipeline Steering (VS Code Panel)</h3>
          </div>
          <button type="button" onClick={onClose} className="text-cosmic-muted hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 p-6 space-y-6 overflow-y-auto">
          <div className="space-y-2">
            <label className="text-xs font-semibold text-cosmic-muted uppercase tracking-wider">State Machine Control</label>
            <div className="grid grid-cols-2 gap-3">
              <button type="button" className="flex items-center justify-center gap-2 p-2.5 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20 text-xs font-semibold">
                <Pause className="w-3.5 h-3.5" /> Pause Workflow
              </button>
              <button type="button" className="flex items-center justify-center gap-2 p-2.5 rounded-lg bg-nagarro-green/10 border border-nagarro-green/30 text-nagarro-green hover:bg-nagarro-green/20 text-xs font-semibold">
                <Play className="w-3.5 h-3.5" /> Resume Workflow
              </button>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-cosmic-muted uppercase tracking-wider">Inject Node Instruction</label>
            <select className="w-full bg-cosmic-bg border border-cosmic-border rounded-lg p-2.5 text-xs text-white focus:border-nagarro-green outline-none">
              {nodes.map((node) => (
                <option key={node.id} value={node.id}>{node.label}</option>
              ))}
            </select>
            <textarea
              rows={4}
              placeholder="e.g., Target EU DORA compliance specifically in pain point detection..."
              className="w-full bg-cosmic-bg border border-cosmic-border rounded-lg p-3 text-xs text-white focus:border-nagarro-green outline-none"
            />
            <button type="button" className="btn-nagarro w-full text-xs py-2.5">
              Inject Instruction Mid-Flight
            </button>
          </div>

          <div className="p-4 bg-amber-950/20 border border-amber-500/40 rounded-xl space-y-3">
            <h4 className="text-xs font-bold text-amber-400 flex items-center gap-1.5">
              <AlertTriangle className="w-4 h-4" /> Mandatory Review Checkpoint
            </h4>
            <p className="text-[11px] text-cosmic-muted">
              Approve state machine execution to proceed to final CXO Brief synthesis.
            </p>
            <div className="flex gap-2">
              <button type="button" className="btn-nagarro flex-1 text-xs py-2">Approve</button>
              <button type="button" className="px-3 py-2 rounded-lg bg-cosmic-bg border border-cosmic-border text-xs text-cosmic-muted hover:text-white">Request Revisions</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
