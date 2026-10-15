import { useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import {
  AlertTriangle,
  Briefcase,
  CheckCircle2,
  FileText,
  Gauge,
  Lightbulb,
  Loader2,
  MessageSquareText,
  Presentation,
  RefreshCw,
  Sparkles,
  Swords,
  Target,
  ThumbsDown,
  ThumbsUp,
  Users,
  XCircle,
} from 'lucide-react'

import type {
  ActionItem,
  MeetingAnalysisResult,
  MeetingRecord,
  Objection,
} from './analysisTypes'
import {
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
  NeedBlock,
  Notice,
  Panel,
  Pill,
  Ring,
  ScoreMeter,
  SeverityPill,
  SkeletonBlock,
  StatusPill,
  StringList,
  TabBar,
  Unavailable,
} from './analyticsUi'

export type LoadState = 'idle' | 'loading' | 'missing' | 'error'

type MeetingTab =
  | 'summary'
  | 'scorecard'
  | 'mistakes'
  | 'discovery'
  | 'objections'
  | 'presentation'
  | 'stakeholders'
  | 'competitive'
  | 'next'
  | 'record'

// ───────────────────────── Tabs ─────────────────────────
function SummaryTab({ analysis }: { analysis: MeetingAnalysisResult }) {
  const summary = analysis.summary
  if (!summary) return <Unavailable name="Summary" warnings={analysis.warnings} />

  const actionList = (items: ActionItem[], empty: string) =>
    items.length ? (
      <div className="space-y-3">
        {items.map((item, index) => (
          <ItemCard key={`${index}-${item.description.slice(0, 24)}`}>
            <p className="text-sm leading-6 text-white">{item.description}</p>
            <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-cosmic-muted">
              <Pill tone="neutral">Owner · {item.owner ?? 'Unassigned'}</Pill>
              <StatusPill value={item.owner_side} />
              <Pill tone="neutral">Due · {item.due_date ?? 'No date'}</Pill>
              <StatusPill value={item.origin} />
            </div>
            <FindingMeta finding={item} />
          </ItemCard>
        ))}
      </div>
    ) : (
      <Empty>{empty}</Empty>
    )

  return (
    <div className="space-y-6">
      <Panel title="Executive summary" icon={<Sparkles className="h-3.5 w-3.5 text-amber-300" />}>
        <p className="text-sm leading-7 text-cosmic-text">{summary.executive_summary}</p>
        <div className="mt-4">
          <Label>Key topics</Label>
          <div className="mt-2">
            <Chips items={summary.key_topics} empty="No topics extracted" />
          </div>
        </div>
      </Panel>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Objectives met" count={summary.objectives_met.length} icon={<CheckCircle2 className="h-3.5 w-3.5 text-emerald-300" />}>
          <StringList items={summary.objectives_met} empty="No stated objective was clearly achieved." tone="green" />
        </Panel>
        <Panel title="Objectives missed" count={summary.objectives_missed.length} icon={<XCircle className="h-3.5 w-3.5 text-red-300" />}>
          <StringList items={summary.objectives_missed} empty="No missed objectives recorded." tone="red" />
        </Panel>
      </div>

      <Panel title="Decisions" count={summary.decisions.length} icon={<Target className="h-3.5 w-3.5 text-cyan-300" />}>
        {summary.decisions.length ? (
          <div className="space-y-3">
            {summary.decisions.map((decision, index) => (
              <ItemCard key={`${index}-${decision.decision.slice(0, 24)}`}>
                <p className="text-sm leading-6 text-white">{decision.decision}</p>
                <p className="mt-2 text-xs text-cosmic-muted">Made by · {decision.made_by ?? 'Not attributed'}</p>
                <FindingMeta finding={decision} />
              </ItemCard>
            ))}
          </div>
        ) : (
          <Empty>No decisions were made in this meeting.</Empty>
        )}
      </Panel>

      <div className="grid gap-6 xl:grid-cols-3">
        <Panel title="Our commitments" count={summary.our_commitments.length} icon={<Briefcase className="h-3.5 w-3.5 text-violet-300" />}>
          {actionList(summary.our_commitments, 'We did not commit to any deliverables.')}
        </Panel>
        <Panel title="Buyer requests" count={summary.buyer_requests.length} icon={<MessageSquareText className="h-3.5 w-3.5 text-cyan-300" />}>
          {actionList(summary.buyer_requests, 'The buyer made no explicit requests.')}
        </Panel>
        <Panel title="Buyer commitments" count={summary.buyer_commitments.length} icon={<Users className="h-3.5 w-3.5 text-emerald-300" />}>
          {actionList(summary.buyer_commitments, 'The buyer made no commitments.')}
        </Panel>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Unresolved questions" count={summary.unresolved_questions.length} icon={<AlertTriangle className="h-3.5 w-3.5 text-amber-300" />}>
          <StringList items={summary.unresolved_questions} empty="No open questions." tone="amber" />
        </Panel>
        <Panel title="Next meeting requirements" count={summary.next_meeting_requirements.length} icon={<Lightbulb className="h-3.5 w-3.5 text-cyan-300" />}>
          <StringList items={summary.next_meeting_requirements} empty="No requirements captured." tone="cyan" />
        </Panel>
      </div>
    </div>
  )
}

function ScorecardTab({ analysis }: { analysis: MeetingAnalysisResult }) {
  const { scorecard, sentiment } = analysis
  return (
    <div className="space-y-6">
      {scorecard ? (
        <Panel title="Meeting scorecard" count={scorecard.metrics.length} icon={<Gauge className="h-3.5 w-3.5 text-emerald-300" />}>
          {scorecard.metrics.length ? (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {scorecard.metrics.map((metric) => (
                <ItemCard key={metric.metric}>
                  <div className="text-sm font-semibold text-white">{humanize(metric.metric)}</div>
                  <div className="mt-3">
                    <ScoreMeter score={metric.score} label={humanize(metric.metric)} />
                  </div>
                  <p className="mt-3 text-xs leading-5 text-cosmic-muted">{metric.explanation}</p>
                  <FindingMeta finding={metric} />
                </ItemCard>
              ))}
            </div>
          ) : (
            <Empty>No scorecard metrics were produced.</Empty>
          )}
        </Panel>
      ) : (
        <Unavailable name="Scorecard" warnings={analysis.warnings} />
      )}

      {sentiment ? (
        <>
          <Panel title="Buyer sentiment" icon={<ThumbsUp className="h-3.5 w-3.5 text-cyan-300" />}>
            <div className="flex flex-wrap items-center gap-2">
              <StatusPill value={sentiment.overall_sentiment} />
              <StatusPill value={sentiment.signal_stage} prefix="Stage ·" />
            </div>
            <p className="mt-3 text-sm leading-7 text-cosmic-text">{sentiment.sentiment_rationale}</p>
            <div className="mt-5 grid gap-4 md:grid-cols-3">
              <Field label="Interest level">
                <ConfidencePill value={sentiment.interest_level} prefix="" />
              </Field>
              <Field label="Purchase intent">
                <ConfidencePill value={sentiment.purchase_intent} prefix="" />
              </Field>
              <Field label="Urgency">
                <ConfidencePill value={sentiment.urgency} prefix="" />
              </Field>
            </div>
          </Panel>

          <div className="grid gap-6 lg:grid-cols-2">
            <Panel title="Moving closer" icon={<ThumbsUp className="h-3.5 w-3.5 text-emerald-300" />}>
              <p className="text-sm leading-7 text-cosmic-text">{sentiment.moving_closer_summary || 'Nothing noted.'}</p>
            </Panel>
            <Panel title="Moving away" icon={<ThumbsDown className="h-3.5 w-3.5 text-red-300" />}>
              <p className="text-sm leading-7 text-cosmic-text">{sentiment.moving_away_summary || 'Nothing noted.'}</p>
            </Panel>
          </div>

          <Panel title="Buying signals" count={sentiment.signals.length} icon={<Sparkles className="h-3.5 w-3.5 text-amber-300" />}>
            {sentiment.signals.length ? (
              <div className="grid gap-3 lg:grid-cols-2">
                {sentiment.signals.map((signal, index) => (
                  <ItemCard key={`${index}-${signal.description.slice(0, 24)}`} tone={signal.direction === 'POSITIVE' ? 'green' : 'red'}>
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusPill value={signal.direction} />
                      <Pill tone="neutral">{humanize(signal.category)}</Pill>
                      <SeverityPill value={signal.strength} prefix="Strength ·" />
                      <Pill tone={signal.is_explicit_commitment ? 'green' : 'neutral'}>
                        {signal.is_explicit_commitment ? 'Explicit commitment' : 'Soft signal'}
                      </Pill>
                    </div>
                    <p className="mt-3 text-sm leading-6 text-white">{signal.description}</p>
                    <FindingMeta finding={signal} />
                  </ItemCard>
                ))}
              </div>
            ) : (
              <Empty>No buying signals were detected.</Empty>
            )}
          </Panel>
        </>
      ) : (
        <Unavailable name="Sentiment" warnings={analysis.warnings} />
      )}
    </div>
  )
}

function MistakesTab({ analysis }: { analysis: MeetingAnalysisResult }) {
  const mistakes = analysis.mistakes
  if (!mistakes) return <Unavailable name="Mistakes" warnings={analysis.warnings} />
  return (
    <div className="space-y-6">
      <Panel title="Mistakes & missed opportunities" count={mistakes.findings.length} icon={<AlertTriangle className="h-3.5 w-3.5 text-orange-300" />}>
        {mistakes.findings.length ? (
          <div className="space-y-4">
            {mistakes.findings.map((finding, index) => (
              <ItemCard key={`${index}-${finding.title}`} tone={finding.severity === 'CRITICAL' ? 'red' : finding.severity === 'HIGH' ? 'orange' : 'neutral'}>
                <div className="flex flex-wrap items-center gap-2">
                  <SeverityPill value={finding.severity} />
                  <Pill tone="neutral">{humanize(finding.category)}</Pill>
                </div>
                <h4 className="mt-3 text-base font-semibold text-white">{finding.title}</h4>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <Field label="What happened">{finding.what_happened}</Field>
                  <Field label="Why it matters">{finding.why_it_matters}</Field>
                  <Field label="What to do instead">{finding.what_to_do_instead}</Field>
                  <Field label="Deal impact">{finding.deal_impact}</Field>
                </div>
                <div className="mt-4 rounded-xl border border-nagarro-green/30 bg-nagarro-green/5 p-3">
                  <Label>A better response</Label>
                  <p className="mt-1.5 text-sm italic leading-6 text-white">“{finding.better_example}”</p>
                </div>
                <FindingMeta finding={finding} />
              </ItemCard>
            ))}
          </div>
        ) : (
          <Empty>No evidence-backed mistakes were identified in this meeting.</Empty>
        )}
      </Panel>
      <Panel title="What went well" count={mistakes.strengths.length} icon={<ThumbsUp className="h-3.5 w-3.5 text-emerald-300" />}>
        <StringList items={mistakes.strengths} empty="No strengths were highlighted." tone="green" />
      </Panel>
    </div>
  )
}

function DiscoveryTab({ analysis }: { analysis: MeetingAnalysisResult }) {
  const discovery = analysis.discovery
  if (!discovery) return <Unavailable name="Discovery" warnings={analysis.warnings} />
  return (
    <div className="space-y-6">
      <Panel title="Discovery coverage" icon={<Target className="h-3.5 w-3.5 text-cyan-300" />}>
        <div className="flex flex-col gap-6 md:flex-row md:items-center">
          <Ring value={discovery.coverage_pct} max={100} size={120}>
            <span className="text-2xl font-bold text-white">{discovery.coverage_pct}%</span>
            <span className="text-[10px] uppercase tracking-[0.14em] text-cosmic-muted">covered</span>
          </Ring>
          <div className="grid flex-1 gap-2 sm:grid-cols-2">
            {discovery.coverage.map((item) => (
              <div key={item.dimension} className="rounded-xl border border-cosmic-border bg-cosmic-bg/30 px-3 py-2.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm text-cosmic-text">{humanize(item.dimension)}</span>
                  <Pill tone={item.covered ? 'green' : 'red'}>{item.covered ? 'Covered' : 'Gap'}</Pill>
                </div>
                {item.note && <p className="mt-1.5 text-xs leading-5 text-cosmic-muted">{item.note}</p>}
              </div>
            ))}
            {!discovery.coverage.length && <Empty>No coverage breakdown was produced.</Empty>}
          </div>
        </div>
      </Panel>

      <div className="grid gap-6 xl:grid-cols-2">
        <NeedBlock title="Stated needs" items={discovery.stated_needs} />
        <NeedBlock title="Inferred needs" items={discovery.inferred_needs} />
        <NeedBlock title="Current solutions" items={discovery.current_solutions} />
        <NeedBlock title="Desired outcomes" items={discovery.desired_outcomes} />
        <NeedBlock title="Quantified value" items={discovery.quantified_value} />
        <NeedBlock title="Requirements" items={discovery.requirements} />
      </div>
      <NeedBlock title="Solution gaps" items={discovery.solution_gaps} icon={<AlertTriangle className="h-3.5 w-3.5 text-orange-300" />} />

      <Panel title="Unanswered discovery questions" count={discovery.unanswered_discovery_questions.length} icon={<Lightbulb className="h-3.5 w-3.5 text-amber-300" />}>
        <StringList items={discovery.unanswered_discovery_questions} empty="All key discovery questions were answered." tone="amber" />
      </Panel>
    </div>
  )
}

const OBJECTION_ORDER: Record<Objection['status'], number> = { UNRESOLVED: 0, PARTIALLY_RESOLVED: 1, RESOLVED: 2 }

function ObjectionsTab({ analysis }: { analysis: MeetingAnalysisResult }) {
  const objections = analysis.objections
  const sorted = useMemo(
    () => (objections ? [...objections.objections].sort((a, b) => OBJECTION_ORDER[a.status] - OBJECTION_ORDER[b.status]) : []),
    [objections],
  )
  if (!objections) return <Unavailable name="Objections" warnings={analysis.warnings} />
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="cosmic-card p-4">
          <Label>Unresolved</Label>
          <div className={`mt-2 text-3xl font-bold ${objections.unresolved_count ? 'text-red-300' : 'text-emerald-300'}`}>{objections.unresolved_count}</div>
        </div>
        <div className="cosmic-card p-4">
          <Label>Total raised</Label>
          <div className="mt-2 text-3xl font-bold text-white">{objections.objections.length}</div>
        </div>
        <div className="cosmic-card p-4">
          <Label>Resolved</Label>
          <div className="mt-2 text-3xl font-bold text-emerald-300">{objections.objections.filter((item) => item.status === 'RESOLVED').length}</div>
        </div>
      </div>

      {sorted.length ? (
        <div className="space-y-4">
          {sorted.map((objection, index) => (
            <ItemCard key={`${index}-${objection.description.slice(0, 24)}`} tone={objection.status === 'UNRESOLVED' ? 'red' : objection.status === 'PARTIALLY_RESOLVED' ? 'amber' : 'neutral'}>
              <div className="flex flex-wrap items-center gap-2">
                <StatusPill value={objection.status} />
                <SeverityPill value={objection.severity} />
                <Pill tone="neutral">{humanize(objection.category)}</Pill>
                <Pill tone="cyan">Raised by · {objection.raised_by ?? 'Unknown'}</Pill>
              </div>
              <p className="mt-3 text-sm leading-6 text-white">{objection.description}</p>
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <Field label="Our response">{objection.our_response ?? 'No response recorded.'}</Field>
                <Field label="Why this status">{objection.status_rationale}</Field>
                <Field label="Recommended response">{objection.recommended_response}</Field>
                <Field label="Follow-up">{objection.follow_up ?? 'None required.'}</Field>
              </div>
              <FindingMeta finding={objection} />
            </ItemCard>
          ))}
        </div>
      ) : (
        <Empty>No significant objections were raised.</Empty>
      )}
    </div>
  )
}

