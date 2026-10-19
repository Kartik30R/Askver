from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class PainPointSchema(BaseModel):
    title: str = Field(default="", description="Legacy / human-readable pain point title")
    category: str = Field(default="GENERAL", description="e.g., Legacy Systems, Fragmented Apps, Slow Cycles, Cost")
    description: str = Field(default="", description="Detailed pain point description")
    impact: str = Field(default="", description="Business impact of the pain point")
    severity: str = Field(default="MEDIUM", description="HIGH, MEDIUM, LOW")
    impacted_business_area: str = Field(default="GENERAL", description="Business area impacted by the pain point")
    # ---- added (all optional, so existing consumers keep working) ----
    urgency: str = Field(default="NEXT_12_MONTHS", description="NOW, NEXT_12_MONTHS, LATER")
    solution_themes: List[str] = Field(default_factory=list, description="Capability keywords for matching case studies")
    evidence_basis: Literal["CLIENT_DOCUMENT", "PUBLIC_FACTS", "INFERRED"] = "INFERRED"
    fact_ids: List[str] = Field(default_factory=list)
    doc_evidence: List[str] = Field(default_factory=list, description="Short excerpts from the client's own documents")
    linked_hypothesis: Optional[str] = None


class PriorityEvidence(BaseModel):
    statement: str
    fact_ids: List[str] = Field(default_factory=list)
    doc_evidence: List[str] = Field(default_factory=list)


class BusinessPrioritiesSchema(BaseModel):
    priorities: List[str]
    pain_points: List[PainPointSchema]
    priority_evidence: List[PriorityEvidence] = Field(default_factory=list)