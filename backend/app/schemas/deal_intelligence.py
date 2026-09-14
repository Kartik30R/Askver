from pydantic import BaseModel, HttpUrl, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID


# ==========================================
# REUSABLE CITATION & DRILL-DOWN SCHEMAS
# ==========================================

class SourceCitation(BaseModel):
    title: str = Field(description="Title of the source document or web article")
    url: Optional[str] = Field(default=None, description="URL if sourced from public web")
    snippet: str = Field(description="Relevant text excerpt or quote from the source")
    source_type: str = Field(description="e.g., 'WEB_NEWS', '10K_FILING', 'INTERNAL_CASE_STUDY', 'CLIENT_RFP'")


class DetailedPoint(BaseModel):
    headline: str = Field(description="Concise summary bullet point")
    detailed_narrative: str = Field(description="Expanded paragraph explaining the bullet point in detail")
    citations: List[SourceCitation] = Field(default_factory=list, description="Source references")


# ==========================================
# AGENT SPECIFIC SCHEMAS
# ==========================================

# Agent 1A: Financial Intelligence
class FinancialMetricScore(BaseModel):
    metric_name: str
    value: Optional[Any] = None
    score: int = Field(default=0, description="0-100 score for the metric")
    status: str = Field(default="unavailable", description="available, unavailable, not_listed")
    notes: str = Field(default="", description="Grounded notes from the real data source")

class FinancialIntelligenceSchema(BaseModel):
    company_name: str
    symbol: Optional[str] = None
    status: str = Field(default="not_listed", description="listed, not_listed")
    market: str = Field(default="USA")
    availability: str = Field(default="unavailable", description="available or unavailable")
    data_source: str = Field(default="yfinance")
    overall_score: int = Field(default=0)
    ai_summary: str
    metric_scores: List[FinancialMetricScore]


# Agent 1B: Company Research
class CompanyOverviewSchema(BaseModel):
    profile: DetailedPoint
    business_model: DetailedPoint
    revenue_streams: List[DetailedPoint]

class CompanyResearchSchema(BaseModel):
    overview: CompanyOverviewSchema
    leadership_team: List[Dict[str, str]]  # Name, Role, Key Background
    digital_initiatives: List[DetailedPoint]
    technology_investments: List[DetailedPoint]
    recent_news_and_m_and_a: List[DetailedPoint]


# Agent 2: Stakeholder Intelligence
class StakeholderPersonaSchema(BaseModel):
    role: str = Field(description="e.g., CEO, CIO, CTO, CDO, CISO, CFO")
    likely_goals: List[str]
    likely_concerns: List[str]
    business_drivers: List[str]

class StakeholderIntelligenceSchema(BaseModel):
    personas: List[StakeholderPersonaSchema]


# Agent 3: Industry Analysis
class IndustryAnalysisSchema(BaseModel):
    major_trends: List[DetailedPoint]
    regulatory_compliance: List[DetailedPoint]
    risks_and_challenges: List[DetailedPoint]
    technology_benchmarks: List[DetailedPoint]


# Agent 4: Pain Points & Priorities
class PainPointSchema(BaseModel):
    category: str = Field(description="e.g., Legacy Systems, Fragmented Apps, Slow Cycles, Cost")
    description: str
    severity: str = Field(description="HIGH, MEDIUM, LOW")
    impacted_business_area: str

class BusinessPrioritiesSchema(BaseModel):
    priorities: List[str]
    pain_points: List[PainPointSchema]


# Agent 5: Enterprise Knowledge RAG
class MatchedAssetSchema(BaseModel):
    asset_id: str
    asset_name: str
    asset_type: str = Field(description="CASE_STUDY, PROPOSAL, SOW, SUCCESS_STORY, PRESENTATION")
    relevance_score: float
    key_metrics_achieved: List[str]
    summary: str


# Agent 6: Service Mapping Engine
class ServiceMappingSchema(BaseModel):
    client_need: str
    detected_bottleneck: str
    recommended_offering: str
    supporting_proof_assets: List[MatchedAssetSchema]
    expected_business_impact: str


# Agent 7: CXO Final Brief
class MeetingStrategySchema(BaseModel):
    executive_summary: str
    talking_points: List[str]
    questions_to_ask: List[str]
    objections_and_responses: List[Dict[str, str]]  # Key: objection, Value: response
    executive_pitch: str


# ==========================================
# MASTER RESPONSE & TRIGGER DTOS
# ==========================================

class TriggerIntelligenceRequest(BaseModel):
    target_company: str
    target_industry: str
    meeting_objective: str
    client_documents_path: Optional[str] = None


class HumanApprovalRequest(BaseModel):
    approved: bool
    feedback: Optional[str] = None
    custom_selected_assets: Optional[List[str]] = None
    service_mappings: Optional[List[ServiceMappingSchema]] = None


class DealIntelligenceResponse(BaseModel):
    deal_id: UUID
    version: int
    thread_id: str
    node_statuses: Dict[str, str] = Field(default_factory=dict, description="Tracks status per node (e.g., 'company_research': 'COMPLETED')")
    company_research: Optional[CompanyResearchSchema] = None
    stakeholder_intelligence: Optional[StakeholderIntelligenceSchema] = None
    industry_analysis: Optional[IndustryAnalysisSchema] = None
    priorities_and_pain_points: Optional[BusinessPrioritiesSchema] = None
    matched_internal_assets: Optional[List[MatchedAssetSchema]] = None
    service_mappings: Optional[List[ServiceMappingSchema]] = None
    meeting_strategy: Optional[MeetingStrategySchema] = None
    updated_at: datetime

    class Config:
        from_attributes = True