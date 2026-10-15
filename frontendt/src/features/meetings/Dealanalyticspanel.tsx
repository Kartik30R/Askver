import { useContext, useMemo, useState } from 'react'
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  CalendarClock,
  CheckCircle2,
  Compass,
  Flag,
  Gauge,
  HelpCircle,
  Loader2,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  Swords,
  Target,
  TrendingUp,
  Users,
} from 'lucide-react'

import type { DealAnalyticsResult, RiskItem, Trend } from './analysisTypes'
import {
  AnalyticsContext,
  BoolRow,
  Chips,
  ConfidencePill,
  Empty,
  Field,
  FindingMeta,
  formatDate,
  formatDateTime,
  humanize,
  ItemCard,
  Label,
  MeetingChips,
  Notice,
  Panel,
  Pill,
  Ring,
  ScoreMeter,
  SeverityPill,
  Sparkline,
  SkeletonBlock,
  StatusPill,
  StringList,
  TabBar,
  TONE_TEXT,
  Unavailable,
} from './analyticsUi'
import type { Tone } from './analyticsUi'
import type { LoadState } from './MeetingAnalysisPanel'

type DealTab = 'overview' | 'risks' | 'committee' | 'competitive' | 'execution' | 'trackers' | 'strategy' | 'timeline'

const trendTone = (trend: Trend): Tone =>
  ({ IMPROVING: 'green', STABLE: 'cyan', DECLINING: 'red', STALLED: 'amber', INSUFFICIENT_DATA: 'neutral' } as const)[trend]

function TrendPill({ trend, prefix }: { trend: Trend; prefix?: string }) {
  const Icon = trend === 'IMPROVING' ? ArrowUpRight : trend === 'DECLINING' ? ArrowDownRight : ArrowRight
  return (
    <Pill tone={trendTone(trend)} icon={<Icon className="h-3 w-3" />}>
      {prefix ? `${prefix} ` : ''}
      {humanize(trend)}
    </Pill>
  )
}

const OPEN_RISK: RiskItem['status'][] = ['OPEN', 'MITIGATING']

// ───────────────────────── Deal pulse (always visible KPI strip) ─────────────────────────
export function DealPulse({
  analysis,
  meetingCount,
  state,
  onOpen,
}: {
  analysis: DealAnalyticsResult | null
  meetingCount: number
  state: LoadState
  onOpen: () => void
}) {
  const win = analysis?.win_probability ?? null
  const health = analysis?.health ?? null
  const momentum = analysis?.momentum ?? null
  const openRisks = analysis?.risks?.risks.filter((risk) => OPEN_RISK.includes(risk.status)) ?? []
  const criticalRisks = openRisks.filter((risk) => risk.severity === 'CRITICAL' || risk.severity === 'HIGH').length

  const placeholder = state === 'loading' ? 'Analysing…' : 'Not analysed'

  return (
    <button
      type="button"
      onClick={onOpen}
      className="cosmic-card group grid w-full gap-px overflow-hidden p-0 text-left transition-all duration-200 hover:border-nagarro-green/40 md:grid-cols-2 xl:grid-cols-5"
      aria-label="Open overall deal analytics"
    >
      <div className="flex items-center gap-4 p-5">
        {win ? (
          <Ring value={win.probability_pct} size={76} stroke={7}>
            <span className="text-lg font-bold text-white">{win.probability_pct}%</span>
          </Ring>
        ) : (
          <div className="flex h-[76px] w-[76px] items-center justify-center rounded-full border border-dashed border-cosmic-border text-cosmic-muted">
            {state === 'loading' ? <Loader2 className="h-5 w-5 animate-spin" /> : <Target className="h-5 w-5" />}
          </div>
        )}
        <div>
          <Label>Win probability</Label>
          <div className="mt-1 text-xs text-cosmic-muted">
            {win ? (
              <>
                {win.change_pct !== null && (
                  <span className={win.change_pct >= 0 ? 'text-emerald-300' : 'text-red-300'}>
                    {win.change_pct >= 0 ? '+' : ''}
                    {win.change_pct} pts ·{' '}
                  </span>
                )}
                {humanize(win.confidence)} confidence
              </>
            ) : (
              placeholder
            )}
          </div>
        </div>
      </div>

      <div className="p-5">
        <Label>Deal health</Label>
        <div className="mt-2 text-3xl font-bold text-white">
          {health?.composite_score != null ? Math.round(health.composite_score) : '—'}
          <span className="text-sm font-normal text-cosmic-muted"> / 100</span>
        </div>
      </div>

      <div className="p-5">
        <Label>Momentum</Label>
        <div className="mt-3">
          {momentum ? <TrendPill trend={momentum.overall_trend} /> : <span className="text-sm text-cosmic-muted">{placeholder}</span>}
        </div>
      </div>

      <div className="p-5">
        <Label>Open risks</Label>
        <div className="mt-2 flex items-baseline gap-2">
          <span className={`text-3xl font-bold ${criticalRisks ? 'text-orange-300' : 'text-white'}`}>{analysis?.risks ? openRisks.length : '—'}</span>
          {criticalRisks > 0 && <span className="text-xs text-orange-300">{criticalRisks} high or critical</span>}
        </div>
      </div>

      <div className="p-5">
        <Label>Meetings analysed</Label>
        <div className="mt-2 text-3xl font-bold text-white">
          {analysis?.meetings_analyzed ?? 0}
          <span className="text-sm font-normal text-cosmic-muted"> / {meetingCount}</span>
        </div>
      </div>
    </button>
  )
}

