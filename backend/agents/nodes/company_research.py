import os
import json
import logging
from typing import Dict, Any, List

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.state import DealIntelligenceState
from app.agents.tools.financial_tool import get_company_financials
from app.agents.tools.search_tool import search_web, search_news
from app.schemas.deal_intelligence import CompanyResearchSchema

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def company_research_node(state: DealIntelligenceState) -> Dict[str, Any]:
    """
    Agent 1: Company Research & Financials Agent
    Performs 5-tier intelligence collection (Financials, Business Model, Tech Stack,
    Leadership, and Real-Time News/M&A) and generates structured JSON output.
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

    # Consolidate raw search context for the LLM
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

        # Enforce structured Pydantic output matching CompanyResearchSchema
        structured_llm = llm.with_structured_output(CompanyResearchSchema)
        
        result: CompanyResearchSchema = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_message_content)
        ])

        # Convert Pydantic object to Dict format for LangGraph state persistence
        result_dict = result.model_dump()

        logger.info(f"Successfully completed Company Research Node for {target_company}")

        # =========================================================================
        # 3. RETURN UPDATED LANGGRAPH STATE
        # =========================================================================
        return {
            "company_overview": result_dict.get("overview", {}),
            "leadership_team": result_dict.get("leadership_team", []),
            "digital_initiatives": result_dict.get("digital_initiatives", []),
            "technology_investments": result_dict.get("technology_investments", []),
            "recent_news_and_m_and_a": result_dict.get("recent_news_and_m_and_a", []),
            "current_step": "COMPANY_RESEARCH_COMPLETED"
        }

    except Exception as e:
        logger.error(f"Error in Company Research Node: {str(e)}", exc_info=True)
        return {
            "errors": [f"Company Research Node failed: {str(e)}"],
            "current_step": "COMPANY_RESEARCH_FAILED"
        }