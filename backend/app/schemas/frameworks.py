"""Consulting frameworks. Every cell must cite fact_ids; code drops any cell whose citations do not resolve."""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

Level = Literal["HIGH", "MEDIUM", "LOW"]


# ---------------------------------------------------------------- strategic frameworks
class SwotItem(BaseModel):
    statement: str = Field(description="One specific, evidence-based sentence. No generic filler")
    impact: Level
    fact_ids: List[str] = Field(description="Fact IDs from the provided list ONLY")


class Swot(BaseModel):
    strengths: List[SwotItem] = Field(description="Internal, helpful. Max 4")
    weaknesses: List[SwotItem] = Field(description="Internal, harmful. Max 4")
    opportunities: List[SwotItem] = Field(description="External, helpful. Max 4")
    threats: List[SwotItem] = Field(description="External, harmful. Max 4")


class TowsMove(BaseModel):
    quadrant: Literal["SO", "WO", "ST", "WT"] = Field(
        description="SO use strength to seize opportunity, WO fix weakness via opportunity, ST use strength against threat, WT defend")
    move: str = Field(description="The strategic move the client could make")
    why_it_matters_for_meeting: str = Field(description="Link to the meeting objective, where a technology partner helps")
    fact_ids: List[str]


class PorterForce(BaseModel):
    force: Literal["RIVALRY", "NEW_ENTRANTS", "SUBSTITUTES", "BUYER_POWER", "SUPPLIER_POWER"]
    rating: Literal["HIGH", "MEDIUM", "LOW", "INSUFFICIENT_EVIDENCE"]
    rationale: str
    implication_for_deal: str
    fact_ids: List[str] = Field(default_factory=list, description="Required unless rating is INSUFFICIENT_EVIDENCE")


class PestleFactor(BaseModel):
    dimension: Literal["POLITICAL", "ECONOMIC", "SOCIAL", "TECHNOLOGICAL", "LEGAL", "ENVIRONMENTAL"]
    factor: str
    impact: Level
    timeframe: Literal["NOW", "WITHIN_12_MONTHS", "LONGER"]
    fact_ids: List[str]


class StrategicFrameworks(BaseModel):
    swot: Swot
    tows: List[TowsMove] = Field(description="3-6 moves total, at least one per quadrant that the evidence supports")
    porter: List[PorterForce] = Field(description="Exactly the five forces")
    pestle: List[PestleFactor] = Field(description="Only dimensions with evidence, max 2 per dimension")


# ---------------------------------------------------------------- commercial frameworks
class BuyingCommitteeMember(BaseModel):
    role: str
    name: Optional[str] = Field(default=None, description="ONLY if a cited fact states this person's name; else null")
    evidence_level: Literal["NAMED_WITH_SOURCES", "ROLE_ARCHETYPE"]
    buying_role: Literal["ECONOMIC_BUYER", "CHAMPION", "TECHNICAL_EVALUATOR", "BLOCKER", "INFLUENCER", "UNKNOWN"]
    likely_stance: Literal["SUPPORTIVE", "NEUTRAL", "SKEPTICAL", "UNKNOWN"]
    influence: Level
    owns_kpis: List[str] = Field(description="What this person is measured on")
    how_to_win_them: str
    fact_ids: List[str] = Field(default_factory=list)


class DigitalMaturityDimension(BaseModel):
    dimension: Literal["CLOUD", "DATA_ANALYTICS", "AI", "SECURITY", "ENGINEERING_DELIVERY", "CUSTOMER_EXPERIENCE"]
    score_1_to_5: Optional[int] = Field(default=None, description="null when evidence is missing")
    rationale: str
    fact_ids: List[str] = Field(default_factory=list)


class PeerBenchmarkRow(BaseModel):
    peer: str
    dimension: str = Field(description="e.g. scale, cloud adoption, AI launches, margins, growth")
    target_position: Literal["AHEAD", "PARITY", "BEHIND", "UNKNOWN"]
    comparison: str
    fact_ids: List[str]


class CommercialFrameworks(BaseModel):
    buying_committee: List[BuyingCommitteeMember]
    digital_maturity: List[DigitalMaturityDimension] = Field(description="All six dimensions; score null if no evidence")
    peer_benchmark: List[PeerBenchmarkRow] = Field(default_factory=list, description="Only rows backed by facts about a named peer")