from pydantic import BaseModel
from typing import List
from .base import DetailedPoint

class IndustryAnalysisSchema(BaseModel):
    major_trends: List[DetailedPoint]
    regulatory_compliance: List[DetailedPoint]
    risks_and_challenges: List[DetailedPoint]
    technology_benchmarks: List[DetailedPoint]