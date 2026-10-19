import logging
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage

from agents.nodes.node_middleware import (
    apply_instruction_context_to_prompt,
    get_injection_context,
    inject_dynamic_instructions,
)
from agents.state import DealIntelligenceState
from agents.tools.evidence_collector import collect_sources, render_sources_for_prompt
from app.core.config import settings
from app.schemas.research_plan import DEPTH_CONFIG, ResearchPlan
from app.services.llm_provider import get_llm

logger = logging.getLogger(__name__)


def _client_doc_hints(deal_id: str, objective: str) -> str:
    """Optional: 3 chunks of the client's own RFP/BRD so the plan reflects what they actually asked for."""
    if not deal_id:
        return ""
    try:
        from app.services.vector_service import query_client_deal_docs
        chunks = query_client_deal_docs(deal_id=deal_id, query=f"requirements challenges scope {objective}", top_k=3)
        return "\n".join(f"- {c.get('content', '')[:400]}" for c in chunks)
    except Exception as exc:                                   # planner must work without client docs
        logger.info("No client doc hints for deal %s: %s", deal_id, exc)
        return ""


@inject_dynamic_instructions
def research_planner_node(state: DealIntelligenceState) -> Dict[str, Any]:
    """
    Step 0 of the research module. One cheap LLM call that decides WHAT to research:
    region, sub-sector, peers, regulations, hypotheses and per-specialist queries.
    Every later node reads this plan instead of guessing (no more hardcoded 'DORA RBI SEC GDPR').
    """
    company = state.get("target_company", "")
    industry = state.get("target_industry", "")
    objective = state.get("meeting_objective", "")
    depth = state.get("research_depth") or "standard"
    cfg = DEPTH_CONFIG.get(depth, DEPTH_CONFIG["standard"])

    logger.info("Research planner | company=%s depth=%s", company, depth)

    # Two grounding searches so the planner does not rely on model memory for region/peers/status.
    sources = collect_sources(
        [f"{company} company overview headquarters business segments",
         f"{company} main competitors market position"],
        agent="research_planner", company=company, max_results=4, max_queries=2,
    )
    if not sources:
        return {
            "errors": ["research_planner: grounding search returned nothing (DuckDuckGo blocked or company unknown)"],
            "node_statuses": {"research_planner": "FAILED"},
        }

    system_prompt = f"""You are a research director at a top-tier strategy consultancy planning an account study before any analyst starts.

Use ONLY the grounding sources for facts about the company. Where they are silent, put the item in known_unknowns; do not guess.

RULES:
1. regions and regulatory_regimes must follow where the company actually operates. Name specific laws and regulators.
2. peers: real direct competitors, at most {cfg['peers']}.
3. hypotheses: 3-5 testable ideas about why this company needs what we sell, tied to the meeting objective. Each must say what evidence would disprove it.
4. agent_plans: only for these specialists: {', '.join(cfg['agents'])}. Search queries must be specific to this company, written as a person would type them, and must not contain hardcoded years.
5. likely_attendee_roles: infer from the objective and client documents; default to CEO, CFO, CIO/CTO only if nothing else is known."""

    human_message = f"""TARGET COMPANY: {company}
TARGET INDUSTRY: {industry}
MEETING OBJECTIVE: {objective}

CLIENT DOCUMENT HINTS:
{_client_doc_hints(state.get("deal_id", ""), objective) or "none provided"}

GROUNDING SOURCES:
{render_sources_for_prompt(sources, limit=8)}

Produce the research plan."""

    try:
        llm = get_llm(
            model=getattr(settings, "LLM_MODEL_CHEAP", None) or settings.LLM_MODEL or "gemini-2.5-flash",
            provider=settings.LLM_PROVIDER or "gemini",
            temperature=0.1,
        )
        final_system = apply_instruction_context_to_prompt(system_prompt, get_injection_context(state))
        plan: ResearchPlan = llm.with_structured_output(ResearchPlan).invoke(
            [SystemMessage(content=final_system), HumanMessage(content=human_message)]
        )

        # Enforce the budget in code even if the model over-produces.
        plan.peers = plan.peers[: cfg["peers"]]
        plan.agent_plans = [a for a in plan.agent_plans if a.agent in cfg["agents"]]

        return {
            "research_plan": plan,
            "sources": sources,
            "node_statuses": {"research_planner": "COMPLETED"},
            "_instructions_applied": True,
        }
    except Exception as exc:
        logger.error("Research planner failed: %s", exc, exc_info=True)
        return {
            "errors": [f"Research Planner failed: {exc}"],
            "node_statuses": {"research_planner": "FAILED"},
        }