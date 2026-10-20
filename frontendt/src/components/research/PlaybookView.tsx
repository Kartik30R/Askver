import { useState } from 'react'
import { AlertTriangle, ArrowRight, Check, Copy, Printer, ShieldAlert, Target } from 'lucide-react'
import type { DiscoveryQuestion, MatchedAsset, MeetingPlaybook } from '../../features/workflow/researchTypes'
import Cite from './Cite'
import { BulletList, Card, Empty, IntensityPill, Pill, humanize } from './ui'
import type { Tone } from './ui'

const STAGE_TONE: Record<DiscoveryQuestion['stage'], Tone> = {
  SITUATION: 'neutral',
  PROBLEM: 'amber',
  IMPACT: 'orange',
  VISION: 'cyan',
  DECISION: 'violet',
}
const STAGES: DiscoveryQuestion['stage'][] = ['SITUATION', 'PROBLEM', 'IMPACT', 'VISION', 'DECISION']

const SECTIONS = [
  ['snapshot', 'Snapshot'],
  ['agenda', 'Agenda'],
  ['talking', 'Talking points'],
  ['questions', 'Questions'],
  ['objections', 'Objections'],
  ['attendees', 'Attendees'],
  ['landmines', 'Landmines'],
  ['proof', 'Proof'],
  ['pitch', 'Pitch & ask'],
  ['risks', 'Risks & gaps'],
] as const

function CopyButton({ text, label = 'Copy' }: { text: string; label?: string }) {
  const [done, setDone] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setDone(true)
      window.setTimeout(() => setDone(false), 1500)
    } catch {
      /* clipboard blocked: ignore */
    }
  }
  return (
    <button type="button" onClick={copy} className="flex items-center gap-1 rounded-lg border border-white/10 px-2 py-1 text-xs text-slate-300 hover:bg-white/5">
      {done ? <Check size={12} /> : <Copy size={12} />}
      {done ? 'Copied' : label}
    </button>
  )
}

const Unverified = ({ figures }: { figures: string[] }) =>
  figures.length ? (
    <span className="ml-1 inline-flex items-center gap-1 text-[11px] text-amber-300" title={`Not found in cited evidence: ${figures.join(', ')}`}>
      <AlertTriangle size={12} /> verify {figures.join(', ')}
    </span>
  ) : null

