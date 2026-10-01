from pydantic import BaseModel, Field
from typing import List, Optional
from .base import DetailedPoint

class LeadershipMemberSchema(BaseModel):
    name: str
    role: str
    background: Optional[str] = None

class CompanyOverviewSchema(BaseModel):
    summary: DetailedPoint
    business_model: DetailedPoint
    revenue_streams: List[DetailedPoint]
    employee_count_estimate: Optional[str] = None
    headquarters: Optional[str] = None

class DigitalInitiativeSchema(BaseModel):
    initiative_name: str
    description: DetailedPoint
    perceived_priority: str = Field(description="HIGH, MEDIUM, or LOW")
    status: str = Field(description="e.g., 'In Progress', 'Planned'")

class TechnologyInvestmentSchema(BaseModel):
    technology_stack: str
    category: str = Field(description="Cloud, Security, AI/ML, ERP, Data")
    vendor_or_tool: Optional[str] = None
    details: DetailedPoint

class RecentNewsItemSchema(BaseModel):
    headline: str
    date_or_period: Optional[str] = None
    category: str = Field(description="M&A, Executive Hire, Earnings, Product Launch, Partnership, Other News")
    details: DetailedPoint

class CompanyResearchSchema(BaseModel):
    overview: CompanyOverviewSchema
    leadership_team: List[LeadershipMemberSchema]
    digital_initiatives: List[DigitalInitiativeSchema]
    technology_investments: List[TechnologyInvestmentSchema]
    recent_news_and_m_and_a: List[RecentNewsItemSchema]