import operator
from typing import Annotated, TypedDict, List, Dict, Optional
from datetime import datetime

from app.schemas.evidence import merge_facts, merge_sources

# Import the strict Pydantic schemas
from app.schemas.node_1_company import CompanyResearchSchema
from app.schemas.node_1b_financial import FinancialIntelligenceSchema
from app.schemas.node_2_stakeholder import StakeholderIntelligenceSchema
from app.schemas.node_3_industry import IndustryAnalysisSchema
from app.schemas.node_4_priorities import BusinessPrioritiesSchema
from app.schemas.node_5_6_services import MatchedAssetSchema, ServiceMappingSchema
from app.schemas.node_7_brief import MeetingStrategySchema
from app.schemas.node_7_brief import CXOExecutiveBriefSchema


def append_instructions(existing, new):
    if new is None:
        return existing
    if new == []:
        return None
    return list(existing or []) + list(new)


def merge_statuses(left: Dict[str, str], right: Dict[str, str]) -> Dict[str, str]:
    merged = left.copy() if left else {}
    if right:
        merged.update(right)
    return merged


def append_errors(existing: Optional[List[str]], new: Optional[List[str]]) -> Optional[List[str]]:
    """Merge error messages while tolerating a missing prior list value."""
    merged = list(existing or [])
    if new:
        merged.extend(new)
    return merged if merged else None


class DealIntelligenceState(TypedDict):
    # =====================================================================
    # 1. INPUTS
    # =====================================================================
    deal_id: str
    target_company: str
    target_industry: str
    meeting_objective: str
    client_documents_path: Optional[str]
    research_depth: Optional[str]

    # =====================================================================
    # 2. RESEARCH LAYER OUTPUTS
    # =====================================================================
    research_plan: Optional[dict]
    sources: Annotated[Dict[str, dict], merge_sources]
    facts: Annotated[Dict[str, dict], merge_facts]
    research_gaps: Annotated[Optional[List[str]], append_errors]
    financial_snapshot: Optional[dict]
    strategic_frameworks: Optional[dict]
    commercial_frameworks: Optional[dict]
    research_pass: Optional[int]
    evidence_report: Optional[dict]
    insight_synthesis: Optional[dict]
    verification_report: Optional[dict]
    playbook_questions: Optional[dict]
    playbook_room: Optional[dict]
    meeting_duration_minutes: Optional[int]
    meeting_playbook: Optional[dict]

    # =====================================================================
    # 3. STRICTLY TYPED AGENT OUTPUTS
    # =====================================================================
    company_research: Optional[CompanyResearchSchema]
    financial_intelligence: Optional[FinancialIntelligenceSchema]
    stakeholder_intelligence: Optional[StakeholderIntelligenceSchema]
    industry_analysis: Optional[IndustryAnalysisSchema]
    priorities_and_pain_points: Optional[BusinessPrioritiesSchema]
    matched_internal_assets: Optional[List[MatchedAssetSchema]]
    service_mappings: Optional[List[ServiceMappingSchema]]
    cxo_executive_brief: Optional[CXOExecutiveBriefSchema]
    
    markdown_export: Optional[str]

    # =====================================================================
    # 3. EXECUTION CONTROL & HITL STATE
    # =====================================================================
    pause_requested: bool
    manual_pause_at_node: Optional[str]
    
    dynamic_instructions: Annotated[Optional[List[str]], append_instructions]
    mandatory_review_checkpoint: str  
    
    human_approved: bool
    human_feedback: Optional[str]
    custom_selected_assets: Optional[List[str]]
    
    current_step: Optional[str]
    execution_paused_at: Optional[datetime]
    last_execution_resumption: Optional[datetime]
    
    node_statuses: Annotated[Dict[str, str], merge_statuses]
    errors: Annotated[Optional[List[str]], append_errors]