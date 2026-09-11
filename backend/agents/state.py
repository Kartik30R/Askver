from typing import TypedDict, List, Dict, Any, Optional

class DealIntelligenceState(TypedDict):
    # -------------------------------------------------------------
    # 1. INPUTS
    # -------------------------------------------------------------
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

    # -------------------------------------------------------------
    # 7. AGENT 6: Service Mapping Engine
    # -------------------------------------------------------------
    service_mappings: List[Dict[str, Any]] # Need -> Offering -> Proof Point -> Expected Impact

    # -------------------------------------------------------------
    # 8. HUMAN-IN-THE-LOOP CONTROL
    # -------------------------------------------------------------
    human_approved: bool
    human_feedback: Optional[str]
    custom_selected_assets: Optional[List[str]]
    markdown_export: Optional[str]

    # -------------------------------------------------------------
    # 9. AGENT 7 & 8: CXO Final Brief Deliverable
    # -------------------------------------------------------------
    cxo_executive_brief: Dict[str, Any]
    # Includes: Executive Summary, Talking Points, Questions to Ask, 
    # Objections & Responses, Executive Pitch

    current_step: str
    errors: Optional[List[str]]