function PresentationTab({ analysis }: { analysis: MeetingAnalysisResult }) {
  const presentation = analysis.presentation
  if (!presentation) return <Unavailable name="Presentation" warnings={analysis.warnings} />
  return (
    <div className="space-y-6">
      {!presentation.deck_provided && (
        <Notice tone="cyan" icon={<Presentation className="mt-0.5 h-4 w-4 flex-none" />}>
          No presentation deck was provided for this meeting, so slide-level analysis is not available.
        </Notice>
      )}
      <Panel title="Presentation effectiveness" icon={<Presentation className="h-3.5 w-3.5 text-violet-300" />} aside={<Pill tone={presentation.deck_provided ? 'green' : 'neutral'}>{presentation.deck_provided ? 'Deck analysed' : 'No deck'}</Pill>}>
        <div className="grid gap-5 md:grid-cols-3">
          <Field label="Relevance to buyer priorities">
            <ScoreMeter score={presentation.relevance_to_buyer_priorities} label="Relevance" />
          </Field>
          <Field label="Value proposition strength">
            <ScoreMeter score={presentation.value_proposition_strength} label="Value proposition" />
          </Field>
          <Field label="Differentiation quality">
            <ScoreMeter score={presentation.differentiation_quality} label="Differentiation" />
          </Field>
        </div>
        {presentation.summary && <p className="mt-5 text-sm leading-7 text-cosmic-text">{presentation.summary}</p>}
      </Panel>

      <Panel title="Slide findings" count={presentation.slide_findings.length} icon={<FileText className="h-3.5 w-3.5 text-cyan-300" />}>
        {presentation.slide_findings.length ? (
          <div className="grid gap-3 lg:grid-cols-2">
            {presentation.slide_findings.map((finding, index) => (
              <ItemCard key={`${index}-${finding.description.slice(0, 24)}`}>
                <div className="flex flex-wrap items-center gap-2">
                  <Pill tone="violet">{finding.slide_number !== null ? `Slide ${finding.slide_number}` : 'General'}</Pill>
                  <StatusPill value={finding.issue_type} />
                </div>
                <p className="mt-3 text-sm leading-6 text-white">{finding.description}</p>
                {finding.recommendation && (
                  <p className="mt-2 text-xs leading-5 text-cosmic-muted">
                    <span className="font-semibold text-cosmic-text">Recommendation · </span>
                    {finding.recommendation}
                  </p>
                )}
                <FindingMeta finding={finding} />
              </ItemCard>
            ))}
          </div>
        ) : (
          <Empty>No slide-level findings.</Empty>
        )}
      </Panel>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Missing topics" count={presentation.missing_topics.length}>
          <StringList items={presentation.missing_topics} empty="No missing topics." tone="amber" />
        </Panel>
        <Panel title="Missing proof points" count={presentation.missing_proof_points.length}>
          <StringList items={presentation.missing_proof_points} empty="No missing proof points." tone="orange" />
        </Panel>
        <Panel title="ROI quantification opportunities" count={presentation.roi_quantification_opportunities.length}>
          <StringList items={presentation.roi_quantification_opportunities} empty="No ROI opportunities noted." tone="cyan" />
        </Panel>
        <Panel title="Changes for the next deck" count={presentation.recommended_changes_for_next_deck.length}>
          <StringList items={presentation.recommended_changes_for_next_deck} empty="No changes recommended." tone="green" />
        </Panel>
      </div>
    </div>
  )
}

