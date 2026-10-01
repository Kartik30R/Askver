import logging
import json
from typing import Dict, Any

from backend.agents.nodes.node_middleware import apply_instruction_context_to_prompt, get_injection_context, inject_dynamic_instructions
from backend.agents.state import DealIntelligenceState
from backend.app.core.config import settings

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from backend.app.schemas.deal_intelligence import MeetingStrategySchema

logger = logging.getLogger(__name__)


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

    # Retrieve Pydantic models from previous nodes
    company_research = state.get("company_research")
    stakeholder_intel = state.get("stakeholder_intelligence")
    industry_analysis = state.get("industry_analysis")
    priorities_and_pain_points = state.get("priorities_and_pain_points")
    matched_internal_assets = state.get("matched_internal_assets", [])
    service_mappings = state.get("service_mappings", [])

    # Human-in-the-loop review overrides
    human_approved = state.get("human_approved", False)
    human_feedback = state.get("human_feedback", None)
    custom_selected_assets = state.get("custom_selected_assets", [])

    logger.info(f"Starting CXO Brief Generator Node for: '{target_company}'")

    aggregated_context = {
        "deal_inputs": {
            "target_company": target_company,
            "target_industry": target_industry,
            "meeting_objective": meeting_objective,
        },
        "company_research": company_research.model_dump() if company_research else {},
        "stakeholder_personas": stakeholder_intel.model_dump() if stakeholder_intel else {},
        "industry_and_compliance": industry_analysis.model_dump() if industry_analysis else {},
        "strategic_priorities_and_pain_points": priorities_and_pain_points.model_dump() if priorities_and_pain_points else {},
        "matched_internal_proof_assets": [a.model_dump() if hasattr(a, 'model_dump') else a for a in matched_internal_assets],
        "proposed_service_mappings": [sm.model_dump() if hasattr(sm, 'model_dump') else sm for sm in service_mappings],
        "human_review_context": {
            "human_approved": human_approved,
            "human_feedback": human_feedback,
            "custom_selected_assets": custom_selected_assets,
        },
    }

    system_prompt = """You are an Executive Sales Strategist and Principal Advisory Consultant.

YOUR GOAL:
Synthesize all collected intelligence into a high-stakes, executive-ready CXO Meeting Strategy Brief.

INSIGHT & TONE RULES:
1. EXECUTIVE TONE: Write directly, sharply, and value-oriented. Avoid sales fluff.
2. TAILORED TALKING POINTS: Generate talking points that align specifically with identified executive personas.
3. SHARP DISCOVERY QUESTIONS: Formulate high-leverage strategic questions.
4. OBJECTION HANDLING: Map anticipated CXO pushbacks to clear, evidence-backed counter-responses.
5. 60-SECOND PITCH: Synthesize a concise elevator pitch.
6. HUMAN FEEDBACK INTEGRATION: If human feedback or custom assets are present, explicitly reflect those directions."""

    human_message_content = f"""
COMPLETE DEAL INTELLIGENCE DATA:
{json.dumps(aggregated_context, indent=2)}

Synthesize this intelligence into the final CXO Meeting Strategy Brief.
"""

    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.2,
            google_api_key=settings.GEMINI_API_KEY
        )

        final_system_prompt = apply_instruction_context_to_prompt(system_prompt, get_injection_context(state))
        structured_llm = llm.with_structured_output(MeetingStrategySchema)

        result: MeetingStrategySchema = structured_llm.invoke([
            SystemMessage(content=final_system_prompt),
            HumanMessage(content=human_message_content)
        ])

        logger.info(f"Successfully generated CXO Executive Brief for '{target_company}'")

        return {
            "cxo_executive_brief": result,
            "node_statuses": {"cxo_brief": "COMPLETED"},
            "_instructions_applied": True
        }

    except Exception as e:
        logger.error(f"Error in CXO Brief Generator Node: {str(e)}", exc_info=True)
        return {
            "errors": [f"CXO Brief Generator Node failed: {str(e)}"],
            "node_statuses": {"cxo_brief": "FAILED"}
        }