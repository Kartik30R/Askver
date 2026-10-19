"""Insight synthesis output. 'Why us' is intentionally absent: it needs matched proof assets, so the playbook builds it."""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

Level = Literal["HIGH", "MEDIUM", "LOW"]


class Insight(BaseModel):
    headline: str = Field(description="The finding in one sentence, 8-16 words")
    so_what: str = Field(description="What it means for this client and for our conversation. Must connect to the meeting objective")
    evidence_strength: Level
    linked_hypothesis: Optional[str] = Field(default=None, description="Copy of the hypothesis statement this speaks to, if any")
    fact_ids: List[str] = Field(description="Fact IDs from the provided list ONLY")
    unverified_figures: List[str] = Field(default_factory=list, description="Leave empty; filled by the verifier in code")


class HypothesisVerdict(BaseModel):
    statement: str = Field(description="Copy of the hypothesis exactly as given")
    verdict: Literal["SUPPORTED", "PARTIAL", "UNSUPPORTED", "CONTRADICTED", "UNTESTED"]
    rationale: str
    fact_ids: List[str] = Field(default_factory=list)


class ThesisPart(BaseModel):
    text: str
    fact_ids: List[str] = Field(default_factory=list)


class DealRisk(BaseModel):
    risk: str = Field(description="What could stall or kill this deal")
    likelihood: Level
    impact: Level
    mitigation: str
    fact_ids: List[str] = Field(default_factory=list)


class InsightSynthesis(BaseModel):
    insights: List[Insight] = Field(description="At most 5, ranked by impact on winning the deal")
    hypothesis_verdicts: List[HypothesisVerdict] = Field(description="One per hypothesis provided")
    why_now: ThesisPart = Field(description="Only from dated trigger or regulatory facts")
    why_this_client: ThesisPart = Field(description="What is specific to this client that makes the opportunity real")
    value_hypothesis: ThesisPart = Field(description="Where value could be created, in the client's own terms. No invented ROI figures")
    deal_risks: List[DealRisk] = Field(description="3-5 items")
    validate_in_meeting: List[str] = Field(description="3-6 things the evidence could not settle and the presenter must confirm live")