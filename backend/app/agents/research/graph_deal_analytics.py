"""
app/agents/deal_analytics/graph.py

Deal-level analytics graph. Run it after EVERY completed meeting analysis (and when a
meeting is edited/deleted), so the deal view always reflects the full history.

    START
      ├─ health ──────────┐
      ├─ momentum ────────┤
      ├─ risks ───────────┤
      ├─ committee ───────┤   stage 1: parallel, each reads all meeting analyses
      ├─ competitive ─────┤
      ├─ execution ───────┤
      └─ trackers ────────┘
              └─ finalize_health    (code: composite score from dimension scores)
                   └─ win_probability   (uses stage-1 outputs + previous snapshot)
                        └─ strategy
                             └─ timeline    (what changed & why)
                                  └─ assemble ─ END
"""
import json
import logging
from typing import Any, Callable, Type

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from app.agents.research.analysis_llm import GROUNDING_RULES, structured_call
from app.agents.research.state_deal_analytics import DealAnalyticsState
from app.core.config import settings
from app.schemas.deal_analytics import (
    BuyingCommittee,
    DealAnalyticsResult,
    DealCompetitivePositioning,
    DealHealth,
    DealStrategy,
    DealTimeline,
    ExecutionEffectiveness,
    HealthDimensionName,
    MomentumAnalysis,
    RiskRegister,
    TrackersAnalysis,
    WinProbability,
)

logger = logging.getLogger(__name__)

# Weights for the composite deal health score (sum = 1.0). Keep versioned with DealHealth.methodology_version.
HEALTH_WEIGHTS: dict[HealthDimensionName, float] = {
    HealthDimensionName.BUYER_ENGAGEMENT: 0.12,
    HealthDimensionName.PROBLEM_CLARITY: 0.10,
    HealthDimensionName.SOLUTION_FIT: 0.12,
    HealthDimensionName.DECISION_MAKER_ACCESS: 0.14,
    HealthDimensionName.BUDGET_READINESS: 0.10,
    HealthDimensionName.COMPETITIVE_POSITION: 0.08,
    HealthDimensionName.OBJECTION_RESOLUTION: 0.10,
    HealthDimensionName.DECISION_PROCESS_CLARITY: 0.08,
    HealthDimensionName.MOMENTUM_TIMELINE: 0.10,
    HealthDimensionName.NEXT_STEP_EXECUTION: 0.06,
}


# ─────────────────────────── Context builders ───────────────────────────
def _slim(obj: Any) -> Any:
    """Shrink meeting analyses before sending them to the model: drop flags, truncate quotes."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in ("verified", "generated_at", "schema_version", "model_name", "warnings"):
                continue
            if k == "quote" and isinstance(v, str):
                out[k] = v[:160]
            else:
                out[k] = _slim(v)
        return out
    if isinstance(obj, list):
        return [_slim(i) for i in obj]
    return obj


def _deal_context(state: DealAnalyticsState, *, include_prev: bool = True) -> str:
    meetings = [
        {
            "meeting_id": m["meeting_id"],
            "title": m.get("title"),
            "type": m.get("meeting_type"),
            "date": m.get("meeting_date"),
            "analysis": _slim(m.get("analysis", {})),
        }
        for m in state.get("meetings", [])
    ]
    parts = [
        f"DEAL PROFILE:\n{json.dumps(state.get('deal_profile') or {}, default=str)}",
        f"RESEARCH BRIEF (pre-meeting company research):\n{json.dumps(state.get('research_brief') or {}, default=str)[:30_000]}",
        f"MEETINGS ANALYSED ({len(meetings)}, oldest first):\n{json.dumps(meetings, default=str)}",
    ]
    if include_prev and state.get("previous_snapshot"):
        parts.append(f"PREVIOUS DEAL SNAPSHOT:\n{json.dumps(_slim(state['previous_snapshot']), default=str)}")
    return "\n\n".join(parts)


def _risks_context(state: DealAnalyticsState) -> str:
    prev = (state.get("previous_snapshot") or {}).get("risks")
    return (
        _deal_context(state, include_prev=False)
        + f"\n\nPREVIOUS RISK REGISTER (reuse risk_key values for risks that persist; mark resolved ones RESOLVED):\n"
        + json.dumps(prev or {}, default=str)
    )


def _stage2_context(state: DealAnalyticsState) -> str:
    stage1 = {}
    for key in ("health", "momentum", "risks", "buying_committee", "competitive", "execution", "trackers",
                "win_probability", "strategy"):
        val = state.get(key)
        if val is not None:
            stage1[key] = _slim(val.model_dump(mode="json"))
    prev = state.get("previous_snapshot")
    return (
        _deal_context(state, include_prev=False)
        + f"\n\nDEAL ANALYTICS ALREADY COMPUTED THIS RUN:\n{json.dumps(stage1, default=str)}"
        + f"\n\nPREVIOUS SNAPSHOT (win probability / risks / health from before the latest meeting):\n"
        + json.dumps(_slim(prev) if prev else None, default=str)
    )


# ─────────────────────────── Prompts ───────────────────────────
ROLE = (
    "You are a principal enterprise deal strategist. You review ALL analysed meetings of one deal plus the "
    "pre-meeting research, and produce deal-level intelligence.\n"
    "Principles: (1) track issues as single evolving items across meetings, never count the same issue twice; "
    "(2) keep confirmed facts separate from hypotheses; (3) cite evidence with meeting_id set on each Evidence; "
    "(4) prefer the most recent meeting when information conflicts, and say so.\n"
)

PROMPTS: dict[str, str] = {
    "health": ROLE + """
