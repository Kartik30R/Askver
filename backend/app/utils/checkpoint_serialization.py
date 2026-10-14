from __future__ import annotations

from typing import Iterable, Any

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer


def get_allowed_msgpack_modules() -> list[tuple[str, str]]:
    """Return the explicit msgpack allowlist for custom Pydantic schema objects used in the workflow state."""
    return [
        ("app.schemas.node_1_company", "CompanyResearchSchema"),
        ("app.schemas.node_1b_financial", "FinancialIntelligenceSchema"),
        ("app.schemas.node_2_stakeholder", "StakeholderIntelligenceSchema"),
        ("app.schemas.node_3_industry", "IndustryAnalysisSchema"),
        ("app.schemas.node_4_priorities", "BusinessPrioritiesSchema"),
        ("app.schemas.node_5_6_services", "ServiceMappingSchema"),
        ("app.schemas.node_5_6_services", "MatchedAssetSchema"),
    ]


def build_checkpoint_serializer() -> JsonPlusSerializer:
    """Build a serializer that permits the workflow’s custom schema classes in checkpoint payloads."""
    return JsonPlusSerializer(allowed_msgpack_modules=get_allowed_msgpack_modules())


def apply_checkpoint_serializer(checkpointer: Any) -> Any:
    """Attach the project-specific serializer to a LangGraph checkpointer if supported."""
    serializer = build_checkpoint_serializer()
    if hasattr(checkpointer, "serde"):
        checkpointer.serde = serializer
    if hasattr(checkpointer, "_serde"):
        checkpointer._serde = serializer
    return checkpointer
