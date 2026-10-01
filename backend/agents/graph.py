import logging
from langgraph.graph import StateGraph, START, END

from app.core.config import settings
from langgraph.checkpoint.postgres import PostgresSaver

# Import node implementations
from backend.agents.nodes.financial_intelligence import financial_intelligence_node
from backend.agents.nodes.stakeholder_intelligence import stakeholder_intelligence_node
from backend.agents.nodes.industry_analysis import industry_analysis_node
from backend.agents.nodes.pain_point_detector import pain_point_detector_node
from backend.agents.nodes.enterprise_rag_matcher import enterprise_rag_matcher_node
from backend.agents.nodes.service_mapper import service_mapper_node
from backend.agents.nodes.human_review_gate import human_review_gate_node, route_human_review
from backend.agents.nodes.cxo_brief_synthesizer import cxo_brief_generator_node
from backend.agents.nodes.report_indexer import report_indexer_node
from backend.agents.nodes.company_research import company_research_node
from backend.agents.state import DealIntelligenceState

logger = logging.getLogger(__name__)


# ============================================================================
# ROUTING FUNCTIONS FOR HITL CONDITIONAL EDGES
# ============================================================================

def route_after_pause_check(state: DealIntelligenceState) -> str:
    """
    Routes based on manual pause request.
    If pause_requested is True, halts execution.
    Otherwise, continues to next node.
    """
    if state.get("pause_requested"):
        return "pause"
    return "continue"


def route_before_cxo_brief(state: DealIntelligenceState) -> str:
    """
    Routes before CXO brief generation.
    
    Mandatory review checkpoint: Always pause for review unless already approved.
    """
    checkpoint_status = state.get("mandatory_review_checkpoint", "pending")
    
    if checkpoint_status == "approved":
        return "proceed_to_brief"
    else:
        return "mandatory_review"


def route_after_review_decision(state: DealIntelligenceState) -> str:
    """
    Routes based on mandatory review decision.
    """
    checkpoint_status = state.get("mandatory_review_checkpoint", "pending")
    
    if checkpoint_status == "approved":
        return "proceed_to_brief"
    elif checkpoint_status == "rejected":
        return "end"
    elif checkpoint_status == "needs_revision":
        return "pause_for_revision"
    else:
        return "mandatory_review"  # Still pending


def pause_node(state: DealIntelligenceState) -> str:
    """
    Pseudo-node for pause/wait logic.
    Returns state unchanged - workflow is paused by this node.
    """
    logger.info(f"Workflow paused at node boundary for deal {state.get('deal_id')}")
    return {
        "current_step": "PAUSED_AT_BOUNDARY",
        "node_statuses": {
            **state.get("node_statuses", {}),
            "workflow_paused": "paused_at_node_boundary"
        }
    }


def mandatory_review_node(state: DealIntelligenceState) -> str:
    """
    Pseudo-node for mandatory review checkpoint.
    """
    logger.info(f"Reached mandatory review checkpoint for deal {state.get('deal_id')}")
    return {
        "current_step": "MANDATORY_REVIEW_CHECKPOINT",
        "node_statuses": {
            **state.get("node_statuses", {}),
            "reached_mandatory_checkpoint": "awaiting_review_approval"
        }
    }


# ============================================================================
# CREATE LANGGRAPH WORKFLOW WITH CHECKPOINTING & HITL
# ============================================================================

def create_deal_intelligence_graph():
    """
    Assembles the LangGraph state machine with:
    - 8 core intelligence nodes
    - Checkpointing for persistence and pause/resume
    - Dynamic instruction injection capability
    - Mandatory review gate before final brief
    - Manual pause/resume at node boundaries
    """
    workflow = StateGraph(DealIntelligenceState)

    # =========================================================================
    # 1. REGISTER NODES
    # =========================================================================
    workflow.add_node("company_research", company_research_node)
    workflow.add_node("financial_intelligence", financial_intelligence_node)
    workflow.add_node("stakeholder_intel", stakeholder_intelligence_node)
    workflow.add_node("industry_analysis", industry_analysis_node)
    workflow.add_node("pain_point_detector", pain_point_detector_node)
    workflow.add_node("enterprise_rag_matcher", enterprise_rag_matcher_node)
    workflow.add_node("service_mapper", service_mapper_node)
    workflow.add_node("human_review_gate", human_review_gate_node)
    
    # HITL Control Nodes
    workflow.add_node("_pause_at_boundary", pause_node)
    workflow.add_node("_mandatory_review_gate", mandatory_review_node)
    
    workflow.add_node("cxo_brief_generator", cxo_brief_generator_node)
    workflow.add_node("report_indexer", report_indexer_node)

    # =========================================================================
    # 2. DEFINE GRAPH TOPOLOGY & EDGES WITH HITL ROUTING
    # =========================================================================

    # Start: Node 1 (Company Research)
    workflow.add_edge(START, "company_research")

    # Parallel Execution: Node 1 -> Node 1B, Node 2, Node 3
    workflow.add_edge("company_research", "industry_analysis")
    workflow.add_edge("company_research", "financial_intelligence")
    workflow.add_edge("company_research", "stakeholder_intel")

    # Convergence: ALL 3 parallel nodes -> Node 4 (Pain Point Detector)
    workflow.add_edge(
        ["stakeholder_intel", "industry_analysis", "financial_intelligence"],
        "pain_point_detector"
    )

    # Sequential Processing: Node 4 -> Node 5 -> Node 6 -> HITL Gate
    workflow.add_edge("pain_point_detector", "enterprise_rag_matcher")
    workflow.add_edge("enterprise_rag_matcher", "service_mapper")
    workflow.add_edge("service_mapper", "human_review_gate")

    # HITL: After human review gate
    workflow.add_conditional_edges(
        "human_review_gate",
        route_human_review,
        {
            "proceed": "_mandatory_review_gate",
            "pause": "_pause_at_boundary",
        }
    )

    # HITL: Mandatory review checkpoint before CXO brief
    workflow.add_conditional_edges(
        "_mandatory_review_gate",
        route_before_cxo_brief,
        {
            "proceed_to_brief": "cxo_brief_generator",
            "mandatory_review": "_mandatory_review_gate",  # Stay at review until decision made
        }
    )

    # Resume from pause: When pause is cleared, route to next logical node
    workflow.add_edge("_pause_at_boundary", "human_review_gate")

    # Final sequence: CXO Brief -> Report Indexer -> END
    workflow.add_edge("cxo_brief_generator", "report_indexer")
    workflow.add_edge("report_indexer", END)

    # =========================================================================
    # 3. COMPILE WITH CHECKPOINTING FOR PERSISTENCE
    # =========================================================================
    
    checkpointer = PostgresSaver.from_conn_string(settings.DATABASE_URL)
    app = workflow.compile(checkpointer=checkpointer)
    logger.info("LangGraph compiled with PostgreSQL checkpointing.")
    
    return app


# Compiled state machine instance ready for runtime invocation
deal_intelligence_graph = create_deal_intelligence_graph()
