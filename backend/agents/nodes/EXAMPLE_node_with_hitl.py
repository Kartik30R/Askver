"""
EXAMPLE: Integrating Dynamic Instructions into an Existing Node

This file demonstrates how to modify an existing node to support dynamic
instruction injection. Use this as a template for updating your other nodes.

Location: backend/agents/nodes/EXAMPLE_node_with_hitl.py
"""

import os
import json
import logging
from typing import Dict, Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.state import DealIntelligenceState
from app.agents.nodes.node_middleware import (
    inject_dynamic_instructions,
    get_injection_context,
    apply_instruction_context_to_prompt,
)

logger = logging.getLogger(__name__)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


# ============================================================================
# ORIGINAL NODE (Before HITL Integration)
# ============================================================================
# 
# def original_stakeholder_intelligence_node(state: DealIntelligenceState) -> Dict[str, Any]:
#     """
#     Original node without HITL support.
#     Does not support dynamic instruction injection.
#     """
#     target_company = state.get("target_company", "")
#     
#     llm = ChatGoogleGenerativeAI(api_key=GEMINI_API_KEY, model="gemini-pro")
#     
#     prompt = """You are an expert at profiling enterprise stakeholders...
#     Provide analysis for each executive..."""
#     
#     response = llm.invoke([SystemMessage(content=prompt)])
#     
#     return {"stakeholder_profiles": parse_response(response.content)}


# ============================================================================
# UPDATED NODE (With HITL Support)
# ============================================================================

@inject_dynamic_instructions  # ← ADD THIS DECORATOR
def stakeholder_intelligence_node(state: DealIntelligenceState) -> Dict[str, Any]:
    """
    Agent 2: Stakeholder Intelligence with Dynamic Instruction Support
    
    Profiles target company executives and key stakeholders.
    NOW SUPPORTS: Dynamic instruction injection for real-time steering.
    
    Example scenario:
    1. Workflow reaches this node and starts LLM analysis
    2. User submits: "Focus on the CFO's concerns about cloud migration costs"
    3. This instruction is injected into the LLM prompt automatically
    4. LLM incorporates the instruction without pausing workflow
    """
    target_company = state.get("target_company", "")
    
    logger.info(f"Starting Stakeholder Intelligence analysis for: {target_company}")
    
    # =========================================================================
    # STEP 1: Get dynamic instructions if any were submitted (NEW)
    # =========================================================================
    instruction_context = get_injection_context(state)
    if instruction_context:
        logger.info("Dynamic instructions detected. Will be injected into LLM prompt.")
    
    # =========================================================================
    # STEP 2: Build base prompt (MOSTLY UNCHANGED)
    # =========================================================================
    base_prompt = f"""You are an expert executive profiler specializing in enterprise 
sales analysis. Your task is to profile the C-suite executives at {target_company} 
based on typical industry patterns and available information.

For EACH executive role (CEO, CFO, CIO, CTO, CDO, CISO), provide:

1. **Professional Background**: Typical career trajectory, education, previous roles
2. **Business Drivers**: What keeps them up at night? What are their KPIs?
3. **Likely Goals**: What is this executive trying to achieve in the next 12-24 months?
4. **Technology Priorities**: What technology investments are they pushing for?
5. **Risk Concerns**: What are their main risk concerns and compliance requirements?
6. **Success Metrics**: How does this executive measure success?
7. **Communication Style**: How should we engage with this executive?
8. **Influence Patterns**: Who influences this executive's decisions?

Structure your response as a JSON object with keys like "CEO", "CFO", "CIO", etc.
Each containing the 8 analysis points above.

Remember: These are profiles based on typical industry patterns, not specific 
knowledge of their company. Use general enterprise software/service knowledge."""

    # =========================================================================
    # STEP 3: Apply dynamic instructions to prompt (NEW)
    # =========================================================================
    final_prompt = apply_instruction_context_to_prompt(base_prompt, instruction_context)
    # ↑ This appends instruction_context to base_prompt if instructions exist
    # ↑ The instructions are merged BEFORE being sent to LLM
    
    logger.debug(f"Final prompt length: {len(final_prompt)} characters")
    
    # =========================================================================
    # STEP 4: Prepare company context (UNCHANGED)
    # =========================================================================
    company_overview = state.get("company_overview", {})
    company_context = json.dumps(company_overview, indent=2)
    
    # =========================================================================
    # STEP 5: Invoke LLM with merged prompt (MOSTLY UNCHANGED)
    # =========================================================================
    llm = ChatGoogleGenerativeAI(
        api_key=GEMINI_API_KEY,
        model="gemini-pro",
        temperature=0.7,  # Balanced between creativity and consistency
    )
    
    try:
        response = llm.invoke([
            SystemMessage(content=final_prompt),  # ← Uses merged prompt
            HumanMessage(content=f"Analyze stakeholder profiles for: {company_context}")
        ])
        
        analyzed_text = response.content
        logger.info(f"LLM analysis completed. Response length: {len(analyzed_text)}")
        
    except Exception as e:
        logger.error(f"LLM invocation failed: {str(e)}")
        analyzed_text = "{}"
    
    # =========================================================================
    # STEP 6: Parse and structure response (UNCHANGED)
    # =========================================================================
    try:
        # Try to extract JSON from response
        if "{" in analyzed_text:
            json_str = analyzed_text[analyzed_text.find("{"):analyzed_text.rfind("}")+1]
            stakeholder_profiles = json.loads(json_str)
        else:
            stakeholder_profiles = {"error": "Could not parse LLM response"}
    except Exception as e:
        logger.error(f"Response parsing failed: {str(e)}")
        stakeholder_profiles = {"error": str(e)}
    
    logger.info(f"Stakeholder profiles generated with {len(stakeholder_profiles)} roles")
    
    # =========================================================================
    # STEP 7: Return results with HITL markers (MODIFIED)
    # =========================================================================
    return {
        "stakeholder_profiles": stakeholder_profiles,
        # ↓ NEW: Mark that dynamic instructions were applied (if any existed)
        "_instructions_applied": bool(instruction_context),
        # ↓ NEW: Log which instruction set was applied
        "node_statuses": {
            "stakeholder_intel": "completed",
            "instructions_applied": bool(instruction_context),
        }
    }


