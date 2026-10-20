import type { PipelineStateResponse } from '../../features/workflow/workflowApi'
import { Card, Empty, Pill } from './ui'

export default function SolutionFitPanel({ state }: { state: PipelineStateResponse }) {
  const mappings = state.service_mappings ?? []
  const assets = state.matched_internal_assets ?? []

  if (!mappings.length && !assets.length) {
    return <Empty text="No solution-fit analysis has been generated yet." />
  }

  return (
    <div className="space-y-5">
      <Card title="Service mappings">
        <div className="space-y-3">
          {mappings.map((mapping, index) => (
            <div key={`${mapping.client_need ?? 'mapping'}-${index}`} className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
              <p className="text-sm font-semibold text-slate-50">{mapping.client_need ?? 'Client need'}</p>
              <p className="mt-2 text-sm text-slate-300">{mapping.proposed_service ?? 'Proposed service'}</p>
              <p className="mt-1 text-xs text-slate-400">{mapping.business_value ?? 'Business value not recorded'}</p>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Matched assets">
        <div className="flex flex-wrap gap-2">
          {assets.map((asset) => (
            <Pill key={asset.asset_id ?? asset.title ?? asset.asset_name ?? Math.random().toString()}>{asset.asset_name ?? asset.title ?? 'Asset'}</Pill>
          ))}
        </div>
      </Card>
    </div>
  )
}
