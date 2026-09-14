"""
Node middleware wrapper for injecting dynamic instructions into LLM prompts.

This allows real-time steering of individual nodes without pausing workflow execution.
"""
import logging
from typing import Dict, Any, Callable, Optional
from functools import wraps

from app.agents.state import DealIntelligenceState

logger = logging.getLogger(__name__)


def inject_dynamic_instructions(node_func: Callable) -> Callable:
    """
    Decorator that wraps a node function to inject dynamic instructions into LLM context.
    
    Before the node executes, any pending dynamic_instructions in state are extracted
    and appended to the system prompt / context used by the node's LLM calls.
    
    Usage:
        @inject_dynamic_instructions
        def my_node(state: DealIntelligenceState) -> Dict[str, Any]:
            ...
    """
    @wraps(node_func)
    def wrapper(state: DealIntelligenceState) -> Dict[str, Any]:
        node_name = node_func.__name__.replace("_node", "")
        dynamic_instructions = state.get("dynamic_instructions")
        
        # Extract and log dynamic instructions
        if dynamic_instructions:
            logger.info(
                f"[{node_name}] Injecting {len(dynamic_instructions)} dynamic instruction(s) "
                f"into node context"
            )
            
            # Store instructions in a format accessible to the node
            # The node should check for this key and prepend to its LLM prompt
            state["_injected_instructions"] = dynamic_instructions
            state["_instructions_applied"] = True
            
            # Log each instruction for audit purposes
            for i, instruction in enumerate(dynamic_instructions, 1):
                logger.debug(f"[{node_name}] Instruction {i}: {instruction}")
        
        # Call the actual node function
        result = node_func(state)
        
        # If instructions were applied, clear them and mark in result
        if result.get("_instructions_applied"):
            result["dynamic_instructions"] = None  # Clear after application
            result["node_statuses"] = result.get("node_statuses", {})
            result["node_statuses"][node_name] = f"applied_{len(dynamic_instructions)}_instructions"
            logger.info(f"[{node_name}] Cleared dynamic instructions after application")
        
        return result
    
    return wrapper


def get_injection_context(state: DealIntelligenceState) -> Optional[str]:
    """
    Formats dynamic instructions for injection into LLM prompts.
    
    Returns a formatted string with instructions that should be appended to
    the system prompt of the node's LLM call.
    
    Args:
        state: Current deal intelligence state
        
    Returns:
        Formatted instruction context string, or None if no instructions
    """
    instructions = state.get("_injected_instructions")
    
    if not instructions:
        return None
    
    # Format instructions for LLM prompt injection
    context = "\n=== REAL-TIME STEERING INSTRUCTIONS ===\n"
    context += "The user has provided the following real-time guidance for your analysis:\n\n"
    
    for i, instruction in enumerate(instructions, 1):
        context += f"{i}. {instruction}\n"
    
    context += "\nPlease incorporate these instructions into your analysis and output.\n"
    context += "====================================\n"
    
    return context


def apply_instruction_context_to_prompt(
    base_prompt: str,
    instruction_context: Optional[str],
) -> str:
    """
    Appends instruction context to a base LLM prompt.
    
    Args:
        base_prompt: Original system/user prompt
        instruction_context: Formatted instruction context from get_injection_context()
        
    Returns:
        Updated prompt with instruction context appended
    """
    if not instruction_context:
        return base_prompt
    
    return f"{base_prompt}\n\n{instruction_context}"


# ============================================================================
# Example: How to use this in a node
# ============================================================================
# 
# from app.agents.nodes.node_middleware import (
#     inject_dynamic_instructions,
#     get_injection_context,
#     apply_instruction_context_to_prompt,
# )
#
# @inject_dynamic_instructions
# def my_node(state: DealIntelligenceState) -> Dict[str, Any]:
#     # Get instruction context if any dynamic instructions were queued
#     instruction_context = get_injection_context(state)
#     
#     # Build base prompt
#     base_prompt = "You are an AI analyst. Analyze the data..."
#     
#     # Apply instruction context
#     final_prompt = apply_instruction_context_to_prompt(base_prompt, instruction_context)
#     
#     # Use final_prompt in LLM calls
#     llm = ChatGoogleGenerativeAI(...)
#     response = llm.invoke([SystemMessage(content=final_prompt), ...])
#     
#     return {"result": response}