function StakeholdersTab({ analysis }: { analysis: MeetingAnalysisResult }) {
  const stakeholders = analysis.stakeholders
  if (!stakeholders) return <Unavailable name="Stakeholders" warnings={analysis.warnings} />
  return (
    <div className="space-y-6">
      <Panel title="Roles not yet seen" count={stakeholders.missing_roles.length} icon={<Users className="h-3.5 w-3.5 text-amber-300" />}>
        {stakeholders.missing_roles.length ? (
          <div className="flex flex-wrap gap-2">
            {stakeholders.missing_roles.map((role) => (
              <Pill key={role} tone="amber">
                {humanize(role)}
              </Pill>
            ))}
          </div>
        ) : (
          <Empty>All key buying roles were represented.</Empty>
        )}
      </Panel>

      {stakeholders.stakeholders.length ? (
        <div className="grid gap-4 xl:grid-cols-2">
          {stakeholders.stakeholders.map((person) => (
            <section key={person.name} className="cosmic-card p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h4 className="truncate text-base font-semibold text-white">{person.name}</h4>
                  <p className="text-xs text-cosmic-muted">{person.title ?? 'Title not stated'}</p>
                </div>
                <div className="flex flex-wrap justify-end gap-2">
                  <StatusPill value={person.side} />
                  <StatusPill value={person.stance} />
                </div>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <Pill tone="cyan">{humanize(person.buying_role)}</Pill>
                <Pill tone={person.role_source === 'CONFIRMED' ? 'green' : 'violet'}>Role {humanize(person.role_source)}</Pill>
                <ConfidencePill value={person.engagement_level} prefix="engagement" />
              </div>
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <Field label="Priorities">
                  <StringList items={person.priorities} empty="None captured." tone="cyan" />
                </Field>
                <Field label="Concerns">
                  <StringList items={person.concerns} empty="None captured." tone="amber" />
                </Field>
                <Field label="Commitments">
                  <StringList items={person.commitments} empty="None." tone="green" />
                </Field>
                <div className="space-y-3">
                  <Field label="Decision authority">{person.decision_authority ?? 'Not established'}</Field>
                  <Field label="Influence">{person.influence_notes ?? 'No evidence of influence'}</Field>
                </div>
              </div>
              {person.engagement_strategy && (
                <div className="mt-4 rounded-xl border border-nagarro-green/30 bg-nagarro-green/5 p-3">
                  <Label>Engagement strategy</Label>
                  <p className="mt-1.5 text-sm leading-6 text-white">{person.engagement_strategy}</p>
                </div>
              )}
              <FindingMeta finding={person} />
            </section>
          ))}
        </div>
      ) : (
        <Empty>No participants could be identified from the transcript.</Empty>
      )}
    </div>
  )
}

