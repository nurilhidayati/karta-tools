from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class RegionSchemas(BaseModel):
    id: int
    name: str
    country_id: int
    ukm_price_multiplier: Optional[float] = 1.0
    insurance: Optional[float] = 1.0
    dataplan: Optional[float] = 1.0
    regional_overhead: Optional[float] = 0.0
    transportation_cost: Optional[float] = 0.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class RegionBoundarySchemas(BaseModel):
    id: int
    name: str
    country_id: int

class CountrySchemas(BaseModel):
    id: int
    name: str
    table: Optional[str] = None
    currency: Optional[str] = "USD"
    currency_symbol: Optional[str] = "$"
    ukm_price: Optional[float] = 8000.0
    insurance: Optional[float] = 132200.0
    dataplan: Optional[float] = 450000.0
    exchange_rate_to_usd: Optional[float] = 1.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    regions: Optional[List[RegionSchemas]] = []

class CountryPricingResponse(BaseModel):
    id: int
    name: str
    currency: str
    currency_symbol: str
    ukm_price: float
    insurance: float
    dataplan: float
    exchange_rate_to_usd: float
    regions: Optional[List[RegionSchemas]] = []

class RegionPricingResponse(BaseModel):
    id: int
    name: str
    country_id: int
    country_name: str
    currency: str
    currency_symbol: str
    # Calculated regional prices
    regional_ukm_price: float
    regional_insurance: float
    regional_dataplan: float
    regional_overhead: float
    transportation_cost: float
    exchange_rate_to_usd: float

class CountryRequest(BaseModel):
    country_id: int

class RegionRequest(BaseModel):
    region_id: int

class UpdateCountryPricingRequest(BaseModel):
    currency: Optional[str] = None
    currency_symbol: Optional[str] = None
    ukm_price: Optional[float] = None
    insurance: Optional[float] = None
    dataplan: Optional[float] = None
    exchange_rate_to_usd: Optional[float] = None

class CreateRegionRequest(BaseModel):
    name: str
    country_id: int
    ukm_price_multiplier: Optional[float] = 1.0
    insurance: Optional[float] = 1.0
    dataplan: Optional[float] = 1.0
    regional_overhead: Optional[float] = 0.0
    transportation_cost: Optional[float] = 0.0

class UpdateRegionRequest(BaseModel):
    name: Optional[str] = None
    ukm_price_multiplier: Optional[float] = None
    insurance: Optional[float] = None
    dataplan: Optional[float] = None
    regional_overhead: Optional[float] = None
    transportation_cost: Optional[float] = None

class CountryBoundarySchemas(BaseModel):
    id: int
    name: str
    table: Optional[str] = None
    