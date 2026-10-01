import logging
from typing import Dict, Any, List

from backend.agents.state import DealIntelligenceState

logger = logging.getLogger(__name__)


def _get_val(obj: Any, key: str, default: Any = None) -> Any:
    """Safely gets a value from either a dictionary or a Pydantic model attribute."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)

def _set_val(obj: Any, key: str, value: Any):
    """Safely sets a value on either a dictionary or a Pydantic model attribute."""
    if isinstance(obj, dict):
        obj[key] = value
    else:
        setattr(obj, key, value)


def human_review_gate_node(state: DealIntelligenceState) -> Dict[str, Any]:
    """
    Human-in-the-Loop (HITL) Gate Node.
    
    Acts as a checkpoint between Node 6 (Service Mapper) and Node 7 (CXO Brief Generator).
    Evaluates human approval status, applies user asset overrides, and incorporates 
    tactical feedback before passing state to the CXO Brief Generator.
    """
    deal_id = state.get("deal_id", "")
    target_company = state.get("target_company", "")
    human_approved = state.get("human_approved", False)
    human_feedback = state.get("human_feedback")
    custom_selected_assets = state.get("custom_selected_assets") or []

    logger.info(f"Evaluating Human Review Gate for Deal ID: '{deal_id}' ({target_company})")

    # If the user has not yet approved the intelligence state via API/UI
    if not human_approved:
        logger.info(f"Deal '{deal_id}' paused at Human Review Gate awaiting sales leader approval.")
        return {
            "current_step": "PAUSED_FOR_HUMAN_REVIEW"
        }

    # User approved the pipeline - process overrides
    matched_internal_assets = state.get("matched_internal_assets", [])
    service_mappings = state.get("service_mappings", [])

    # 1. Filter internal proof assets if custom subset was selected in UI
    filtered_assets = matched_internal_assets
    if custom_selected_assets:
        filtered_assets = [
            asset for asset in matched_internal_assets
            if str(_get_val(asset, "asset_id")) in custom_selected_assets or _get_val(asset, "asset_name") in custom_selected_assets
        ]
        logger.info(f"Applied custom asset selection filter: {len(filtered_assets)} assets retained out of {len(matched_internal_assets)}.")

    # 2. Update service mappings to align with selected assets
    updated_mappings = service_mappings
    if custom_selected_assets:
        for mapping in updated_mappings:
            proof_assets = _get_val(mapping, "supporting_proof_assets")
            if proof_assets is not None:
                filtered_proofs = [
                    asset for asset in proof_assets
                    if str(_get_val(asset, "asset_id")) in custom_selected_assets or _get_val(asset, "asset_name") in custom_selected_assets
                ]
                _set_val(mapping, "supporting_proof_assets", filtered_proofs)

    logger.info(f"Human review approved for deal '{deal_id}'. Advancing to CXO Brief Generator.")

    return {
        "matched_internal_assets": filtered_assets,
        "service_mappings": updated_mappings,
        "human_approved": True,
        "human_feedback": human_feedback,
        "current_step": "HUMAN_REVIEW_APPROVED"
    }


def route_human_review(state: DealIntelligenceState) -> str:
    """
    Conditional edge router function for LangGraph.
    
    Determines whether the workflow should proceed to Node 7 or pause execution.
    """
    current_step = state.get("current_step", "")
    human_approved = state.get("human_approved", False)

    if human_approved or current_step == "HUMAN_REVIEW_APPROVED":
        return "proceed"
    
    return "pause"