Score every HealthDimensionName from 0-10 with rationale, missing information and source_meeting_ids.
Low scores must reflect real gaps (e.g. no economic buyer seen => DECISION_MAKER_ACCESS low).
If there is no information at all for a dimension, give 3 with LOW confidence and list what is missing.""",
    "momentum": ROLE + """
Determine whether the deal is getting stronger, weaker, or stuck, and why.
- Fill trend_points with one entry per meeting (oldest first), copying values from each meeting analysis.
- With only one meeting, use INSUFFICIENT_DATA for trends.""",
    "risks": ROLE + """
Build the consolidated risk register across these categories: commercial, stakeholder, competitive,
technical, strategic fit, execution, procurement, timing.
- One risk = one entry with occurrences, first_seen / last_seen meeting ids.
- Reuse risk_key from the previous register for persisting risks; mark risks RESOLVED when later evidence shows it.
- Set highest_priority_risk_key.""",
    "buying_committee": ROLE + """
Assess buying-committee coverage: who we have engaged, who is missing, champion strength,
economic buyer / technical evaluator / procurement / security-legal involvement, and conflicting priorities.
Never mark role_confirmed unless a meeting analysis shows role_source=CONFIRMED.""",
    "competitive": ROLE + """
Consolidate competitive positioning. confirmed=true only if the buyer actually named or evaluated the competitor;
otherwise it is a hypothesis (confirmed=false). Do not invent competitor capabilities.""",
    "execution": ROLE + """
Evaluate our team's execution ACROSS meetings: recurring patterns, repeated mistake categories, improvements,
and a commitments ledger. Mark a commitment FULFILLED only if a later meeting shows it was delivered;
OVERDUE only if a due date passed with no evidence. commitment_reliability_pct = fulfilled / total (null if none).""",
    "trackers": ROLE + """
Produce: (1) unanswered customer questions still open across meetings, (2) research-vs-conversation gaps
comparing the research brief to what meetings revealed, (3) warning signals / potential deal killers
(loss of champion, blockers, failed criteria, repeated disengagement, no decision date), each with its uncertainty.
Set signal_stage using explicit evidence only.""",
    "win_probability": ROLE + """
Estimate win probability (0-100) from the computed deal analytics. This is an AI estimate, not a calibrated forecast.
- Anchor on the previous snapshot if present and justify any change (set previous_pct and change_pct).
- Do not exceed 40% without an identified economic buyer or concrete buyer commitment. Do not exceed 70% with
  unresolved HIGH/CRITICAL risks. Early deals with few meetings should have LOW or MEDIUM confidence.
- List supporting and reducing factors with evidence, major uncertainties, and conditions that would move the number.""",
    "strategy": ROLE + """
Turn the analytics into an actionable plan: max 5 ranked top_actions (impact, urgency, linked risk keys),
the highest-priority risk, next stakeholder to engage, questions for the next meeting, documents to prepare,
objections to address, presentation changes, negotiation strategy, a suggested agenda, and the conditions that
must be met before forecasting the deal as likely to close.""",
    "timeline": ROLE + """
