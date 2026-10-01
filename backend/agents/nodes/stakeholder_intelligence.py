import logging
import json
from typing import Dict, Any, List

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from backend.agents.nodes.node_middleware import apply_instruction_context_to_prompt, get_injection_context, inject_dynamic_instructions
from backend.agents.state import DealIntelligenceState
from backend.agents.tools.search_tool import search_web
from backend.app.core.config import settings

# Import strict schema
from backend.app.schemas.node_2_stakeholder import StakeholderIntelligenceSchema

logger = logging.getLogger(__name__)


@inject_dynamic_instructions
def stakeholder_intelligence_node(state: DealIntelligenceState) -> Dict[str, Any]:
    """
    Agent 2: Stakeholder Persona Intelligence Agent (Sequential)
    Reads 'leadership_team' populated by Node 1 to perform targeted executive-level
    searches, mapping hyper-personalized C-Suite buyer personas.
    """
    target_company = state.get("target_company", "")
    target_industry = state.get("target_industry", "")
    meeting_objective = state.get("meeting_objective", "")
    
    # Safely extract leadership team from Node 1's Pydantic output
    company_research = state.get("company_research")
    leadership_team = company_research.leadership_team if company_research else []

    logger.info(
        f"Starting Sequential Stakeholder Intelligence Node for: {target_company} "
        f"with {len(leadership_team)} identified leaders."
    )

    # =========================================================================
    # 1. NAME-SPECIFIC & ROLE-SPECIFIC TARGETED SEARCH SWEEPS
    # =========================================================================
    exec_search_context = []
    
    if leadership_team:
        for leader in leadership_team[:5]: 
            # Because leader is a LeadershipMemberSchema Pydantic object now
            name = leader.name
            role = leader.role
            background = leader.background or ""
            
            if name:
                query = f'"{name}" "{target_company}" {role} strategic priorities vision quotes'
                results = search_web(query, max_results=2)
                exec_search_context.append({
                    "executive_name": name,
                    "role": role,
                    "background_from_node1": background,
                    "search_results": results
                })

    query_broad_tech = f"{target_company} CIO CTO CISO technology roadmap budget priorities"
    query_broad_growth = f"{target_company} CEO CFO strategic growth margin expansion initiatives"
    
    broad_tech_results = search_web(query_broad_tech, max_results=3)
    broad_growth_results = search_web(query_broad_growth, max_results=3)

    raw_context = {
        # Serializing Pydantic list to dict for JSON compatibility in the prompt
        "identified_leadership_team": [l.model_dump() for l in leadership_team],
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
1. Whenever an executive's name and background are available in the context, EXPLICITLY reference them in their persona profile.
2. Ground goals, concerns, and business drivers in the specific meeting objective.
3. Avoid generic statements. Specify exact operational levers.
4. Generate actionable, high-density outputs strictly conforming to the requested schema."""

    human_message_content = f"""
TARGET COMPANY: {target_company}
TARGET INDUSTRY: {target_industry}
MEETING OBJECTIVE: {meeting_objective}

IDENTIFIED LEADERSHIP TEAM & RESEARCH CONTEXT:
{json.dumps(raw_context, indent=2)}

Generate hyper-personalized persona profiles strictly matching the StakeholderIntelligenceSchema.
"""

    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.2,
            google_api_key=settings.GEMINI_API_KEY
        )

        final_system_prompt = apply_instruction_context_to_prompt(system_prompt, get_injection_context(state))

        # Enforce structured output matching the schema
        structured_llm = llm.with_structured_output(StakeholderIntelligenceSchema)

        result: StakeholderIntelligenceSchema = structured_llm.invoke([
            SystemMessage(content=final_system_prompt),
            HumanMessage(content=human_message_content)
        ])

        logger.info(f"Successfully completed Sequential Stakeholder Intelligence Node for {target_company}")

        # Return Pydantic object mapping exactly to state.py
        return {
            "stakeholder_intelligence": result,
            "node_statuses": {"stakeholder_intelligence": "COMPLETED"},
            "_instructions_applied": True
        }

    except Exception as e:
        logger.error(f"Error in Stakeholder Intelligence Node: {str(e)}", exc_info=True)
        return {
            "errors": [f"Stakeholder Intelligence Node failed: {str(e)}"],
            "node_statuses": {"stakeholder_intelligence": "FAILED"}
        }