import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  GitGraph, FileText, MessageSquareCode, Play, Pause, RotateCcw,
  CheckCircle2, Clock, AlertTriangle, Send, X, ChevronRight, Sliders, History,
  PanelTop
} from 'lucide-react'

export default function DealDashboard() {
  // Top-level View Mode: 'pipeline' | 'tabs' | 'report_chat'
  const [viewMode, setViewMode] = useState<'pipeline' | 'tabs' | 'report_chat'>('pipeline')

  // Selected node for Chrome Tabs view
  const [activeTabNode, setActiveTabNode] = useState('company_research')

  // VS Code Drawer Toggle
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)

  // Version Control Checkpoint Dropdown state
  const [selectedCheckpoint, setSelectedCheckpoint] = useState('chk_latest')

  // Mock LangGraph Agent Execution Pipeline Nodes
  const nodes = [
    { id: 'company_research', label: 'Company Research', status: 'completed' },
    { id: 'financial_intelligence', label: 'Financial Intel', status: 'completed' },
    { id: 'stakeholder_intel', label: 'Stakeholder Analysis', status: 'completed' },
    { id: 'industry_analysis', label: 'Industry Analysis', status: 'completed' },
    { id: 'pain_point_detector', label: 'Pain Point Detector', status: 'completed' },
    { id: 'enterprise_rag_matcher', label: 'Enterprise RAG', status: 'completed' },
    { id: 'service_mapper', label: 'Service Mapper', status: 'completed' },
    { id: 'human_review_gate', label: 'Human Review Gate', status: 'paused' },
    { id: 'cxo_brief_generator', label: 'CXO Brief Generator', status: 'pending' },
    { id: 'report_indexer', label: 'Report Indexer', status: 'pending' },
  ]

  // Mock Node Details output
  const mockNodeOutputs: Record<string, string> = {
    company_research: `### Target Overview: Acme Global Financials
* **Headquarters**: London, UK
* **Core Business**: Multi-national Commercial Banking
* **Transformation Goal**: Transitioning legacy mainframes to cloud-native microservices.`,
    financial_intelligence: `### Financial Health & Budget Signals
* **Market Cap**: $45.2B | **EBITDA Margin**: 18.4%
* **CapEx Allocation**: $500M earmarked for IT modernization over 3 years.
* **Margin Impact**: Legacy mainframe maintenance costs consuming $40M annually.`,
    human_review_gate: `### Mandatory Review Checkpoint
**Status**: Awaiting Human Approval before final CXO brief generation.
* Re-verify mapped services against strict EU DORA compliance rules.`
  }

  return (
    <div className="space-y-6 relative min-h-[calc(100vh-8rem)]">
      {/* Workspace Header Toolbar */}
      <div className="cosmic-card p-4 flex flex-wrap items-center justify-between gap-4">
        {/* Deal Title & State Branch */}
        <div className="flex items-center gap-3">
          <div className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-ping" />
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              Acme Global Financials
              <span className="text-xs font-mono font-normal text-cosmic-muted bg-cosmic-bg px-2 py-0.5 rounded border border-cosmic-border">
                thread_deal_4k91a002
              </span>
            </h2>
          </div>
        </div>

        {/* View Mode Switcher */}
        <div className="flex bg-cosmic-bg p-1 rounded-lg border border-cosmic-border">
          <button
            onClick={() => setViewMode('pipeline')}
            className={`flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
              viewMode === 'pipeline' ? 'bg-nagarro-green text-black' : 'text-cosmic-muted hover:text-white'
            }`}
          >
            <GitGraph className="w-3.5 h-3.5" />
            GitLab Pipeline Flow
          </button>
         <button
            onClick={() => setViewMode('tabs')}
            className={`flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
              viewMode === 'tabs' ? 'bg-nagarro-green text-black' : 'text-cosmic-muted hover:text-white'
            }`}
          >
            {/* Swapped LayoutTabs for PanelTop here */}
            <PanelTop className="w-3.5 h-3.5" />
            Node Tabs
          </button>
          <button
            onClick={() => setViewMode('report_chat')}
            className={`flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
              viewMode === 'report_chat' ? 'bg-nagarro-green text-black' : 'text-cosmic-muted hover:text-white'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            Report & AI Chat
          </button>
        </div>

        {/* Checkpoint Version Revert Controls */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 text-xs text-cosmic-muted bg-cosmic-bg px-2.5 py-1.5 rounded-lg border border-cosmic-border">
            <History className="w-3.5 h-3.5 text-nagarro-green" />
            <select
              value={selectedCheckpoint}
              onChange={(e) => setSelectedCheckpoint(e.target.value)}
              className="bg-transparent text-white focus:outline-none cursor-pointer"
            >
              <option value="chk_latest" className="bg-cosmic-surface">Head (Latest Checkpoint)</option>
              <option value="chk_node_5" className="bg-cosmic-surface">Checkpoint #5: Pain Point Detector</option>
              <option value="chk_node_1" className="bg-cosmic-surface">Checkpoint #1: Company Research</option>
            </select>
          </div>

          {/* VS Code Side Drawer Trigger Icon Button */}
          <button
            onClick={() => setIsDrawerOpen(true)}
            className="p-2 bg-cosmic-surface hover:bg-cosmic-border border border-cosmic-border rounded-lg text-nagarro-green relative transition-colors"
            title="Open Interactive HITL Instruction Drawer"
          >
            <Sliders className="w-4 h-4" />
            <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-nagarro-green animate-pulse" />
          </button>
        </div>
      </div>

      {/* ========================================================================================= */}
      {/* VIEW 1: GITLAB-STYLE PIPELINE FLOW CARDS */}
      {/* ========================================================================================= */}
      {viewMode === 'pipeline' && (
        <div className="cosmic-card p-6 overflow-x-auto">
          <div className="text-xs font-semibold text-cosmic-muted mb-4 uppercase tracking-wider flex items-center justify-between">
            <span>LangGraph Execution Topology</span>
            <span className="text-amber-400 flex items-center gap-1">
              <AlertTriangle className="w-3.5 h-3.5" /> Workflow Paused at Mandatory Review Gate
            </span>
          </div>

          <div className="flex items-center gap-4 min-w-max py-6">
            {nodes.map((node, idx) => (
              <React.Fragment key={node.id}>
                {/* Node Card */}
                <div
                  onClick={() => { setActiveTabNode(node.id); setViewMode('tabs'); }}
                  className={`w-48 p-4 rounded-xl border transition-all cursor-pointer ${
                    node.status === 'completed'
                      ? 'bg-cosmic-surface/90 border-nagarro-green/40 hover:border-nagarro-green'
                      : node.status === 'paused'
                      ? 'bg-amber-950/20 border-amber-500/60 animate-pulse'
                      : 'bg-cosmic-bg/40 border-cosmic-border opacity-50'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-mono uppercase text-cosmic-muted">Stage 0{idx + 1}</span>
                    {node.status === 'completed' && <CheckCircle2 className="w-4 h-4 text-nagarro-green" />}
                    {node.status === 'paused' && <Clock className="w-4 h-4 text-amber-400" />}
                    {node.status === 'pending' && <div className="w-3 h-3 rounded-full border border-cosmic-muted" />}
                  </div>
                  <h4 className="text-xs font-bold text-white mb-1">{node.label}</h4>
                  <span className={`text-[10px] font-semibold uppercase ${
                    node.status === 'completed' ? 'text-nagarro-green' : node.status === 'paused' ? 'text-amber-400' : 'text-cosmic-muted'
                  }`}>
                    {node.status}
                  </span>
                </div>

                {/* Connection Line */}
                {idx < nodes.length - 1 && (
                  <div className={`h-0.5 w-6 ${node.status === 'completed' ? 'bg-nagarro-green' : 'bg-cosmic-border'}`} />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      )}

      {/* ========================================================================================= */}
      {/* VIEW 2: CHROME-STYLE TABS VIEW */}
      {/* ========================================================================================= */}
      {viewMode === 'tabs' && (
        <div className="cosmic-card overflow-hidden">
          {/* Top Chrome Tab Bar */}
          <div className="flex items-center bg-cosmic-bg border-b border-cosmic-border overflow-x-auto">
            {nodes.map((node) => (
              <button
                key={node.id}
                onClick={() => setActiveTabNode(node.id)}
                className={`flex items-center gap-2 px-4 py-3 text-xs font-medium border-r border-cosmic-border whitespace-nowrap transition-all ${
                  activeTabNode === node.id
                    ? 'bg-cosmic-surface text-nagarro-green border-t-2 border-t-nagarro-green'
                    : 'text-cosmic-muted hover:text-white hover:bg-cosmic-surface/50'
                }`}
              >
                {node.status === 'completed' && <CheckCircle2 className="w-3.5 h-3.5 text-nagarro-green" />}
                {node.status === 'paused' && <Clock className="w-3.5 h-3.5 text-amber-400" />}
                {node.label}
              </button>
            ))}
          </div>

          {/* Active Tab Output Content */}
          <div className="p-6">
            <div className="prose prose-invert max-w-none text-sm">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {mockNodeOutputs[activeTabNode] || `### Node Stage: ${activeTabNode}\nData extraction in progress or awaiting upstream inputs...`}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================================= */}
      {/* VIEW 3: STRATEGY REPORT & AI CHAT (SPLIT SCREEN) */}
      {/* ========================================================================================= */}
      {viewMode === 'report_chat' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[650px]">
          {/* Left Column: Markdown Strategy Brief Document */}
          <div className="lg:col-span-7 cosmic-card p-6 overflow-y-auto">
            <h3 className="text-lg font-bold text-white mb-4 pb-2 border-b border-cosmic-border flex items-center justify-between">
              <span>Executive Brief Preview</span>
              <span className="text-xs font-mono text-nagarro-green">Snapshot #snp_991823</span>
            </h3>
            <div className="prose prose-invert max-w-none text-sm text-cosmic-text space-y-4">
              <h2>Strategic Roadmap: Acme Global Financials</h2>
              <p>Based on hybrid extraction across Acme RFPs and internal case studies, Nagarro proposes a 3-tier cloud migration strategy...</p>
              <h3>Key Value Drivers</h3>
              <ul>
                <li><strong>Mainframe Decommissioning:</strong> Expected 35% reduction in annual operational expenses.</li>
                <li><strong>DORA Regulatory Compliance:</strong> Automated compliance monitoring for EU operations.</li>
              </ul>
            </div>
          </div>

          {/* Right Column: AI Interactive Revision & Diff Chat */}
          <div className="lg:col-span-5 cosmic-card flex flex-col h-full">
            <div className="p-4 border-b border-cosmic-border flex items-center justify-between bg-cosmic-surface/60">
              <span className="text-xs font-bold text-white flex items-center gap-2">
                <MessageSquareCode className="w-4 h-4 text-nagarro-green" />
                AI Strategy Copilot (RAG Chat & Edits)
              </span>
            </div>

            {/* Chat Conversation Area */}
            <div className="flex-1 p-4 overflow-y-auto space-y-4 text-xs">
              <div className="bg-cosmic-bg p-3 rounded-lg border border-cosmic-border text-cosmic-muted">
                Ask questions or request real-time diff proposals for specific sections.
              </div>
              <div className="bg-nagarro-green/10 text-white p-3 rounded-lg border border-nagarro-green/30 ml-6">
                <p className="font-semibold text-nagarro-green mb-1">User</p>
                Make the Executive Summary more aggressive regarding cost savings.
              </div>
              <div className="bg-cosmic-surface p-3 rounded-lg border border-cosmic-border mr-6">
                <p className="font-semibold text-white mb-1">AI Assistant (Proposed Diff)</p>
                Updated Executive Summary to emphasize immediate 35% CapEx reduction within 18 months.
              </div>
            </div>

            {/* Chat Input */}
            <div className="p-3 border-t border-cosmic-border bg-cosmic-bg/80 flex items-center gap-2">
              <input
                type="text"
                placeholder="Instruct AI to rewrite or query document..."
                className="flex-1 bg-cosmic-surface border border-cosmic-border rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-nagarro-green"
              />
              <button className="btn-nagarro p-2 rounded-lg">
                <Send className="w-4 h-4 text-black" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================================= */}
      {/* VS CODE-STYLE RIGHT SIDE DRAWER (HITL DYNAMIC INSTRUCTION & STEERING) */}
      {/* ========================================================================================= */}
      {isDrawerOpen && (
        <div className="fixed inset-0 z-50 overflow-hidden bg-black/50 backdrop-blur-xs flex justify-end">
          <div className="w-full max-w-md bg-cosmic-surface border-l border-cosmic-border h-full flex flex-col shadow-2xl animate-in slide-in-from-right duration-200">
            {/* Drawer Header */}
            <div className="p-4 border-b border-cosmic-border flex items-center justify-between bg-cosmic-bg/80">
              <div className="flex items-center gap-2">
                <Sliders className="w-4 h-4 text-nagarro-green" />
                <h3 className="text-sm font-bold text-white">HITL Pipeline Steering (VS Code Panel)</h3>
              </div>
              <button onClick={() => setIsDrawerOpen(false)} className="text-cosmic-muted hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Drawer Body */}
            <div className="flex-1 p-6 space-y-6 overflow-y-auto">
              {/* Pause / Resume Execution Controls */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-cosmic-muted uppercase tracking-wider">State Machine Control</label>
                <div className="grid grid-cols-2 gap-3">
                  <button className="flex items-center justify-center gap-2 p-2.5 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20 text-xs font-semibold">
                    <Pause className="w-3.5 h-3.5" /> Pause Workflow
                  </button>
                  <button className="flex items-center justify-center gap-2 p-2.5 rounded-lg bg-nagarro-green/10 border border-nagarro-green/30 text-nagarro-green hover:bg-nagarro-green/20 text-xs font-semibold">
                    <Play className="w-3.5 h-3.5" /> Resume Workflow
                  </button>
                </div>
              </div>

              {/* Dynamic Instruction Injection */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-cosmic-muted uppercase tracking-wider">Inject Node Instruction</label>
                <select className="w-full bg-cosmic-bg border border-cosmic-border rounded-lg p-2.5 text-xs text-white focus:border-nagarro-green outline-none">
                  {nodes.map(n => <option key={n.id} value={n.id}>{n.label}</option>)}
                </select>
                <textarea
                  rows={4}
                  placeholder="e.g., Target EU DORA compliance specifically in pain point detection..."
                  className="w-full bg-cosmic-bg border border-cosmic-border rounded-lg p-3 text-xs text-white focus:border-nagarro-green outline-none"
                />
                <button className="btn-nagarro w-full text-xs py-2.5">
                  Inject Instruction Mid-Flight
                </button>
              </div>

              {/* Mandatory Review Gate Action */}
              <div className="p-4 bg-amber-950/20 border border-amber-500/40 rounded-xl space-y-3">
                <h4 className="text-xs font-bold text-amber-400 flex items-center gap-1.5">
                  <AlertTriangle className="w-4 h-4" /> Mandatory Review Checkpoint
                </h4>
                <p className="text-[11px] text-cosmic-muted">
                  Approve state machine execution to proceed to final CXO Brief synthesis.
                </p>
                <div className="flex gap-2">
                  <button className="btn-nagarro flex-1 text-xs py-2">Approve</button>
                  <button className="px-3 py-2 rounded-lg bg-cosmic-bg border border-cosmic-border text-xs text-cosmic-muted hover:text-white">Request Revisions</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}