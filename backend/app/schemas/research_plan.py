from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

AgentName = Literal[
    "business_model", "financial", "strategy", "technology",
    "leadership", "industry", "competitors", "triggers",
]


class Hypothesis(BaseModel):
    statement: str = Field(description="e.g. 'Post-merger identity silos are blocking a unified user view'")
    why_it_matters: str
    how_to_test: str = Field(description="What evidence would confirm or kill it")


class AgentQuestions(BaseModel):
    agent: AgentName
    questions: List[str] = Field(description="2-4 specific research questions for this specialist")
    search_queries: List[str] = Field(description="2-4 concrete web queries, no hardcoded years")


class ResearchPlan(BaseModel):
    company_legal_name: str
    listing_status: Literal["listed", "private", "unknown"] = "unknown"
    ticker_hint: Optional[str] = None
    regions: List[str] = Field(description="Operating geographies, e.g. ['India', 'Southeast Asia']")
    sub_sector: str = Field(description="Narrower than the industry, e.g. 'OTT streaming and live sports media'")
    business_lines: List[str]
    peers: List[str] = Field(description="3-5 closest competitors/peers for benchmarking")
    regulatory_regimes: List[str] = Field(description="Frameworks that actually apply for these regions")
    likely_attendee_roles: List[str] = Field(description="Roles likely in the meeting, from objective/docs")
    hypotheses: List[Hypothesis] = Field(description="3-5 testable deal hypotheses")
    agent_plans: List[AgentQuestions]
    known_unknowns: List[str] = Field(default_factory=list, description="What cannot be determined from the grounding context")


# Cost control lives in code, not in the prompt. LLM-call budget per run is roughly:
# planner (1) + one extraction per specialist + frameworks + synthesis + playbook.
DEPTH_CONFIG: Dict[str, dict] = {
    "quick":    {"max_queries": 2, "max_results": 3, "peers": 2, "agents": ["business_model", "financial", "leadership", "triggers"]},
    "standard": {"max_queries": 3, "max_results": 4, "peers": 3, "agents": ["business_model", "financial", "strategy", "technology", "leadership", "industry", "triggers"]},
    "deep":     {"max_queries": 4, "max_results": 5, "peers": 5, "agents": ["business_model", "financial", "strategy", "technology", "leadership", "industry", "competitors", "triggers"]},
}