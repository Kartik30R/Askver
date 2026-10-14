"""
Node middleware wrapper for injecting dynamic instructions into LLM prompts.

This allows real-time steering of individual nodes without pausing workflow execution.
"""
import logging
from typing import Dict, Any, Callable, Optional
from functools import wraps

from agents.state import DealIntelligenceState


logger = logging.getLogger(__name__)


def _normalize_instruction_entries(instructions):
    normalized = []
    for entry in instructions or []:
        if isinstance(entry, str):
            normalized.append({"text": entry, "target_nodes": []})
        elif isinstance(entry, dict):
            text = entry.get("text") or entry.get("instruction") or entry.get("message")
            if text is None:
                continue
            targets = entry.get("target_nodes") or entry.get("nodes") or entry.get("targets") or []
            if isinstance(targets, str):
                targets = [targets]
            normalized.append({"text": str(text), "target_nodes": list(targets)})
    return normalized


def _extract_matching_instructions(instructions, node_name: str):
    matches = []
    for entry in _normalize_instruction_entries(instructions):
        targets = entry.get("target_nodes") or []
        if not targets or node_name in targets or "*" in targets:
            matches.append(entry["text"])
    return matches


def _strip_applied_instructions(existing, applied):
    remaining = []
    applied_texts = set(applied or [])
    for entry in _normalize_instruction_entries(existing):
        text = entry["text"]
        if text in applied_texts:
            continue
        remaining.append(entry)
    if not remaining:
        return []
    return [item["text"] if not item["target_nodes"] else {"text": item["text"], "target_nodes": item["target_nodes"]} for item in remaining]


def inject_dynamic_instructions(node_func: Callable) -> Callable:
    """
    Decorator that wraps a node function to inject dynamic instructions into LLM context.
    """
    @wraps(node_func)
    def wrapper(state: DealIntelligenceState) -> Dict[str, Any]:
        node_name = node_func.__name__.replace("_node", "")
        dynamic_instructions = state.get("dynamic_instructions") or []
        logger.info("[pipeline][node_start] %s | instructions=%d", node_name, len(dynamic_instructions))

        matching_instructions = _extract_matching_instructions(dynamic_instructions, node_name)
        if matching_instructions:
            logger.info(
                f"[{node_name}] Injecting {len(matching_instructions)} dynamic instruction(s) "
                f"into node context"
            )
            state["_injected_instructions"] = matching_instructions
            state["_instructions_applied"] = True
            for i, instruction in enumerate(matching_instructions, 1):
                logger.debug(f"[{node_name}] Instruction {i}: {instruction}")
        else:
            state["_injected_instructions"] = []
            state.pop("_instructions_applied", None)

        result = node_func(state)
        logger.info("[pipeline][node_complete] %s | node_statuses=%s | result_keys=%s", node_name, result.get("node_statuses"), list(result.keys()))

        injected = state.get("_injected_instructions") or []
        if injected:
            remaining = _strip_applied_instructions(dynamic_instructions, injected)
            result["dynamic_instructions"] = remaining
            result["_instructions_applied"] = True
            logger.info(f"[{node_name}] Cleared applied dynamic instructions after injection (count={len(injected)})")

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
