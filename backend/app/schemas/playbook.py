"""Final deliverable. Shaped after the sample (talking points -> questions -> objections) and extended.

Hard rule enforced in the prompt and by a validator in code:
- statements about the CLIENT must cite fact_ids
- statements about OUR capability must cite proof_asset_ids (never invented)
"""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class OneSlideSnapshot(BaseModel):
    situation: str = Field(description="Where the client is right now, 2-3 sentences")
    why_now: str = Field(description="The trigger event(s) that make this meeting timely")
    opening_hook: str = Field(description="First 30 seconds: an insight they have not heard")
    meeting_goal: str
    fact_ids: List[str] = Field(default_factory=list)


class AgendaItem(BaseModel):
    minutes: int
    topic: str
    purpose: str


class TalkingPoint(BaseModel):
    sequence: int = Field(description="Order to deliver in the room, starting at 1")
    headline: str = Field(description="5-9 words, glanceable")
    point: str = Field(description="1-2 sentences, specific numbers and names from facts")
    target_persona: str = Field(description="Who this lands with, e.g. CFO, CTO, all")
    bridge_to_question: Optional[int] = Field(default=None, description="Index of the discovery question this sets up")
    fact_ids: List[str] = Field(default_factory=list)
    proof_asset_ids: List[str] = Field(default_factory=list)
    unverified_figures: List[str] = Field(default_factory=list, description="Filled by code; leave empty")


class DiscoveryQuestion(BaseModel):
    stage: Literal["SITUATION", "PROBLEM", "IMPACT", "VISION", "DECISION"]
    question: str
    why_we_ask: str = Field(description="What this reveals and how it moves the deal")
    listen_for: List[str] = Field(description="Signals in the answer: budget, owner, deadline, competitor, blocker")
    follow_up: str
    target_persona: str
    fact_ids: List[str] = Field(default_factory=list)
    unverified_figures: List[str] = Field(default_factory=list, description="Filled by code; leave empty")


class ObjectionHandling(BaseModel):
    objection: str
    likelihood: Literal["HIGH", "MEDIUM", "LOW"]
    raised_by: str = Field(description="Persona most likely to raise it")
    underlying_concern: str = Field(description="What they really worry about")
    response: str
    proof_asset_ids: List[str] = Field(default_factory=list, description="Only IDs from matched assets")
    fact_ids: List[str] = Field(default_factory=list)
    do_not_say: Optional[str] = None
    unverified_figures: List[str] = Field(default_factory=list, description="Filled by code; leave empty")


class AttendeePlaybook(BaseModel):
    role: str
    name: Optional[str] = Field(default=None, description="Only if a sourced name exists; else null")
    evidence_level: Literal["NAMED_WITH_SOURCES", "ROLE_ARCHETYPE"]
    buying_role: Literal["ECONOMIC_BUYER", "CHAMPION", "TECHNICAL_EVALUATOR", "BLOCKER", "INFLUENCER", "UNKNOWN"]
    what_they_care_about: List[str]
    approach: str
    best_questions_for_them: List[int] = Field(default_factory=list, description="Indexes into discovery_questions")
    fact_ids: List[str] = Field(default_factory=list)


class Landmine(BaseModel):
    topic: str
    why: str
    safer_framing: str
    fact_ids: List[str] = Field(default_factory=list)


class ProofPoint(BaseModel):
    pain_point: str
    asset_id: str
    how_to_use: str


class PitchAndAsk(BaseModel):
    pitch_60_seconds: str
    pitch_3_minutes: str
    the_ask: str
    next_steps: List[str]
    follow_up_email_subject: str
    follow_up_email_body: str = Field(description="Use [bracketed placeholders] for what only the meeting can reveal")
    fact_ids: List[str] = Field(default_factory=list)
    proof_asset_ids: List[str] = Field(default_factory=list)


class QuestionsBlock(BaseModel):
    """LLM call 1: how we listen."""
    discovery_questions: List[DiscoveryQuestion]
    objections: List[ObjectionHandling]
    attendees: List[AttendeePlaybook]


class RoomBlock(BaseModel):
    """LLM call 2: how we run the room. Written after the questions so talking points can lead into them."""
    snapshot: OneSlideSnapshot
    agenda: List[AgendaItem]
    talking_points: List[TalkingPoint]
    landmines: List[Landmine]
    proof_points: List[ProofPoint]
    pitch_and_ask: PitchAndAsk


class MeetingPlaybook(BaseModel):
    snapshot: OneSlideSnapshot
    agenda: List[AgendaItem]
    talking_points: List[TalkingPoint]
    discovery_questions: List[DiscoveryQuestion]
    objections: List[ObjectionHandling]
    attendees: List[AttendeePlaybook]
    landmines: List[Landmine]
    proof_points: List[ProofPoint]
    pitch_and_ask: PitchAndAsk
    deal_risks: List[str] = Field(description="What could kill this deal")
    known_gaps: List[str] = Field(description="What research could not confirm; the presenter should verify")
    overall_confidence: Literal["HIGH", "MEDIUM", "LOW"]


def find_invalid_references(playbook: dict, fact_ids: set, asset_ids: set) -> List[str]:
    """Code-side check: every cited ID must exist. Run after generation; regenerate or strip offenders."""
    problems: List[str] = []

    def walk(node, path=""):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "fact_ids":
                    problems.extend(f"{path}.{k}: unknown fact {i}" for i in v if i not in fact_ids)
                elif k == "proof_asset_ids":
                    problems.extend(f"{path}.{k}: unknown asset {i}" for i in v if i not in asset_ids)
                else:
                    walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for n, v in enumerate(node):
                walk(v, f"{path}[{n}]")

    walk(playbook)
    return problems