from pydantic import BaseModel, Field
from typing import List

class MatchedAssetSchema(BaseModel):
    asset_id: str
    asset_name: str
    asset_type: str = Field(description="CASE_STUDY, PROPOSAL, SOW, SUCCESS_STORY, PRESENTATION")
    relevance_score: float
    key_metrics_achieved: List[str]
    summary: str

class ServiceMappingSchema(BaseModel):
    client_need: str
    detected_bottleneck: str
    recommended_offering: str
    supporting_proof_assets: List[MatchedAssetSchema]
    expected_business_impact: str