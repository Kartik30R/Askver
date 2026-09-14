from typing import Annotated, TypedDict, List, Dict, Any, Optional
from datetime import datetime





def append_instructions(existing: Optional[List[str]], new: Optional[List[str]]) -> Optional[List[str]]:
    """Append new dynamic instructions to existing list."""
    if not existing:
        existing = []
    if new:
        existing.extend(new)
    return existing if existing else None


class DealIntelligenceState(TypedDict):
    # =====================================================================
    # 1. INPUTS
    # =====================================================================
    deal_id: str
    target_company: str
    target_industry: str
    meeting_objective: str
    client_documents_path: Optional[str]

    # -------------------------------------------------------------
    # 2. AGENT 1: Company Intelligence
    # -------------------------------------------------------------
    company_overview: Dict[str, Any]      # Profile, Business Model, Revenue Sources
    leadership_team: List[Dict[str, Any]]
    digital_initiatives: List[Dict[str, Any]]
    technology_investments: List[Dict[str, Any]]
    recent_news_and_m_and_a: List[Dict[str, Any]]  # News, Acquisitions, Partnerships

    # -------------------------------------------------------------
    # 2A. AGENT 1B: Financial Intelligence
    # -------------------------------------------------------------
    financial_intelligence: Dict[str, Any]

    # -------------------------------------------------------------
    # 3. AGENT 2: Stakeholder Intelligence
    # -------------------------------------------------------------
    stakeholder_profiles: Dict[str, Dict[str, List[str]]] 
    # Keys: CEO, CIO, CTO, CDO, CISO, CFO
    # Values: {"likely_goals": [...], "likely_concerns": [...], "business_drivers": [...]}

    # -------------------------------------------------------------
    # 4. AGENT 3: Industry Intelligence
    # -------------------------------------------------------------
    industry_analysis: Dict[str, Any]     # Trends, Regulatory Compliance, Risks, Opportunities

    # -------------------------------------------------------------
    # 5. AGENT 4: Business Priorities & Pain Points
    # -------------------------------------------------------------
    business_priorities: List[str]        # Cost Optimization, Digital Transformation, etc.
    detected_pain_points: List[Dict[str, Any]] # Legacy Systems, Slow Release Cycles, High Cost

    # -------------------------------------------------------------
    # 6. AGENT 5: Enterprise Knowledge Hub RAG
    # -------------------------------------------------------------
    matched_internal_assets: List[Dict[str, Any]] # Case Studies, Proposals, Success Stories, SoWs
    matched_client_rfp_chunks: List[Dict[str, Any]]

    # =====================================================================
    # 7. AGENT 6: Service Mapping Engine
    # =====================================================================
    service_mappings: List[Dict[str, Any]] # Need -> Offering -> Proof Point -> Expected Impact

    # =====================================================================
    # 8. EXECUTION CONTROL & HITL STATE
    # =====================================================================
    # Pause/Resume control
    pause_requested: bool  # User requested workflow pause
    manual_pause_at_node: Optional[str]  # Node name where user paused execution
    
    # Dynamic steering: real-time instructions merged into active node
    dynamic_instructions: Annotated[Optional[List[str]], append_instructions]
    
    # Mandatory review gate before CXO brief generation
    mandatory_review_checkpoint: str  # "pending", "approved", "rejected", "needs_revision"
    
    # Human-in-the-Loop approval state
    human_approved: bool
    human_feedback: Optional[str]
    custom_selected_assets: Optional[List[str]]
    
    # Execution tracking
    current_step: Optional[str]  # Current node or status name
    execution_paused_at: Optional[datetime]  # Timestamp when paused
    last_execution_resumption: Optional[datetime]  # Timestamp when resumed
    
    node_statuses: Annotated[Dict[str, str], merge_statuses]
    errors: Optional[List[str]]
    
    # =====================================================================
    # 9. AGENT 7 & 8: CXO Final Brief Deliverable
    # =====================================================================
    cxo_executive_brief: Dict[str, Any]
    # Includes: Executive Summary, Talking Points, Questions to Ask, 
    # Objections & Responses, Executive Pitch

    markdown_export: Optional[str] = None