Build a chronological timeline of meaningful events (meetings, buying signals, risks opened/resolved,
stakeholder changes, win-probability changes, commitments fulfilled/missed, stage changes, customer decisions).
Then state what changed after the latest meeting versus the previous snapshot and why the assessment moved.""",
}


# ─────────────────────────── Node factory ───────────────────────────
def _make_node(key: str, state_key: str, schema: Type[BaseModel], ctx: Callable[[DealAnalyticsState], str]):
    async def node(state: DealAnalyticsState) -> dict[str, Any]:
        try:
            result = await structured_call(schema, system=PROMPTS[key] + "\n\n" + GROUNDING_RULES, user=ctx(state))
            return {state_key: result}
        except Exception as exc:  # noqa: BLE001
            logger.exception("Deal analytics node '%s' failed", key)
            return {state_key: None, "warnings": [f"Section '{key}' failed: {exc}"]}

    node.__name__ = f"{key}_node"
    return node


# ─────────────────────────── Non-LLM nodes ───────────────────────────
async def finalize_health_node(state: DealAnalyticsState) -> dict[str, Any]:
    """Composite score is computed deterministically so it is consistent across runs."""
    health: DealHealth | None = state.get("health")
    if not health or not health.dimensions:
        return {}
    total_w = score = 0.0
    for d in health.dimensions:
        w = HEALTH_WEIGHTS.get(d.dimension, 0.0)
        score += (d.score / 10.0) * w
        total_w += w
    health.composite_score = round(100 * score / total_w, 1) if total_w else None
    return {"health": health}


async def assemble_node(state: DealAnalyticsState) -> dict[str, Any]:
    meetings = state.get("meetings", [])
    result = DealAnalyticsResult(
        deal_id=state["deal_id"],
        snapshot_version=state.get("snapshot_version", 1),
        meetings_analyzed=len(meetings),
        latest_meeting_id=state.get("latest_meeting_id") or (meetings[-1]["meeting_id"] if meetings else None),
        model_name=settings.LLM_MODEL,
        win_probability=state.get("win_probability"),
        health=state.get("health"),
        momentum=state.get("momentum"),
        risks=state.get("risks"),
        buying_committee=state.get("buying_committee"),
        competitive=state.get("competitive"),
        execution=state.get("execution"),
        trackers=state.get("trackers"),
        strategy=state.get("strategy"),
        timeline=state.get("timeline"),
        warnings=state.get("warnings", []),
    )
    # Keep delta fields consistent even if the LLM drifted.
    prev = (state.get("previous_snapshot") or {}).get("win_probability") or {}
    wp = result.win_probability
    if wp and prev.get("probability_pct") is not None:
        wp.previous_pct = prev["probability_pct"]
        wp.change_pct = wp.probability_pct - prev["probability_pct"]
    return {"result": result}


# ─────────────────────────── Graph ───────────────────────────
STAGE1 = (
    ("health", "health", DealHealth, _deal_context),
    ("momentum", "momentum", MomentumAnalysis, _deal_context),
    ("risks", "risks", RiskRegister, _risks_context),
    ("buying_committee", "buying_committee", BuyingCommittee, _deal_context),
    ("competitive", "competitive", DealCompetitivePositioning, _deal_context),
    ("execution", "execution", ExecutionEffectiveness, _deal_context),
    ("trackers", "trackers", TrackersAnalysis, _deal_context),
)


def build_deal_analytics_graph(checkpointer=None):
    g = StateGraph(DealAnalyticsState)

    for key, state_key, schema, ctx in STAGE1:
        g.add_node(f"{key}_agent", _make_node(key, state_key, schema, ctx))  # node name != state key
        g.add_edge(START, f"{key}_agent")
    g.add_node("finalize_health", finalize_health_node)
    g.add_node("win_probability_agent", _make_node("win_probability", "win_probability", WinProbability, _stage2_context))
    g.add_node("strategy_agent", _make_node("strategy", "strategy", DealStrategy, _stage2_context))
    g.add_node("timeline_agent", _make_node("timeline", "timeline", DealTimeline, _stage2_context))
    g.add_node("assemble", assemble_node)

    g.add_edge([f"{k}_agent" for k, *_ in STAGE1], "finalize_health")  # fan-in: waits for all stage-1 nodes
    g.add_edge("finalize_health", "win_probability_agent")
    g.add_edge("win_probability_agent", "strategy_agent")
    g.add_edge("strategy_agent", "timeline_agent")
    g.add_edge("timeline_agent", "assemble")
    g.add_edge("assemble", END)

    return g.compile(checkpointer=checkpointer)


# ─────────────────────────── Service-facing entry point ───────────────────────────
async def run_deal_analytics(
    *,
    deal_id: str,
    owner_id: str,
    meetings: list[dict],                 # oldest first; see MeetingDigest
    deal_profile: dict | None = None,
    research_brief: dict | None = None,
    previous_snapshot: dict | None = None,
    latest_meeting_id: str | None = None,
    checkpointer=None,
) -> DealAnalyticsResult:
    if not meetings:
        raise ValueError("Deal analytics needs at least one analysed meeting")
    graph = build_deal_analytics_graph(checkpointer)
    initial: DealAnalyticsState = {
        "deal_id": deal_id,
        "owner_id": owner_id,
        "latest_meeting_id": latest_meeting_id,
        "deal_profile": deal_profile,
        "research_brief": research_brief,
        "meetings": meetings,
        "previous_snapshot": previous_snapshot,
        "snapshot_version": (previous_snapshot or {}).get("snapshot_version", 0) + 1,
        "warnings": [],
    }
    snapshot_no = initial["snapshot_version"]
    config = {"configurable": {"thread_id": f"deal-analytics-{deal_id}-v{snapshot_no}"}}
    final = await graph.ainvoke(initial, config=config)
    return final["result"]