# ============================================================================
# COMPARISON: What Changed?
# ============================================================================
#
# BEFORE:
#   - No decorator
#   - No instruction context retrieval
#   - Base prompt used directly in LLM call
#   - No instruction application tracking
#
# AFTER:
#   - @inject_dynamic_instructions decorator added (1 line)
#   - Call get_injection_context(state) (1 line)
#   - Call apply_instruction_context_to_prompt() (1 line)
#   - Return _instructions_applied marker (1 line)
#
# Total code additions: ~4 lines
# Breaking changes: None - fully backward compatible
# Performance impact: Minimal (~1-5ms for instruction formatting)


# ============================================================================
# PRACTICAL EXAMPLES: How Users Will Use This
# ============================================================================

"""
EXAMPLE 1: Dynamic Steering (Real-time Instructions)
========================================================

User is reviewing workflow progress and wants to adjust analysis:

1. User submits via frontend:
   POST /api/v1/deals/123/pipeline/hitl/dynamic-instruction
   {
       "instructions": [
           "Focus on the CFO's concerns about cloud migration costs",
           "Emphasize the CIO's interest in AI/ML platforms",
           "Highlight any ESG or sustainability-focused executives"
       ],
       "priority": 8
   }

2. Instructions are appended to state.dynamic_instructions

3. Next time node runs (or on resume if paused), get_injection_context() 
   retrieves these instructions and formats them as:
   
   === REAL-TIME STEERING INSTRUCTIONS ===
   The user has provided the following real-time guidance for your analysis:
   
   1. Focus on the CFO's concerns about cloud migration costs
   2. Emphasize the CIO's interest in AI/ML platforms
   3. Highlight any ESG or sustainability-focused executives
   
   Please incorporate these instructions into your analysis and output.
   ====================================

4. This context is appended to the base prompt before LLM invocation

5. LLM sees extended prompt and incorporates these nuances

6. Final analysis is enhanced with user-directed focus


EXAMPLE 2: Manual Pause & Resume
==================================

1. User clicks "Pause" button (requests pause)
2. Workflow completes current node and halts at boundary
3. User reviews state via GET /pipeline/hitl/checkpoint-state
4. User submits new instructions via POST /pipeline/hitl/resume with:
   {
       "instructions": [
           "The CEO is primarily concerned about cost reduction",
           "De-prioritize digital transformation in your profiles"
       ],
       "feedback": "Good analysis so far. Refocus on cost concerns."
   }
5. Workflow resumes with these instructions injected into next node
6. Next node(s) execute with enhanced user-provided context


EXAMPLE 3: Mandatory Review (Before Final Brief)
=================================================

1. Workflow executes through all intelligence nodes
2. Before entering cxo_brief_generator, automatically pauses
3. User sees checkpoint state with all collected intelligence
4. User can:
   a) APPROVE: "Looks good, proceed to final brief"
   b) REJECT: "Not a good fit, cancel workflow"
   c) NEEDS_REVISION: "Refocus on cloud initiatives, re-run analysis"
   d) MODIFY: Include executive_brief_modifications for final output

5. User submits:
   POST /pipeline/hitl/mandatory-review/approve
   {
       "checkpoint_status": "approved",
       "feedback": "Profiles are accurate and comprehensive",
       "custom_selected_assets": ["asset_123", "asset_456"],
       "executive_brief_modifications": {
           "talking_points": [
               "New talking point about cloud ROI",
               "Updated case study reference"
           ]
       }
   }

6. Workflow proceeds to cxo_brief_generator with modifications applied
"""


