import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Briefcase, FileUp, ArrowRight, Play, Layers, Clock, CheckCircle2 } from 'lucide-react'

export default function DealList() {
  const navigate = useNavigate()
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [step, setStep] = useState(1)

  // Mock deal records
  const deals = [
    {
      id: 'deal_4k91a002',
      name: 'Acme Global Financials',
      industry: 'Banking & Financial Services',
      value: '$2,500,000',
      status: 'PAUSED_AT_BOUNDARY',
      currentStep: 'Human Review Gate',
      docsCount: 3,
      updatedAt: '10 mins ago'
    },
    {
      id: 'deal_8821b019',
      name: 'HealthPlus Enterprise',
      industry: 'Healthcare & Pharma',
      value: '$1,800,000',
      status: 'COMPLETED',
      currentStep: 'Report Indexed',
      docsCount: 5,
      updatedAt: '2 hours ago'
    }
  ]

  return (
    <div className="space-y-6">
      {/* Top Bar Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Deal Intelligence Center</h1>
          <p className="text-sm text-cosmic-muted mt-1">Manage active enterprise proposals and multi-agent workflows.</p>
        </div>
        <button onClick={() => setIsModalOpen(true)} className="btn-nagarro flex items-center gap-2">
          <Plus className="w-4 h-4 text-black" />
          <span>Create New Deal</span>
        </button>
      </div>

      {/* Grid of Deals */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {deals.map((deal) => (
          <div
            key={deal.id}
            onClick={() => navigate(`/deals/${deal.id}`)}
            className="cosmic-card p-6 cursor-pointer hover:border-nagarro-green/60 transition-all group"
          >
            <div className="flex items-start justify-between mb-4">
              <div>
                <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-cosmic-border text-nagarro-green">
                  {deal.industry}
                </span>
                <h3 className="text-lg font-bold text-white mt-2 group-hover:text-nagarro-green transition-colors">
                  {deal.name}
                </h3>
              </div>
              <span className="text-sm font-semibold text-white bg-cosmic-bg/80 px-3 py-1 rounded-lg border border-cosmic-border">
                {deal.value}
              </span>
            </div>

            <div className="space-y-3 pt-4 border-t border-cosmic-border/50 text-xs text-cosmic-muted">
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Layers className="w-4 h-4 text-nagarro-green" />
                  Active Step:
                </span>
                <span className="text-white font-medium">{deal.currentStep}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-cosmic-muted" />
                  Last Activity:
                </span>
                <span>{deal.updatedAt}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Modal Wizard: Create New Deal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="cosmic-card w-full max-w-xl p-6 relative">
            {/* Step Indicators */}
            <div className="flex items-center justify-between mb-6 pb-4 border-b border-cosmic-border">
              <h2 className="text-lg font-bold text-white">Initiate Deal Intelligence</h2>
              <div className="flex items-center gap-2 text-xs">
                <span className={`px-2 py-1 rounded ${step === 1 ? 'bg-nagarro-green text-black font-bold' : 'text-cosmic-muted'}`}>1. Target Info</span>
                <span className="text-cosmic-muted">→</span>
                <span className={`px-2 py-1 rounded ${step === 2 ? 'bg-nagarro-green text-black font-bold' : 'text-cosmic-muted'}`}>2. Upload RFP</span>
                <span className="text-cosmic-muted">→</span>
                <span className={`px-2 py-1 rounded ${step === 3 ? 'bg-nagarro-green text-black font-bold' : 'text-cosmic-muted'}`}>3. Start Workflow</span>
              </div>
            </div>

            {/* Step 1: Basic Metadata */}
            {step === 1 && (
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-cosmic-muted mb-1">Target Company Name</label>
                  <input type="text" placeholder="Acme Global Financials" className="w-full bg-cosmic-bg border border-cosmic-border rounded-lg px-3 py-2 text-sm text-white focus:border-nagarro-green outline-none" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-cosmic-muted mb-1">Industry Sector</label>
                  <input type="text" placeholder="Banking & Financial Services" className="w-full bg-cosmic-bg border border-cosmic-border rounded-lg px-3 py-2 text-sm text-white focus:border-nagarro-green outline-none" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-cosmic-muted mb-1">Estimated Deal Value ($)</label>
                  <input type="text" placeholder="2500000" className="w-full bg-cosmic-bg border border-cosmic-border rounded-lg px-3 py-2 text-sm text-white focus:border-nagarro-green outline-none" />
                </div>
                <div className="flex justify-end gap-3 pt-4">
                  <button onClick={() => setIsModalOpen(false)} className="px-4 py-2 text-xs text-cosmic-muted hover:text-white">Cancel</button>
                  <button onClick={() => setStep(2)} className="btn-nagarro text-xs flex items-center gap-1">Next: Upload RFP <ArrowRight className="w-3.5 h-3.5" /></button>
                </div>
              </div>
            )}

            {/* Step 2: Document Upload */}
            {step === 2 && (
              <div className="space-y-4">
                <div className="border-2 border-dashed border-cosmic-border rounded-xl p-8 text-center bg-cosmic-bg/40 hover:border-nagarro-green/50 transition-colors cursor-pointer">
                  <FileUp className="w-10 h-10 text-nagarro-green mx-auto mb-2" />
                  <p className="text-sm text-white font-medium">Drag and drop RFP / BRD documents here</p>
                  <p className="text-xs text-cosmic-muted mt-1">Files indexed into collection: <code className="text-nagarro-green">deal_deal_4k91a002_docs</code></p>
                </div>
                <div className="flex justify-between pt-4">
                  <button onClick={() => setStep(1)} className="px-4 py-2 text-xs text-cosmic-muted hover:text-white">Back</button>
                  <button onClick={() => setStep(3)} className="btn-nagarro text-xs flex items-center gap-1">Next: Confirm <ArrowRight className="w-3.5 h-3.5" /></button>
                </div>
              </div>
            )}

            {/* Step 3: Launch Workflow */}
            {step === 3 && (
              <div className="space-y-4 text-center py-4">
                <CheckCircle2 className="w-12 h-12 text-nagarro-green mx-auto animate-bounce" />
                <h3 className="text-lg font-bold text-white">Ready to Trigger LangGraph State Machine</h3>
                <p className="text-xs text-cosmic-muted max-w-md mx-auto">
                  8 specialized AI agents will asynchronously research financials, extract pain points, and match internal case studies.
                </p>
                <div className="flex justify-center gap-3 pt-4">
                  <button onClick={() => setStep(2)} className="px-4 py-2 text-xs text-cosmic-muted hover:text-white">Back</button>
                  <button onClick={() => { setIsModalOpen(false); navigate('/deals/deal_4k91a002'); }} className="btn-nagarro text-xs flex items-center gap-2">
                    <Play className="w-3.5 h-3.5 fill-black" /> Trigger Pipeline
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}