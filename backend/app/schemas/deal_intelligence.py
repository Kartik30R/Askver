from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime
from uuid import UUID

from app.schemas.node_1_company import CompanyResearchSchema
from app.schemas.node_1b_financial import FinancialIntelligenceSchema
from app.schemas.node_2_stakeholder import StakeholderIntelligenceSchema
from app.schemas.node_3_industry import IndustryAnalysisSchema
from app.schemas.node_4_priorities import BusinessPrioritiesSchema
from app.schemas.node_5_6_services import MatchedAssetSchema, ServiceMappingSchema
from app.schemas.node_7_brief import CXOExecutiveBriefSchema


class PipelineTriggerResponse(BaseModel):
    status: str = Field(..., description="Lifecycle status for the queued pipeline execution")
    message: str = Field(..., description="Human-readable response message")
    thread_id: Optional[str] = Field(None, description="LangGraph thread id, if provided")


class PipelineStatusResponse(BaseModel):
    deal_id: UUID = Field(..., description="The deal identifier")
    status: str = Field(..., description="Current pipeline state on the deal")


class TriggerIntelligenceRequest(BaseModel):
    target_company: str
    target_industry: str
    meeting_objective: str
    client_documents_path: Optional[str] = None
    research_depth: Optional[str] = Field(default="standard", description="Research depth: quick, standard, deep")
    meeting_duration_minutes: Optional[int] = Field(default=45, ge=15, le=180, description="Target meeting length in minutes")


class HumanApprovalRequest(BaseModel):
    approved: bool
    feedback: Optional[str] = None
    custom_selected_assets: Optional[List[str]] = None
    service_mappings: Optional[List[ServiceMappingSchema]] = None


class DealIntelligenceResponse(BaseModel):
    deal_id: UUID
    version: int
    thread_id: str
    node_statuses: Dict[str, str] = Field(default_factory=dict)
    company_research: Optional[CompanyResearchSchema] = None
    financial_intelligence: Optional[FinancialIntelligenceSchema] = None
    stakeholder_intelligence: Optional[StakeholderIntelligenceSchema] = None
    industry_analysis: Optional[IndustryAnalysisSchema] = None
    priorities_and_pain_points: Optional[BusinessPrioritiesSchema] = None
    matched_internal_assets: Optional[List[MatchedAssetSchema]] = None
    service_mappings: Optional[List[ServiceMappingSchema]] = None
    cxo_executive_brief: Optional[CXOExecutiveBriefSchema] = None
    updated_at: datetime

    class Config:
        from_attributes = True