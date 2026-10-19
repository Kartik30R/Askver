"""Insight synthesis (1 strong-model call) and the verifier (code only).

synthesis: frameworks + facts -> top insights, hypothesis verdicts, why-now / why-this-client, deal risks.
verifier:  deterministic checks on what synthesis produced: ungrounded figures, conflicting figures,
           coverage, source quality -> overall_confidence and known_gaps for the playbook.
"""
import json
import logging
import re
from datetime import date
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from agents.nodes.frameworks import COMMON_RULES, render_facts_for_prompt
from agents.nodes.node_middleware import (
    apply_instruction_context_to_prompt,
    get_injection_context,
    inject_dynamic_instructions,
)
from agents.state import DealIntelligenceState
from app.core.config import settings
from app.schemas.insights import InsightSynthesis
from app.services.llm_provider import get_llm

logger = logging.getLogger(__name__)

CATEGORIES = ("FINANCIAL", "LEADERSHIP", "STRATEGY", "TECHNOLOGY", "INDUSTRY", "TRIGGER")

# Figures with a currency symbol, percent sign or magnitude unit. Bare numbers and years are ignored on purpose.
_FIG = re.compile(
    r"(?:[$₹€£]\s?\d[\d,]*(?:\.\d+)?\s?(?:bn|b|m|k|t|cr|crore|lakh|million|billion|trillion)?\b"
    r"|\d[\d,]*(?:\.\d+)?\s?(?:%|bn\b|billion\b|million\b|trillion\b|crore\b|cr\b|lakh\b|pb\b|tb\b|m\b|b\b|k\b|t\b|x\b))",
    re.IGNORECASE,
)
_UNITS = (("trillion", "t"), ("billion", "b"), ("million", "m"), ("crore", "cr"), ("bn", "b"))


def _norm_fig(s: str) -> str:
    s = s.lower().replace(",", "")
    s = re.sub(r"^[$₹€£]\s*", "", s)
    s = re.sub(r"\s+", "", s)
    for long, short in _UNITS:
        s = s.replace(long, short)
    return s


def figures_in(text: str) -> set:
    return {_norm_fig(m) for m in _FIG.findall(text or "")}


def _fact_text(f: dict) -> str:
    return " ".join(str(x) for x in (f.get("claim"), f.get("value"), f.get("period")) if x)


def unverified_figures(text: str, fact_ids: List[str], facts: Dict[str, dict]) -> List[str]:
    """Figures stated in `text` that appear in none of the cited facts."""
    allowed: set = set()
    for i in fact_ids:
        if i in facts:
            allowed |= figures_in(_fact_text(facts[i]))
    return sorted(f for f in figures_in(text) if f not in allowed)


def find_conflicts(facts: Dict[str, dict]) -> List[str]:
    """Same statement with different figures (e.g. two sources disagree on subscriber count)."""
    groups: Dict[str, List[dict]] = {}
    for f in facts.values():
        stripped = re.sub(r"\s+", " ", _FIG.sub("#", f["claim"].lower())).strip()
        if "#" in stripped:
            groups.setdefault((f["category"] + "|" + stripped), []).append(f)
    out = []
    for g in groups.values():
        figs = {frozenset(figures_in(_fact_text(f))) for f in g}
        if len(figs) > 1:
            out.append("conflicting figures: " + " vs ".join(sorted(g_["claim"] for g_ in g))[:240])
    return out


def _llm():
    return get_llm(
        model=getattr(settings, "LLM_MODEL_STRONG", None) or settings.LLM_MODEL or "gemini-2.5-flash",
        provider=settings.LLM_PROVIDER or "gemini",
        temperature=0.2,
    )


def _plan_dict(state) -> dict:
    plan = state.get("research_plan")
    return plan.model_dump() if hasattr(plan, "model_dump") else dict(plan or {})


