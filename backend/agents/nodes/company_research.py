import logging
import json
from typing import Dict, Any

from backend.agents.nodes.node_middleware import (
    apply_instruction_context_to_prompt, 
    get_injection_context, 
    inject_dynamic_instructions
)
from backend.app.core.config import settings  # Assuming settings export
from backend.agents.tools.financial_tool import get_company_financials
from backend.agents.tools.search_tool import search_news, search_web

# Import the state and strict Pydantic schema exactly as defined in your architecture
from app.agents.state import DealIntelligenceState
from backend.app.schemas.node_1_company import CompanyResearchSchema

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)
GEMINI_API_KEY = settings.GEMINI_API_KEY


@inject_dynamic_instructions
def company_research_node(state: DealIntelligenceState) -> Dict[str, Any]:
    """
    Agent 1: Company Research & Financials Agent
    Performs 5-tier intelligence collection and generates a unified CompanyResearchSchema.
    """
    target_company = state.get("target_company", "")
    target_industry = state.get("target_industry", "")
    
    logger.info(f"Starting Company Research Node for: {target_company} ({target_industry})")

    # =========================================================================
    # 1. MULTI-TIER DATA EXTRACTION (Financials, Web, and News)
    # =========================================================================
    
    # Tier 1: Financial Data via yfinance
    logger.info(f"Fetching financial data for ticker/company: {target_company}")
    financial_data = get_company_financials(target_company)

    # Tier 2: Business Model & Revenue Streams Search
    query_overview = f"{target_company} business model revenue streams key divisions target market profile"
    overview_results = search_web(query_overview, max_results=4)

    # Tier 3: Digital & Technology Investments Search
    query_tech = f"{target_company} digital transformation tech stack cloud migration AI investments IT budget"
    tech_results = search_web(query_tech, max_results=4)

    # Tier 4: Leadership Team Search
    query_leadership = f"{target_company} C-suite executives CEO CIO CTO CFO CISO background leadership team"
    leadership_results = search_web(query_leadership, max_results=3)

    # Tier 5: Latest News, Press Releases, & M&A Search
    query_news = f"{target_company} acquisition merger strategic partnership product launch latest news"
    news_results = search_news(query_news, max_results=5)

    raw_context = {
        "financial_summary": financial_data,
        "overview_sources": overview_results,
        "tech_sources": tech_results,
        "leadership_sources": leadership_results,
        "latest_news_and_m_and_a_sources": news_results
    }

    # =========================================================================
    # 2. LLM INVOCATION WITH SYSTEM PROMPT & STRUCTURED OUTPUT
    # =========================================================================
    
    system_prompt = """You are an Elite Enterprise Strategy & Financial Intelligence Analyst preparing an executive briefing for a C-suite deal pitch.

YOUR GOAL:
Extract maximum, highly granular, verifiable intelligence on the target company using ONLY the provided research context. Do NOT write high-level generic statements. Include specific monetary figures, technology names, vendor names, partner names, operational metrics, and dates whenever present.

DATA DENSITY & UI FORMATTING RULES:
1. Every major point across profile, business model, revenue streams, tech investments, digital initiatives, and news MUST follow this exact UI hierarchy:
   - headline: A short, punchy summary title (5-10 words).
   - detailed_narrative: 2-4 dense sentences explaining the mechanism, strategic impact, monetary figures, or operational context.
   - citations: Include list of references mapping title, url, snippet excerpt, and source_type ('WEB_NEWS', '10K_FILING', 'FINANCIAL_API', 'WEB_SEARCH') directly from the context.
2. Embed explicit financial figures (Revenue, Market Cap, Growth Rates, Margins) from the financial summary or news into narratives.
3. Extract C-suite leaders (CEO, CIO, CTO, CFO, CISO) with exact names, roles, and key strategic priorities/backgrounds.
4. Extract explicit technology choices (e.g., AWS, Azure, SAP S/4HANA, Salesforce, Snowflake) and digital roadmap items.
5. Highlight recent M&A, partnerships, and press releases with accurate context."""

    human_message_content = f"""
TARGET COMPANY: {target_company}
TARGET INDUSTRY: {target_industry}

RESEARCH CONTEXT DATA:
{json.dumps(raw_context, indent=2)}

Synthesize the data into the required structured schema. Make sure every single field is populated with maximum precision and explicit source citations.
"""

    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.1,
            google_api_key=GEMINI_API_KEY
        )

        # Inject dynamic instructions via middleware mapping
        final_system_prompt = apply_instruction_context_to_prompt(system_prompt, get_injection_context(state))

        # Enforce structured Pydantic output matching CompanyResearchSchema
        structured_llm = llm.with_structured_output(CompanyResearchSchema)
        
        # Invoke the chain; 'result' is strictly validated against CompanyResearchSchema
        result: CompanyResearchSchema = structured_llm.invoke([
            SystemMessage(content=final_system_prompt),
            HumanMessage(content=human_message_content)
        ])

        logger.info(f"Successfully completed Company Research Node for {target_company}")

        # =========================================================================
        # 3. RETURN UPDATED LANGGRAPH STATE
        # =========================================================================
        # Return maps exactly to DealIntelligenceState structure
        return {
            "company_research": result, 
            "node_statuses": {"company_research": "COMPLETED"}
        }

    except Exception as e:
        logger.error(f"Error in Company Research Node: {str(e)}", exc_info=True)
        return {
            "errors": [f"Company Research Node failed: {str(e)}"],
            "node_statuses": {"company_research": "FAILED"}
        }