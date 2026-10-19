"""Evidence gate and targeted refinement. Code-only: zero LLM cost except the extra specialist calls it triggers.

Flow:  research_join -> evidence_gate --REFINE--> research_refine -> evidence_gate -> frameworks
The loop runs at most MAX_REFINE_PASSES times, then proceeds and records the remaining thin areas as gaps.
"""
import logging
from typing import Any, Dict, List

from agents.nodes.research_specialists import make_specialist
from agents.state import DealIntelligenceState
from app.schemas.research_plan import DEPTH_CONFIG

logger = logging.getLogger(__name__)

MAX_REFINE_PASSES = 1
MAX_REFINE_AGENTS = 3

# Which specialists feed each fact category (a category is only demanded if one of them is scheduled)
CATEGORY_AGENTS = {
    "FINANCIAL": ["financial"],
    "LEADERSHIP": ["leadership"],
    "STRATEGY": ["business_model", "strategy"],
    "TECHNOLOGY": ["technology"],
    "INDUSTRY": ["industry"],
    "TRIGGER": ["triggers"],
}
MIN_PER_CATEGORY = {"FINANCIAL": 2, "LEADERSHIP": 2, "STRATEGY": 3, "TECHNOLOGY": 2, "INDUSTRY": 2, "TRIGGER": 1}
# Categories a second search can plausibly fix (financial numbers come from yfinance, not queries)
REFINE_AGENTS = {
    "LEADERSHIP": ["leadership"], "TRIGGER": ["triggers"], "TECHNOLOGY": ["technology"],
    "STRATEGY": ["strategy", "business_model"], "INDUSTRY": ["industry"],
}


def _plan_dict(state) -> dict:
    plan = state.get("research_plan")
    return plan.model_dump() if hasattr(plan, "model_dump") else dict(plan or {})


def _followup_queries(category: str, company: str, industry: str, plan: dict) -> List[str]:
    regions = " ".join(plan.get("regions", [])[:2])
    return {
        "LEADERSHIP": [f"{company} chief technology officer CIO appointed", f"{company} leadership team CFO CISO interview"],
        "TRIGGER": [f"{company} announces acquisition partnership launch", f"{company} regulator fine outage restructuring"],
        "TECHNOLOGY": [f"{company} engineering blog cloud platform migration", f"{company} careers data engineer cloud stack"],
        "STRATEGY": [f"{company} annual report chairman letter strategic priorities", f"{company} earnings call outlook strategy"],
        "INDUSTRY": [f"{regions} {industry} regulation compliance deadline".strip(), f"{regions} {industry} market size growth".strip()],
    }.get(category, [])


def evidence_gate_node(state: DealIntelligenceState) -> Dict[str, Any]:
    facts = state.get("facts") or {}
    depth = state.get("research_depth") or "standard"
    scheduled = set(DEPTH_CONFIG.get(depth, DEPTH_CONFIG["standard"])["agents"])
    done = state.get("research_pass") or 0

    counts: Dict[str, int] = {c: 0 for c in CATEGORY_AGENTS}
    for f in facts.values():
        if f.get("category") in counts:
            counts[f["category"]] += 1

    required = [c for c, agents in CATEGORY_AGENTS.items() if scheduled.intersection(agents)]
    weak = [c for c in required if counts[c] < MIN_PER_CATEGORY[c]]
    fixable = [c for c in weak if c in REFINE_AGENTS]
    decision = "REFINE" if fixable and done < MAX_REFINE_PASSES else "PROCEED"

    update: Dict[str, Any] = {
        "evidence_report": {"counts": counts, "weak": weak, "fixable": fixable, "decision": decision, "pass": done},
        "node_statuses": {"evidence_gate": "COMPLETED"},
    }
    if decision == "PROCEED" and weak:
        update["research_gaps"] = [f"thin evidence: {c.lower()} has {counts[c]} verified fact(s), wanted {MIN_PER_CATEGORY[c]}" for c in weak]
    logger.info("Evidence gate | pass=%s counts=%s weak=%s -> %s", done, counts, weak, decision)
    return update


def research_refine_node(state: DealIntelligenceState) -> Dict[str, Any]:
    """Re-run only the weak specialists with gap-targeted, template-built queries (no planner call)."""
    company, industry = state.get("target_company", ""), state.get("target_industry", "")
    plan = _plan_dict(state)
    report = state.get("evidence_report") or {}
    cfg = DEPTH_CONFIG.get(state.get("research_depth") or "standard", DEPTH_CONFIG["standard"])

    new_facts: Dict[str, dict] = {}
    new_sources: Dict[str, dict] = {}
    errors: List[str] = []
    ran = 0
    for category in report.get("fixable", []):
        agent = next((a for a in REFINE_AGENTS[category] if a in cfg["agents"]), None)
        queries = _followup_queries(category, company, industry, plan)
        if not agent or not queries or ran >= MAX_REFINE_AGENTS:
            continue
        ran += 1
        agent_plans = [ap for ap in plan.get("agent_plans", []) if ap.get("agent") != agent] + [{
            "agent": agent,
            "questions": [f"Find additional verifiable {category.lower()} facts about {company}"],
            "search_queries": queries,
        }]
        out = make_specialist(agent)({**dict(state), "research_plan": {**plan, "agent_plans": agent_plans}})
        new_facts.update(out.get("facts") or {})
        new_sources.update(out.get("sources") or {})
        errors.extend(out.get("errors") or [])

    update: Dict[str, Any] = {
        "facts": new_facts, "sources": new_sources,
        "research_pass": (state.get("research_pass") or 0) + 1,
        "node_statuses": {"research_refine": "COMPLETED"},
    }
    if errors:
        update["errors"] = errors
    return update


def route_after_gate(state):
    """Conditional edge for graph.py."""
    if (state.get("evidence_report") or {}).get("decision") == "REFINE":
        return "research_refine"
    return ["strategic_frameworks", "commercial_frameworks"]