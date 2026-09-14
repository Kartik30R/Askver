import os
import json
import logging
from typing import Dict, Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.state import DealIntelligenceState
from app.schemas.deal_intelligence import MeetingStrategySchema
from app.agents.node_middleware import inject_dynamic_instructions, get_injection_context, apply_instruction_context_to_prompt

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

@inject_dynamic_instructions
def cxo_brief_generator_node(state: DealIntelligenceState) -> Dict[str, Any]:
    """
    Agent 7: CXO Brief Generator
    Synthesizes accumulated research, persona insights, pain points, internal RAG assets, 
    and service mappings into an executive-ready CXO meeting strategy brief.
    """
    target_company = state.get("target_company", "")
    target_industry = state.get("target_industry", "")
    meeting_objective = state.get("meeting_objective", "")

    # Retrieve state from previous nodes
    company_overview = state.get("company_overview", {})
    leadership_team = state.get("leadership_team", [])
    stakeholder_profiles = state.get("stakeholder_profiles", {})
    industry_analysis = state.get("industry_analysis", {})
    business_priorities = state.get("business_priorities", [])
    detected_pain_points = state.get("detected_pain_points", [])
    matched_internal_assets = state.get("matched_internal_assets", [])
    service_mappings = state.get("service_mappings", [])

    # Human-in-the-loop review overrides (if provided)
    human_approved = state.get("human_approved", False)
    human_feedback = state.get("human_feedback", None)
    custom_selected_assets = state.get("custom_selected_assets", [])

    logger.info(f"Starting CXO Brief Generator Node for: '{target_company}'")

    # =========================================================================
    # 1. CONSOLIDATE COMPLETE DEAL INTELLIGENCE CONTEXT
    # =========================================================================
    aggregated_context = {
        "deal_inputs": {
            "target_company": target_company,
            "target_industry": target_industry,
            "meeting_objective": meeting_objective,
        },
        "executive_leadership_team": leadership_team,
        "stakeholder_personas": stakeholder_profiles,
        "industry_and_compliance": industry_analysis,
        "strategic_priorities": business_priorities,
        "detected_pain_points": detected_pain_points,
        "matched_internal_proof_assets": matched_internal_assets,
        "proposed_service_mappings": service_mappings,
        "human_review_context": {
            "human_approved": human_approved,
            "human_feedback": human_feedback,
            "custom_selected_assets": custom_selected_assets,
        },
    }

    # =========================================================================
    # 2. LLM INVOCATION WITH SYSTEM PROMPT & STRUCTURED OUTPUT
    # =========================================================================
    system_prompt = """You are an Executive Sales Strategist and Principal Advisory Consultant.

YOUR GOAL:
Synthesize all collected intelligence—company financials, executive personas, compliance mandates, pain points, matched case studies, and service mappings—into a high-stakes, executive-ready CXO Meeting Strategy Brief.

INSIGHT & TONE RULES:
1. EXECUTIVE TONE: Write directly, sharply, and value-oriented. Avoid sales fluff or generic generalities.
2. TAILORED TALKING POINTS: Generate talking points that align specifically with identified executive personas (e.g., frame ROI for CFO, technical velocity for CIO, operational resilience for CISO/COO).
3. SHARP DISCOVERY QUESTIONS: Formulate high-leverage strategic questions that surface budget timelines, decision governance, and validate root-cause pain points.
4. OBJECTION HANDLING: Map anticipated CXO pushbacks (e.g., 'In-house capabilities are sufficient', 'High migration risk') to clear, evidence-backed counter-responses referencing our matched case studies.
5. 60-SECOND PITCH: Synthesize a concise elevator pitch covering target pain points, recommended solution architecture, and proven business metrics.
6. HUMAN FEEDBACK INTEGRATION: If human feedback or custom assets are present in 'human_review_context', explicitly reflect those directions in the brief."""

    human_message_content = f"""
COMPLETE DEAL INTELLIGENCE DATA:
{json.dumps(aggregated_context, indent=2)}

Synthesize this intelligence into the final CXO Meeting Strategy Brief matching the required schema.
"""

    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.2,
            google_api_key=GEMINI_API_KEY
        )

        
        # Inject dynamic instructions if present
        final_system_prompt = apply_instruction_context_to_prompt(system_prompt, get_injection_context(state))

        structured_llm = llm.with_structured_output(MeetingStrategySchema)

        result: MeetingStrategySchema = structured_llm.invoke([
            SystemMessage(content=final_system_prompt),
            HumanMessage(content=human_message_content)
        ])

        executive_brief_dict = result.model_dump()

        logger.info(f"Successfully generated CXO Executive Brief for '{target_company}'")

        return {
            "cxo_executive_brief": executive_brief_dict,
            "node_statuses": {"cxo_brief": "COMPLETED"},
            "_instructions_applied": True
        }

    except Exception as e:
        logger.error(f"Error in CXO Brief Generator Node: {str(e)}", exc_info=True)
        return {
            "errors": [f"CXO Brief Generator Node failed: {str(e)}"],
            "node_statuses": {"cxo_brief": "COMPLETED"}

        }