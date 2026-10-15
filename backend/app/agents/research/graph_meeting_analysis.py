"""
app/agents/meeting_analysis/graph.py

Per-meeting analysis graph.

    START
      └─ preprocess
           ├─ summary ─────────┐
           ├─ sentiment ───────┤
           ├─ mistakes ────────┤
           ├─ discovery ───────┤   (parallel fan-out, all read the same transcript)
           ├─ objections ──────┤
           ├─ stakeholders ────┤
           ├─ competitive ─────┤
           └─ presentation ────┘
                     └─ scorecard   (needs the analyzer outputs)
                          └─ next_actions
                               └─ verify_evidence   (deterministic: checks quotes exist in source)
                                    └─ assemble ─ END

A single analyzer failing never kills the run: the section is left empty, a warning
is recorded, and the result status becomes PARTIAL.
"""
import logging
import re
from typing import Any, Callable, Type

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from app.agents.research.analysis_llm import GROUNDING_RULES, structured_call
from app.agents.research.state_meeting_analysis import MeetingAnalysisState
from app.core.config import settings
from app.schemas.analysis_common import Evidence, EvidenceSource
from app.schemas.meeting_analysis import (
    AnalysisStatus,
    CompetitiveAnalysis,
    DiscoveryAnalysis,
    MeetingAnalysisResult,
    MeetingScorecard,
    MeetingSummary,
    MistakesAnalysis,
    NextActionsAnalysis,
    ObjectionAnalysis,
    PresentationAnalysis,
    SentimentAnalysis,
    StakeholderAnalysis,
)

logger = logging.getLogger(__name__)

MAX_CHARS = 400_000  # safety cap on transcript size sent to the model


# ─────────────────────────── Context builders ───────────────────────────
def _meeting_header(state: MeetingAnalysisState) -> str:
    return (
        f"MEETING TITLE: {state.get('title')}\n"
        f"MEETING TYPE: {state.get('meeting_type') or 'Not specified'}\n"
        f"DATE: {state.get('meeting_date')}\n"
        f"ATTENDEES (as entered by user): {state.get('attendees') or 'Not provided'}\n"
        f"STATED OBJECTIVES: {state.get('objectives') or 'Not provided'}\n"
        f"USER NOTES: {state.get('notes') or 'None'}\n"
    )


def _base_context(state: MeetingAnalysisState) -> str:
    parts = [_meeting_header(state)]
    if state.get("deal_context"):
        parts.append(f"DEAL RESEARCH CONTEXT (prior company research):\n{state['deal_context']}")
    if state.get("previous_meetings_digest"):
        parts.append(f"EARLIER MEETINGS ON THIS DEAL:\n{state['previous_meetings_digest']}")
    parts.append(f"TRANSCRIPT:\n{state['transcript_text'][:MAX_CHARS]}")
    return "\n\n".join(parts)


def _with_docs(state: MeetingAnalysisState) -> str:
    ctx = _base_context(state)
    if state.get("supporting_docs_text"):
        ctx += f"\n\nSUPPORTING DOCUMENTS:\n{state['supporting_docs_text'][:60_000]}"
    return ctx


def _presentation_context(state: MeetingAnalysisState) -> str:
    return _with_docs(state) + f"\n\nPRESENTATION DECK (text by slide):\n{state.get('deck_text') or ''}"


def _scorecard_context(state: MeetingAnalysisState) -> str:
    """Scorecard is built from the other analyses, not from scratch."""
    sections = {}
    for key in ("summary", "sentiment", "mistakes", "discovery", "objections", "competitive"):
        val = state.get(key)
        if val is not None:
            sections[key] = val.model_dump(mode="json", exclude={"evidence"})
    return f"{_meeting_header(state)}\nANALYSIS SECTIONS ALREADY PRODUCED:\n{sections}"


