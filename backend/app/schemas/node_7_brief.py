from pydantic import BaseModel, Field
from typing import List

class ObjectionResponseSchema(BaseModel):
    objection: str = Field(description="A likely objection the CXO might raise")
    response: str = Field(description="The recommended data-backed response to counter the objection")

class CXOExecutiveBriefSchema(BaseModel):
    executive_summary: str = Field(description="High-level summary of the meeting strategy and value proposition")
    talking_points: List[str] = Field(description="Key strategic talking points to drive the conversation")
    questions_to_ask: List[str] = Field(description="High-value discovery questions to ask the CXO")
    objections_and_responses: List[ObjectionResponseSchema] = Field(description="Anticipated pushback and how to handle it")
    executive_pitch: str = Field(description="The final elevator pitch tailored to the target company")