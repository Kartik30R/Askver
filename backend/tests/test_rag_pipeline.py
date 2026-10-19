from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.services import chat_service, vector_service
from app.services.deal_service import DealService
from app.services.document_parser import parse_and_chunk_document
from app.services.hitl_manager import HITLManager
from app.schemas.hitl import WorkflowStateSnapshot
from agents.graph import route_after_review_decision
from agents.state import append_errors, append_instructions
from agents.tools import financial_tool
from agents.tools.search_tool import search_news
from app.utils.checkpoint_serialization import get_allowed_msgpack_modules


def test_parse_and_chunk_document_supports_markdown_files(tmp_path):
    file_path = tmp_path / "research.md"
    file_path.write_text(
        "# Strategy brief\n\n"
        "This is a detailed paragraph about customer onboarding and workflow automation.\n\n"
        "Another paragraph about digital sales enablement, enterprise governance, and delivery risk.\n\n"
        + "\n".join(["Text line about transformation and governance."] * 20),
        encoding="utf-8",
    )

    chunks = parse_and_chunk_document(str(file_path), "md", {"source": "tests"})

    assert chunks
    assert all(chunk.page_content for chunk in chunks)
    assert all(chunk.metadata.get("source") == "tests" for chunk in chunks)


def test_get_embeddings_model_sets_retrieval_task_type(monkeypatch):
    captured: dict[str, object] = {}

    class DummyEmbeddings:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(vector_service, "GEMINI_API_KEY", "demo-key")
    monkeypatch.setattr(vector_service, "GoogleGenerativeAIEmbeddings", DummyEmbeddings)

    model = vector_service.get_embeddings_model(task_type="retrieval_query")

    assert isinstance(model, DummyEmbeddings)
    assert captured["model"] == "gemini-embedding-001"
    assert captured["google_api_key"] == "demo-key"
    assert captured["task_type"] == "retrieval_query"


def test_pgvector_uses_jsonb_metadata_for_indexing_and_queries(monkeypatch):
    captured: dict[str, object] = {}

    class DummyPGVector:
        def __init__(self, **kwargs):
            captured.setdefault("ctor", {}).update(kwargs)

        def similarity_search_with_score(self, *args, **kwargs):
            captured.setdefault("query", {}).update(kwargs)
            return []

        @classmethod
        def from_documents(cls, **kwargs):
            captured.setdefault("from_documents", {}).update(kwargs)
            return cls(**kwargs)

    monkeypatch.setattr(vector_service, "PGVector", DummyPGVector)
    monkeypatch.setattr(vector_service, "DATABASE_URL", "postgresql://example", raising=False)
    monkeypatch.setattr(vector_service, "GEMINI_API_KEY", "demo-key")

    documents = [
        {
            "page_content": "sample text",
            "metadata": {"title": "sample"},
        }
    ]

    result = vector_service._sync_index_documents(
        embeddings=object(),
        documents=[__import__("langchain_core.documents", fromlist=["Document"]).Document(**doc) for doc in documents],
        collection_name="demo_collection",
    )

    vector_service.query_internal_knowledge_base("sample", top_k=3)

    assert result == "demo_collection"
    assert captured["from_documents"].get("use_jsonb") is True
    assert captured["ctor"].get("use_jsonb") is True
    assert captured["query"].get("k") == 3


def test_append_instructions_reducer_behavior():
    assert append_instructions(None, ["a"]) == ["a"]
    assert append_instructions(["a"], None) == ["a"]
    assert append_instructions(["a"], []) is None


def test_workflow_state_accepts_targeted_instruction_objects():
    payload = {
        "deal_id": "deal-123",
        "dynamic_instructions": [
            {"text": "Focus on expansion markets", "target_nodes": ["service_mapper"]},
            "Keep the executive brief concise",
        ],
        "target_nodes": ["service_mapper"],
        "rerun_from_node": "service_mapper",
    }

    state = WorkflowStateSnapshot.model_validate(payload)

    assert state.dynamic_instructions[0]["text"] == "Focus on expansion markets"
    assert state.target_nodes == ["service_mapper"]
    assert state.rerun_from_node == "service_mapper"


def test_append_errors_handles_none_existing_list():
    assert append_errors(None, ["node failed"]) == ["node failed"]
    assert append_errors(["a"], None) == ["a"]
    assert append_errors(None, None) is None
    assert append_errors(["a"], ["b", "c"]) == ["a", "b", "c"]


def test_deal_service_hydrates_rerun_state_before_node_execution():
    state = {
        "target_company": "Acme",
        "target_industry": "Industrial software",
        "meeting_objective": "Find AI use cases",
        "priorities_and_pain_points": {
            "priorities": [],
            "pain_points": [{
                "title": "fragmented data",
                "description": "customer data is fragmented",
                "impact": "slows decisions",
                "category": "data",
            }],
        },
        "matched_internal_assets": [],
    }

    hydrated = DealService._hydrate_run_state_static(state)

    assert hasattr(hydrated["priorities_and_pain_points"], "pain_points")
    assert hydrated["priorities_and_pain_points"].pain_points[0].title == "fragmented data"


