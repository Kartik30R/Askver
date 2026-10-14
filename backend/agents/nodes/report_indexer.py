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


def generate_markdown_report(state: DealIntelligenceState) -> str:
    """
    Synthesizes all state information from Nodes 1-7 into a clean, 
    publication-ready Markdown report.
    """
    target_company = state.get("target_company", "N/A")
    target_industry = state.get("target_industry", "N/A")
    meeting_objective = state.get("meeting_objective", "N/A")

    # Safely dump Pydantic objects to dicts for markdown parsing
    cxo_brief = _safe_dump(state.get("cxo_executive_brief"))
    financial_intel = _safe_dump(state.get("financial_intelligence"))
    company_research = _safe_dump(state.get("company_research"))
    stakeholder_intel = _safe_dump(state.get("stakeholder_intelligence"))
    industry_analysis = _safe_dump(state.get("industry_analysis"))
    priorities = _safe_dump(state.get("priorities_and_pain_points"))
    
    # Lists of Pydantic models
    matched_assets = [_safe_dump(a) for a in (state.get("matched_internal_assets") or [])]
    service_mappings = [_safe_dump(sm) for sm in (state.get("service_mappings") or [])]
    md_lines = []

    # Document Header
    md_lines.append(f"# Executive Deal Intelligence Report: {target_company}")
    md_lines.append(f"**Industry:** {target_industry} | **Objective:** {meeting_objective}\n")
    md_lines.append("---")

       # Section 1: Financial Intelligence
    md_lines.append("\n## 1. Financial Intelligence")
    if financial_intel:
        md_lines.append(
            f"### Company Financial Status: "
            f"{financial_intel.get('status', 'not_listed').upper()}"
        )
        md_lines.append(f"- **Ticker:** {financial_intel.get('symbol') or 'N/A'}")
        md_lines.append(f"- **Market:** {financial_intel.get('market', 'USA')}")
        md_lines.append(
            f"- **Overall Financial Score:** "
            f"{financial_intel.get('overall_score_10', 'N/A')}"
        )
        md_lines.append(
            f"- **Market Cap Tier:** "
            f"{financial_intel.get('market_cap_category', 'Unknown')}"
        )
        md_lines.append(
            f"\n{financial_intel.get('ai_summary', 'Financial summary unavailable.')}"
        )

        for c in financial_intel.get("financial_concerns") or []:
            md_lines.append(f"- ⚠ {c}")
    else:
        md_lines.append("Financial intelligence unavailable.")

    md_lines.append("\n---")

    # Section 2: Executive Strategy Brief 
    md_lines.append("\n## 2. Executive Strategy Brief")
    if cxo_brief:
        md_lines.append(f"### Executive Summary\n{cxo_brief.get('executive_summary', 'N/A')}\n")
        md_lines.append(f"### 60-Second Pitch\n> {cxo_brief.get('executive_pitch', 'N/A')}\n")
        
        md_lines.append("### Key CXO Talking Points")
        for tp in cxo_brief.get("talking_points", []):
            md_lines.append(f"- {tp}")
        
        md_lines.append("\n### Strategic Discovery Questions")
        for q in cxo_brief.get("questions_to_ask", []):
            md_lines.append(f"- {q}")

        md_lines.append("\n### Objection Handling Matrix")
        for obj_item in cxo_brief.get("objections_and_responses", []):
            objection = obj_item.get("objection", list(obj_item.keys())[0] if isinstance(obj_item, dict) and obj_item else "N/A")
            response = obj_item.get("response", list(obj_item.values())[0] if isinstance(obj_item, dict) and obj_item else "N/A")
            md_lines.append(f"- **Objection:** *\"{objection}\"*\n  - **Response:** {response}")
    else:
        md_lines.append("Executive brief unavailable.")

    md_lines.append("\n---")

    # Section 3: Business Priorities & Pain Points 
    md_lines.append("\n## 3. Business Priorities & Detected Pain Points")
    if priorities:
        md_lines.append("### Strategic Priorities")
        for prio in priorities.get("priorities", []):
            md_lines.append(f"- {prio}")

        md_lines.append("\n### Identified Bottlenecks")
        for pp in priorities.get("pain_points", []):
            cat = pp.get("category", "General")
            desc = pp.get("description", "")
            sev = pp.get("severity", "MEDIUM")
            md_lines.append(f"#### [{sev}] {cat}")
            md_lines.append(f"{desc}\n")

    md_lines.append("---")

    # Section 4: Solution Architecture & Matched Proof Assets
    md_lines.append("\n## 4. Recommended Solution Architecture & Proof Assets")
    if service_mappings:
        md_lines.append("### Service Mappings")
        for sm in service_mappings:
            need = sm.get("client_need", "")
            bot = sm.get("detected_bottleneck", "")
            offering = sm.get("recommended_offering", "")
            impact = sm.get("expected_business_impact", "")
            proof_assets = sm.get("supporting_proof_assets", [])

            md_lines.append(f"#### Offering: {offering}")
            md_lines.append(f"- **Client Need:** {need}")
            if bot:
                md_lines.append(f"- **Root Bottleneck:** {bot}")
            md_lines.append(f"- **Expected ROI:** {impact}")
            if proof_assets:
                md_lines.append("- **Supporting Proof Assets:**")
                for asset in proof_assets:
                    name = asset.get("asset_name", asset.get("title", "Internal Asset"))
                    atype = asset.get("asset_type", "CASE_STUDY")
                    summary = asset.get("summary", "")
                    md_lines.append(f"  - *[{atype}] {name}*: {summary}")
            md_lines.append("")

    # ACCESSED: Render global matched internal assets from Node 5
    if matched_assets:
        md_lines.append("\n### Internal Knowledge Base Proof Assets (RAG Results)")
        for asset in matched_assets:
            name = asset.get("asset_name", asset.get("title", "Matched Asset"))
            atype = asset.get("asset_type", "CASE_STUDY")
            summary = asset.get("summary", "")
            metrics = asset.get("key_metrics_achieved", [])
            metrics_str = f" | **Key Metrics:** {', '.join(metrics)}" if metrics else ""
            md_lines.append(f"- **[{atype}] {name}**: {summary}{metrics_str}")

    md_lines.append("\n---")

    # ACCESSED: Section 5 - Industry Analysis & Regulatory Environment (Node 3)
    md_lines.append("\n## 5. Industry Trends & Compliance Drivers")

    if industry_analysis:
        for key, title in (
            ("major_trends", "Industry Trends & Disruption"),
            ("regulatory_compliance", "Regulatory & Compliance Mandates"),
            ("risks_and_challenges", "Risks & Challenges"),
            ("technology_benchmarks", "Technology Benchmarks"),
        ):
            items = industry_analysis.get(key) or []
            if items:
                md_lines.append(f"\n### {title}")
                for p in items:
                    md_lines.append(
                        f"- **{p.get('headline', '')}**: "
                        f"{p.get('detailed_narrative', '')}"
                    )
    else:
        md_lines.append("Industry analysis unavailable.")

    md_lines.append("\n---")


    # Section 6: Stakeholder Persona Intelligence (Node 2)
    md_lines.append("\n## 6. Stakeholder Persona Intelligence")
    if stakeholder_intel:
        personas = stakeholder_intel.get("personas", [])
        
        if personas:
            for p in personas:
                role = p.get("role", "N/A")
                md_lines.append(f"### Persona: {role}")
                goals = ", ".join(p.get("likely_goals", []))
                concerns = ", ".join(p.get("likely_concerns", []))
                drivers = ", ".join(p.get("business_drivers", []))
                md_lines.append(f"- **Primary Goals:** {goals}")
                md_lines.append(f"- **Key Concerns:** {concerns}")
                md_lines.append(f"- **Business Drivers:** {drivers}\n")
        else:
            for role, data in stakeholder_intel.items():
                if isinstance(data, dict):
                    md_lines.append(f"### Persona: {role}")
                    goals = ", ".join(data.get("likely_goals", []))
                    concerns = ", ".join(data.get("likely_concerns", []))
                    drivers = ", ".join(data.get("business_drivers", []))
                    md_lines.append(f"- **Primary Goals:** {goals}")
                    md_lines.append(f"- **Key Concerns:** {concerns}")
                    md_lines.append(f"- **Business Drivers:** {drivers}\n")

    md_lines.append("---")

    # Section 7: Target Company Background & Leadership (Node 1)
    md_lines.append("\n## 7. Target Company Background")
    if company_research:
        overview = company_research.get("overview") or {}

        for key, label in (
            ("summary", "Summary"),
            ("business_model", "Business Model"),
        ):
            p = overview.get(key) or {}
            if p:
                md_lines.append(
                    f"**{label}:** {p.get('headline', '')}. "
                    f"{p.get('detailed_narrative', '')}\n"
                )

        if overview.get("headquarters"):
            md_lines.append(f"**Headquarters:** {overview['headquarters']}\n")

        leadership_team = company_research.get("leadership_team") or []
        if leadership_team:
            md_lines.append("### Identified Executive Leadership")
            for leader in leadership_team:
                name = leader.get("Name", leader.get("name", "N/A"))
                role = leader.get("Role", leader.get("role", "N/A"))
                bg = leader.get("Key Background", leader.get("background", ""))
                md_lines.append(f"- **{name}** ({role}): {bg}")
    return "\n".join(md_lines)


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