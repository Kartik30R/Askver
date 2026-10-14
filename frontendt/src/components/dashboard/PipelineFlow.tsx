import React from 'react'
import { AlertTriangle, CheckCircle2, Clock, Loader2 } from 'lucide-react'

export type PipelineNodeState = 'completed' | 'paused' | 'failed' | 'running' | 'pending'

export type PipelineNode = {
  id: string
  label: string
  status: PipelineNodeState
}

type PipelineFlowProps = {
  nodes: PipelineNode[]
  statusBanner: string
  onNodeClick: (nodeId: string) => void
}

export default function PipelineFlow({ nodes, statusBanner, onNodeClick }: PipelineFlowProps) {
  return (
    <div className="cosmic-card p-6 overflow-hidden">
      <div className="text-xs font-semibold text-cosmic-muted mb-4 uppercase tracking-wider flex items-center justify-between">
        <span>LangGraph Execution Topology</span>
        <span className={`flex items-center gap-1 ${statusBanner.toLowerCase().includes('failed') ? 'text-red-400' : statusBanner.toLowerCase().includes('paused') || statusBanner.toLowerCase().includes('review') ? 'text-amber-400' : 'text-nagarro-green'}`}>
          {statusBanner.toLowerCase().includes('failed') ? <AlertTriangle className="w-3.5 h-3.5" /> : <Clock className="w-3.5 h-3.5" />}
          {statusBanner}
        </span>
      </div>

      <div className="pipeline-flow-scroll overflow-x-auto overflow-y-hidden pb-2">
        <div className="flex min-w-max items-center gap-4 py-6">
        {nodes.map((node, idx) => (
          <React.Fragment key={node.id}>
            <div
              onClick={() => onNodeClick(node.id)}
              className={`w-48 p-4 rounded-xl border transition-all cursor-pointer ${
                node.status === 'completed'
                  ? 'bg-cosmic-surface/90 border-nagarro-green/40 hover:border-nagarro-green'
                  : node.status === 'paused'
                    ? 'bg-amber-950/20 border-amber-500/60 animate-pulse'
                    : node.status === 'failed'
                      ? 'bg-red-950/20 border-red-500/40'
                      : node.status === 'running'
                        ? 'bg-blue-950/20 border-blue-500/40'
                        : 'bg-cosmic-bg/40 border-cosmic-border opacity-50'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-mono uppercase text-cosmic-muted">Stage 0{idx + 1}</span>
                {node.status === 'completed' && <CheckCircle2 className="w-4 h-4 text-nagarro-green" />}
                {node.status === 'paused' && <Clock className="w-4 h-4 text-amber-400" />}
                {node.status === 'failed' && <AlertTriangle className="w-4 h-4 text-red-400" />}
                {node.status === 'running' && <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />}
                {node.status === 'pending' && <div className="w-3 h-3 rounded-full border border-cosmic-muted" />}
              </div>
              <h4 className="text-xs font-bold text-white mb-1">{node.label}</h4>
              <span className={`text-[10px] font-semibold uppercase ${
                node.status === 'completed' ? 'text-nagarro-green' : node.status === 'paused' ? 'text-amber-400' : node.status === 'failed' ? 'text-red-400' : node.status === 'running' ? 'text-blue-400' : 'text-cosmic-muted'
              }`}>
                {node.status.toUpperCase()}
              </span>
            </div>

            {idx < nodes.length - 1 && (
              <div className={`h-0.5 w-6 ${node.status === 'completed' ? 'bg-nagarro-green' : 'bg-cosmic-border'}`} />
            )}
          </React.Fragment>
        ))}
        </div>
      </div>
    </div>
  )
}