def test_route_after_review_decision_handles_pending_review_without_error():
    assert route_after_review_decision({"mandatory_review_checkpoint": "pending"}) == "wait_for_review"
    assert route_after_review_decision({"mandatory_review_checkpoint": "approved"}) == "proceed_to_brief"
    assert route_after_review_decision({"mandatory_review_checkpoint": "needs_revision"}) == "wait_for_review"
    assert route_after_review_decision({"mandatory_review_checkpoint": "rejected"}) == "end"


def test_pipeline_owner_guard_rejects_non_owner():
    from app.api.v1.controllers.pipeline_controller import ensure_deal_owned_by_user
    from uuid import uuid4
    from fastapi import HTTPException

    class DummyUser:
        id = uuid4()

    class DummyDeal:
        owner_id = uuid4()

    try:
        ensure_deal_owned_by_user(DummyDeal(), DummyUser())
        assert False, "Expected HTTP 403 for non-owner access"
    except HTTPException as exc:
        assert exc.status_code == 403


def test_approve_text_edit_updates_report_snapshot_for_active_version():
    proposal_id = uuid4()
    chat_service.ACTIVE_EDIT_PROPOSALS = {str(proposal_id): {
        "deal_id": str(uuid4()),
        "section": "general",
        "proposed_text": "Updated executive brief",
    }}

    latest_state = {
        "markdown_export": "Old executive brief",
        "current_step": "COMPLETED",
        "node_statuses": {"cxo_brief_generator": "COMPLETED"},
    }
    saved = {}

    service = chat_service.ChatService.__new__(chat_service.ChatService)

    async def get_latest_intelligence_snapshot(deal_id):
        return SimpleNamespace(
            version=3,
            thread_id="thread-1",
            current_step="COMPLETED",
            snapshot_data=latest_state,
        )

    async def save_intelligence_snapshot(**kwargs):
        saved.update(kwargs)
        return SimpleNamespace(version=4)

    service.intel_repo = SimpleNamespace(
        get_latest_intelligence_snapshot=get_latest_intelligence_snapshot,
        save_intelligence_snapshot=save_intelligence_snapshot,
    )

    async def run_test():
        result = await service.approve_text_edit(uuid4(), proposal_id, approved=True)
        assert result.approved is True
        assert saved.get("snapshot_data", {}).get("markdown_export") == "Updated executive brief"

    asyncio.run(run_test())


def test_get_company_financials_uses_actual_exchange_from_yahoo(monkeypatch):
    class DummyTicker:
        info = {
            "longName": "Reliance Industries",
            "marketCap": 200_000_000_000,
            "currency": "INR",
            "exchange": "NSE",
            "fullExchangeName": "National Stock Exchange of India",
            "totalRevenue": 1_000_000_000,
            "revenueGrowth": 0.12,
            "grossMargins": 0.38,
            "operatingMargins": 0.18,
            "ebitda": 200_000_000,
            "freeCashflow": 150_000_000,
        }

    monkeypatch.setattr("agents.tools.financial_tool.resolve_company_symbol", lambda query: "RELIANCE.NS")
    monkeypatch.setattr("agents.tools.financial_tool.yf.Ticker", lambda symbol: DummyTicker())

    result = financial_tool.get_company_financials("Reliance Industries")

    assert result["market"] == "NSE"
    assert "NSE" in result["ai_summary"]


def test_search_news_uses_direct_web_search_first(monkeypatch):
    class DummyDDGS:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def news(self, *args, **kwargs):
            return []

    monkeypatch.setattr("agents.tools.search_tool.DDGS", lambda: DummyDDGS())
    monkeypatch.setattr(
        "agents.tools.search_tool.search_web",
        lambda *args, **kwargs: [{"title": "fallback", "url": "https://example.com", "snippet": "fallback snippet"}],
    )

    results = search_news("example query")

    assert results
    assert results[0]["title"] == "fallback"
    assert results[0]["source_type"] == "WEB_SEARCH"


def test_report_routes_do_not_expose_version_history_or_revert():
    from app.api.v1.controllers import reports_controller

    route_paths = {route.path for route in reports_controller.router.routes}

    assert "/versions" not in route_paths
    assert "/revert/{snapshot_id}" not in route_paths


def test_checkpoint_serializer_allows_project_schema_types():
    allowed = get_allowed_msgpack_modules()
    assert ("app.schemas.node_1_company", "CompanyResearchSchema") in allowed
    assert ("app.schemas.node_1b_financial", "FinancialIntelligenceSchema") in allowed
    assert ("app.schemas.node_3_industry", "IndustryAnalysisSchema") in allowed
    assert ("app.schemas.node_2_stakeholder", "StakeholderIntelligenceSchema") in allowed
    assert ("app.schemas.node_4_priorities", "BusinessPrioritiesSchema") in allowed
    assert ("app.schemas.node_5_6_services", "ServiceMappingSchema") in allowed
