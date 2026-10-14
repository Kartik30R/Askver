import React, { useMemo, useState } from 'react'
import { AlertTriangle, Pause, Play, Sliders, X } from 'lucide-react'
import { submitDynamicInstruction } from '../../features/workflow/workflowApi'
import type { PipelineNode } from './PipelineFlow'

type HITLDrawerProps = {
  dealId: string
  nodes: PipelineNode[]
  onClose: () => void
  onInstructionSubmitted?: () => void
}

export default function HITLDrawer({ dealId, nodes, onClose, onInstructionSubmitted }: HITLDrawerProps) {
  const [selectedNodes, setSelectedNodes] = useState<string[]>(['company_research'])
  const [rerunFromNode, setRerunFromNode] = useState<string>('company_research')
  const [instructionText, setInstructionText] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const availableNodeOptions = useMemo(
    () => nodes.filter((node) => !!node.id).map((node) => ({ value: node.id, label: node.label })),
    [nodes],
  )

  const handleNodeToggle = (nodeId: string) => {
    setSelectedNodes((current) => {
      const next = current.includes(nodeId) ? current.filter((id) => id !== nodeId) : [...current, nodeId]
      if (next.length === 0) {
        return [nodeId]
      }
      return next
    })
  }

  const handleSubmit = async () => {
    if (!instructionText.trim()) {
      setError('Please enter an instruction before injecting.')
      return
    }
    if (!dealId) {
      setError('This deal is not ready for instruction injection.')
      return
    }

    setIsSubmitting(true)
    setError('')
    setSuccess('')

    try {
      const payload = {
        instructions: [instructionText.trim()],
        target_nodes: selectedNodes,
        rerun_from_node: rerunFromNode || selectedNodes[0],
        priority: 5,
      }

      await submitDynamicInstruction(dealId, payload)
      setSuccess('Instruction queued and the workflow is rerunning from the selected node.')
      if (onInstructionSubmitted) onInstructionSubmitted()
      setInstructionText('')
      setTimeout(() => onClose(), 400)
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Unable to inject the instruction.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/50 backdrop-blur-xs flex justify-end">
      <div className="w-full max-w-md bg-cosmic-surface border-l border-cosmic-border h-full flex flex-col shadow-2xl animate-in slide-in-from-right duration-200">
        <div className="p-4 border-b border-cosmic-border flex items-center justify-between bg-cosmic-bg/80">
          <div className="flex items-center gap-2">
            <Sliders className="w-4 h-4 text-nagarro-green" />
            <h3 className="text-sm font-bold text-white">HITL Pipeline Steering</h3>
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

            <div className="space-y-2 rounded-xl border border-cosmic-border bg-cosmic-bg/40 p-3">
              <div className="text-[10px] uppercase tracking-[0.14em] text-cosmic-muted">Target nodes</div>
              <div className="flex flex-wrap gap-2">
                {availableNodeOptions.map((node) => {
                  const active = selectedNodes.includes(node.value)
                  return (
                    <button
                      key={node.value}
                      type="button"
                      onClick={() => handleNodeToggle(node.value)}
                      className={`rounded-full border px-2.5 py-1 text-[10px] font-medium ${active ? 'border-nagarro-green bg-nagarro-green/15 text-nagarro-green' : 'border-cosmic-border bg-cosmic-bg text-cosmic-muted'}`}
                    >
                      {node.label}
                    </button>
                  )
                })}
              </div>
            </div>

            <label className="text-[10px] uppercase tracking-[0.14em] text-cosmic-muted">Rerun from</label>
            <select
              value={rerunFromNode}
              onChange={(event) => setRerunFromNode(event.target.value)}
              className="w-full bg-cosmic-bg border border-cosmic-border rounded-lg p-2.5 text-xs text-white focus:border-nagarro-green outline-none"
            >
              {availableNodeOptions.map((node) => (
                <option key={node.value} value={node.value}>{node.label}</option>
              ))}
            </select>

            <textarea
              rows={5}
              value={instructionText}
              onChange={(event) => setInstructionText(event.target.value)}
              placeholder="e.g., Focus on EU DORA compliance and prioritize the modernization roadmap for the pain point detector and downstream outputs."
              className="w-full bg-cosmic-bg border border-cosmic-border rounded-lg p-3 text-xs text-white focus:border-nagarro-green outline-none"
            />
            <button
              type="button"
              disabled={isSubmitting}
              onClick={() => void handleSubmit()}
              className="btn-nagarro w-full text-xs py-2.5 disabled:opacity-60"
            >
              {isSubmitting ? 'Injecting...' : 'Inject Instruction Mid-Flight'}
            </button>
            {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-[11px] text-red-300">{error}</div>}
            {success && <div className="rounded-lg border border-nagarro-green/30 bg-nagarro-green/10 px-3 py-2 text-[11px] text-nagarro-green">{success}</div>}
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
