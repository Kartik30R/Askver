import type { PipelineStateResponse } from '../../features/workflow/workflowApi'
import { Card, Empty, Pill, QualityPill } from './ui'

export default function InsightsPanel({ state }: { state: PipelineStateResponse }) {
  const insights = state.insight_synthesis?.insights ?? []
  const risks = state.insight_synthesis?.deal_risks ?? []

  if (!insights.length && !risks.length) {
    return <Empty text="No insight synthesis has been generated yet." />
  }

  return (
    <div className="space-y-5">
      <Card title="Key insights">
        <div className="space-y-3">
          {insights.map((item, index) => (
            <div key={`${item.headline}-${index}`} className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-semibold text-slate-50">{item.headline}</p>
                <QualityPill level={item.evidence_strength} />
              </div>
              <p className="mt-2 text-sm text-slate-300">{item.so_what}</p>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Deal risks">
        <div className="space-y-3">
          {risks.map((risk, index) => (
            <div key={`${risk.risk}-${index}`} className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
              <div className="flex items-center gap-2">
                <p className="text-sm font-semibold text-slate-50">{risk.risk}</p>
                <Pill>{risk.likelihood}</Pill>
                <Pill>{risk.impact}</Pill>
              </div>
              <p className="mt-2 text-sm text-slate-300">{risk.mitigation}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