function CompetitiveTab({ analysis }: { analysis: MeetingAnalysisResult }) {
  const competitive = analysis.competitive
  if (!competitive) return <Unavailable name="Competitive" warnings={analysis.warnings} />
  return (
    <div className="space-y-6">
      <Panel title="Competitors mentioned" count={competitive.competitors.length} icon={<Swords className="h-3.5 w-3.5 text-red-300" />}>
        {competitive.competitors.length ? (
          <div className="grid gap-3 lg:grid-cols-2">
            {competitive.competitors.map((competitor) => (
              <ItemCard key={competitor.name}>
                <h4 className="text-base font-semibold text-white">{competitor.name}</h4>
                <p className="mt-2 text-sm leading-6 text-cosmic-text">{competitor.context}</p>
                <p className="mt-2 text-xs leading-5 text-cosmic-muted">
                  <span className="font-semibold text-cosmic-text">Buyer perception · </span>
                  {competitor.buyer_perception ?? 'Not stated'}
                </p>
                <FindingMeta finding={competitor} />
              </ItemCard>
            ))}
          </div>
        ) : (
          <Empty>No competitors were mentioned in this meeting.</Empty>
        )}
      </Panel>

      <div className="grid gap-6 xl:grid-cols-3">
        <NeedBlock title="Buyer evaluation criteria" items={competitive.buyer_evaluation_criteria} />
        <NeedBlock title="Our apparent strengths" items={competitive.our_apparent_strengths} />
        <NeedBlock title="Our apparent weaknesses" items={competitive.our_apparent_weaknesses} />
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <Panel title="Claims needing evidence" count={competitive.claims_needing_evidence.length}>
          <StringList items={competitive.claims_needing_evidence} empty="No unsupported claims." tone="orange" />
        </Panel>
        <Panel title="Differentiation opportunities" count={competitive.differentiation_opportunities.length}>
          <StringList items={competitive.differentiation_opportunities} empty="None identified." tone="green" />
        </Panel>
        <Panel title="Questions to uncover positioning" count={competitive.questions_to_uncover_positioning.length}>
          <StringList items={competitive.questions_to_uncover_positioning} empty="None suggested." tone="cyan" />
        </Panel>
      </div>
    </div>
  )
}

