"""Run a single node using workflow state loaded from the latest snapshot.

Usage (from backend):
  venv/Scripts/python.exe -u run_node_from_snapshot.py --node company_research
  venv/Scripts/python.exe -u run_node_from_snapshot.py --node financial_intelligence --snapshot outputs/node_states.txt

If no snapshot is found, a minimal initial state is created (same as sequential runner).
After execution, the updated state snapshot is appended to `outputs/node_states.txt`.
"""
import argparse
import json
from pathlib import Path
import logging

from app.utils.serializers import to_primitive
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

logger = logging.getLogger("run_node_from_snapshot")
logging.basicConfig(level=logging.INFO)

# Schema rehydration helpers: when loading a JSON snapshot we convert dicts
# back into Pydantic models for nodes that expect attribute-style access.
try:
    from app.schemas.node_1_company import CompanyResearchSchema
except Exception:
    CompanyResearchSchema = None
try:
    from app.schemas.node_1b_financial import FinancialIntelligenceSchema
except Exception:
    FinancialIntelligenceSchema = None
try:
    from app.schemas.node_2_stakeholder import StakeholderIntelligenceSchema
except Exception:
    StakeholderIntelligenceSchema = None
try:
    from app.schemas.node_3_industry import IndustryAnalysisSchema
except Exception:
    IndustryAnalysisSchema = None


def rehydrate_state(state: dict) -> dict:
    """Convert known dicts in `state` back into Pydantic models where possible."""
    # company_research
    try:
        if CompanyResearchSchema is not None and isinstance(state.get("company_research"), dict):
            dump = state["company_research"]
            validator = getattr(CompanyResearchSchema, "model_validate", None) or getattr(CompanyResearchSchema, "parse_obj", None)
            if callable(validator):
                state["company_research"] = validator(dump)
    except Exception:
        logger.exception("Failed to rehydrate company_research; leaving as dict")

    # financial_intelligence
    try:
        if FinancialIntelligenceSchema is not None and isinstance(state.get("financial_intelligence"), dict):
            dump = state["financial_intelligence"]
            validator = getattr(FinancialIntelligenceSchema, "model_validate", None) or getattr(FinancialIntelligenceSchema, "parse_obj", None)
            if callable(validator):
                state["financial_intelligence"] = validator(dump)
    except Exception:
        logger.exception("Failed to rehydrate financial_intelligence; leaving as dict")

    # stakeholder_intelligence
    try:
        if StakeholderIntelligenceSchema is not None and isinstance(state.get("stakeholder_intelligence"), dict):
            dump = state["stakeholder_intelligence"]
            validator = getattr(StakeholderIntelligenceSchema, "model_validate", None) or getattr(StakeholderIntelligenceSchema, "parse_obj", None)
            if callable(validator):
                state["stakeholder_intelligence"] = validator(dump)
    except Exception:
        logger.exception("Failed to rehydrate stakeholder_intelligence; leaving as dict")

    # industry_analysis
    try:
        if IndustryAnalysisSchema is not None and isinstance(state.get("industry_analysis"), dict):
            dump = state["industry_analysis"]
            validator = getattr(IndustryAnalysisSchema, "model_validate", None) or getattr(IndustryAnalysisSchema, "parse_obj", None)
            if callable(validator):
                state["industry_analysis"] = validator(dump)
    except Exception:
        logger.exception("Failed to rehydrate industry_analysis; leaving as dict")

    return state


NODE_MAP = {
    "company_research": company_research_node,
    "financial_intelligence": financial_intelligence_node,
    "stakeholder_intel": stakeholder_intelligence_node,
    "industry_analysis": industry_analysis_node,
    "pain_point_detector": pain_point_detector_node,
    "enterprise_rag_matcher": enterprise_rag_matcher_node,
    "service_mapper": service_mapper_node,
    "human_review_gate": human_review_gate_node,
    "cxo_brief_generator": cxo_brief_generator_node,
    "report_indexer": report_indexer_node,
}


