import logging
import json
from typing import Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from backend.agents.nodes.node_middleware import apply_instruction_context_to_prompt, get_injection_context, inject_dynamic_instructions
from backend.agents.state import DealIntelligenceState
from backend.agents.tools.financial_tool import build_private_company_search_queries, get_company_financials
from backend.agents.tools.search_tool import search_news, search_web
from backend.app.core.config import settings

# Import strict schema
from backend.app.schemas.node_1b_financial import FinancialIntelligenceSchema

logger = logging.getLogger(__name__)


@inject_dynamic_instructions
def financial_intelligence_node(state: DealIntelligenceState) -> Dict[str, Any]:
    target_company = state.get("target_company", "")
    target_industry = state.get("target_industry", "General Industry")
    
    logger.info(f"Starting AI Financial Intelligence Node for: {target_company} ({target_industry})")

    # 1. Fetch raw data
    financial_raw = get_company_financials(target_company)
    search_context = []

    # 2. If private/unlisted, perform web search fallback
    if financial_raw.get("availability") == "unavailable":
        logger.info(f"{target_company} is private. Running web financial discovery.")
        queries = build_private_company_search_queries(target_company)
        for q in queries[:3]:
            search_context.extend(search_web(q, max_results=2))
        search_context.extend(search_news(f"{target_company} revenue profit valuation risks", max_results=3))

    # 3. LLM Industry-Relative Scoring Prompt
    system_prompt = f"""You are a Senior Equity Research Analyst & Financial Modeling AI.

TASK:
Analyze the target company's financials relative to its target industry benchmarks ({target_industry}) and market cap tier.

SCORING INSTRUCTIONS:
- Evaluate metrics (e.g., P/E ratio, Revenue Growth, Margins, Debt) based on current INDUSTRY MEDIANS and typical valuation multiples for {target_industry}.
- Assign scores out of 10 for key metrics (e.g., "7/10") and 0-100 overall scores.
- Provide concise 1-sentence rationales explaining why the score was given relative to the industry median.
- Extract explicit Financial Concerns & Risks.

STRICT GUARDRAILS:
- Do NOT invent financial numbers if they are not present in the raw data or search context.
- Populate the output strictly according to the required schema."""

    human_prompt = f"""
TARGET COMPANY: {target_company}
TARGET INDUSTRY: {target_industry}
RAW FINANCIAL DATA: {json.dumps(financial_raw, indent=2)}
PRIVATE RESEARCH CONTEXT: {json.dumps(search_context, indent=2)}

Synthesize the data into the requested schema. Make sure to extract metrics, assign relative scores, and identify financial concerns.
"""

    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.0,
            google_api_key=settings.GEMINI_API_KEY
        )
        
        # Apply dynamic instructions
        final_system_prompt = apply_instruction_context_to_prompt(system_prompt, get_injection_context(state))

        # Enforce structured output to match FinancialIntelligenceSchema
        structured_llm = llm.with_structured_output(FinancialIntelligenceSchema)
        
        result: FinancialIntelligenceSchema = structured_llm.invoke([
            SystemMessage(content=final_system_prompt),
            HumanMessage(content=human_prompt)
        ])

        # State updates: return the Pydantic object directly
        return {
            "financial_intelligence": result,
            "node_statuses": {"financial_intelligence": "COMPLETED"},
            "_instructions_applied": True
        }

    except Exception as e:
        logger.error(f"Error in Financial Intelligence Node: {str(e)}", exc_info=True)
        return {
            "errors": [f"Financial Intelligence Node failed: {str(e)}"],
            "node_statuses": {"financial_intelligence": "FAILED"}
        }