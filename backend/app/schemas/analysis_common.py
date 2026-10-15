"""
app/schemas/analysis_common.py

Shared building blocks for meeting analysis and deal analytics.

Design rules baked into these types:
  1. Every finding carries evidence (so the UI can show "why").
  2. Facts vs inferences are always distinguishable (Basis).
  3. Every finding has a confidence level.
"""
from enum import Enum

from pydantic import BaseModel, Field


class Confidence(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Basis(str, Enum):
    STATED = "STATED"      # the customer / team actually said it
    INFERRED = "INFERRED"  # the AI thinks this is what it means


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Side(str, Enum):
    OUR_TEAM = "OUR_TEAM"
    BUYER = "BUYER"
    UNKNOWN = "UNKNOWN"


class EvidenceSource(str, Enum):
    TRANSCRIPT = "TRANSCRIPT"
    PRESENTATION = "PRESENTATION"
    NOTES = "NOTES"
    RESEARCH = "RESEARCH"
    PRIOR_MEETING = "PRIOR_MEETING"


class Evidence(BaseModel):
    """A pointer back to the source material behind a finding."""

    source: EvidenceSource = EvidenceSource.TRANSCRIPT
    quote: str = Field(
        description="Verbatim excerpt copied exactly from the source (max ~40 words). Never paraphrase.",
        max_length=600,
    )
    speaker: str | None = None
    timestamp: str | None = Field(default=None, description="e.g. '00:12:41' if present in the transcript")
    slide_number: int | None = None
    meeting_id: str | None = Field(default=None, description="Set only for deal-level evidence")
    verified: bool = Field(
        default=False,
        description="Set by the pipeline, NOT the LLM: True if the quote was found in the source text.",
    )


class Finding(BaseModel):
    """Base for any analytical finding."""

    basis: Basis = Basis.INFERRED
    confidence: Confidence = Confidence.MEDIUM
    evidence: list[Evidence] = Field(default_factory=list)
