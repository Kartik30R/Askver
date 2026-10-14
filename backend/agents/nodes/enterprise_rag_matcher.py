import logging
import json
from typing import Dict, Any

from agents.nodes.node_middleware import apply_instruction_context_to_prompt, get_injection_context, inject_dynamic_instructions
from agents.state import DealIntelligenceState
from app.core.config import settings
from app.services.llm_provider import get_llm
from app.services.vector_service import query_internal_knowledge_base

from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel

# FIXED: Updated import path to match the new schema locations
from app.schemas.node_5_6_services import MatchedAssetSchema

logger = logging.getLogger(__name__)


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
    priorities_and_pain_points = state.get("priorities_and_pain_points")
    
    pain_points = priorities_and_pain_points.pain_points if priorities_and_pain_points else []

    logger.info(f"Starting Enterprise RAG Matcher Node for industry: {target_industry}")

    raw_retrieved_assets = []

    # Query PGVector based on the specific pain points identified in Node 4
    for point in pain_points:
        query_text = f"{point.category}: {point.description}"
        
        results = query_internal_knowledge_base(
            query=query_text,
            industry_filter=target_industry if target_industry else None,
            top_k=3
        )
        raw_retrieved_assets.extend(results)

    unique_assets = {}
    for asset in raw_retrieved_assets:
        content = asset.get("content", "")
        if content not in unique_assets:
            unique_assets[content] = asset

    if not unique_assets:
        logger.warning("No internal assets matched the deal requirements.")
        return {
            "matched_internal_assets": [],
            "node_statuses": {"enterprise_rag": "COMPLETED"}
        }

    system_prompt = """You are an Enterprise Solutions Architect.
YOUR GOAL: Review the raw snippets retrieved from the company's internal knowledge base and extract the most relevant case studies, proposals, and success stories that solve the client's detected pain points.

RULES:
1. Only return assets that explicitly demonstrate resolving a problem the client has.
2. For each asset, extract the 'key_metrics_achieved' if present in the text.
3. Provide a concise 'summary' of how the asset proves our capability."""

    human_message_content = f"""
DETECTED CLIENT PAIN POINTS:
{json.dumps([p.model_dump() for p in pain_points], separators=(',', ':'), default=str)}

RAW INTERNAL KNOWLEDGE BASE SNIPPETS RETRIEVED:
{json.dumps(list(unique_assets.values()), separators=(',', ':'), default=str)}

Synthesize these raw snippets into a structured list of highly relevant, matched assets.
"""

    try:
        llm = get_llm(
            model=settings.LLM_MODEL or "gemini-2.5-flash",
            provider=settings.LLM_PROVIDER or "gemini",
            temperature=0.1,
        )

        final_system_prompt = apply_instruction_context_to_prompt(system_prompt, get_injection_context(state))
        structured_llm = llm.with_structured_output(AssetExtractionWrapper)

        result: AssetExtractionWrapper = structured_llm.invoke([
            SystemMessage(content=final_system_prompt),
            HumanMessage(content=human_message_content)
        ])

        logger.info(f"Successfully matched {len(result.matched_assets)} internal assets.")

        return {
            "matched_internal_assets": result.matched_assets,
            "node_statuses": {"enterprise_rag": "COMPLETED"},
            "_instructions_applied": True
        }

    except Exception as e:
        logger.error(f"Error in Enterprise RAG Matcher Node: {str(e)}")
        return {
            "errors": [f"Enterprise RAG Matcher failed: {str(e)}"],
            "node_statuses": {"enterprise_rag": "FAILED"}
        }