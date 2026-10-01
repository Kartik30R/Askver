from pydantic import BaseModel, Field
from typing import List

class StakeholderPersonaSchema(BaseModel):
    role: str = Field(description="e.g., CEO, CIO, CTO, CDO, CISO, CFO")
    likely_goals: List[str]
    likely_concerns: List[str]
    business_drivers: List[str]

class StakeholderIntelligenceSchema(BaseModel):
    personas: List[StakeholderPersonaSchema]