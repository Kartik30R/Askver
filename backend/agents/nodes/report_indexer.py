import os
import json
import logging
from typing import Dict, Any, List

from langchain_core.documents import Document

from app.agents.state import DealIntelligenceState
from app.services.vector_service import index_client_deal_chunks

logger = logging.getLogger(__name__)


def generate_markdown_report(state: DealIntelligenceState) -> str:
    """
    Synthesizes all state information from Nodes 1-7 into a clean, 
    publication-ready Markdown report.
    """
    target_company = state.get("target_company", "N/A")
    target_industry = state.get("target_industry", "N/A")
    meeting_objective = state.get("meeting_objective", "N/A")

    cxo_brief = state.get("cxo_executive_brief", {})
    company_overview = state.get("company_overview", {})
    leadership_team = state.get("leadership_team", [])
    stakeholder_profiles = state.get("stakeholder_profiles", {})
    industry_analysis = state.get("industry_analysis", {})
    business_priorities = state.get("business_priorities", [])
    detected_pain_points = state.get("detected_pain_points", [])
    matched_internal_assets = state.get("matched_internal_assets", [])
    service_mappings = state.get("service_mappings", [])

    md_lines = []

    # Document Header
    md_lines.append(f"# Executive Deal Intelligence Report: {target_company}")
    md_lines.append(f"**Industry:** {target_industry} | **Objective:** {meeting_objective}\n")
    md_lines.append("---")

    # Section 1: Executive Strategy Brief (Node 7)
    md_lines.append("\n## 1. Executive Strategy Brief")
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
            if isinstance(obj_item, dict):
                for obj, resp in obj_item.items():
                    md_lines.append(f"- **Objection:** *\"{obj}\"*\n  - **Response:** {resp}")
    else:
        md_lines.append("Executive brief unavailable.")

    md_lines.append("\n---")

    # Section 2: Business Priorities & Pain Points (Node 4)
    md_lines.append("\n## 2. Business Priorities & Detected Pain Points")
    if business_priorities:
        md_lines.append("### Strategic Priorities")
        for prio in business_priorities:
            md_lines.append(f"- {prio}")

    if detected_pain_points:
        md_lines.append("\n### Identified Bottlenecks & Operational Friction")
        for pp in detected_pain_points:
            cat = pp.get("category", "General")
            desc = pp.get("description", "")
            sev = pp.get("severity", "MEDIUM")
            area = pp.get("impacted_business_area", "N/A")
            md_lines.append(f"#### [{sev}] {cat} - *{area}*")
            md_lines.append(f"{desc}\n")

    md_lines.append("---")

    # Section 3: Service Mappings & Internal Proof Assets (Nodes 5 & 6)
    md_lines.append("\n## 3. Recommended Solution Architecture & Service Mapping")
    if service_mappings:
        for sm in service_mappings:
            need = sm.get("client_need", "")
            bot = sm.get("detected_bottleneck", "")
            offering = sm.get("recommended_offering", "")
            impact = sm.get("expected_business_impact", "")
            proof_assets = sm.get("supporting_proof_assets", [])

            md_lines.append(f"### Offering: {offering}")
            md_lines.append(f"- **Client Need:** {need}")
            md_lines.append(f"- **Root Bottleneck:** {bot}")
            md_lines.append(f"- **Expected ROI / Business Impact:** {impact}")
            if proof_assets:
                md_lines.append("- **Supporting Proof Assets:**")
                for asset in proof_assets:
                    name = asset.get("asset_name", asset.get("title", "Internal Asset"))
                    atype = asset.get("asset_type", "CASE_STUDY")
                    summary = asset.get("summary", "")
                    md_lines.append(f"  - *[{atype}] {name}*: {summary}")
            md_lines.append("")

    md_lines.append("---")

    # Section 4: Stakeholder Persona Intelligence (Node 2)
    md_lines.append("\n## 4. Stakeholder Persona Intelligence")
    if stakeholder_profiles:
        for role, data in stakeholder_profiles.items():
            md_lines.append(f"### Persona: {role}")
            goals = ", ".join(data.get("likely_goals", []))
            concerns = ", ".join(data.get("likely_concerns", []))
            drivers = ", ".join(data.get("business_drivers", []))
            md_lines.append(f"- **Primary Goals:** {goals}")
            md_lines.append(f"- **Key Concerns:** {concerns}")
            md_lines.append(f"- **Business Drivers:** {drivers}\n")

    md_lines.append("---")

    # Section 5: Target Company Overview & Leadership (Node 1)
    md_lines.append("\n## 5. Target Company Background")
    if company_overview:
        profile = company_overview.get("profile", {})
        if isinstance(profile, dict):
            md_lines.append(f"{profile.get('detailed_narrative', '')}\n")
    
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

    # 1. Synthesize full Markdown report from accumulated state
    markdown_report = generate_markdown_report(state)

    # 2. Index final Markdown report into the deal's PGVector collection for Q&A capability
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
            index_client_deal_chunks(deal_id=deal_id, chunks=[report_document])
            logger.info(f"Successfully indexed final report to PGVector for deal {deal_id}")
        except Exception as e:
            logger.error(f"Failed to index final report to vector store: {str(e)}")

    logger.info(f"Completed Report Indexer Node for deal '{deal_id}'")

    # Return updated state additions (preserving all state inputs from Nodes 1-7)
    return {
        "markdown_export": markdown_report,
        "current_step": "REPORT_INDEXING_COMPLETED"
    }