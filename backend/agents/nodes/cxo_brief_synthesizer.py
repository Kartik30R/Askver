import logging
import json
from typing import Dict, Any

from agents.nodes.node_middleware import apply_instruction_context_to_prompt, get_injection_context, inject_dynamic_instructions
from agents.state import DealIntelligenceState
from app.core.config import settings
from app.schemas.node_7_brief import MeetingStrategySchema
from app.services.llm_provider import get_llm

from langchain_core.messages import SystemMessage, HumanMessage


logger = logging.getLogger(__name__)


def _extract_headline_narrative(detailed_point) -> Dict[str, str]:
    """Extract headline and narrative from DetailedPoint, omitting citations."""
    if hasattr(detailed_point, 'headline'):
        return {
            "headline": detailed_point.headline,
            "narrative": detailed_point.detailed_narrative
        }
    elif isinstance(detailed_point, dict):
        return {
            "headline": detailed_point.get("headline", ""),
            "narrative": detailed_point.get("detailed_narrative", "")
        }
    return {}


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
    financial_intel = state.get("financial_intelligence")

    # Human-in-the-loop review overrides
    human_approved = state.get("human_approved", False)
    human_feedback = state.get("human_feedback", None)
    custom_selected_assets = state.get("custom_selected_assets", [])

    logger.info(f"Starting CXO Brief Generator Node for: '{target_company}'")

    # Helper: Strip citations from company research
    def strip_company_citations(cr):
        if not cr:
            return {}
        cr_dict = cr.model_dump() if hasattr(cr, 'model_dump') else cr
        return {
            "overview": {
                "summary": _extract_headline_narrative(cr_dict["overview"]["summary"]),
                "business_model": _extract_headline_narrative(cr_dict["overview"]["business_model"]),
                "revenue_streams": [_extract_headline_narrative(rs) for rs in cr_dict["overview"].get("revenue_streams", [])],
                "employee_count_estimate": cr_dict["overview"].get("employee_count_estimate"),
                "headquarters": cr_dict["overview"].get("headquarters"),
            },
            "leadership_team": cr_dict.get("leadership_team", []),
            "digital_initiatives": cr_dict.get("digital_initiatives", []),
            "technology_investments": cr_dict.get("technology_investments", []),
            "recent_news_and_m_and_a": [
                {"headline": item.get("headline", ""), "category": item.get("category", ""), 
                 "details": _extract_headline_narrative(item.get("details", {}))}
                for item in cr_dict.get("recent_news_and_m_and_a", [])
            ],
        }

    # Helper: Strip citations from industry analysis
    def strip_industry_citations(ia):
        if not ia:
            return {}
        ia_dict = ia.model_dump() if hasattr(ia, 'model_dump') else ia
        return {
            "major_trends": [_extract_headline_narrative(t) for t in ia_dict.get("major_trends", [])],
            "regulatory_compliance": [_extract_headline_narrative(r) for r in ia_dict.get("regulatory_compliance", [])],
            "risks_and_challenges": [_extract_headline_narrative(r) for r in ia_dict.get("risks_and_challenges", [])],
            "technology_benchmarks": [_extract_headline_narrative(t) for t in ia_dict.get("technology_benchmarks", [])],
        }

    # Helper: Strip citations from service mappings
    def strip_mapping_citations(mappings):
        out = []
        for sm in mappings or []:
            d = sm.model_dump() if hasattr(sm, "model_dump") else sm
            out.append({
                "client_need": d.get("client_need", ""),
                "detected_bottleneck": d.get("detected_bottleneck", ""),
                "recommended_offering": d.get("recommended_offering", ""),
                "expected_business_impact": d.get("expected_business_impact", ""),
                "supporting_proof_assets": [
                    {"asset_id": a.get("asset_id"), "asset_name": a.get("asset_name"),
                     "key_metrics_achieved": a.get("key_metrics_achieved", [])}
                    for a in d.get("supporting_proof_assets") or []
                ],
            })
        return out

    aggregated_context = {
        "deal_inputs": {
            "target_company": target_company,
            "target_industry": target_industry,
            "meeting_objective": meeting_objective,
        },
       
        "company_research": strip_company_citations(company_research),
        "financial_intelligence": financial_intel.model_dump() if financial_intel else {},
        "stakeholder_personas": stakeholder_intel.model_dump() if stakeholder_intel else {},
        "industry_and_compliance": strip_industry_citations(industry_analysis),
        "strategic_priorities_and_pain_points": priorities_and_pain_points.model_dump() if priorities_and_pain_points else {},
        "matched_internal_proof_assets": [
            {"asset_id": a.get("asset_id") if isinstance(a, dict) else getattr(a, 'asset_id', None),
             "asset_name": a.get("asset_name") if isinstance(a, dict) else getattr(a, 'asset_name', None),
             "asset_type": a.get("asset_type") if isinstance(a, dict) else getattr(a, 'asset_type', None)}
            for a in matched_internal_assets
        ],
        "proposed_service_mappings": strip_mapping_citations(service_mappings),
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
{json.dumps(aggregated_context, separators=(',', ':'), default=str)}

Synthesize this intelligence into the final CXO Meeting Strategy Brief.
"""

    try:
        llm = get_llm(
            model=settings.LLM_MODEL or "gemini-2.0-flash",
            provider=settings.LLM_PROVIDER or "gemini",
            temperature=0.2,
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