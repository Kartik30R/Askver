
import logging

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph

from agents.nodes.enterprise_rag_matcher import enterprise_rag_matcher_node
from agents.nodes.evidence_gate import evidence_gate_node, research_refine_node, route_after_gate
from agents.nodes.frameworks import commercial_frameworks_node, strategic_frameworks_node
from agents.nodes.human_review_gate import human_review_gate_node
from agents.nodes.insight_synthesis import insight_synthesis_node, verifier_node
from agents.nodes.pain_point_detector import pain_point_detector_node
from agents.nodes.playbook import playbook_assemble_node, playbook_questions_node, playbook_room_node
from agents.nodes.report_indexer import report_indexer_node
from agents.nodes.research_financial import research_financial_node
from agents.nodes.research_planner import research_planner_node
from agents.nodes.research_specialists import (
    research_business_model_node,
    research_competitors_node,
    research_industry_node,
    research_leadership_node,
    research_strategy_node,
    research_technology_node,
    research_triggers_node,
)
from agents.nodes.service_mapper import service_mapper_node
from agents.state import DealIntelligenceState
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
    "priorities_and_pain_points": (BusinessPrioritiesSchema, False),
    "matched_internal_assets": (MatchedAssetSchema, True),
    "service_mappings": (ServiceMappingSchema, True),
}


SPECIALISTS = [
    ("research_business_model", research_business_model_node),
    ("research_financial", research_financial_node),
    ("research_strategy", research_strategy_node),
    ("research_technology", research_technology_node),
    ("research_leadership", research_leadership_node),
    ("research_industry", research_industry_node),
    ("research_competitors", research_competitors_node),
    ("research_triggers", research_triggers_node),
]


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


def route_after_planner_fanout(state):
    if (state.get("node_statuses") or {}).get("research_planner") == "FAILED":
        return END
    return [name for name, _ in SPECIALISTS]


def route_after_review_decision(state) -> str:
    s = str(state.get("mandatory_review_checkpoint", "pending")).lower()
    if s == "approved":
        return "playbook_questions"
    if s == "rejected":
        return "end"
    return "wait_for_review"


def create_deal_intelligence_graph(checkpointer):
    wf = StateGraph(DealIntelligenceState)

    wf.add_node("research_planner", tracked("research_planner", research_planner_node))
    for name, fn in SPECIALISTS:
        wf.add_node(name, tracked(name, fn))
    wf.add_node("research_join", lambda state: {})
    wf.add_node("evidence_gate", tracked("evidence_gate", evidence_gate_node))
    wf.add_node("research_refine", tracked("research_refine", research_refine_node))

    wf.add_node("strategic_frameworks", tracked("strategic_frameworks", strategic_frameworks_node))
    wf.add_node("commercial_frameworks", tracked("commercial_frameworks", commercial_frameworks_node))
    wf.add_node("framework_join", lambda state: {})
    wf.add_node("insight_synthesis", tracked("insight_synthesis", insight_synthesis_node))
    wf.add_node("verifier", tracked("verifier", verifier_node))
    wf.add_node("pain_point_detector", tracked("pain_point_detector", pain_point_detector_node))

    wf.add_node("enterprise_rag_matcher", tracked("enterprise_rag_matcher", enterprise_rag_matcher_node))
    wf.add_node("service_mapper", tracked("service_mapper", service_mapper_node))
    wf.add_node("mandatory_review", tracked("mandatory_review", human_review_gate_node))

    wf.add_node("playbook_questions", tracked("playbook_questions", playbook_questions_node))
    wf.add_node("playbook_room", tracked("playbook_room", playbook_room_node))
    wf.add_node("playbook_assemble", tracked("playbook_assemble", playbook_assemble_node))
    wf.add_node("report_indexer", tracked("report_indexer", report_indexer_node))

    wf.add_edge(START, "research_planner")
    wf.add_conditional_edges("research_planner", route_after_planner_fanout)
    wf.add_edge([name for name, _ in SPECIALISTS], "research_join")
    wf.add_edge("research_join", "evidence_gate")
    wf.add_conditional_edges("evidence_gate", route_after_gate)
    wf.add_edge("research_refine", "evidence_gate")
    wf.add_edge(["strategic_frameworks", "commercial_frameworks"], "framework_join")
    wf.add_edge("framework_join", "insight_synthesis")
    wf.add_edge("insight_synthesis", "verifier")
    wf.add_edge("verifier", "pain_point_detector")
    wf.add_edge("pain_point_detector", "enterprise_rag_matcher")
    wf.add_edge("enterprise_rag_matcher", "service_mapper")
    wf.add_edge("service_mapper", "mandatory_review")
    wf.add_conditional_edges("mandatory_review", route_after_review_decision)
    wf.add_edge("playbook_questions", "playbook_room")
    wf.add_edge("playbook_room", "playbook_assemble")
    wf.add_edge("playbook_assemble", "report_indexer")
    wf.add_edge("report_indexer", END)

    return wf.compile(checkpointer=checkpointer, interrupt_before=["mandatory_review"])