import type { PipelineStateResponse } from '../../features/workflow/workflowApi'
import { BulletList, Card, Empty, Pill, QualityPill, humanize } from './ui'

export default function FrameworksPanel({ state }: { state: PipelineStateResponse }) {
  const strategic = state.strategic_frameworks
  const commercial = state.commercial_frameworks

  if (!strategic && !commercial) {
    return <Empty text="No frameworks have been generated yet." />
  }

  return (
    <div className="space-y-5">
      {strategic && (
        <Card title="Strategic frameworks">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <p className="mb-2 text-xs uppercase tracking-wide text-slate-400">SWOT</p>
              <div className="space-y-2">
                <p className="text-sm text-slate-200">Strengths: {strategic.swot.strengths.length}</p>
                <p className="text-sm text-slate-200">Weaknesses: {strategic.swot.weaknesses.length}</p>
                <p className="text-sm text-slate-200">Opportunities: {strategic.swot.opportunities.length}</p>
                <p className="text-sm text-slate-200">Threats: {strategic.swot.threats.length}</p>
              </div>
            </div>
            <div>
              <p className="mb-2 text-xs uppercase tracking-wide text-slate-400">Porter / PESTLE</p>
              <div className="space-y-2">
                <p className="text-sm text-slate-200">Porter forces: {strategic.porter.length}</p>
                <p className="text-sm text-slate-200">PESTLE factors: {strategic.pestle.length}</p>
                <p className="text-sm text-slate-200">TOWS moves: {strategic.tows.length}</p>
              </div>
            </div>
          </div>
          <div className="mt-4">
            <p className="mb-2 text-xs uppercase tracking-wide text-slate-400">Key strategic moves</p>
            <BulletList items={strategic.tows.map((item) => `${item.quadrant}: ${item.move}`)} tone="text-slate-300" />
          </div>
        </Card>
      )}

      {commercial && (
        <Card title="Commercial frameworks">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <p className="mb-2 text-xs uppercase tracking-wide text-slate-400">Buying committee</p>
              <div className="space-y-2">
                {commercial.buying_committee.slice(0, 4).map((member) => (
                  <div key={`${member.role}-${member.name ?? 'role'}`} className="rounded-xl border border-white/10 bg-white/[0.02] p-2">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-slate-100">{member.name ?? member.role}</span>
                      <Pill>{member.role}</Pill>
                    </div>
                    <div className="mt-1 flex flex-wrap gap-2">
                      <QualityPill level={member.influence} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <p className="mb-2 text-xs uppercase tracking-wide text-slate-400">Digital maturity</p>
              <div className="space-y-2">
                {commercial.digital_maturity.slice(0, 4).map((dimension) => (
                  <div key={dimension.dimension} className="rounded-xl border border-white/10 bg-white/[0.02] p-2">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm text-slate-100">{humanize(dimension.dimension)}</span>
                      <span className="text-xs text-slate-400">{dimension.score_1_to_5 ?? '—'}</span>
                    </div>
                    <p className="mt-1 text-xs text-slate-400">{dimension.rationale}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}
