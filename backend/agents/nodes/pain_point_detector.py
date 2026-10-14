import logging
import json
from typing import Dict, Any, List

from agents.nodes.node_middleware import apply_instruction_context_to_prompt, get_injection_context, inject_dynamic_instructions
from agents.state import DealIntelligenceState
from app.core.config import settings
from app.services.vector_service import query_client_deal_docs
from app.services.llm_provider import get_llm

from langchain_core.messages import SystemMessage, HumanMessage

# Import strict schema
from app.schemas.node_4_priorities import BusinessPrioritiesSchema

logger = logging.getLogger(__name__)


@inject_dynamic_instructions
def pain_point_detector_node(state: DealIntelligenceState) -> Dict[str, Any]:
    """
    Agent 4: Pain Point & Priority Detector
    Convergence node that synthesizes public web research from Nodes 1, 2, & 3
    with private client document chunks retrieved from the deal's isolated vector collection.
    """
    deal_id = state.get("deal_id", "")
    target_company = state.get("target_company", "")
    target_industry = state.get("target_industry", "")
    meeting_objective = state.get("meeting_objective", "")

    # Retrieve accumulated state objects from previous nodes
    company_research = state.get("company_research")
    stakeholder_intel = state.get("stakeholder_intelligence")
    industry_analysis = state.get("industry_analysis")

    logger.info(f"Starting Pain Point Detector Node for Deal ID: '{deal_id}' ({target_company})")

    # =========================================================================
    # 1. RETRIEVE CLIENT RFP / BRD CHUNKS FROM DEAL VECTOR STORE
    # =========================================================================
    matched_client_rfp_chunks: List[Dict[str, Any]] = []
    
    if deal_id:
        rfp_query = (
            f" explicit pain points technical challenges legacy system bottlenecks "
            f" requirements constraints project risks {meeting_objective} "
        )
        matched_client_rfp_chunks = query_client_deal_docs(
            deal_id=deal_id, 
            query=rfp_query, 
            top_k=6
        )
        logger.info(f"Retrieved {len(matched_client_rfp_chunks)} client RFP/BRD chunks for deal {deal_id}")

    client_rfp_context = [
        {
            "snippet": chunk.get("content", ""),
            "metadata": chunk.get("metadata", {}),
            "relevance_score": chunk.get("score", 0.0)
        }
        for chunk in matched_client_rfp_chunks
    ]

    # =========================================================================
    # 2. CONSOLIDATE ACCUMULATED CONTEXT
    # =========================================================================
    aggregated_context = {
        "public_company_intelligence": company_research.model_dump() if company_research else {},
        "stakeholder_concerns": stakeholder_intel.model_dump() if stakeholder_intel else {},
        "industry_and_compliance_pressures": industry_analysis.model_dump() if industry_analysis else {},
        "private_client_rfp_brd_context": client_rfp_context
    }

    # =========================================================================
    # 3. LLM INVOCATION WITH SYSTEM PROMPT & STRUCTURED OUTPUT
    # =========================================================================
    system_prompt = """You are an Enterprise Strategy Consultant and Technical Due Diligence Partner.

YOUR GOAL:
Synthesize public company intelligence, leadership priorities, industry/compliance pressures, and private client RFP/BRD document excerpts to detect explicit operational/technical pain points and top strategic priorities.

SYNTHESIS & PRIORITY RULES:
1. PRIVATE CLIENT RFP/BRD OVERRIDE: Any explicit challenge, legacy constraint, or requirement found in the 'private_client_rfp_brd_context' MUST take highest priority over general web research.
2. Extract high-level Strategic Business Priorities.
3. For each Detected Pain Point, specify:
   - category: Primary category (e.g., 'Legacy Systems', 'Fragmented Architecture', 'Regulatory Non-Compliance', 'High Operational Cost', 'Slow Time-to-Market').
   - description: 2-3 dense sentences explaining root causes, operational bottlenecks, and financial/business risks.
   - severity: Categorize strictly as 'HIGH', 'MEDIUM', or 'LOW'.
   - impacted_business_area: Specific department or function impacted.
4. Align detected pain points directly with the MEETING OBJECTIVE."""

    human_message_content = f"""
TARGET COMPANY: {target_company}
TARGET INDUSTRY: {target_industry}
MEETING OBJECTIVE: {meeting_objective}

ACCUMULATED DEAL INTELLIGENCE CONTEXT:
{json.dumps(aggregated_context, separators=(',', ':'), default=str)}

Cross-examine all public and client-provided sources, then synthesize the business priorities and structured pain points strictly matching BusinessPrioritiesSchema.
"""

    try:
        llm = get_llm(
            model=settings.LLM_MODEL or "gemini-2.0-flash",
            provider=settings.LLM_PROVIDER or "gemini",
            temperature=0.1,
        )

        final_system_prompt = apply_instruction_context_to_prompt(system_prompt, get_injection_context(state))

        structured_llm = llm.with_structured_output(BusinessPrioritiesSchema)

        result: BusinessPrioritiesSchema = structured_llm.invoke([
            SystemMessage(content=final_system_prompt),
            HumanMessage(content=human_message_content)
        ])

        logger.info(
            f"Successfully detected priorities and pain points for company '{target_company}'"
        )

        return {
            "priorities_and_pain_points": result,
            "node_statuses": {"pain_point_detector": "COMPLETED"},
            "_instructions_applied": True
        }

    except Exception as e:
        logger.error(f"Error in Pain Point Detector Node: {str(e)}", exc_info=True)
        return {
            "errors": [f"Pain Point Detector Node failed: {str(e)}"],
            "node_statuses": {"pain_point_detector": "FAILED"}
        }