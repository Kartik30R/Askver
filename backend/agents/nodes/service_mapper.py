import logging
import json
from typing import Dict, Any, List
from pydantic import BaseModel, Field

from agents.nodes.node_middleware import apply_instruction_context_to_prompt, get_injection_context, inject_dynamic_instructions
from agents.state import DealIntelligenceState
from app.core.config import settings
from app.services.llm_provider import get_llm

from langchain_core.messages import SystemMessage, HumanMessage

# Import strict schema
from app.schemas.node_5_6_services import ServiceMappingSchema

logger = logging.getLogger(__name__)


class ServiceMappingWrapper(BaseModel):
    service_mappings: List[ServiceMappingSchema] = Field(
        description="Structured mappings connecting client pain points to enterprise offerings and proof assets."
    )


@inject_dynamic_instructions
def service_mapper_node(state: DealIntelligenceState) -> Dict[str, Any]:
    """
    Agent 6: Service Mapping Engine
    Bridges client friction points with enterprise offerings by converting detected
    pain points (Node 4) and retrieved internal assets (Node 5) into structured,
    evidence-backed solution proposals.
    """
    target_company = state.get("target_company", "")
    target_industry = state.get("target_industry", "")
    meeting_objective = state.get("meeting_objective", "")
    
    priorities_and_pain_points = state.get("priorities_and_pain_points")
    matched_internal_assets = state.get("matched_internal_assets", [])

    logger.info(f"Starting Service Mapper Node for company: '{target_company}'")

    if not priorities_and_pain_points or not priorities_and_pain_points.pain_points:
        logger.warning("No detected pain points available for service mapping.")
        return {
            "service_mappings": [],
            "node_statuses": {"service_mapper": "COMPLETED"}
        }

    # Context compilation for LLM synthesis
    mapping_context = {
        "target_company": target_company,
        "target_industry": target_industry,
        "meeting_objective": meeting_objective,
        "detected_pain_points": [p.model_dump() for p in priorities_and_pain_points.pain_points],
        "matched_internal_assets": [a.model_dump() for a in matched_internal_assets] if matched_internal_assets else []
    }

    system_prompt = """You are a Principal Solutions Architect and Enterprise Technology Strategist.

YOUR GOAL:
Map detected client pain points and technical bottlenecks to modern service offerings, backed directly by evidence from internal case studies, proposals, and success stories.

SYNTHESIS & MAPPING RULES:
1. For every detected pain point or strategic need, identify a concrete, modern technology/service offering.
2. Link relevant supporting proof assets from 'matched_internal_assets'. Ensure proof assets directly support the capability claim.
3. Quantify the expected business impact whenever possible.
4. Ensure every recommended offering aligns tightly with the primary MEETING OBJECTIVE to maximize pitch relevance."""

    human_message_content = f"""
DEAL & SOLUTION MAPPING CONTEXT:
{json.dumps(mapping_context, separators=(',', ':'), default=str)}

Synthesize the pain points and internal proof points into a structured set of service mappings matching the ServiceMappingWrapper schema.
"""

    try:
        llm = get_llm(
            model=settings.LLM_MODEL or "gemini-2.0-flash",
            provider=settings.LLM_PROVIDER or "gemini",
            temperature=0.1,
        )

        final_system_prompt = apply_instruction_context_to_prompt(system_prompt, get_injection_context(state))

        structured_llm = llm.with_structured_output(ServiceMappingWrapper)

        result: ServiceMappingWrapper = structured_llm.invoke([
            SystemMessage(content=final_system_prompt),
            HumanMessage(content=human_message_content)
        ])

        logger.info(f"Successfully generated {len(result.service_mappings)} service mappings for '{target_company}'")

        return {
            "service_mappings": result.service_mappings,
            "node_statuses": {"service_mapper": "COMPLETED"},
            "_instructions_applied": True
        }

    except Exception as e:
        logger.error(f"Error in Service Mapper Node: {str(e)}", exc_info=True)
        return {
            "errors": [f"Service Mapper Node failed: {str(e)}"],
            "node_statuses": {"service_mapper": "FAILED"}
        }