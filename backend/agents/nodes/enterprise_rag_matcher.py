import os
import json
import logging
from typing import Dict, Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field

from app.agents.state import DealIntelligenceState
from app.schemas.deal_intelligence import MatchedAssetSchema
from app.services.vector_service import query_internal_knowledge_base
from app.agents.node_middleware import inject_dynamic_instructions, get_injection_context, apply_instruction_context_to_prompt

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

class AssetExtractionWrapper(BaseModel):
    matched_assets: list[MatchedAssetSchema]

@inject_dynamic_instructions
def enterprise_rag_matcher_node(state: DealIntelligenceState) -> Dict[str, Any]:
    """
    Agent 5: Enterprise Knowledge RAG Matcher
    Takes detected pain points from Node 4 and searches the global company IP 
    vector store to find highly relevant Case Studies, Proposals, and SoWs.
    """
    target_industry = state.get("target_industry", "")
    detected_pain_points = state.get("detected_pain_points", [])

    logger.info(f"Starting Enterprise RAG Matcher Node for industry: {target_industry}")

    raw_retrieved_assets = []

    # Query PGVector based on the specific pain points identified in Node 4
    for point in detected_pain_points:
        query_text = f"{point.get('category', '')}: {point.get('description', '')}"
        
        # Pull top 3 matching internal case studies/proposals for this specific pain point
        results = query_internal_knowledge_base(
            query=query_text,
            industry_filter=target_industry if target_industry else None,
            top_k=3
        )
        raw_retrieved_assets.extend(results)

    # Deduplicate raw retrieved assets by vector_doc_id or content
    unique_assets = {}
    for asset in raw_retrieved_assets:
        content = asset.get("content", "")
        if content not in unique_assets:
            unique_assets[content] = asset

    if not unique_assets:
        logger.warning("No internal assets matched the deal requirements.")
        return {
            "matched_internal_assets": [],
            "current_step": "ENTERPRISE_RAG_COMPLETED"
        }

    # Use LLM to evaluate the relevance of the retrieved chunks and format them cleanly
    system_prompt = """You are an Enterprise Solutions Architect.
YOUR GOAL: Review the raw snippets retrieved from the company's internal knowledge base and extract the most relevant case studies, proposals, and success stories that solve the client's detected pain points.

RULES:
1. Only return assets that explicitly demonstrate resolving a problem the client has.
2. For each asset, extract the 'key_metrics_achieved' (e.g., 'Reduced costs by 20%', 'Launched in 3 months') if present in the text.
3. Provide a concise 'summary' of how the asset proves our capability."""

    human_message_content = f"""
DETECTED CLIENT PAIN POINTS:
{json.dumps(detected_pain_points, indent=2)}

RAW INTERNAL KNOWLEDGE BASE SNIPPETS RETRIEVED:
{json.dumps(list(unique_assets.values()), indent=2)}

Synthesize these raw snippets into a structured list of highly relevant, matched assets.
"""

    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.1,
            google_api_key=GEMINI_API_KEY
        )

        # Inject dynamic instructions if present
        final_system_prompt = apply_instruction_context_to_prompt(system_prompt, get_injection_context(state))

        structured_llm = llm.with_structured_output(AssetExtractionWrapper)

        result: AssetExtractionWrapper = structured_llm.invoke([
            SystemMessage(content=final_system_prompt),
            HumanMessage(content=human_message_content)
        ])

        matched_assets = [asset.model_dump() for asset in result.matched_assets]
        logger.info(f"Successfully matched {len(matched_assets)} internal assets.")

        return {
            "matched_internal_assets": matched_assets,
            "current_step": "ENTERPRISE_RAG_COMPLETED",
            "_instructions_applied": True
        }

    except Exception as e:
        logger.error(f"Error in Enterprise RAG Matcher Node: {str(e)}")
        return {
            "errors": [f"Enterprise RAG Matcher failed: {str(e)}"],
            "current_step": "ENTERPRISE_RAG_FAILED"
        }