import type { PipelineStateResponse } from '../../features/workflow/workflowApi'
import { Card, Empty, Pill } from './ui'

export default function PainPointsPanel({ state }: { state: PipelineStateResponse }) {
  const painPoints = state.detected_pain_points ?? []
  const priorities = state.priorities ?? []

  if (!painPoints.length && !priorities.length) {
    return <Empty text="No pain points or priorities have been generated yet." />
  }

  return (
    <div className="space-y-5">
      <Card title="Priorities">
        <div className="flex flex-wrap gap-2">
          {priorities.map((priority) => (
            <Pill key={priority}>{priority}</Pill>
          ))}
        </div>
      </Card>

      <Card title="Detected pain points">
        <div className="space-y-3">
          {painPoints.map((item, index) => (
            <div key={`${item.category}-${index}`} className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
              <div className="flex items-center gap-2">
                <p className="text-sm font-semibold text-slate-50">{item.category}</p>
                <Pill>{item.severity}</Pill>
              </div>
              <p className="mt-2 text-sm text-slate-300">{item.description}</p>
              <p className="mt-1 text-xs text-slate-400">Business area: {item.impacted_business_area}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