def _compact_frameworks(state) -> str:
    """Statements + citations only; drops rationale prose to keep the prompt small."""
    s, c = state.get("strategic_frameworks") or {}, state.get("commercial_frameworks") or {}
    swot = {k: [{"t": i["statement"], "f": i["fact_ids"]} for i in v] for k, v in (s.get("swot") or {}).items()}
    pack = {
        "swot": swot,
        "tows": [{"q": m["quadrant"], "move": m["move"], "f": m["fact_ids"]} for m in s.get("tows", [])],
        "porter": [{"force": p["force"], "rating": p["rating"], "why": p["rationale"], "f": p["fact_ids"]} for p in s.get("porter", [])],
        "pestle": [{"d": p["dimension"], "factor": p["factor"], "when": p["timeframe"], "f": p["fact_ids"]} for p in s.get("pestle", [])],
        "committee": [{"role": m["role"], "name": m["name"], "buying_role": m["buying_role"], "stance": m["likely_stance"]} for m in c.get("buying_committee", [])],
        "maturity": [{"d": m["dimension"], "score": m["score_1_to_5"]} for m in c.get("digital_maturity", [])],
        "peers": [{"peer": p["peer"], "pos": p["target_position"], "c": p["comparison"], "f": p["fact_ids"]} for p in c.get("peer_benchmark", [])],
    }
    return json.dumps(pack, separators=(",", ":"))


def _finalize(res: InsightSynthesis, facts: Dict[str, dict], hypotheses: List[str]) -> dict:
    d, valid = res.model_dump(), set(facts)

    def keep(items):
        out = []
        for it in items:
            ids = [i for i in it.get("fact_ids", []) if i in valid]
            if ids:
                out.append({**it, "fact_ids": ids})
        return out

    d["insights"] = keep(d["insights"])[:5]
    for part in ("why_now", "why_this_client", "value_hypothesis"):
        d[part]["fact_ids"] = [i for i in d[part]["fact_ids"] if i in valid]
        if not d[part]["fact_ids"]:
            d[part]["text"] = ""                      # an uncited thesis part is empty, not a guess
    d["deal_risks"] = [{**r, "fact_ids": [i for i in r.get("fact_ids", []) if i in valid]} for r in d["deal_risks"]]

    verdicts = {v["statement"].strip().lower(): v for v in d["hypothesis_verdicts"]}
    final = []
    for h in hypotheses:
        v = verdicts.get(h.strip().lower())
        if not v:
            final.append({"statement": h, "verdict": "UNTESTED", "rationale": "No verdict returned", "fact_ids": []})
            continue
        v["fact_ids"] = [i for i in v.get("fact_ids", []) if i in valid]
        if not v["fact_ids"] and v["verdict"] in ("SUPPORTED", "PARTIAL", "CONTRADICTED"):
            v["verdict"] = "UNSUPPORTED"
        final.append(v)
    d["hypothesis_verdicts"] = final
    return d


@inject_dynamic_instructions
def insight_synthesis_node(state: DealIntelligenceState) -> Dict[str, Any]:
    company, objective = state.get("target_company", ""), state.get("meeting_objective", "")
    facts, sources = state.get("facts") or {}, state.get("sources") or {}
    plan = _plan_dict(state)
    hypotheses = [h.get("statement", "") for h in plan.get("hypotheses", []) if h.get("statement")]

    if not facts or not (state.get("strategic_frameworks") or state.get("commercial_frameworks")):
        return {"research_gaps": ["insight synthesis skipped: no frameworks or facts to synthesise"],
                "node_statuses": {"insight_synthesis": "COMPLETED"}}

    system = f"""You are a partner at a strategy consultancy turning an analysis into the few things that decide whether a CXO meeting leads to a deal. Today is {date.today().isoformat()}.

Produce: up to 5 insights ranked by impact on winning the deal (each with a clear 'so what'), one verdict per hypothesis, why_now, why_this_client, value_hypothesis, 3-5 deal risks, and what must be validated live.

Extra rules:
- An insight is a conclusion drawn from combining facts, not a restatement of one fact.
- why_now must rest on dated triggers or regulatory deadlines. If none exist, leave its fact_ids empty.
- value_hypothesis must not contain invented ROI, savings or percentages. Only figures present in cited facts.
- validate_in_meeting: list what the evidence could not settle (budget owner, timeline, incumbent vendors, decision process).

{COMMON_RULES}"""
    human = (
        f"COMPANY: {company}\nMEETING OBJECTIVE: {objective}\n"
        f"HYPOTHESES (give one verdict each, copy the statement exactly):\n" + "\n".join(f"- {h}" for h in hypotheses) +
        f"\n\nFRAMEWORK OUTPUT (f = fact ids):\n{_compact_frameworks(state)}"
        f"\n\nFACTS:\n{render_facts_for_prompt(facts, sources)}"
    )
    try:
        res: InsightSynthesis = _llm().with_structured_output(InsightSynthesis).invoke([
            SystemMessage(content=apply_instruction_context_to_prompt(system, get_injection_context(state))),
            HumanMessage(content=human),
        ])
        return {"insight_synthesis": _finalize(res, facts, hypotheses),
                "node_statuses": {"insight_synthesis": "COMPLETED"}, "_instructions_applied": True}
    except Exception as exc:
        logger.error("Insight synthesis failed: %s", exc, exc_info=True)
        return {"errors": [f"insight_synthesis: {exc}"], "node_statuses": {"insight_synthesis": "FAILED"}}


