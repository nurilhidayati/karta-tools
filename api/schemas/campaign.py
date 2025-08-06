# Example fix if some fields can be null
from typing import Optional, Dict, Any
from pydantic import BaseModel

class CampaignSchemas(BaseModel):
    id: int
    campaign_name: Optional[str]
    country: Optional[str]
    city: Optional[str]
    ukm_plan: Optional[float]
    ukm_actual: Optional[float]
    persentase_ukm_actual: Optional[float]


class CampaignRequest(BaseModel):
    campaign_name: str
    country: Optional[str] = None
    city: Optional[str] = None
    ukm_plan: Optional[float] = None
    ukm_actual: Optional[float] = None
    persentase_ukm_actual: Optional[float] = None