function NextActionsTab({ analysis }: { analysis: MeetingAnalysisResult }) {
  const next = analysis.next_actions
  if (!next) return <Unavailable name="Next actions" warnings={analysis.warnings} />
  return (
    <div className="space-y-6">
      <Panel title="Recommended next actions" count={next.actions.length} icon={<Target className="h-3.5 w-3.5 text-emerald-300" />}>
        {next.actions.length ? (
          <div className="space-y-3">
            {next.actions.map((action, index) => (
              <ItemCard key={`${index}-${action.action.slice(0, 24)}`}>
                <div className="flex items-start gap-3">
                  <span className="mt-0.5 inline-flex h-6 w-6 flex-none items-center justify-center rounded-full border border-nagarro-green/40 bg-nagarro-green/10 text-xs font-bold text-nagarro-green">
                    {index + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold leading-6 text-white">{action.action}</p>
                    <p className="mt-1 text-xs leading-5 text-cosmic-muted">{action.rationale}</p>
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <SeverityPill value={action.impact} prefix="Impact ·" />
                      <SeverityPill value={action.urgency} prefix="Urgency ·" />
                      <Pill tone="neutral">Owner · {action.suggested_owner ?? 'Unassigned'}</Pill>
                      <StatusPill value={action.origin} />
                    </div>
                  </div>
                </div>
                <FindingMeta finding={action} />
              </ItemCard>
            ))}
          </div>
        ) : (
          <Empty>No next actions were recommended.</Empty>
        )}
      </Panel>
      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Questions for the next meeting" count={next.next_meeting_questions.length}>
          <StringList items={next.next_meeting_questions} empty="None suggested." tone="cyan" />
        </Panel>
        <Panel title="Suggested agenda" count={next.suggested_agenda.length}>
          <StringList items={next.suggested_agenda} empty="No agenda suggested." ordered />
        </Panel>
      </div>
    </div>
  )
}

// ───────────────────────── Record (meeting inputs) ─────────────────────────
export function MeetingRecordView({ meeting, analysis }: { meeting: MeetingRecord; analysis: MeetingAnalysisResult | null }) {
  const attendees = (meeting.attendees ?? '').split(',').map((person) => person.trim()).filter(Boolean)
  const stats = analysis?.transcript_stats ?? null
  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Objectives" icon={<Briefcase className="h-3.5 w-3.5 text-violet-300" />}>
          <p className="text-sm leading-7 text-cosmic-text">{meeting.objectives || 'No meeting objectives captured.'}</p>
        </Panel>
        <Panel title="Notes" icon={<Sparkles className="h-3.5 w-3.5 text-amber-300" />}>
          <p className="text-sm leading-7 text-cosmic-text">{meeting.notes || 'No supporting notes captured for this meeting.'}</p>
        </Panel>
        <Panel title="Attendees" count={attendees.length} icon={<Users className="h-3.5 w-3.5 text-cyan-300" />}>
          <Chips items={attendees} empty="No attendees recorded" />
        </Panel>
        <Panel title="Meeting details" icon={<CheckCircle2 className="h-3.5 w-3.5 text-emerald-300" />}>
          <ul className="space-y-1.5 text-sm text-cosmic-text">
            <li>Created · {formatDateTime(meeting.created_at)}</li>
            <li>Updated · {formatDateTime(meeting.updated_at)}</li>
            {stats && (
              <>
                <li>Transcript · {stats.word_count.toLocaleString()} words</li>
                <li>Timestamps · {stats.has_timestamps ? 'Present' : 'Not present'}</li>
                <li>Speakers detected · {stats.speakers.length ? stats.speakers.join(', ') : 'None'}</li>
              </>
            )}
          </ul>
        </Panel>
      </div>
      {meeting.summary && (
        <Panel title="User summary" icon={<FileText className="h-3.5 w-3.5 text-cyan-300" />}>
          <p className="text-sm leading-7 text-cosmic-text">{meeting.summary}</p>
        </Panel>
      )}
      <Panel title="Transcript" icon={<MessageSquareText className="h-3.5 w-3.5 text-cyan-300" />}>
        <div className="max-h-[420px] overflow-auto rounded-xl border border-cosmic-border bg-slate-950/50 p-4">
          <p className="whitespace-pre-wrap text-sm leading-7 text-cosmic-muted">{meeting.transcript_text}</p>
        </div>
      </Panel>
    </div>
  )
}