# ============================================================================
# INTEGRATION CHECKLIST FOR YOUR NODES
# ============================================================================
#
# For each of your nodes (company_research, industry_analysis, etc.):
#
# [ ] 1. Add imports:
#        from app.agents.nodes.node_middleware import (
#            inject_dynamic_instructions,
#            get_injection_context,
#            apply_instruction_context_to_prompt,
#        )
#
# [ ] 2. Add decorator:
#        @inject_dynamic_instructions
#        def your_node_name(state):
#
# [ ] 3. After determining base_prompt, add:
#        instruction_context = get_injection_context(state)
#        final_prompt = apply_instruction_context_to_prompt(base_prompt, instruction_context)
#        
#        # Use final_prompt instead of base_prompt in LLM call:
#        response = llm.invoke([SystemMessage(content=final_prompt), ...])
#
# [ ] 4. In return statement, add:
#        return {
#            "your_field": result,
#            "_instructions_applied": True,  # ← Add this line
#        }
#
# [ ] 5. Test:
#        a) Run workflow normally - should work as before
#        b) Submit dynamic instructions - should appear in logs
#        c) Pause/resume - should still work
#        d) Check that instructions were incorporated in analysis


# ============================================================================
# ADVANCED: Custom Instruction Handling
# ============================================================================

def advanced_node_with_custom_instruction_handling(state: DealIntelligenceState) -> Dict[str, Any]:
    """
    Advanced example: Filtering instructions by type before applying.
    
    Useful if you want fine-grained control over which instructions apply
    to which nodes.
    """
    instruction_context = get_injection_context(state)
    instructions = state.get("_injected_instructions", [])
    
    # Example: Filter only instructions containing certain keywords
    relevant_instructions = [
        instr for instr in instructions
        if any(keyword in instr.lower() for keyword in ["financial", "revenue", "roi"])
    ]
    
    # Rebuild instruction context with filtered instructions
    if relevant_instructions:
        custom_context = "\n=== FILTERED INSTRUCTIONS ===\n"
        for i, instr in enumerate(relevant_instructions, 1):
            custom_context += f"{i}. {instr}\n"
        custom_context += "===========================\n"
    else:
        custom_context = None
    
    # Use custom context instead of standard one
    base_prompt = "Your base prompt..."
    final_prompt = apply_instruction_context_to_prompt(base_prompt, custom_context)
    
    # Continue with normal node logic
    return {"result": final_prompt}