def _next_actions_context(state: MeetingAnalysisState) -> str:
    sections = {}
    for key in ("summary", "sentiment", "mistakes", "discovery", "objections", "stakeholders", "competitive", "scorecard"):
        val = state.get(key)
        if val is not None:
            sections[key] = val.model_dump(mode="json", exclude={"evidence"})
    return f"{_meeting_header(state)}\nANALYSIS SECTIONS ALREADY PRODUCED:\n{sections}"


# ─────────────────────────── Prompts ───────────────────────────
ROLE = "You are a senior enterprise sales coach and deal analyst. You analyse one meeting transcript at a time.\n"

PROMPTS: dict[str, str] = {
    "summary": ROLE + """
Produce the meeting summary and outcomes.
- Separate what was AGREED (origin=AGREED) from anything you would merely recommend.
- our_commitments = deliverables our team promised. buyer_requests = things the buyer asked us for.
- Compare the stated objectives against what actually happened.""",
    "sentiment": ROLE + """
Assess buyer sentiment and buying signals.
- Distinguish explicit commitments (e.g. 'send the contract', 'introduce our CFO') from polite interest ('sounds interesting').
- Classify signal_stage using ONLY explicit evidence.
- List both positive and negative signals. For internal-only meetings, assess internal alignment instead of buyer intent.""",
    "mistakes": ROLE + """
Find sales mistakes and missed opportunities by OUR team.
- Only flag mistakes you can support with a verbatim transcript quote. If there are none, return an empty list.
- For each: what happened, why it matters, what to do instead, and a concrete better sentence/question.
- Check: questions not asked, poor/unanswered answers, weak objection handling, pitching over discovery,
  unsupported claims, missed ROI quantification, decision-maker not identified, weak differentiation,
  premature pricing/discounting, no clear next step, commitments made without qualification.
- Also list genuine strengths.""",
    "discovery": ROLE + """
Analyse how well our team understood the customer's needs.
- Separate stated needs from inferred needs.
- Fill 'coverage' for every DiscoveryDimension (covered true/false) and compute coverage_pct from it.
- List discovery questions that remain unanswered and gaps between needs and our solution.""",
    "objections": ROLE + """
Track every significant buyer objection or concern.
- For each: category, who raised it, severity, our response, status (RESOLVED / PARTIALLY_RESOLVED / UNRESOLVED)
  with the evidence for that status, and a recommended response.
- Be strict: an objection is RESOLVED only if the buyer acknowledged the answer.
- Set unresolved_count correctly.""",
    "stakeholders": ROLE + """
Build a profile for every identifiable participant.
- role_source=CONFIRMED only if the title/role was stated; otherwise INFERRED.
- Do not claim decision authority or influence without evidence.
- missing_roles = buying-committee roles not yet seen in this meeting.""",
    "competitive": ROLE + """
Extract competitive intelligence.
- Only list competitors the buyer or team actually mentioned. Never invent competitors or capabilities.
- Separate buyer evaluation criteria, our apparent strengths and weaknesses, and claims that need proof.""",
    "presentation": ROLE + """
Evaluate the presentation deck that was used in this meeting against the transcript and buyer priorities.
- Reference slide numbers (from the '--- Slide N ---' markers) and link them to transcript moments.
- Flag irrelevant slides, unsupported claims, missing proof points, omitted topics and ROI opportunities.
- If no deck text is provided, set deck_provided=false and leave everything else empty.""",
    "scorecard": ROLE + """
Score the meeting 0-10 on every ScorecardMetricName using the analyses already produced.
- Scores must be justified by those findings; give a short explanation for each.
- Use LOW confidence when the underlying section was empty or weak.""",
    "next_actions": ROLE + """
Recommend next actions for the sales team (origin=AI_RECOMMENDED).
- Rank by impact then urgency. Tie each to a specific finding (unresolved objection, discovery gap, mistake, commitment).
- Also give questions to ask in the next meeting and a suggested agenda.""",
}


