import os
import json
import logging
from typing import Dict, Any, List

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.state import DealIntelligenceState
from app.schemas.deal_intelligence import BusinessPrioritiesSchema
from app.services.vector_service import query_client_deal_docs

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def pain_point_detector_node(state: DealIntelligenceState) -> Dict[str, Any]:
    """
    Agent 4: Pain Point & Priority Detector
    Convergence node that synthesizes public web research from Nodes 1, 2, & 3
    with private client document chunks (RFP, RFI, BRD, Architecture docs) retrieved 
    from the deal's isolated vector collection.
    """
    deal_id = state.get("deal_id", "")
    target_company = state.get("target_company", "")
    target_industry = state.get("target_industry", "")
    meeting_objective = state.get("meeting_objective", "")

    # Retrieve accumulated state from previous nodes
    company_overview = state.get("company_overview", {})
    digital_initiatives = state.get("digital_initiatives", [])
    technology_investments = state.get("technology_investments", [])
    recent_news = state.get("recent_news_and_m_and_a", [])
    stakeholder_profiles = state.get("stakeholder_profiles", {})
    industry_analysis = state.get("industry_analysis", {})

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

    # Format retrieved RFP text snippets for the prompt
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
        "public_company_intelligence": {
            "overview": company_overview,
            "digital_initiatives": digital_initiatives,
            "technology_investments": technology_investments,
            "recent_news_m_and_a": recent_news
        },
        "stakeholder_concerns": stakeholder_profiles,
        "industry_and_compliance_pressures": industry_analysis,
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
2. Extract 4-6 high-level Strategic Business Priorities.
3. For each Detected Pain Point, specify:
   - category: Primary category (e.g., 'Legacy Systems', 'Fragmented Architecture', 'Regulatory Non-Compliance', 'High Operational Cost', 'Slow Time-to-Market').
   - description: 2-3 dense sentences explaining root causes, operational bottlenecks, and financial/business risks.
   - severity: Categorize strictly as 'HIGH', 'MEDIUM', or 'LOW'.
   - impacted_business_area: Specific department or function impacted (e.g., 'Core Banking Operations', 'Claims Processing', 'Enterprise Security').
4. Align detected pain points directly with the MEETING OBJECTIVE so downstream service mapping remains sharp and targeted."""

    human_message_content = f"""
TARGET COMPANY: {target_company}
TARGET INDUSTRY: {target_industry}
MEETING OBJECTIVE: {meeting_objective}

ACCUMULATED DEAL INTELLIGENCE CONTEXT:
{json.dumps(aggregated_context, indent=2)}

Cross-examine all public and client-provided sources, then synthesize the business priorities and structured pain points.
"""

    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.1,
            google_api_key=GEMINI_API_KEY
        )

        structured_llm = llm.with_structured_output(BusinessPrioritiesSchema)

        result: BusinessPrioritiesSchema = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_message_content)
        ])

        priorities = result.priorities
        pain_points = [pp.model_dump() for pp in result.pain_points]

        logger.info(
            f"Successfully detected {len(priorities)} priorities and {len(pain_points)} "
            f"pain points for company '{target_company}'"
        )

        return {
            "business_priorities": priorities,
            "detected_pain_points": pain_points,
            "matched_client_rfp_chunks": matched_client_rfp_chunks,
            "current_step": "PAIN_POINT_DETECTION_COMPLETED"
        }

    except Exception as e:
        logger.error(f"Error in Pain Point Detector Node: {str(e)}", exc_info=True)
        return {
            "errors": [f"Pain Point Detector Node failed: {str(e)}"],
            "current_step": "PAIN_POINT_DETECTION_FAILED"
        }