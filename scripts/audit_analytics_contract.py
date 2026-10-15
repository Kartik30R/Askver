from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, get_type_hints

from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.agents.research.state_deal_analytics import DealAnalyticsState, MeetingDigest
from app.agents.research.state_meeting_analysis import MeetingAnalysisState
from app.schemas.deal_analytics import DealAnalyticsResult
from app.schemas.meeting_analysis import MeetingAnalysisResult

OUT_PATH = ROOT / "analytics_field_inventory.json"


def _typed_dict_keys(tp: Any) -> list[str]:
    try:
        hints = get_type_hints(tp)
    except Exception:
        hints = getattr(tp, "__annotations__", {})
    return sorted(hints.keys())


def _model_field_paths(model: type[BaseModel], prefix: str = "") -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for field_name, field in model.model_fields.items():
        path = f"{prefix}.{field_name}" if prefix else field_name
        field_type = field.annotation
        origin = getattr(field_type, "__origin__", None)
        if origin is list:
            inner = getattr(field_type, "__args__", (str,))[0]
            out.append((f"{path}[]", _pretty_type(inner)))
        elif origin is dict:
            out.append((f"{path}", _pretty_type(field_type)))
        elif isinstance(field_type, type) and issubclass(field_type, BaseModel):
            out.append((f"{path}", _pretty_type(field_type)))
            for sub_path, sub_type in _model_field_paths(field_type, path):
                out.append((sub_path, sub_type))
        elif field_type is None:
            out.append((path, "None"))
        else:
            out.append((path, _pretty_type(field_type)))
    return out


def _pretty_type(tp: Any) -> str:
    if tp is Any:
        return "Any"
    if tp is None:
        return "None"
    if isinstance(tp, type):
        if issubclass(tp, BaseModel):
            return tp.__name__
        return tp.__name__
    origin = getattr(tp, "__origin__", None)
    if origin is list:
        args = getattr(tp, "__args__", ())
        inner = args[0] if args else "Any"
        return f"list[{_pretty_type(inner)}]"
    if origin is dict:
        args = getattr(tp, "__args__", ())
        key_type = args[0] if len(args) > 0 else str
        value_type = args[1] if len(args) > 1 else Any
        return f"dict[{_pretty_type(key_type)}, {_pretty_type(value_type)}]"
    if origin is tuple:
        args = getattr(tp, "__args__", ())
        return f"tuple[{', '.join(_pretty_type(a) for a in args)}]"
    if origin is not None:
        return str(tp)
    return str(tp)


def _normalize_model_mapping(model: type[BaseModel]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for field_name, field in model.model_fields.items():
        mapping[field_name] = field_name
    return mapping


def main() -> None:
    meeting_state_keys = _typed_dict_keys(MeetingAnalysisState)
    deal_state_keys = _typed_dict_keys(DealAnalyticsState)
    meeting_result_fields = set(MeetingAnalysisResult.model_fields.keys())
    deal_result_fields = set(DealAnalyticsResult.model_fields.keys())

    print("MeetingAnalysisState keys:")
    for key in meeting_state_keys:
        status = "PASS" if key in meeting_result_fields or key in {"warnings", "unverified_quote_count"} else "FAIL"
        print(f"  - {key}: {status}")

    print("\nDealAnalyticsState keys:")
    for key in deal_state_keys:
        status = "PASS" if key in deal_result_fields or key in {"warnings"} else "FAIL"
        print(f"  - {key}: {status}")

    inventory: list[dict[str, str]] = []
    for path, type_name in _model_field_paths(MeetingAnalysisResult):
        inventory.append({"model": "MeetingAnalysisResult", "path": path, "type": type_name})
    for path, type_name in _model_field_paths(DealAnalyticsResult):
        inventory.append({"model": "DealAnalyticsResult", "path": path, "type": type_name})

    OUT_PATH.write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    print(f"\nWrote field inventory to {OUT_PATH}")

    # state-to-result mapping summary
    mapping = []
    for key in meeting_state_keys:
        exposed = "transcript_stats" if key == "transcript_stats" else key
        mapping.append({"state_key": key, "exposed_as": exposed if key in meeting_result_fields or key == "transcript_stats" else "(none)", "status": "PASS" if key in meeting_result_fields or key == "transcript_stats" else "FAIL"})
    for key in deal_state_keys:
        exposed = key
        mapping.append({"state_key": key, "exposed_as": exposed if key in deal_result_fields else "(none)", "status": "PASS" if key in deal_result_fields else "FAIL"})
    print(json.dumps(mapping, indent=2))


if __name__ == "__main__":
    main()