# ─────────────────────────── Node factory ───────────────────────────
def _make_node(
    key: str,
    schema: Type[BaseModel],
    context_builder: Callable[[MeetingAnalysisState], str],
):
    async def node(state: MeetingAnalysisState) -> dict[str, Any]:
        try:
            result = await structured_call(
                schema,
                system=PROMPTS[key] + "\n\n" + GROUNDING_RULES,
                user=context_builder(state),
            )
            return {key: result}
        except Exception as exc:  # noqa: BLE001
            logger.exception("Meeting analysis node '%s' failed", key)
            return {key: None, "warnings": [f"Section '{key}' failed: {exc}"]}

    node.__name__ = f"{key}_node"
    return node


# ─────────────────────────── Non-LLM nodes ───────────────────────────
_SPEAKER_RE = re.compile(r"^\s*(?:\[?\d{1,2}:\d{2}(?::\d{2})?\]?\s*)?([A-Z][\w .'\-]{1,40}?)\s*(?:\(\d{1,2}:\d{2}(?::\d{2})?\))?\s*:", re.M)
_TS_RE = re.compile(r"\d{1,2}:\d{2}(?::\d{2})?")


async def preprocess_node(state: MeetingAnalysisState) -> dict[str, Any]:
    text = state["transcript_text"]
    speakers = sorted({m.group(1).strip() for m in _SPEAKER_RE.finditer(text)})
    stats = {
        "word_count": len(text.split()),
        "speakers": speakers[:30],
        "has_timestamps": bool(_TS_RE.search(text)),
    }
    warnings = []
    if stats["word_count"] < 150:
        warnings.append("Transcript is very short; analysis confidence will be limited.")
    if len(text) > MAX_CHARS:
        warnings.append("Transcript exceeded the size cap and was truncated for analysis.")
    return {"transcript_stats": stats, "warnings": warnings}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _iter_evidence(obj: Any):
    """Yield every Evidence object nested anywhere inside a pydantic model / list."""
    if isinstance(obj, Evidence):
        yield obj
    elif isinstance(obj, BaseModel):
        for name in obj.model_fields:
            yield from _iter_evidence(getattr(obj, name))
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            yield from _iter_evidence(item)


async def verify_evidence_node(state: MeetingAnalysisState) -> dict[str, Any]:
    """Deterministic anti-hallucination pass: a quote is 'verified' only if it appears in its source."""
    corpus = {
        EvidenceSource.TRANSCRIPT: _norm(state["transcript_text"]),
        EvidenceSource.PRESENTATION: _norm(state.get("deck_text") or ""),
        EvidenceSource.NOTES: _norm((state.get("notes") or "") + " " + (state.get("supporting_docs_text") or "")),
        EvidenceSource.RESEARCH: _norm(str(state.get("deal_context") or "")),
        EvidenceSource.PRIOR_MEETING: _norm(state.get("previous_meetings_digest") or ""),
    }
    unverified = 0
    for key in ("summary", "sentiment", "mistakes", "discovery", "objections", "presentation",
                "stakeholders", "competitive", "scorecard", "next_actions"):
        section = state.get(key)
        for ev in _iter_evidence(section):
            q = _norm(ev.quote)
            ev.verified = bool(q) and q in corpus.get(ev.source, "")
            if not ev.verified:
                unverified += 1

    updates: dict[str, Any] = {"unverified_quote_count": unverified}
    warnings: list[str] = []

    # Mistakes must be evidence-supported: drop any with no verified quote.
    mistakes: MistakesAnalysis | None = state.get("mistakes")
    if mistakes:
        kept = [f for f in mistakes.findings if any(e.verified for e in f.evidence)]
        dropped = len(mistakes.findings) - len(kept)
        if dropped:
            warnings.append(f"Dropped {dropped} sales-mistake finding(s) without a verifiable transcript quote.")
            mistakes.findings = kept
            updates["mistakes"] = mistakes
    if unverified:
        warnings.append(f"{unverified} evidence quote(s) could not be matched to the source text.")
    updates["warnings"] = warnings
    return updates


