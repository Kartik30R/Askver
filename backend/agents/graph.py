import logging
from langgraph.graph import StateGraph, START, END

from app.agents.state import DealIntelligenceState

# Import node implementations
from app.agents.nodes.company_research import company_research_node
from app.agents.nodes.stakeholder_intel import stakeholder_intel_node
from app.agents.nodes.industry_analysis import industry_analysis_node
from app.agents.nodes.pain_point_detector import pain_point_detector_node
from app.agents.nodes.enterprise_rag_matcher import enterprise_rag_matcher_node
from app.agents.nodes.service_mapper import service_mapper_node
from app.agents.nodes.human_review_gate import human_review_gate_node, route_human_review
from app.agents.nodes.cxo_brief_generator import cxo_brief_generator_node
from app.agents.nodes.report_indexer import report_indexer_node

logger = logging.getLogger(__name__)


def create_deal_intelligence_graph():
    """
    Assembles the 8-node LangGraph state machine with parallel execution,
    HITL conditional routing, and final report indexing.
    """
    workflow = StateGraph(DealIntelligenceState)

    # -------------------------------------------------------------------------
    # 1. REGISTER NODES
    # -------------------------------------------------------------------------
    workflow.add_node("company_research", company_research_node)
    workflow.add_node("stakeholder_intel", stakeholder_intel_node)
    workflow.add_node("industry_analysis", industry_analysis_node)
    workflow.add_node("pain_point_detector", pain_point_detector_node)
    workflow.add_node("enterprise_rag_matcher", enterprise_rag_matcher_node)
    workflow.add_node("service_mapper", service_mapper_node)
    workflow.add_node("human_review_gate", human_review_gate_node)
    workflow.add_node("cxo_brief_generator", cxo_brief_generator_node)
    workflow.add_node("report_indexer", report_indexer_node)

    # -------------------------------------------------------------------------
    # 2. DEFINE GRAPH TOPOLOGY & EDGES
    # -------------------------------------------------------------------------

    # Parallel Start: Node 1 (Company Research) & Node 3 (Industry Analysis)
    workflow.add_edge(START, "company_research")
    workflow.add_edge(START, "industry_analysis")

    # Node 1 -> Node 2 (Stakeholder Intel depends on Company Research)
    workflow.add_edge("company_research", "stakeholder_intel")

    # Convergence: Node 2 + Node 3 -> Node 4 (Pain Point Detector)
    workflow.add_edge(["stakeholder_intel", "industry_analysis"], "pain_point_detector")

    # Sequential Processing: Node 4 -> Node 5 -> Node 6 -> HITL Gate
    workflow.add_edge("pain_point_detector", "enterprise_rag_matcher")
    workflow.add_edge("enterprise_rag_matcher", "service_mapper")
    workflow.add_edge("service_mapper", "human_review_gate")

    # -------------------------------------------------------------------------
    # 3. CONDITIONAL ROUTING (HUMAN REVIEW GATE)
    # -------------------------------------------------------------------------
    workflow.add_conditional_edges(
        "human_review_gate",
        route_human_review,
        {
            "proceed": "cxo_brief_generator",
            "pause": END  # Halts execution in PostgreSQL thread state until user approves
        }
    )

    # Final Synthesis & Indexing: Node 7 -> Node 8 -> END
    workflow.add_edge("cxo_brief_generator", "report_indexer")
    workflow.add_edge("report_indexer", END)

    # Compile Executable Graph
    app = workflow.compile()
    logger.info("LangGraph Deal Intelligence Graph successfully compiled.")
    return app


# Compiled state machine instance ready for runtime invocation
deal_intelligence_graph = create_deal_intelligence_graph()