def load_latest_state(snapshot_path: Path) -> dict:
    if not snapshot_path.exists():
        return None
    try:
        # Expect the snapshot file to contain a single JSON object representing
        # the current workflow state (production-like memory). Load it directly.
        with snapshot_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        # If the file contains an envelope {"node":..., "state": {...}},
        # accept both formats.
        if isinstance(data, dict) and "state" in data:
            return data["state"]
        return data
    except Exception:
        logger.exception("Failed to parse snapshot file; attempting legacy parsing.")
        # Legacy fallback: parse last '---' delimited block
        raw = snapshot_path.read_text(encoding="utf-8")
        parts = [p.strip() for p in raw.split("---") if p.strip()]
        if not parts:
            return None
        try:
            last = json.loads(parts[-1])
            return last.get("state")
        except Exception:
            logger.exception("Legacy parse also failed; starting fresh.")
            return None


def write_snapshot(file_path: Path, node_name: str, state: dict):
    # Overwrite the snapshot file with the latest workflow state. This file
    # represents the in-memory persistent state of the workflow (single JSON).
    payload = {"node": node_name, "state": to_primitive(state)}
    with file_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)


def minimal_initial_state() -> dict:
    # Complete baseline matching DealIntelligenceState fields. When a snapshot
    # is partial, we'll merge the loaded values into this baseline so no fields
    # are accidentally dropped.
    return {
        "deal_id": "test-deal-001",
        "target_company": "Microsoft Corporation",
        "target_industry": "Technology",
        "meeting_objective": "Evaluate partnership opportunity",
        "client_documents_path": None,

        # Strictly typed agent outputs
        "company_research": None,
        "financial_intelligence": None,
        "stakeholder_intelligence": None,
        "industry_analysis": None,
        "priorities_and_pain_points": None,
        "matched_internal_assets": [],
        "service_mappings": [],
        "cxo_executive_brief": None,
        "markdown_export": None,

        # Execution control & HITL
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

        # bookkeeping
        "node_statuses": {},
        "errors": None,
    }


def merge_state(state: dict, update: dict) -> dict:
    if not update:
        return state
    for k, v in update.items():
        state[k] = to_primitive(v)
    return state


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--node", required=True, help="Node name to run")
    p.add_argument("--snapshot", default="outputs/node_states.txt", help="Snapshot file to load/save")
    args = p.parse_args()

    node_name = args.node
    snapshot_path = Path(args.snapshot)

    if node_name not in NODE_MAP:
        logger.error(f"Unknown node: {node_name}")
        logger.error(f"Known nodes: {list(NODE_MAP.keys())}")
        raise SystemExit(1)

    loaded = load_latest_state(snapshot_path) or {}
    # Merge loaded snapshot into a full baseline so fields from `state.py` are
    # always present even if the snapshot was partial.
    state = minimal_initial_state()
    if isinstance(loaded, dict):
        state.update(loaded)

    # Rehydrate known Pydantic models from dicts so node implementations get
    # attribute-style access (e.g., company_research.leadership_team).
    state = rehydrate_state(state)
    # Also rehydrate priorities_and_pain_points if present (many nodes expect .model_dump)
    try:
        from app.schemas.node_4_priorities import BusinessPrioritiesSchema
    except Exception:
        BusinessPrioritiesSchema = None
    try:
        if BusinessPrioritiesSchema is not None and isinstance(state.get("priorities_and_pain_points"), dict):
            validator = getattr(BusinessPrioritiesSchema, "model_validate", None) or getattr(BusinessPrioritiesSchema, "parse_obj", None)
            if callable(validator):
                state["priorities_and_pain_points"] = validator(state["priorities_and_pain_points"])
    except Exception:
        logger.exception("Failed to rehydrate priorities_and_pain_points; leaving as dict")

    # Ensure list fields are present and iterable for nodes that assume lists.
    state["matched_internal_assets"] = state.get("matched_internal_assets") or []
    state["service_mappings"] = state.get("service_mappings") or []

    logger.info(f"Running node: {node_name} with state deal_id={state.get('deal_id')}")
    func = NODE_MAP[node_name]
    try:
        result = func(state)
        state = merge_state(state, result)
        write_snapshot(snapshot_path, node_name, state)
        logger.info(f"Node {node_name} completed; snapshot appended to {snapshot_path}")
        print(json.dumps({"node": node_name, "result": to_primitive(result)}, indent=2, ensure_ascii=False))
    except Exception as e:
        logger.exception(f"Node {node_name} failed: {e}")
        errs = state.get("errors") or []
        errs.append(f"{node_name}: {str(e)}")
        state["errors"] = errs
        write_snapshot(snapshot_path, node_name + "_failed", to_primitive(state))


if __name__ == "__main__":
    main()
