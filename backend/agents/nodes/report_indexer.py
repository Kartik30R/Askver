import logging
from typing import Dict, Any

from langchain_core.documents import Document

from app.services.vector_service import index_documents_to_collection
from agents.state import DealIntelligenceState

logger = logging.getLogger(__name__)


def _safe_dump(obj: Any) -> Dict[str, Any]:
    """Helper to safely dump Pydantic objects to dicts for markdown mapping."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return obj or {}


def _cite(ids) -> str:
    ids = [i for i in (ids or []) if i]
    return " " + " ".join(f"[{i}]" for i in ids) if ids else ""


def generate_markdown_report(state: DealIntelligenceState) -> str:
    company = state.get("target_company", "N/A")
    industry = state.get("target_industry", "N/A")
    objective = state.get("meeting_objective", "N/A")
    pb = state.get("meeting_playbook") or {}
    ins = state.get("insight_synthesis") or {}
    fin = state.get("financial_snapshot") or {}
    pains = (_safe_dump(state.get("priorities_and_pain_points")) or {})
    assets = [_safe_dump(a) for a in (state.get("matched_internal_assets") or [])]
    maps = [_safe_dump(m) for m in (state.get("service_mappings") or [])]
    ver = state.get("verification_report") or {}

    out: list[str] = [f"# Meeting Playbook: {company}",
                      f"**Industry:** {industry}  \n**Meeting objective:** {objective}  \n"
                      f"**Overall confidence:** {pb.get('overall_confidence', 'n/a')}"]

    snap = pb.get("snapshot") or {}
    out += ["---", "## Executive Snapshot",
            f"**Situation:** {snap.get('situation', '')}{_cite(snap.get('fact_ids'))}",
            f"**Why now:** {snap.get('why_now', '')}",
            f"**Opening hook:** {snap.get('opening_hook', '')}",
            f"**Goal:** {snap.get('meeting_goal', '')}"]

    out += ["---", "## Agenda"] + [f"- {a.get('minutes')} min — **{a.get('topic')}**: {a.get('purpose')}" for a in pb.get("agenda", [])]

    out += ["---", "## Talking Points"]
    for tp in sorted(pb.get("talking_points", []), key=lambda t: t.get("sequence", 0)):
        out.append(f"{tp.get('sequence')}. **{tp.get('headline')}** ({tp.get('target_persona')}) — "
                   f"{tp.get('point')}{_cite(tp.get('fact_ids'))}")

    out += ["---", "## Discovery Questions"]
    for i, q in enumerate(pb.get("discovery_questions", [])):
        out += [f"{i + 1}. **[{q.get('stage')}]** {q.get('question')}",
                f"   - Why we ask: {q.get('why_we_ask')}",
                f"   - Listen for: {', '.join(q.get('listen_for', []))}",
                f"   - Follow-up: {q.get('follow_up')}"]

    out += ["---", "## Objections & Responses"]
    for o in pb.get("objections", []):
        out += [f"- **{o.get('objection')}** ({o.get('likelihood')}, raised by {o.get('raised_by')})",
                f"  - Real concern: {o.get('underlying_concern')}",
                f"  - Response: {o.get('response')}{_cite(o.get('fact_ids'))}"]

    out += ["---", "## Financial Snapshot"]
    if fin:
        out += [f"- {k.replace('_', ' ').title()}: {v}" for k, v in fin.items() if v not in (None, "", [], {})][:15]
    else:
        out.append("_No verified financial data (private company or data unavailable)._")

    out += ["---", "## Strategic Insights"]
    for i in ins.get("insights", []):
        out.append(f"- **{i.get('headline')}** — {i.get('so_what')}{_cite(i.get('fact_ids'))}")

    out += ["---", "## Pain Points"]
    for p in pains.get("pain_points", []):
        out.append(f"- **{p.get('category')}** ({p.get('severity')}, {p.get('urgency')}): {p.get('description')}"
                   f"{_cite(p.get('fact_ids'))}")

    out += ["---", "## Attendees"]
    for a in pb.get("attendees", []):
        out.append(f"- **{a.get('name') or a.get('role')}** — {a.get('buying_role')}: {a.get('approach')}")

    out += ["---", "## Proof Points & Service Fit"]
    for p in pb.get("proof_points", []):
        out.append(f"- {p.get('pain_point')} → asset `{p.get('asset_id')}`: {p.get('how_to_use')}")
    for m in maps:
        out.append(f"- Service: **{m.get('proposed_service') or m.get('client_need', '')}**")
    if assets and not pb.get("proof_points"):
        out += [f"- {a.get('asset_name') or a.get('title')}" for a in assets]

    pa = pb.get("pitch_and_ask") or {}
    out += ["---", "## Pitch & Ask", f"**60 seconds:** {pa.get('pitch_60_seconds', '')}",
            f"**The ask:** {pa.get('the_ask', '')}"]

    out += ["---", "## Deal Risks"] + [f"- {r}" for r in pb.get("deal_risks", [])]
    out += ["---", "## Known Gaps (verify in the room)"] + [f"- {g}" for g in pb.get("known_gaps", [])]
    out += ["---", "## Sources"]
    for sid, s in (state.get("sources") or {}).items():
        out.append(f"- [{sid}] {s.get('title', '')} — {s.get('url') or ''} (tier {s.get('tier', 4)})")
    return "\n".join(out)


def report_indexer_node(state: DealIntelligenceState) -> Dict[str, Any]:
    """
    Agent 8: Interactive Report Indexer & Document Exporter Node
    Compiles all state data into a Markdown report, indexes the report into PGVector
    for interactive Q&A follow-ups, and preserves all previous state data.
    """
    deal_id = state.get("deal_id", "")
    target_company = state.get("target_company", "")

    logger.info(f"Starting Report Indexer Node for Deal ID: '{deal_id}' ({target_company})")

    markdown_report = generate_markdown_report(state)

    if deal_id:
        report_document = Document(
            page_content=markdown_report,
            metadata={
                "deal_id": deal_id,
                "target_company": target_company,
                "document_category": "FINAL_INTELLIGENCE_REPORT",
                "source_type": "GENERATED_REPORT"
            }
        )
        try:
            index_documents_to_collection(f"deal_{deal_id}_reports", [report_document], pre_delete_collection=False)
            logger.info(f"Successfully indexed final report to collection deal_{deal_id}_reports")
        except Exception as e:
            logger.error(f"Failed to index final report to vector store: {str(e)}")

    return {
        "markdown_export": markdown_report,
        "node_statuses": {"report_indexing": "COMPLETED"}
    }