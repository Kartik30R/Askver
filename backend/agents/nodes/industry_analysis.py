import os
import json
import logging
from typing import Dict, Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.state import DealIntelligenceState
from app.agents.tools.search_tool import search_web, search_news
from app.schemas.deal_intelligence import IndustryAnalysisSchema
from app.agents.node_middleware import inject_dynamic_instructions, get_injection_context, apply_instruction_context_to_prompt

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


@inject_dynamic_instructions
def industry_analysis_node(state: DealIntelligenceState) -> Dict[str, Any]:
    """
    Agent 3: Industry Intelligence & Compliance Agent
    Performs 4-tier industry search sweeps (Macro Trends, Regulatory Mandates, 
    Cyber/Operational Risks, and IT/Cloud Benchmarks) and outputs structured 
    analysis with verified citations.
    """
    target_company = state.get("target_company", "")
    target_industry = state.get("target_industry", "")
    meeting_objective = state.get("meeting_objective", "")
    company_overview = state.get("company_overview", {})

    logger.info(f"Starting Industry Analysis Node for industry: '{target_industry}' (Company: '{target_company}')")

    # =========================================================================
    # 1. GEOGRAPHIC & SUB-SECTOR CONTEXT EXTRACTION FROM NODE 1 STATE
    # =========================================================================
    # Attempt to extract operating region or country context from company overview narrative
    company_profile_narrative = ""
    if isinstance(company_overview, dict) and "profile" in company_overview:
        profile_data = company_overview.get("profile", {})
        if isinstance(profile_data, dict):
            company_profile_narrative = profile_data.get("detailed_narrative", "")

    # =========================================================================
    # 2. 4-TIER INDUSTRY & COMPLIANCE SEARCH SWEEPS
    # =========================================================================
    
    # Tier 1: Macro Trends & Technological Disruption
    query_trends = f"{target_industry} industry key technology trends market disruption 2025 2026"
    trends_results = search_web(query_trends, max_results=4)

    # Tier 2: Regulatory & Compliance Mandates
    query_compliance = f"{target_industry} regulatory compliance mandates rules requirements DORA RBI SEC GDPR PCI-DSS"
    compliance_results = search_web(query_compliance, max_results=4)

    # Tier 3: Cybersecurity, Operational Risks, and Fraud Vectors
    query_risks = f"{target_industry} cybersecurity threats fraud risks operational resilience challenges"
    risks_results = search_web(query_risks, max_results=3)

    # Tier 4: Cloud & IT Spending Benchmarks
    query_benchmarks = f"{target_industry} cloud adoption rate average IT budget spend benchmarks modernization"
    benchmarks_results = search_web(query_benchmarks, max_results=3)

    # Consolidate raw search context for the LLM
    raw_context = {
        "company_context_summary": company_profile_narrative,
        "macro_trends_sources": trends_results,
        "regulatory_compliance_sources": compliance_results,
        "risks_and_challenges_sources": risks_results,
        "technology_benchmarks_sources": benchmarks_results
    }

    # =========================================================================
    # 3. LLM INVOCATION WITH SYSTEM PROMPT & STRUCTURED OUTPUT
    # =========================================================================

    system_prompt = """You are an Enterprise Industry Analyst and Regulatory Compliance Strategist.

YOUR GOAL:
Analyze the target industry, geographic operational context, meeting objective, and search context to extract macro sector trends, regulatory mandates, operational risks, and technology adoption benchmarks.

INSIGHT QUALITY & UI FORMATTING RULES:
1. Every item across major_trends, regulatory_compliance, risks_and_challenges, and technology_benchmarks MUST adhere to this UI structure:
   - headline: A short, punchy summary title (5-10 words).
   - detailed_narrative: 2-4 dense sentences detailing market shifts, compliance mandates, penalty risks, or benchmark metrics.
   - citations: Mapped list of source titles, URLs, snippet excerpts, and source_type ('WEB_NEWS', 'REGULATORY_DOC', 'WEB_SEARCH') extracted directly from context.
2. Explicitly name regulatory frameworks and governing bodies applicable to the industry and region (e.g., DORA, RBI Cybersecurity Framework, PCI-DSS 4.0, HIPAA, SEC Rules, Open Banking standards).
3. Include explicit compliance deadlines, penalty risks, risk percentages, and average industry IT spending figures whenever present in the search context.
4. Connect broader industry pressures directly to operational friction points the target company faces."""

    human_message_content = f"""
TARGET COMPANY: {target_company}
TARGET INDUSTRY: {target_industry}
MEETING OBJECTIVE: {meeting_objective}

INDUSTRY RESEARCH CONTEXT:
{json.dumps(raw_context, indent=2)}

Synthesize the data into the required structured schema. Ensure every list field (major_trends, regulatory_compliance, risks_and_challenges, technology_benchmarks) contains detailed points with verified citations.
"""

    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.1,
            google_api_key=GEMINI_API_KEY
        )

        # Inject dynamic instructions if present
        final_system_prompt = apply_instruction_context_to_prompt(system_prompt, get_injection_context(state))

        structured_llm = llm.with_structured_output(IndustryAnalysisSchema)

        result: IndustryAnalysisSchema = structured_llm.invoke([
            SystemMessage(content=final_system_prompt),
            HumanMessage(content=human_message_content)
        ])

        result_dict = result.model_dump()

        logger.info(f"Successfully completed Industry Analysis Node for '{target_industry}'")

        return {
            "industry_analysis": result_dict,
            "node_statuses": {"industry_analysis": "COMPLETED"},
            "_instructions_applied": True
        }

    except Exception as e:
        logger.error(f"Error in Industry Analysis Node: {str(e)}", exc_info=True)
        return {
            "errors": [f"Industry Analysis Node failed: {str(e)}"],
            "node_statuses": {"industry_analysis": "FAILED"}
        }