// ───────────────────────── Panel ─────────────────────────
export function MeetingAnalysisPanel({
  meeting,
  analysis,
  state,
  error,
  onRun,
}: {
  meeting: MeetingRecord
  analysis: MeetingAnalysisResult | null
  state: LoadState
  error: string | null
  onRun: () => void
}) {
  const [tab, setTab] = useState<MeetingTab>('summary')

  const tabs = useMemo(
    () =>
      [
        { id: 'summary', label: 'Summary' },
        { id: 'scorecard', label: 'Scorecard & sentiment' },
        { id: 'mistakes', label: 'Coaching', count: analysis?.mistakes?.findings.length },
        { id: 'discovery', label: 'Discovery' },
        { id: 'objections', label: 'Objections', count: analysis?.objections?.unresolved_count },
        { id: 'presentation', label: 'Presentation' },
        { id: 'stakeholders', label: 'Stakeholders', count: analysis?.stakeholders?.stakeholders.length },
        { id: 'competitive', label: 'Competitive' },
        { id: 'next', label: 'Next actions', count: analysis?.next_actions?.actions.length },
        { id: 'record', label: 'Transcript & notes' },
      ] as const,
    [analysis],
  )

  const header: ReactNode = (
    <div className="cosmic-card p-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Pill tone="cyan">{meeting.meeting_type ?? 'Meeting'}</Pill>
            <span className="text-xs text-cosmic-muted">{formatDate(meeting.meeting_date)}</span>
            {analysis && <StatusPill value={analysis.status} />}
          </div>
          <h2 className="mt-3 text-2xl font-bold tracking-tight text-white">{meeting.title}</h2>
          <p className="mt-1 text-sm text-cosmic-muted">{meeting.attendees || 'No attendees listed'}</p>
        </div>
        <button type="button" className="btn-nagarro inline-flex items-center gap-2 self-start" onClick={onRun} disabled={state === 'loading'}>
          {state === 'loading' ? <Loader2 className="h-4 w-4 animate-spin" /> : analysis ? <RefreshCw className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
          {state === 'loading' ? 'Analysing…' : analysis ? 'Re-run analysis' : 'Run analysis'}
        </button>
      </div>

      {analysis && (
        <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-cosmic-border/60 pt-4 text-xs text-cosmic-muted">
          <span>Generated · {formatDateTime(analysis.generated_at)}</span>
          <span>Model · {analysis.model_name ?? 'Unknown'}</span>
          <span>Schema · v{analysis.schema_version}</span>
          <span>Unverified quotes · {analysis.unverified_quote_count}</span>
          {analysis.unverified_quote_count > 0 && <Pill tone="amber">Review evidence</Pill>}
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
            Analysing the transcript. This can take up to a minute.
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
        {state === 'error' && <Notice tone="red">{error ?? 'Unable to load the meeting analysis.'}</Notice>}
        {state === 'missing' && (
          <div className="cosmic-card p-10 text-center">
            <Sparkles className="mx-auto mb-4 h-10 w-10 text-nagarro-green opacity-80" />
            <h3 className="text-lg font-semibold text-white">This meeting has not been analysed yet</h3>
            <p className="mx-auto mt-2 max-w-md text-sm text-cosmic-muted">
              Run the analysis to get the summary, scorecard, objections, coaching notes and recommended next actions for this meeting.
            </p>
          </div>
        )}
        <MeetingRecordView meeting={meeting} analysis={null} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {header}

      {analysis.status !== 'COMPLETED' && (
        <Notice tone={analysis.status === 'FAILED' ? 'red' : 'amber'}>
          <div className="font-semibold">{analysis.status === 'FAILED' ? 'The analysis failed' : 'Some sections are incomplete'}</div>
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

      {tab === 'summary' && <SummaryTab analysis={analysis} />}
      {tab === 'scorecard' && <ScorecardTab analysis={analysis} />}
      {tab === 'mistakes' && <MistakesTab analysis={analysis} />}
      {tab === 'discovery' && <DiscoveryTab analysis={analysis} />}
      {tab === 'objections' && <ObjectionsTab analysis={analysis} />}
      {tab === 'presentation' && <PresentationTab analysis={analysis} />}
      {tab === 'stakeholders' && <StakeholdersTab analysis={analysis} />}
      {tab === 'competitive' && <CompetitiveTab analysis={analysis} />}
      {tab === 'next' && <NextActionsTab analysis={analysis} />}
      {tab === 'record' && <MeetingRecordView meeting={meeting} analysis={analysis} />}
    </div>
  )
}