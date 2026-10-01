from pydantic import BaseModel, Field
from typing import List, Optional, Any

class FinancialMetricScore(BaseModel):
    metric_name: str
    value: Optional[Any] = None
    score_10: str = Field(default="N/A", description="e.g., '7/10'")
    score_100: int = Field(default=0, description="0-100 score for the metric")
    status: str = Field(default="unavailable", description="available, unavailable, not_listed")
    rationale: str = Field(default="", description="e.g., 'Sustained 15% revenue growth year-over-year'")
    notes: str = Field(default="", description="Grounded notes from the real data source")

class FinancialIntelligenceSchema(BaseModel):
    company_name: str
    symbol: Optional[str] = None
    status: str = Field(default="not_listed", description="listed, not_listed, private")
    market: str = Field(default="USA")
    market_cap_category: str = Field(default="Unknown", description="Mega Cap, Large Cap, Mid Cap, Small Cap, Micro Cap")
    availability: str = Field(default="unavailable", description="available or unavailable")
    data_source: str = Field(default="yfinance")
    overall_score_10: str = Field(default="0/10")
    ai_summary: str
    financial_concerns: List[str] = Field(default_factory=list, description="Red flags, revenue drops, debt warnings")
    metric_scores: List[FinancialMetricScore]