# ----------------------------------------------------------------------------- verifier (no LLM)
def verifier_node(state: DealIntelligenceState) -> Dict[str, Any]:
    facts, sources = state.get("facts") or {}, state.get("sources") or {}
    synth = state.get("insight_synthesis") or {}
    flagged: List[str] = []

    # 1. figures in insights must trace to cited facts
    insights = []
    for ins in synth.get("insights", []):
        bad = unverified_figures(ins["headline"] + " " + ins["so_what"], ins["fact_ids"], facts)
        if bad:
            ins = {**ins, "unverified_figures": bad, "evidence_strength": "LOW"}
            flagged.append(f"insight '{ins['headline'][:60]}' states figure(s) not in its cited facts: {', '.join(bad)}")
        insights.append(ins)
    if synth:
        synth = {**synth, "insights": insights}
        for part in ("why_now", "why_this_client", "value_hypothesis"):
            bad = unverified_figures(synth[part]["text"], synth[part]["fact_ids"], facts)
            if bad:
                flagged.append(f"{part} states figure(s) not in its cited facts: {', '.join(bad)}")

    # 2. figures in framework cells
    sf = state.get("strategic_frameworks") or {}
    cells = [(f"swot.{k}", i) for k, v in (sf.get("swot") or {}).items() for i in v]
    cells += [("tows", {"statement": m["move"], "fact_ids": m["fact_ids"]}) for m in sf.get("tows", [])]
    cells += [("pestle", {"statement": p["factor"], "fact_ids": p["fact_ids"]}) for p in sf.get("pestle", [])]
    for section, cell in cells:
        bad = unverified_figures(cell["statement"], cell["fact_ids"], facts)
        if bad:
            flagged.append(f"{section}: '{cell['statement'][:60]}' states figure(s) not in cited facts: {', '.join(bad)}")

    conflicts = find_conflicts(facts)

    # 3. coverage and source quality
    present = {c for c in CATEGORIES if any(f["category"] == c for f in facts.values())}
    coverage = len(present) / len(CATEGORIES)

    def best_tier(f):
        return min((sources.get(i, {}).get("tier", 4) for i in f["source_ids"]), default=4)

    n = max(len(facts), 1)
    high_share = sum(1 for f in facts.values() if f.get("confidence") == "HIGH") / n
    tier_quality = sum(1 for f in facts.values() if best_tier(f) <= 3) / n
    insight_total = len(insights)
    grounding = 1 - (sum(1 for i in insights if i["unverified_figures"]) / insight_total) if insight_total else 0.0

    if len(facts) < 10 or coverage <= 0.5 or grounding < 0.6 or insight_total == 0:
        confidence = "LOW"
    elif coverage >= 0.83 and grounding >= 0.9 and high_share >= 0.25 and tier_quality >= 0.5 and not conflicts:
        confidence = "HIGH"
    else:
        confidence = "MEDIUM"

    unsupported = [v["statement"] for v in synth.get("hypothesis_verdicts", []) if v["verdict"] in ("UNSUPPORTED", "UNTESTED")]
    gaps = list(state.get("research_gaps") or [])
    gaps += [f"hypothesis not supported by evidence: {h}" for h in unsupported]
    gaps += [f"no {c.lower()} facts found" for c in CATEGORIES if c not in present]
    gaps += conflicts + flagged
    gaps += list(synth.get("validate_in_meeting", []))

    report = {
        "overall_confidence": confidence,
        "scores": {"coverage": round(coverage, 2), "grounding": round(grounding, 2),
                   "high_confidence_share": round(high_share, 2), "reliable_source_share": round(tier_quality, 2),
                   "facts": len(facts), "sources": len(sources)},
        "unverified_figures": flagged, "possible_conflicts": conflicts,
        "known_gaps": list(dict.fromkeys(gaps)),               # de-duplicated, order kept
    }
    update: Dict[str, Any] = {"verification_report": report, "node_statuses": {"verifier": "COMPLETED"}}
    if synth:
        update["insight_synthesis"] = synth
    return update