// ───────────────────────── Tabs ─────────────────────────
function OverviewTab({ analysis }: { analysis: DealAnalyticsResult }) {
  const { win_probability: win, health, momentum } = analysis
  return (
    <div className="space-y-6">
      {win ? (
        <Panel title="Win probability" icon={<Target className="h-3.5 w-3.5 text-emerald-300" />} aside={<Pill tone="violet">{win.label}</Pill>}>
          <div className="flex flex-col gap-6 md:flex-row">
            <div className="flex flex-col items-center gap-3">
              <Ring value={win.probability_pct} size={148} stroke={11}>
                <span className="text-4xl font-bold text-white">{win.probability_pct}%</span>
              </Ring>
              <div className="flex flex-wrap justify-center gap-2">
                <TrendPill trend={win.trend} />
                <ConfidencePill value={win.confidence} />
              </div>
              <div className="text-xs text-cosmic-muted">
                Previous · {win.previous_pct !== null ? `${win.previous_pct}%` : 'First assessment'}
                {win.change_pct !== null && (
                  <span className={win.change_pct >= 0 ? ' text-emerald-300' : ' text-red-300'}>
                    {' '}
                    ({win.change_pct >= 0 ? '+' : ''}
                    {win.change_pct} pts)
                  </span>
                )}
              </div>
            </div>
            <div className="min-w-0 flex-1">
              <Label>Rationale</Label>
              <p className="mt-2 text-sm leading-7 text-cosmic-text">{win.rationale}</p>
            </div>
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <div>
              <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-emerald-300">
                <ArrowUpRight className="h-3.5 w-3.5" /> Supporting factors
              </div>
              {win.supporting_factors.length ? (
                <div className="space-y-3">
                  {win.supporting_factors.map((factor, index) => (
                    <ItemCard key={`${index}-${factor.description.slice(0, 24)}`} tone="green">
                      <p className="text-sm leading-6 text-white">{factor.description}</p>
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        <SeverityPill value={factor.impact} prefix="Impact ·" />
                        <MeetingChips ids={factor.source_meeting_ids} />
                      </div>
                      <FindingMeta finding={factor} />
                    </ItemCard>
                  ))}
                </div>
              ) : (
                <Empty>No supporting factors identified.</Empty>
              )}
            </div>
            <div>
              <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-red-300">
                <ArrowDownRight className="h-3.5 w-3.5" /> Reducing factors
              </div>
              {win.reducing_factors.length ? (
                <div className="space-y-3">
                  {win.reducing_factors.map((factor, index) => (
                    <ItemCard key={`${index}-${factor.description.slice(0, 24)}`} tone="red">
                      <p className="text-sm leading-6 text-white">{factor.description}</p>
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        <SeverityPill value={factor.impact} prefix="Impact ·" />
                        <MeetingChips ids={factor.source_meeting_ids} />
                      </div>
                      <FindingMeta finding={factor} />
                    </ItemCard>
                  ))}
                </div>
              ) : (
                <Empty>No reducing factors identified.</Empty>
              )}
            </div>
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-3">
            <div>
              <Label>Major uncertainties</Label>
              <div className="mt-2">
                <StringList items={win.major_uncertainties} empty="None noted." tone="amber" />
              </div>
            </div>
            <div>
              <Label>Would improve the outlook</Label>
              <div className="mt-2">
                <StringList items={win.conditions_to_improve} empty="None noted." tone="green" />
              </div>
            </div>
            <div>
              <Label>Would reduce the outlook</Label>
              <div className="mt-2">
                <StringList items={win.conditions_to_decline} empty="None noted." tone="red" />
              </div>
            </div>
          </div>
        </Panel>
      ) : (
        <Unavailable name="Win probability" warnings={analysis.warnings} />
      )}

      {health ? (
        <Panel title="Deal health" icon={<Gauge className="h-3.5 w-3.5 text-cyan-300" />} aside={<Pill tone="neutral">Methodology v{health.methodology_version}</Pill>}>
          <div className="flex flex-col gap-6 md:flex-row">
            <div className="flex flex-none flex-col items-center gap-2">
              <Ring value={health.composite_score ?? 0} size={124}>
                <span className="text-3xl font-bold text-white">{health.composite_score !== null ? Math.round(health.composite_score) : '—'}</span>
                <span className="text-[10px] uppercase tracking-[0.14em] text-cosmic-muted">composite</span>
              </Ring>
            </div>
            <div className="grid flex-1 gap-3 lg:grid-cols-2">
              {health.dimensions.map((dimension) => (
                <ItemCard key={dimension.dimension}>
                  <div className="text-sm font-semibold text-white">{humanize(dimension.dimension)}</div>
                  <div className="mt-2">
                    <ScoreMeter score={dimension.score} label={humanize(dimension.dimension)} />
                  </div>
                  <p className="mt-2 text-xs leading-5 text-cosmic-muted">{dimension.rationale}</p>
                  {dimension.missing_information.length > 0 && (
                    <div className="mt-3">
                      <Label>Missing information</Label>
                      <div className="mt-1.5">
                        <StringList items={dimension.missing_information} tone="amber" />
                      </div>
                    </div>
                  )}
                  <div className="mt-3">
                    <Label>Sources</Label>
                    <div className="mt-1.5">
                      <MeetingChips ids={dimension.source_meeting_ids} />
                    </div>
                  </div>
                  <FindingMeta finding={dimension} />
                </ItemCard>
              ))}
              {!health.dimensions.length && <Empty>No health dimensions were scored.</Empty>}
            </div>
          </div>
        </Panel>
      ) : (
        <Unavailable name="Health" warnings={analysis.warnings} />
      )}

      {momentum ? (
        <Panel title="Momentum & trajectory" icon={<TrendingUp className="h-3.5 w-3.5 text-violet-300" />} aside={<TrendPill trend={momentum.overall_trend} prefix="Overall ·" />}>
          <p className="text-sm leading-7 text-cosmic-text">{momentum.verdict}</p>
          <div className="mt-4 flex flex-wrap gap-2">
            <TrendPill trend={momentum.engagement_trend} prefix="Engagement ·" />
            <TrendPill trend={momentum.sentiment_trend} prefix="Sentiment ·" />
            <TrendPill trend={momentum.buying_signal_trend} prefix="Buying signals ·" />
          </div>

          {momentum.trend_points.length > 0 && (
            <div className="mt-6 grid gap-5 md:grid-cols-3">
              <Sparkline label="Meeting score" max={10} tone="green" values={momentum.trend_points.map((point) => point.scorecard_overall)} />
              <Sparkline label="Discovery coverage %" max={100} tone="cyan" values={momentum.trend_points.map((point) => point.discovery_coverage_pct)} />
              <Sparkline label="Unresolved objections" max={Math.max(5, ...momentum.trend_points.map((point) => point.unresolved_objections ?? 0))} tone="orange" values={momentum.trend_points.map((point) => point.unresolved_objections)} />
            </div>
          )}

          <div className="mt-6 overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-xs">
              <thead className="text-[10px] uppercase tracking-[0.14em] text-cosmic-muted">
                <tr>
                  <th className="py-2 pr-3 font-medium">Meeting</th>
                  <th className="py-2 pr-3 font-medium">Sentiment</th>
                  <th className="py-2 pr-3 font-medium">Engagement</th>
                  <th className="py-2 pr-3 font-medium">Stage</th>
                  <th className="py-2 pr-3 font-medium">Score</th>
                  <th className="py-2 pr-3 font-medium">Objections</th>
                  <th className="py-2 font-medium">Coverage</th>
                </tr>
              </thead>
              <tbody>
                {momentum.trend_points.map((point) => (
                  <tr key={point.meeting_id} className="border-t border-cosmic-border/60 text-cosmic-text">
                    <td className="py-2.5 pr-3">
                      <MeetingLinkCell id={point.meeting_id} title={point.meeting_title} date={point.meeting_date} />
                    </td>
                    <td className="py-2.5 pr-3">{point.sentiment ? <StatusPill value={point.sentiment} /> : '—'}</td>
                    <td className="py-2.5 pr-3">{point.engagement ? <ConfidencePill value={point.engagement} prefix="" /> : '—'}</td>
                    <td className="py-2.5 pr-3">{point.signal_stage ? <StatusPill value={point.signal_stage} /> : '—'}</td>
                    <td className="py-2.5 pr-3 tabular-nums">{point.scorecard_overall ?? '—'}</td>
                    <td className="py-2.5 pr-3 tabular-nums">{point.unresolved_objections ?? '—'}</td>
                    <td className="py-2.5 tabular-nums">{point.discovery_coverage_pct !== null ? `${point.discovery_coverage_pct}%` : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!momentum.trend_points.length && <Empty>No per-meeting trend data yet.</Empty>}
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <div>
              <Label>New stakeholders entered</Label>
              <div className="mt-2">
                <Chips items={momentum.new_stakeholders_entered} empty="No new stakeholders" />
              </div>
            </div>
            <div>
              <Label>Delays or missed milestones</Label>
              <div className="mt-2">
                <StringList items={momentum.delays_or_missed_milestones} empty="None recorded." tone="amber" />
              </div>
            </div>
          </div>
        </Panel>
      ) : (
        <Unavailable name="Momentum" warnings={analysis.warnings} />
      )}
    </div>
  )
}

function MeetingLinkCell({ id, title, date }: { id: string; title: string; date: string }) {
  const { openMeeting } = useContext(AnalyticsContext)
  return (
    <button type="button" onClick={() => openMeeting(id)} className="text-left hover:text-nagarro-green">
      <div className="font-medium text-white">{title}</div>
      <div className="text-[11px] text-cosmic-muted">{formatDate(date)}</div>
    </button>
  )
}

function RisksTab({ analysis }: { analysis: DealAnalyticsResult }) {
  const register = analysis.risks
  if (!register) return <Unavailable name="Risks" warnings={analysis.warnings} />
  const priority = register.risks.find((risk) => risk.risk_key === register.highest_priority_risk_key) ?? null
  const sorted = [...register.risks].sort((a, b) => Number(OPEN_RISK.includes(b.status)) - Number(OPEN_RISK.includes(a.status)))
  return (
    <div className="space-y-6">
      {priority && (
        <Notice tone="red" icon={<ShieldAlert className="mt-0.5 h-4 w-4 flex-none" />}>
          <div className="text-[10px] uppercase tracking-[0.18em] opacity-80">Highest priority risk</div>
          <div className="font-semibold">{priority.title}</div>
        </Notice>
      )}
      {!priority && register.highest_priority_risk_key && (
        <Notice tone="amber">Highest priority risk key · {register.highest_priority_risk_key}</Notice>
      )}
      <Panel title="Risk register" count={register.risks.length} icon={<ShieldAlert className="h-3.5 w-3.5 text-orange-300" />}>
        {sorted.length ? (
          <div className="grid gap-4 xl:grid-cols-2">
            {sorted.map((risk) => (
              <ItemCard key={risk.risk_key} tone={risk.severity === 'CRITICAL' ? 'red' : risk.severity === 'HIGH' ? 'orange' : 'neutral'}>
                <div className="flex flex-wrap items-center gap-2">
                  <SeverityPill value={risk.severity} />
                  <StatusPill value={risk.status} />
                  <Pill tone="neutral">{humanize(risk.category)}</Pill>
                  <Pill tone="neutral">Seen in {risk.occurrences} meeting{risk.occurrences === 1 ? '' : 's'}</Pill>
                </div>
                <h4 className="mt-3 text-base font-semibold text-white">{risk.title}</h4>
                <p className="mt-1 text-sm leading-6 text-cosmic-text">{risk.description}</p>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <Field label="Mitigation">{risk.mitigation ?? 'No mitigation defined'}</Field>
                  <Field label="Suggested owner">{risk.suggested_owner ?? 'Unassigned'}</Field>
                  <Field label="First seen">
                    {risk.first_seen_meeting_id ? <MeetingChips ids={[risk.first_seen_meeting_id]} /> : '—'}
                  </Field>
                  <Field label="Last seen">
                    {risk.last_seen_meeting_id ? <MeetingChips ids={[risk.last_seen_meeting_id]} /> : '—'}
                  </Field>
                </div>
                <div className="mt-3 text-[11px] text-cosmic-muted">Key · {risk.risk_key}</div>
                <FindingMeta finding={risk} />
              </ItemCard>
            ))}
          </div>
        ) : (
          <Empty>No risks have been identified for this deal.</Empty>
        )}
      </Panel>
    </div>
  )
}

function CommitteeTab({ analysis }: { analysis: DealAnalyticsResult }) {
  const committee = analysis.buying_committee
  if (!committee) return <Unavailable name="Buying committee" warnings={analysis.warnings} />
  return (
    <div className="space-y-6">
      <Panel title="Committee coverage" icon={<Users className="h-3.5 w-3.5 text-cyan-300" />}>
        <p className="text-sm leading-7 text-cosmic-text">{committee.coverage_summary || 'No coverage summary.'}</p>
        <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          <BoolRow label="Economic buyer access" value={committee.economic_buyer_access} />
          <BoolRow label="Technical evaluator access" value={committee.technical_evaluator_access} />
          <BoolRow label="Champion identified" value={committee.champion_identified} />
          <BoolRow label="Procurement involved" value={committee.procurement_involved} />
          <BoolRow label="Security / legal involved" value={committee.security_legal_involved} />
          <div className="flex items-center justify-between gap-3 rounded-xl border border-cosmic-border bg-cosmic-bg/30 px-3 py-2.5">
            <span className="text-sm text-cosmic-text">Champion strength</span>
            {committee.champion_strength ? <ConfidencePill value={committee.champion_strength} prefix="" /> : <Pill>Not assessed</Pill>}
          </div>
        </div>
        <div className="mt-5 grid gap-5 lg:grid-cols-3">
          <Field label="Next stakeholder to engage">{committee.next_stakeholder_to_engage ?? 'Not determined'}</Field>
          <Field label="Missing roles">
            {committee.missing_roles.length ? (
              <div className="flex flex-wrap gap-2">
                {committee.missing_roles.map((role) => (
                  <Pill key={role} tone="amber">
                    {humanize(role)}
                  </Pill>
                ))}
              </div>
            ) : (
              'All key roles covered'
            )}
          </Field>
          <Field label="Conflicting priorities">
            <StringList items={committee.conflicting_priorities} empty="None identified." tone="orange" />
          </Field>
        </div>
      </Panel>

      <Panel title="Committee members" count={committee.members.length}>
        {committee.members.length ? (
          <div className="grid gap-4 xl:grid-cols-2">
            {committee.members.map((member) => (
              <ItemCard key={member.name}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h4 className="text-base font-semibold text-white">{member.name}</h4>
                    <p className="text-xs text-cosmic-muted">{member.title ?? 'Title not stated'}</p>
                  </div>
                  <StatusPill value={member.stance} />
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <Pill tone="cyan">{humanize(member.buying_role)}</Pill>
                  <Pill tone={member.role_confirmed ? 'green' : 'violet'}>{member.role_confirmed ? 'Role confirmed' : 'Role inferred'}</Pill>
                  <ConfidencePill value={member.engagement} prefix="engagement" />
                  <Pill tone="neutral">{member.meetings_attended} meeting{member.meetings_attended === 1 ? '' : 's'}</Pill>
                </div>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <Field label="Priorities">
                    <StringList items={member.priorities} empty="None captured." tone="cyan" />
                  </Field>
                  <Field label="Concerns">
                    <StringList items={member.concerns} empty="None captured." tone="amber" />
                  </Field>
                </div>
                <div className="mt-4">
                  <Field label="Recommended engagement">{member.recommended_engagement ?? 'No recommendation'}</Field>
                </div>
                <FindingMeta finding={member} />
              </ItemCard>
            ))}
          </div>
        ) : (
          <Empty>No committee members identified yet.</Empty>
        )}
      </Panel>
    </div>
  )
}

function CompetitiveTab({ analysis }: { analysis: DealAnalyticsResult }) {
  const competitive = analysis.competitive
  if (!competitive) return <Unavailable name="Competitive" warnings={analysis.warnings} />
  return (
    <div className="space-y-6">
      <Panel title="Competitors" count={competitive.competitors.length} icon={<Swords className="h-3.5 w-3.5 text-red-300" />}>
        {competitive.competitors.length ? (
          <div className="grid gap-4 xl:grid-cols-2">
            {competitive.competitors.map((competitor) => (
              <ItemCard key={competitor.name}>
                <div className="flex items-start justify-between gap-3">
                  <h4 className="text-base font-semibold text-white">{competitor.name}</h4>
                  <Pill tone={competitor.confirmed ? 'green' : 'violet'}>{competitor.confirmed ? 'Confirmed' : 'Hypothesis'}</Pill>
                </div>
                <p className="mt-2 text-xs leading-5 text-cosmic-muted">
                  <span className="font-semibold text-cosmic-text">Buyer perception · </span>
                  {competitor.buyer_perception ?? 'Not stated'}
                </p>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <Field label="Where they may be stronger">
                    <StringList items={competitor.where_they_may_be_stronger} empty="None noted." tone="red" />
                  </Field>
                  <Field label="Where we are stronger">
                    <StringList items={competitor.where_we_are_stronger} empty="None noted." tone="green" />
                  </Field>
                </div>
                <FindingMeta finding={competitor} />
              </ItemCard>
            ))}
          </div>
        ) : (
          <Empty>No competitors have been confirmed or hypothesised.</Empty>
        )}
      </Panel>
      <div className="grid gap-6 lg:grid-cols-2 xl:grid-cols-3">
        <Panel title="Evaluation criteria" count={competitive.evaluation_criteria.length}>
          <StringList items={competitive.evaluation_criteria} empty="None captured." tone="cyan" />
        </Panel>
        <Panel title="Strongest differentiators" count={competitive.strongest_differentiators.length}>
          <StringList items={competitive.strongest_differentiators} empty="None identified." tone="green" />
        </Panel>
        <Panel title="Competitive gaps" count={competitive.competitive_gaps.length}>
          <StringList items={competitive.competitive_gaps} empty="None identified." tone="red" />
        </Panel>
        <Panel title="Unresolved competitive questions" count={competitive.unresolved_competitive_questions.length}>
          <StringList items={competitive.unresolved_competitive_questions} empty="None." tone="amber" />
        </Panel>
        <Panel title="Recommended positioning changes" count={competitive.recommended_positioning_changes.length}>
          <StringList items={competitive.recommended_positioning_changes} empty="None recommended." tone="violet" />
        </Panel>
      </div>
    </div>
  )
}

function ExecutionTab({ analysis }: { analysis: DealAnalyticsResult }) {
  const execution = analysis.execution
  if (!execution) return <Unavailable name="Execution" warnings={analysis.warnings} />
  return (
    <div className="space-y-6">
      <Panel title="Sales execution" icon={<Compass className="h-3.5 w-3.5 text-violet-300" />}>
        <div className="flex flex-col gap-6 md:flex-row md:items-center">
          <Ring value={execution.commitment_reliability_pct ?? 0} size={116}>
            <span className="text-2xl font-bold text-white">
              {execution.commitment_reliability_pct !== null ? `${execution.commitment_reliability_pct}%` : '—'}
            </span>
            <span className="text-[10px] uppercase tracking-[0.14em] text-cosmic-muted">reliability</span>
          </Ring>
          <div className="flex-1 space-y-3">
            <div className="flex flex-wrap gap-2">
              <TrendPill trend={execution.discovery_quality_trend} prefix="Discovery quality ·" />
            </div>
            <p className="text-sm leading-7 text-cosmic-text">{execution.follow_up_reliability_note || 'No follow-up reliability note.'}</p>
          </div>
        </div>
      </Panel>

      <div className="grid gap-6 xl:grid-cols-3">
        <Panel title="Recurring patterns" count={execution.recurring_patterns.length}>
          <StringList items={execution.recurring_patterns} empty="No recurring patterns yet." tone="amber" />
        </Panel>
        <Panel title="Repeated mistake categories" count={execution.repeated_mistake_categories.length}>
          <StringList items={execution.repeated_mistake_categories} empty="No repeated mistakes." tone="red" />
        </Panel>
        <Panel title="Improvements over time" count={execution.improvements_over_time.length}>
          <StringList items={execution.improvements_over_time} empty="No improvements recorded yet." tone="green" />
        </Panel>
      </div>

      <Panel title="Commitments ledger" count={execution.commitments.length} icon={<CheckCircle2 className="h-3.5 w-3.5 text-emerald-300" />}>
        {execution.commitments.length ? (
          <div className="space-y-3">
            {execution.commitments.map((commitment, index) => (
              <ItemCard key={`${index}-${commitment.commitment.slice(0, 24)}`}>
                <div className="flex flex-wrap items-center gap-2">
                  <StatusPill value={commitment.status} />
                  <Pill tone="neutral">Owner · {commitment.owner ?? 'Unassigned'}</Pill>
                  <Pill tone="neutral">Due · {commitment.due ?? 'No date'}</Pill>
                  <MeetingChips ids={[commitment.made_in_meeting_id]} />
                </div>
                <p className="mt-3 text-sm leading-6 text-white">{commitment.commitment}</p>
                <FindingMeta finding={commitment} />
              </ItemCard>
            ))}
          </div>
        ) : (
          <Empty>No commitments have been tracked.</Empty>
        )}
      </Panel>
    </div>
  )
}

const GAP_TONE: Record<string, Tone> = { CONFIRMED: 'green', CONTRADICTED: 'red', NEW_INSIGHT: 'violet', UNVALIDATED: 'amber' }

function TrackersTab({ analysis }: { analysis: DealAnalyticsResult }) {
  const trackers = analysis.trackers
  if (!trackers) return <Unavailable name="Trackers" warnings={analysis.warnings} />
  return (
    <div className="space-y-6">
      <Panel title="Buying signal stage" icon={<Flag className="h-3.5 w-3.5 text-cyan-300" />}>
        <StatusPill value={trackers.signal_stage} />
      </Panel>

      <Panel title="Warning signals" count={trackers.warning_signals.length} icon={<AlertTriangle className="h-3.5 w-3.5 text-orange-300" />}>
        {trackers.warning_signals.length ? (
          <div className="grid gap-4 xl:grid-cols-2">
            {trackers.warning_signals.map((signal, index) => (
              <ItemCard key={`${index}-${signal.title}`} tone={signal.is_disqualifying ? 'red' : 'neutral'}>
                <div className="flex flex-wrap items-center gap-2">
                  <SeverityPill value={signal.severity} />
                  {signal.is_disqualifying && <Pill tone="red">Potential deal killer</Pill>}
                </div>
                <h4 className="mt-3 text-base font-semibold text-white">{signal.title}</h4>
                <p className="mt-1 text-sm leading-6 text-cosmic-text">{signal.description}</p>
                {signal.uncertainty_note && (
                  <p className="mt-2 text-xs leading-5 text-cosmic-muted">
                    <span className="font-semibold text-cosmic-text">Uncertainty · </span>
                    {signal.uncertainty_note}
                  </p>
                )}
                <FindingMeta finding={signal} />
              </ItemCard>
            ))}
          </div>
        ) : (
          <Empty>No warning signals detected.</Empty>
        )}
      </Panel>

      <Panel title="Unanswered customer questions" count={trackers.unanswered_questions.length} icon={<HelpCircle className="h-3.5 w-3.5 text-amber-300" />}>
        {trackers.unanswered_questions.length ? (
          <div className="space-y-3">
            {trackers.unanswered_questions.map((question, index) => (
              <ItemCard key={`${index}-${question.question.slice(0, 24)}`}>
                <div className="flex flex-wrap items-center gap-2">
                  <StatusPill value={question.status} />
                  <Pill tone="neutral">Asked by · {question.asked_by ?? 'Unknown'}</Pill>
                  <Pill tone="neutral">Owner · {question.owner ?? 'Unassigned'}</Pill>
                  {question.first_raised_meeting_id && <MeetingChips ids={[question.first_raised_meeting_id]} />}
                </div>
                <p className="mt-3 text-sm leading-6 text-white">{question.question}</p>
                <FindingMeta finding={question} />
              </ItemCard>
            ))}
          </div>
        ) : (
          <Empty>No open customer questions.</Empty>
        )}
      </Panel>

      <Panel title="Research vs conversation" count={trackers.research_gaps.length} icon={<Compass className="h-3.5 w-3.5 text-violet-300" />}>
        {trackers.research_gaps.length ? (
          <div className="space-y-3">
            {trackers.research_gaps.map((gap, index) => (
              <ItemCard key={`${index}-${gap.hypothesis_from_research.slice(0, 24)}`}>
                <div className="flex items-center gap-2">
                  <Pill tone={GAP_TONE[gap.verdict] ?? 'neutral'}>{humanize(gap.verdict)}</Pill>
                </div>
                <div className="mt-3 grid gap-4 md:grid-cols-2">
                  <Field label="Research hypothesis">{gap.hypothesis_from_research}</Field>
                  <Field label="What the meetings showed">{gap.reality_from_meetings}</Field>
                </div>
                <FindingMeta finding={gap} />
              </ItemCard>
            ))}
          </div>
        ) : (
          <Empty>No research gaps identified.</Empty>
        )}
      </Panel>
    </div>
  )
}

function StrategyTab({ analysis }: { analysis: DealAnalyticsResult }) {
  const strategy = analysis.strategy
  if (!strategy) return <Unavailable name="Strategy" warnings={analysis.warnings} />
  const sorted = [...strategy.top_actions].sort((a, b) => a.rank - b.rank)
  return (
    <div className="space-y-6">
      <Panel title="Top actions" count={sorted.length} icon={<Target className="h-3.5 w-3.5 text-emerald-300" />}>
        {sorted.length ? (
          <div className="space-y-3">
            {sorted.map((action) => (
              <ItemCard key={`${action.rank}-${action.action.slice(0, 24)}`}>
                <div className="flex items-start gap-3">
                  <span className="mt-0.5 inline-flex h-7 w-7 flex-none items-center justify-center rounded-full border border-nagarro-green/40 bg-nagarro-green/10 text-sm font-bold text-nagarro-green">
                    {action.rank}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold leading-6 text-white">{action.action}</p>
                    <p className="mt-1 text-xs leading-5 text-cosmic-muted">{action.rationale}</p>
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <SeverityPill value={action.impact} prefix="Impact ·" />
                      <SeverityPill value={action.urgency} prefix="Urgency ·" />
                      <Pill tone="neutral">Owner · {action.suggested_owner ?? 'Unassigned'}</Pill>
                      {action.linked_risk_keys.map((key) => (
                        <Pill key={key} tone="orange">
                          Risk · {key}
                        </Pill>
                      ))}
                    </div>
                  </div>
                </div>
                <FindingMeta finding={action} />
              </ItemCard>
            ))}
          </div>
        ) : (
          <Empty>No strategic actions yet.</Empty>
        )}
      </Panel>

      <div className="grid gap-6 lg:grid-cols-3">
        <Panel title="Risk to resolve first">
          <p className="text-sm leading-6 text-cosmic-text">{strategy.highest_priority_risk_to_resolve ?? 'Not determined'}</p>
        </Panel>
        <Panel title="Engage next">
          <p className="text-sm leading-6 text-cosmic-text">{strategy.next_stakeholder_to_engage ?? 'Not determined'}</p>
        </Panel>
        <Panel title="Negotiation strategy">
          <p className="text-sm leading-6 text-cosmic-text">{strategy.negotiation_strategy ?? 'Not yet defined'}</p>
        </Panel>
      </div>

      <div className="grid gap-6 lg:grid-cols-2 xl:grid-cols-3">
        <Panel title="Questions for the next meeting" count={strategy.questions_for_next_meeting.length}>
          <StringList items={strategy.questions_for_next_meeting} empty="None suggested." tone="cyan" />
        </Panel>
        <Panel title="Documents to prepare" count={strategy.documents_to_prepare.length}>
          <StringList items={strategy.documents_to_prepare} empty="None." tone="violet" />
        </Panel>
        <Panel title="Objections to address first" count={strategy.objections_to_address_before_advancing.length}>
          <StringList items={strategy.objections_to_address_before_advancing} empty="None." tone="orange" />
        </Panel>
        <Panel title="Presentation changes" count={strategy.presentation_changes.length}>
          <StringList items={strategy.presentation_changes} empty="None." tone="green" />
        </Panel>
        <Panel title="Suggested next agenda" count={strategy.suggested_next_meeting_agenda.length}>
          <StringList items={strategy.suggested_next_meeting_agenda} empty="No agenda suggested." ordered />
        </Panel>
        <Panel title="Before forecasting a close" count={strategy.conditions_before_forecasting_close.length}>
          <StringList items={strategy.conditions_before_forecasting_close} empty="No conditions defined." tone="amber" />
        </Panel>
      </div>
    </div>
  )
}

const EVENT_TONE: Record<string, Tone> = {
  MEETING: 'cyan',
  BUYING_SIGNAL: 'green',
  RISK_OPENED: 'orange',
  RISK_RESOLVED: 'green',
  STAKEHOLDER_CHANGE: 'violet',
  WIN_PROBABILITY_CHANGE: 'amber',
  COMMITMENT_FULFILLED: 'green',
  COMMITMENT_MISSED: 'red',
  STAGE_CHANGE: 'violet',
  CUSTOMER_DECISION: 'cyan',
}

function TimelineTab({ analysis }: { analysis: DealAnalyticsResult }) {
  const timeline = analysis.timeline
  const { openMeeting } = useContext(AnalyticsContext)
  if (!timeline) return <Unavailable name="Timeline" warnings={analysis.warnings} />
  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="What changed after the latest meeting" count={timeline.what_changed_after_latest_meeting.length} icon={<RefreshCw className="h-3.5 w-3.5 text-cyan-300" />}>
          <StringList items={timeline.what_changed_after_latest_meeting} empty="No changes recorded." tone="cyan" />
        </Panel>
        <Panel title="Why the assessment changed" icon={<Sparkles className="h-3.5 w-3.5 text-amber-300" />}>
          <p className="text-sm leading-7 text-cosmic-text">{timeline.why_assessment_changed || 'No change in assessment.'}</p>
        </Panel>
      </div>

      <Panel title="Deal history" count={timeline.events.length} icon={<CalendarClock className="h-3.5 w-3.5 text-violet-300" />}>
        {timeline.events.length ? (
          <ol className="relative space-y-5 border-l border-cosmic-border pl-6">
            {timeline.events.map((event, index) => {
              const tone = EVENT_TONE[event.event_type] ?? 'neutral'
              return (
                <li key={`${index}-${event.title}`} className="relative">
                  <span className={`absolute -left-[31px] top-1.5 h-3 w-3 rounded-full border-2 border-cosmic-bg ${TONE_TEXT[tone].replace('text-', 'bg-')}`} />
                  <div className="flex flex-wrap items-center gap-2">
                    <Pill tone={tone}>{humanize(event.event_type)}</Pill>
                    <span className="text-xs text-cosmic-muted">{formatDate(event.date)}</span>
                    {event.meeting_id && (
                      <button type="button" className="source-chip" onClick={() => openMeeting(event.meeting_id as string)}>
                        Open meeting
                      </button>
                    )}
                  </div>
                  <div className="mt-1.5 text-sm font-semibold text-white">{event.title}</div>
                  {event.detail && <p className="mt-0.5 text-sm leading-6 text-cosmic-muted">{event.detail}</p>}
                </li>
              )
            })}
          </ol>
        ) : (
          <Empty>No events recorded yet.</Empty>
        )}
      </Panel>
    </div>
  )
}

// ───────────────────────── Panel ─────────────────────────
export function DealAnalyticsPanel({
  analysis,
  state,
  error,
  onRun,
  meetingCount,
}: {
  analysis: DealAnalyticsResult | null
  state: LoadState
  error: string | null
  onRun: () => void
  meetingCount: number
}) {
  const [tab, setTab] = useState<DealTab>('overview')
  const { meetingTitle, openMeeting } = useContext(AnalyticsContext)

  const tabs = useMemo(
    () =>
      [
        { id: 'overview', label: 'Overview' },
        { id: 'risks', label: 'Risks', count: analysis?.risks?.risks.length },
        { id: 'committee', label: 'Buying committee', count: analysis?.buying_committee?.members.length },
        { id: 'competitive', label: 'Competitive' },
        { id: 'execution', label: 'Execution' },
        { id: 'trackers', label: 'Trackers', count: analysis?.trackers?.warning_signals.length },
        { id: 'strategy', label: 'Strategy' },
        { id: 'timeline', label: 'Timeline', count: analysis?.timeline?.events.length },
      ] as const,
    [analysis],
  )

  const header = (
    <div className="cosmic-card p-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Pill tone="green" icon={<BarChart3 className="h-3 w-3" />}>
              Overall deal analytics
            </Pill>
            {analysis?.status && <StatusPill value={analysis.status} />}
          </div>
          <h2 className="mt-3 text-2xl font-bold tracking-tight text-white">{analysis?.deal_profile?.title ?? 'Deal intelligence across all meetings'}</h2>
          <p className="mt-1 text-sm text-cosmic-muted">
            {analysis?.deal_profile
              ? [analysis.deal_profile.target_company, analysis.deal_profile.target_industry, analysis.deal_profile.status].filter(Boolean).join(' · ')
              : 'A synthesis of every meeting, your research brief and how the deal has changed over time.'}
          </p>
          {analysis?.deal_profile?.meeting_objective && <p className="mt-2 text-sm text-cosmic-text">Objective · {analysis.deal_profile.meeting_objective}</p>}
        </div>
        <button type="button" className="btn-nagarro inline-flex items-center gap-2 self-start" onClick={onRun} disabled={state === 'loading' || meetingCount === 0}>
          {state === 'loading' ? <Loader2 className="h-4 w-4 animate-spin" /> : analysis ? <RefreshCw className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
          {state === 'loading' ? 'Analysing deal…' : analysis ? 'Refresh deal analytics' : 'Run deal analytics'}
        </button>
      </div>
      {analysis && (
        <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-cosmic-border/60 pt-4 text-xs text-cosmic-muted">
          <span>Snapshot v{analysis.snapshot_version}</span>
          <span>Meetings analysed · {analysis.meetings_analyzed}</span>
          <span>
            Latest meeting ·{' '}
            {analysis.latest_meeting_id ? (
              <button type="button" className="text-nagarro-green hover:underline" onClick={() => openMeeting(analysis.latest_meeting_id as string)}>
                {meetingTitle(analysis.latest_meeting_id) ?? analysis.latest_meeting_id.slice(0, 8)}
              </button>
            ) : (
              '—'
            )}
          </span>
          <span>Generated · {formatDateTime(analysis.generated_at)}</span>
          <span>Model · {analysis.model_name ?? 'Unknown'}</span>
          <span>Schema · v{analysis.schema_version}</span>
        </div>
      )}
    </div>
  )

  if (state === 'loading' && !analysis) {
    return (
      <div className="space-y-6">
        {header}
        <div className="cosmic-card p-6">
          <div className="mb-4 flex items-center gap-3 text-sm text-cosmic-muted">
            <Loader2 className="h-4 w-4 animate-spin text-nagarro-green" />
            Building the deal view from every meeting. This can take a few minutes.
          </div>
          <SkeletonBlock rows={4} />
        </div>
      </div>
    )
  }

  if (!analysis) {
    return (
      <div className="space-y-6">
        {header}
        {state === 'error' && <Notice tone="red">{error ?? 'Unable to load deal analytics.'}</Notice>}
        <div className="cosmic-card p-10 text-center">
          <BarChart3 className="mx-auto mb-4 h-10 w-10 text-nagarro-green opacity-80" />
          <h3 className="text-lg font-semibold text-white">No deal analytics yet</h3>
          <p className="mx-auto mt-2 max-w-md text-sm text-cosmic-muted">
            {meetingCount === 0
              ? 'Add a meeting with a transcript first. Deal analytics are built from your meeting analyses.'
              : 'Run deal analytics to see win probability, health, risks, the buying committee and a recommended strategy.'}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {header}
      {analysis.status && analysis.status !== 'COMPLETED' && (
        <Notice tone={analysis.status === 'FAILED' ? 'red' : 'amber'}>
          <div className="font-semibold">{analysis.status === 'FAILED' ? 'The deal analysis failed' : 'Some deal sections are incomplete'}</div>
        </Notice>
      )}
      {analysis.warnings.length > 0 && (
        <Notice tone="amber">
          <div className="font-semibold">Analysis warnings</div>
          <ul className="mt-1 list-disc space-y-0.5 pl-4 text-xs opacity-90">
            {analysis.warnings.map((warning, index) => (
              <li key={`${index}-${warning.slice(0, 20)}`}>{warning}</li>
            ))}
          </ul>
        </Notice>
      )}
      {state === 'error' && <Notice tone="red">{error}</Notice>}

      <TabBar tabs={tabs} active={tab} onChange={setTab} />

      {tab === 'overview' && <OverviewTab analysis={analysis} />}
      {tab === 'risks' && <RisksTab analysis={analysis} />}
      {tab === 'committee' && <CommitteeTab analysis={analysis} />}
      {tab === 'competitive' && <CompetitiveTab analysis={analysis} />}
      {tab === 'execution' && <ExecutionTab analysis={analysis} />}
      {tab === 'trackers' && <TrackersTab analysis={analysis} />}
      {tab === 'strategy' && <StrategyTab analysis={analysis} />}
      {tab === 'timeline' && <TimelineTab analysis={analysis} />}
    </div>
  )
}