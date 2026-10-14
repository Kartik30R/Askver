
import logging

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph

from agents.nodes.company_research import company_research_node
from agents.nodes.cxo_brief_synthesizer import cxo_brief_generator_node
from agents.nodes.enterprise_rag_matcher import enterprise_rag_matcher_node
from agents.nodes.financial_intelligence import financial_intelligence_node
from agents.nodes.human_review_gate import human_review_gate_node
from agents.nodes.industry_analysis import industry_analysis_node
from agents.nodes.pain_point_detector import pain_point_detector_node
from agents.nodes.report_indexer import report_indexer_node
from agents.nodes.service_mapper import service_mapper_node
from agents.nodes.stakeholder_intelligence import stakeholder_intelligence_node
from agents.state import DealIntelligenceState
from app.schemas.node_1_company import CompanyResearchSchema
from app.schemas.node_1b_financial import FinancialIntelligenceSchema
from app.schemas.node_2_stakeholder import StakeholderIntelligenceSchema
from app.schemas.node_3_industry import IndustryAnalysisSchema
from app.schemas.node_4_priorities import BusinessPrioritiesSchema
from app.schemas.node_5_6_services import MatchedAssetSchema, ServiceMappingSchema
from app.utils.serializers import to_primitive

logger = logging.getLogger(__name__)

deal_intelligence_graph = None


def configure_deal_intelligence_graph(checkpointer: AsyncPostgresSaver):
    global deal_intelligence_graph
    deal_intelligence_graph = create_deal_intelligence_graph(checkpointer)
    return deal_intelligence_graph


def get_deal_intelligence_graph():
    if deal_intelligence_graph is None:
        raise RuntimeError("Deal intelligence graph has not been configured yet.")
    return deal_intelligence_graph


# ---------------------------------------------------------------------------
# State rule: the graph state holds PLAIN JSON. Nodes still get Pydantic models.
# ---------------------------------------------------------------------------
_HYDRATE = {
    "company_research": (CompanyResearchSchema, False),
    "financial_intelligence": (FinancialIntelligenceSchema, False),
    "stakeholder_intelligence": (StakeholderIntelligenceSchema, False),
    "industry_analysis": (IndustryAnalysisSchema, False),
    "priorities_and_pain_points": (BusinessPrioritiesSchema, False),
    "matched_internal_assets": (MatchedAssetSchema, True),
    "service_mappings": (ServiceMappingSchema, True),
}


def _hydrate(state) -> dict:
    s = dict(state)
    for key, (schema, is_list) in _HYDRATE.items():
        v = s.get(key)
        if v is None:
            continue
        if is_list:
            s[key] = [x if isinstance(x, schema) else schema.model_validate(x) for x in v]
        elif not isinstance(v, schema):
            s[key] = schema.model_validate(v)
    return s


def tracked(name, fn):
    """Hydrate inputs, dump outputs, key the status by node name, never let a node crash the run."""
    def wrapper(state):
        try:
            update = dict(fn(_hydrate(state)) or {})
        except Exception as exc:
            logger.exception("Node %s crashed", name)
            return {"errors": [f"{name}: {exc}"], "node_statuses": {name: "FAILED"}}
        failed = any(v == "FAILED" for v in (update.get("node_statuses") or {}).values())
        update = {k: to_primitive(v) for k, v in update.items() if not k.startswith("_")}
        update["node_statuses"] = {name: "FAILED" if failed else "COMPLETED"}
        return update
    wrapper.__name__ = name
    return wrapper


def route_after_research(state):
    if (state.get("node_statuses") or {}).get("company_research") == "FAILED":
        return END                                    # fail fast, nothing downstream can work
    return ["industry_analysis", "financial_intelligence", "stakeholder_intel"]


def route_after_review_decision(state) -> str:
    s = state.get("mandatory_review_checkpoint", "pending")
    if s == "approved":
        return "proceed_to_brief"
    if s == "rejected":
        return "end"
    return "wait_for_review"          # pending / needs_revision -> interrupt fires again, no loop


def create_deal_intelligence_graph(checkpointer):
    wf = StateGraph(DealIntelligenceState)

    for name, fn in [
        ("company_research", company_research_node),
        ("financial_intelligence", financial_intelligence_node),
        ("stakeholder_intel", stakeholder_intelligence_node),
        ("industry_analysis", industry_analysis_node),
        ("pain_point_detector", pain_point_detector_node),
        ("enterprise_rag_matcher", enterprise_rag_matcher_node),
        ("service_mapper", service_mapper_node),
        ("cxo_brief_generator", cxo_brief_generator_node),
        ("report_indexer", report_indexer_node),
    ]:
        wf.add_node(name, tracked(name, fn))
    wf.add_node("mandatory_review", human_review_gate_node)   # works on dicts, not wrapped

    wf.add_edge(START, "company_research")
    wf.add_conditional_edges("company_research", route_after_research)
    wf.add_edge(["stakeholder_intel", "industry_analysis", "financial_intelligence"], "pain_point_detector")
    wf.add_edge("pain_point_detector", "enterprise_rag_matcher")
    wf.add_edge("enterprise_rag_matcher", "service_mapper")
    wf.add_edge("service_mapper", "mandatory_review")
    wf.add_conditional_edges("mandatory_review", route_after_review_decision, {
        "proceed_to_brief": "cxo_brief_generator",
        "end": END,
        "wait_for_review": "mandatory_review",
    })
    wf.add_edge("cxo_brief_generator", "report_indexer")
    wf.add_edge("report_indexer", END)

    return wf.compile(checkpointer=checkpointer, interrupt_before=["mandatory_review"])