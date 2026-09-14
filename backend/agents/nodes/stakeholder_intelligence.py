import os
import json
import logging
from typing import Dict, Any, List

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.state import DealIntelligenceState
from app.agents.tools.search_tool import search_web
from app.schemas.deal_intelligence import StakeholderIntelligenceSchema
from app.agents.node_middleware import inject_dynamic_instructions, get_injection_context, apply_instruction_context_to_prompt

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


@inject_dynamic_instructions
def stakeholder_intelligence_node(state: DealIntelligenceState) -> Dict[str, Any]:
    """
    Agent 2: Stakeholder Persona Intelligence Agent (Sequential)
    Reads 'leadership_team' populated by Node 1 to perform targeted executive-level
    searches, mapping hyper-personalized C-Suite buyer personas (CEO, CIO, CTO, CDO, CISO, CFO).
    """
    target_company = state.get("target_company", "")
    target_industry = state.get("target_industry", "")
    meeting_objective = state.get("meeting_objective", "")
    leadership_team: List[Dict[str, str]] = state.get("leadership_team", [])

    logger.info(
        f"Starting Sequential Stakeholder Intelligence Node for: {target_company} "
        f"with {len(leadership_team)} identified leaders."
    )

    # =========================================================================
    # 1. NAME-SPECIFIC & ROLE-SPECIFIC TARGETED SEARCH SWEEPS
    # =========================================================================
    
    # Build query strings referencing specific named executives if present
    exec_search_context = []
    
    if leadership_team:
        for leader in leadership_team[:5]:  # Focus on top 5 identified executives
            name = leader.get("Name", "") or leader.get("name", "")
            role = leader.get("Role", "") or leader.get("role", "")
            if name:
                query = f'"{name}" "{target_company}" {role} strategic priorities vision quotes'
                results = search_web(query, max_results=2)
                exec_search_context.append({
                    "executive_name": name,
                    "role": role,
                    "background_from_node1": leader.get("Key Background", "") or leader.get("background", ""),
                    "search_results": results
                })

    # General fallback sweeps if specific executive searches yielded minimal context
    query_broad_tech = f"{target_company} CIO CTO CISO technology roadmap budget priorities"
    query_broad_growth = f"{target_company} CEO CFO strategic growth margin expansion initiatives"
    
    broad_tech_results = search_web(query_broad_tech, max_results=3)
    broad_growth_results = search_web(query_broad_growth, max_results=3)

    raw_context = {
        "identified_leadership_team": leadership_team,
        "named_executive_deep_dives": exec_search_context,
        "broad_tech_context": broad_tech_results,
        "broad_growth_context": broad_growth_results
    }

    # =========================================================================
    # 2. LLM INVOCATION WITH SYSTEM PROMPT & STRUCTURED OUTPUT
    # =========================================================================

    system_prompt = """You are an Executive Sales Strategist and Enterprise Buyer Intelligence Specialist.

YOUR GOAL:
Analyze the target company, industry context, meeting objective, identified executive leaders, and search context to generate tailored C-Suite Persona Profiles for six core leadership roles: CEO, CIO, CTO, CDO, CISO, and CFO.

HYPER-PERSONALIZATION RULES:
1. Whenever an executive's name and background are available in the leadership team data, EXPLICITLY reference their name, background, and known strategic focus in their respective persona profile.
2. Ground goals, concerns, and business drivers in the target company's current operating environment and the SPECIFIC MEETING OBJECTIVE.
3. Avoid generic statements (e.g., avoid "wants cost reduction"). Specify exact operational levers (e.g., "seeking to compress cloud infrastructure spend and eliminate dual-licensing during legacy platform migration").
4. Connect each persona's concerns directly to deal implementation risks, integration complexity, or organizational friction.
5. Generate actionable, high-density outputs for all six personas (CEO, CIO, CTO, CDO, CISO, CFO)."""

    human_message_content = f"""
TARGET COMPANY: {target_company}
TARGET INDUSTRY: {target_industry}
MEETING OBJECTIVE: {meeting_objective}

IDENTIFIED LEADERSHIP TEAM & RESEARCH CONTEXT:
{json.dumps(raw_context, indent=2)}

Generate hyper-personalized persona profiles for CEO, CIO, CTO, CDO, CISO, and CFO matching the required schema.
"""

    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.2,
            google_api_key=GEMINI_API_KEY
        )

        # Inject dynamic instructions if present
        final_system_prompt = apply_instruction_context_to_prompt(system_prompt, get_injection_context(state))

        structured_llm = llm.with_structured_output(StakeholderIntelligenceSchema)

        result: StakeholderIntelligenceSchema = structured_llm.invoke([
            SystemMessage(content=final_system_prompt),
            HumanMessage(content=human_message_content)
        ])

        # Format output dictionary to match DealIntelligenceState structure
        personas_list = result.model_dump().get("personas", [])
        formatted_stakeholder_profiles: Dict[str, Dict[str, Any]] = {}

        for p in personas_list:
            role_key = p.get("role", "").upper()
            formatted_stakeholder_profiles[role_key] = {
                "likely_goals": p.get("likely_goals", []),
                "likely_concerns": p.get("likely_concerns", []),
                "business_drivers": p.get("business_drivers", [])
            }

        logger.info(f"Successfully completed Sequential Stakeholder Intelligence Node for {target_company}")

        return {
            "stakeholder_profiles": formatted_stakeholder_profiles,
            "node_statuses": {"stakeholder_intelligence": "COMPLETED"},
            "_instructions_applied": True
        }

    except Exception as e:
        logger.error(f"Error in Stakeholder Intelligence Node: {str(e)}", exc_info=True)
        return {
            "errors": [f"Stakeholder Intelligence Node failed: {str(e)}"],
            "node_statuses": {"stakeholder_intelligence": "FAILED"}
        }