from pydantic import BaseModel, Field
from typing import List

class PainPointSchema(BaseModel):
    category: str = Field(description="e.g., Legacy Systems, Fragmented Apps, Slow Cycles, Cost")
    description: str
    severity: str = Field(description="HIGH, MEDIUM, LOW")
    impacted_business_area: str

class BusinessPrioritiesSchema(BaseModel):
    priorities: List[str]
    pain_points: List[PainPointSchema]