export default function PlaybookView({ playbook, assets }: { playbook: MeetingPlaybook; assets: MatchedAsset[] }) {
  const [pitchTab, setPitchTab] = useState<'60' | '180'>('60')
  const assetName = (id: string) => {
    const a = assets.find((x) => x.asset_id === id)
    return a?.asset_name ?? a?.title ?? id
  }
  const pb = playbook
  const talking = [...pb.talking_points].sort((a, b) => a.sequence - b.sequence)
  const questionNo = new Map(pb.discovery_questions.map((q, i) => [q, i + 1] as const))
  const totalMinutes = pb.agenda.reduce((n, a) => n + a.minutes, 0)

  return (
    <div className="space-y-5">
      <nav className="print-hide sticky top-0 z-20 -mx-1 flex flex-wrap items-center gap-1 rounded-xl border border-white/10 bg-slate-950/90 p-1.5 backdrop-blur">
        {SECTIONS.map(([id, label]) => (
          <a key={id} href={`#pb-${id}`} className="rounded-lg px-2.5 py-1 text-xs text-slate-300 hover:bg-white/10 hover:text-white">
            {label}
          </a>
        ))}
        <button type="button" onClick={() => window.print()} className="ml-auto flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs text-slate-300 hover:bg-white/10">
          <Printer size={13} /> Print
        </button>
      </nav>

      <div id="pb-snapshot" className="scroll-mt-16">
        <Card title="One-slide snapshot" icon={<Target size={15} />}>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-400">Situation</p>
              <p className="mt-1 text-sm text-slate-100">
                {pb.snapshot.situation}
                <Cite ids={pb.snapshot.fact_ids} />
              </p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-400">Why now</p>
              <p className="mt-1 text-sm text-slate-100">{pb.snapshot.why_now}</p>
            </div>
            <div className="rounded-xl border border-cyan-400/20 bg-cyan-500/5 p-3">
              <p className="text-xs uppercase tracking-wide text-cyan-300">Opening hook (first 30 seconds)</p>
              <p className="mt-1 text-sm text-slate-100">{pb.snapshot.opening_hook}</p>
            </div>
            <div className="rounded-xl border border-violet-400/20 bg-violet-500/5 p-3">
              <p className="text-xs uppercase tracking-wide text-violet-300">Goal of the meeting</p>
              <p className="mt-1 text-sm text-slate-100">{pb.snapshot.meeting_goal}</p>
            </div>
          </div>
        </Card>
      </div>

      <div id="pb-agenda" className="scroll-mt-16">
        <Card title="Agenda" right={<Pill tone="neutral">{totalMinutes} min</Pill>}>
          {pb.agenda.length ? (
            <ol className="space-y-2">
              {pb.agenda.map((a, i) => (
                <li key={`${i}-${a.topic}`} className="flex gap-3 text-sm">
                  <span className="w-14 flex-none rounded-md bg-white/5 py-0.5 text-center text-xs text-slate-300">{a.minutes} min</span>
                  <span>
                    <span className="font-medium text-slate-100">{a.topic}</span>
                    <span className="text-slate-400"> — {a.purpose}</span>
                  </span>
                </li>
              ))}
            </ol>
          ) : (
            <Empty text="No agenda generated." />
          )}
        </Card>
      </div>

      <div id="pb-talking" className="scroll-mt-16">
        <Card title="Talking points (in delivery order)">
          <ol className="space-y-3">
            {talking.map((t) => (
              <li key={t.sequence} className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-cyan-500/20 text-xs font-bold text-cyan-200">{t.sequence}</span>
                  <span className="text-sm font-semibold text-slate-50">{t.headline}</span>
                  <Pill>{t.target_persona}</Pill>
                </div>
                <p className="mt-2 text-sm text-slate-200">
                  {t.point}
                  <Cite ids={t.fact_ids} />
                  <Unverified figures={t.unverified_figures} />
                </p>
                {t.proof_asset_ids.length > 0 && (
                  <p className="mt-1 text-xs text-emerald-300">Proof: {t.proof_asset_ids.map(assetName).join(' · ')}</p>
                )}
                {t.bridge_to_question != null && (
                  <p className="mt-2 flex items-center gap-1 text-xs text-violet-300">
                    <ArrowRight size={12} /> Leads into question {t.bridge_to_question + 1}
                  </p>
                )}
              </li>
            ))}
          </ol>
        </Card>
      </div>

      <div id="pb-questions" className="scroll-mt-16">
        <Card title="Discovery questions" right={<Pill>{pb.discovery_questions.length} questions</Pill>}>
          <div className="space-y-5">
            {STAGES.map((stage) => {
              const qs = pb.discovery_questions.filter((q) => q.stage === stage)
              if (!qs.length) return null
              return (
                <div key={stage}>
                  <div className="mb-2 flex items-center gap-2">
                    <Pill tone={STAGE_TONE[stage]}>{humanize(stage)}</Pill>
                  </div>
                  <ul className="space-y-3">
                    {qs.map((q) => (
                      <li key={q.question} className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
                        <p className="text-sm font-medium text-slate-50">
                          <span className="mr-2 text-slate-500">Q{questionNo.get(q)}</span>
                          {q.question}
                          <Cite ids={q.fact_ids} />
                          <Unverified figures={q.unverified_figures} />
                        </p>
                        <p className="mt-1 text-xs text-slate-400">Why we ask: {q.why_we_ask}</p>
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {q.listen_for.map((l) => (
                            <Pill key={l} tone="cyan">
                              listen: {l}
                            </Pill>
                          ))}
                        </div>
                        <p className="mt-2 text-xs text-slate-300">Follow-up: {q.follow_up}</p>
                        <p className="mt-1 text-[11px] text-slate-500">Best for: {q.target_persona}</p>
                      </li>
                    ))}
                  </ul>
                </div>
              )
            })}
            {!pb.discovery_questions.length && <Empty text="No discovery questions generated." />}
          </div>
        </Card>
      </div>

      <div id="pb-objections" className="scroll-mt-16">
        <Card title="Objections & responses">
          <ul className="space-y-3">
            {pb.objections.map((o) => (
              <li key={o.objection} className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-semibold text-slate-50">“{o.objection}”</span>
                  <IntensityPill level={o.likelihood} prefix="Likelihood" />
                  <Pill>{o.raised_by}</Pill>
                </div>
                <p className="mt-2 text-xs text-slate-400">Real concern: {o.underlying_concern}</p>
                <p className="mt-2 text-sm text-slate-100">
                  {o.response}
                  <Cite ids={o.fact_ids} />
                  <Unverified figures={o.unverified_figures} />
                </p>
                {o.proof_asset_ids.length > 0 && <p className="mt-1 text-xs text-emerald-300">Proof: {o.proof_asset_ids.map(assetName).join(' · ')}</p>}
                {o.do_not_say && (
                  <p className="mt-2 flex items-start gap-1 text-xs text-rose-300">
                    <ShieldAlert size={13} className="mt-0.5 flex-none" /> Don’t say: {o.do_not_say}
                  </p>
                )}
              </li>
            ))}
            {!pb.objections.length && <Empty text="No objections generated." />}
          </ul>
        </Card>
      </div>

      <div id="pb-attendees" className="scroll-mt-16">
        <Card title="Who will be in the room">
          <div className="grid gap-3 md:grid-cols-2">
            {pb.attendees.map((a) => (
              <div key={`${a.role}-${a.name ?? ''}`} className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-semibold text-slate-50">{a.name ?? a.role}</span>
                  {a.name && <span className="text-xs text-slate-400">{a.role}</span>}
                  <Pill tone={a.evidence_level === 'NAMED_WITH_SOURCES' ? 'green' : 'neutral'}>
                    {a.evidence_level === 'NAMED_WITH_SOURCES' ? 'Sourced' : 'Role archetype'}
                  </Pill>
                  <Pill tone="violet">{humanize(a.buying_role)}</Pill>
                </div>
                <BulletList items={a.what_they_care_about} tone="mt-2 text-slate-300" />
                <p className="mt-2 text-sm text-slate-200">
                  {a.approach}
                  <Cite ids={a.fact_ids} />
                </p>
                {a.best_questions_for_them.length > 0 && (
                  <p className="mt-1 text-xs text-slate-400">Ask them: {a.best_questions_for_them.map((i) => `Q${i + 1}`).join(', ')}</p>
                )}
              </div>
            ))}
          </div>
          {!pb.attendees.length && <Empty text="No attendee guidance generated." />}
        </Card>
      </div>

      <div id="pb-landmines" className="scroll-mt-16">
        <Card title="Landmines to avoid" icon={<AlertTriangle size={15} />}>
          <ul className="space-y-3">
            {pb.landmines.map((l) => (
              <li key={l.topic} className="rounded-xl border border-rose-400/20 bg-rose-500/5 p-3 text-sm">
                <p className="font-semibold text-slate-50">{l.topic}</p>
                <p className="mt-1 text-slate-300">
                  {l.why}
                  <Cite ids={l.fact_ids} />
                </p>
                <p className="mt-1 text-emerald-300">Say instead: {l.safer_framing}</p>
              </li>
            ))}
            {!pb.landmines.length && <Empty text="No landmines identified." />}
          </ul>
        </Card>
      </div>

      <div id="pb-proof" className="scroll-mt-16">
        <Card title="Proof points from your knowledge base">
          <ul className="space-y-2">
            {pb.proof_points.map((p) => (
              <li key={`${p.asset_id}-${p.pain_point}`} className="rounded-xl border border-white/10 bg-white/[0.02] p-3 text-sm">
                <p className="text-xs text-slate-400">For pain point: {p.pain_point}</p>
                <p className="font-medium text-slate-50">{assetName(p.asset_id)}</p>
                <p className="text-slate-300">{p.how_to_use}</p>
              </li>
            ))}
            {!pb.proof_points.length && <Empty text="No internal proof assets matched. Upload case studies to the Knowledge Base for stronger proof points." />}
          </ul>
        </Card>
      </div>

      <div id="pb-pitch" className="scroll-mt-16">
        <Card
          title="Pitch & the ask"
          right={
            <div className="flex gap-1">
              {(['60', '180'] as const).map((k) => (
                <button
                  key={k}
                  type="button"
                  onClick={() => setPitchTab(k)}
                  className={`rounded-lg px-2.5 py-1 text-xs ${pitchTab === k ? 'bg-cyan-500/20 text-cyan-200' : 'text-slate-400 hover:bg-white/5'}`}
                >
                  {k === '60' ? '60 seconds' : '3 minutes'}
                </button>
              ))}
            </div>
          }
        >
          <p className="whitespace-pre-line text-sm text-slate-100">
            {pitchTab === '60' ? pb.pitch_and_ask.pitch_60_seconds : pb.pitch_and_ask.pitch_3_minutes}
            <Cite ids={pb.pitch_and_ask.fact_ids} />
          </p>
          <div className="mt-4 rounded-xl border border-violet-400/20 bg-violet-500/5 p-3">
            <p className="text-xs uppercase tracking-wide text-violet-300">The ask</p>
            <p className="mt-1 text-sm text-slate-100">{pb.pitch_and_ask.the_ask}</p>
          </div>
          <p className="mt-4 text-xs uppercase tracking-wide text-slate-400">Next steps</p>
          <BulletList items={pb.pitch_and_ask.next_steps} />
          <div className="mt-4 rounded-xl border border-white/10 bg-white/[0.02] p-3">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-xs uppercase tracking-wide text-slate-400">Follow-up email draft</p>
              <CopyButton
                text={`Subject: ${pb.pitch_and_ask.follow_up_email_subject}\n\n${pb.pitch_and_ask.follow_up_email_body}`}
                label="Copy email"
              />
            </div>
            <p className="text-sm font-medium text-slate-100">{pb.pitch_and_ask.follow_up_email_subject}</p>
            <p className="mt-2 whitespace-pre-line text-sm text-slate-300">{pb.pitch_and_ask.follow_up_email_body}</p>
          </div>
        </Card>
      </div>

      <div id="pb-risks" className="grid scroll-mt-16 gap-5 md:grid-cols-2">
        <Card title="What could kill this deal">
          <BulletList items={pb.deal_risks} />
          {!pb.deal_risks.length && <Empty text="No risks listed." />}
        </Card>
        <Card title="Verify in the room (known gaps)">
          <BulletList items={pb.known_gaps} tone="text-amber-200" />
          {!pb.known_gaps.length && <Empty text="No gaps recorded." />}
        </Card>
      </div>
    </div>
  )
}
