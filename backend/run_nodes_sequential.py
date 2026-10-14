"""Run each LangGraph node sequentially and save the evolving state to a text file.

Usage (from repo root):
  cd backend
  venv/Scripts/python.exe -u run_nodes_sequential.py

This script calls each node function in the same order they are registered in
`agents/graph.py`, merges returned partial state into a single `state` dict,
serializes complex objects to JSON-friendly primitives using `to_primitive`, and
appends the state snapshot to `backend/outputs/node_states.txt` after each node.
"""
import os
import json
from pathlib import Path
import logging

from agents.state import DealIntelligenceState

# Import nodes in the same order as the graph registration
from agents.nodes.company_research import company_research_node
from agents.nodes.financial_intelligence import financial_intelligence_node
from agents.nodes.stakeholder_intelligence import stakeholder_intelligence_node
from agents.nodes.industry_analysis import industry_analysis_node
from agents.nodes.pain_point_detector import pain_point_detector_node
from agents.nodes.enterprise_rag_matcher import enterprise_rag_matcher_node
from agents.nodes.service_mapper import service_mapper_node
from agents.nodes.human_review_gate import human_review_gate_node
from agents.nodes.cxo_brief_synthesizer import cxo_brief_generator_node
from agents.nodes.report_indexer import report_indexer_node

from app.utils.serializers import to_primitive
try:
    from app.schemas.node_1_company import CompanyResearchSchema
except Exception:
    CompanyResearchSchema = None


def _rehydrate_state_for_nodes(state: dict) -> dict:
    if CompanyResearchSchema is not None and isinstance(state.get("company_research"), dict):
        validator = getattr(CompanyResearchSchema, "model_validate", None) or getattr(CompanyResearchSchema, "parse_obj", None)
        try:
            if callable(validator):
                state["company_research"] = validator(state["company_research"])
        except Exception:
            pass
    return state

logger = logging.getLogger("run_nodes_sequential")
logging.basicConfig(level=logging.INFO)


def ensure_outputs_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def write_snapshot(file_path: Path, node_name: str, state: dict):
    # Overwrite the snapshot file with the latest workflow state so the file
    # acts as the single source of truth (in-memory workflow memory).
    payload = {"node": node_name, "state": to_primitive(state)}
    with file_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)


def merge_state(state: dict, update: dict) -> dict:
    """Shallow merge node return into state. Node returns are assumed to be
    partial dicts keyed by the state fields (for example, {'company_research': ...}).
    """
    if not update:
        return state
    for k, v in update.items():
        # Convert v to primitives (handles Pydantic models)
        state[k] = to_primitive(v)
    return state


def main():
    outputs_dir = Path(__file__).parent / "outputs"
    ensure_outputs_dir(outputs_dir)
    out_file = outputs_dir / "node_states.txt"

    # Clear previous output file
    # If there's an existing snapshot, load it and merge into the baseline so
    # we preserve all fields defined in the canonical state.
    baseline = {
        "deal_id": "test-deal-001",
        "target_company": "Microsoft Corporation",
        "target_industry": "Technology",
        "meeting_objective": "Evaluate partnership opportunity",
        "client_documents_path": None,
        "company_research": None,
        "financial_intelligence": None,
        "stakeholder_intelligence": None,
        "industry_analysis": None,
        "priorities_and_pain_points": None,
        "matched_internal_assets": [],
        "service_mappings": [],
        "cxo_executive_brief": None,
        "markdown_export": None,
        "pause_requested": False,
        "manual_pause_at_node": None,
        "dynamic_instructions": None,
        "mandatory_review_checkpoint": "pending",
        "human_approved": False,
        "human_feedback": None,
        "custom_selected_assets": None,
        "current_step": None,
        "execution_paused_at": None,
        "last_execution_resumption": None,
        "node_statuses": {},
        "errors": None,
    }
    if out_file.exists():
        try:
            loaded = json.loads(out_file.read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and "state" in loaded:
                baseline.update(loaded.get("state") or {})
            elif isinstance(loaded, dict):
                baseline.update(loaded)
        except Exception:
            # If parsing fails, start from fresh baseline and overwrite below
            pass
    # Ensure file will be overwritten with the evolving baseline

    # Minimal initial state required by DealIntelligenceState TypedDict
    state: dict = {
        "deal_id": "test-deal-001",
        "target_company": "Microsoft Corporation",
        "target_industry": "Technology",
        "meeting_objective": "Evaluate partnership opportunity",
        "client_documents_path": None,

        "company_research": None,
        "financial_intelligence": None,
        "stakeholder_intelligence": None,
        "industry_analysis": None,
        "priorities_and_pain_points": None,
        "matched_internal_assets": None,
        "service_mappings": None,
        "cxo_executive_brief": None,
        "markdown_export": None,

        "pause_requested": False,
        "manual_pause_at_node": None,
        "dynamic_instructions": None,
        "mandatory_review_checkpoint": "pending",
        "human_approved": False,
        "human_feedback": None,
        "custom_selected_assets": None,
        "current_step": None,
        "execution_paused_at": None,
        "last_execution_resumption": None,
        "node_statuses": {},
        "errors": None,
    }

    # Ordered list of (name, callable)
    nodes = [
        ("company_research", company_research_node),
        ("industry_analysis", industry_analysis_node),
        ("financial_intelligence", financial_intelligence_node),
        ("stakeholder_intel", stakeholder_intelligence_node),
        ("pain_point_detector", pain_point_detector_node),
        ("enterprise_rag_matcher", enterprise_rag_matcher_node),
        ("service_mapper", service_mapper_node),
        ("human_review_gate", human_review_gate_node),
        ("cxo_brief_generator", cxo_brief_generator_node),
        ("report_indexer", report_indexer_node),
    ]

    for name, func in nodes:
        logger.info(f"Running node: {name}")
        try:
            # Rehydrate common schema fields so node implementations that
            # expect attribute access work correctly.
            state = _rehydrate_state_for_nodes(state)
            result = func(state)
            # Merge returned partial state (and convert to primitives)
            state = merge_state(state, result)
            # Write snapshot after node
            write_snapshot(out_file, name, state)
            logger.info(f"Node {name} completed; snapshot saved to {out_file}")
        except Exception as e:
            logger.exception(f"Node {name} raised an exception: {e}")
            # Record error in state and persist
            errs = state.get("errors") or []
            errs.append(f"{name}: {str(e)}")
            state["errors"] = errs
            write_snapshot(out_file, name + "_failed", to_primitive(state))

    logger.info("All nodes executed sequentially. Final state written.")


if __name__ == "__main__":
    main()