async def assemble_node(state: MeetingAnalysisState) -> dict[str, Any]:
    section_keys = ("summary", "sentiment", "mistakes", "discovery", "objections", "presentation",
                    "stakeholders", "competitive", "scorecard", "next_actions")
    missing = [k for k in section_keys if state.get(k) is None]
    # Presentation being absent is normal only if a deck exists but failed; analyzer always returns an object.
    if len(missing) == len(section_keys):
        status = AnalysisStatus.FAILED
    elif missing:
        status = AnalysisStatus.PARTIAL
    else:
        status = AnalysisStatus.COMPLETED

    result = MeetingAnalysisResult(
        meeting_id=state["meeting_id"],
        deal_id=state["deal_id"],
        status=status,
        model_name=settings.LLM_MODEL,
        warnings=state.get("warnings", []),
        unverified_quote_count=state.get("unverified_quote_count", 0),
        **{k: state.get(k) for k in section_keys},
    )
    return {"result": result}


# ─────────────────────────── Graph ───────────────────────────
PARALLEL_ANALYZERS = (
    ("summary", MeetingSummary, _base_context),
    ("sentiment", SentimentAnalysis, _base_context),
    ("mistakes", MistakesAnalysis, _base_context),
    ("discovery", DiscoveryAnalysis, _with_docs),
    ("objections", ObjectionAnalysis, _base_context),
    ("stakeholders", StakeholderAnalysis, _base_context),
    ("competitive", CompetitiveAnalysis, _with_docs),
    ("presentation", PresentationAnalysis, _presentation_context),
)


def build_meeting_analysis_graph(checkpointer=None):
    g = StateGraph(MeetingAnalysisState)

    g.add_node("preprocess", preprocess_node)
    for key, schema, ctx in PARALLEL_ANALYZERS:
        g.add_node(f"{key}_agent", _make_node(key, schema, ctx))
    g.add_node("scorecard_agent", _make_node("scorecard", MeetingScorecard, _scorecard_context))
    g.add_node("next_actions_agent", _make_node("next_actions", NextActionsAnalysis, _next_actions_context))
    g.add_node("verify_evidence", verify_evidence_node)
    g.add_node("assemble", assemble_node)

    g.add_edge(START, "preprocess")
    # NOTE: LangGraph forbids a node name equal to a state key, hence the "_agent" suffix.
    analyzer_names = [f"{k}_agent" for k, _, _ in PARALLEL_ANALYZERS]
    for name in analyzer_names:
        g.add_edge("preprocess", name)
    g.add_edge(analyzer_names, "scorecard_agent")  # fan-in: waits for ALL analyzers
    g.add_edge("scorecard_agent", "next_actions_agent")
    g.add_edge("next_actions_agent", "verify_evidence")
    g.add_edge("verify_evidence", "assemble")
    g.add_edge("assemble", END)

    return g.compile(checkpointer=checkpointer)


# ─────────────────────────── Service-facing entry point ───────────────────────────
async def run_meeting_analysis(
    *,
    meeting,                       # app.db.models.meeting.Meeting
    deck_text: str | None = None,
    supporting_docs_text: str | None = None,
    deal_context: dict | None = None,
    previous_meetings_digest: str | None = None,
    checkpointer=None,
) -> MeetingAnalysisResult:
    graph = build_meeting_analysis_graph(checkpointer)
    initial: MeetingAnalysisState = {
        "meeting_id": str(meeting.id),
        "deal_id": str(meeting.deal_id),
        "owner_id": str(meeting.owner_id),
        "title": meeting.title,
        "meeting_type": meeting.meeting_type,
        "meeting_date": meeting.meeting_date.isoformat(),
        "attendees": meeting.attendees,
        "objectives": meeting.objectives,
        "notes": meeting.notes,
        "transcript_text": meeting.transcript_text,
        "deck_text": deck_text,
        "supporting_docs_text": supporting_docs_text,
        "deal_context": deal_context,
        "previous_meetings_digest": previous_meetings_digest,
        "warnings": [],
    }
    config = {"configurable": {"thread_id": f"meeting-analysis-{meeting.id}"}}
    final = await graph.ainvoke(initial, config=config)
    return final["result"]
