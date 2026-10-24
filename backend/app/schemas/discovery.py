from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CostEstimateResponse(BaseModel):
    is_estimate: bool = Field(True, description="Always labeled estimate per DEC-014, never actual")
    limited_data: bool = Field(True, description="True when sample size is insufficient or unrated")
    estimated_cost_display: str = Field("Limited data", description="Honest placeholder copy when no real quote data exists")
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    currency: str = "INR"


class VendorDiscoveryItem(BaseModel):
    id: str
    business_name: str
    category: str
    city: str
    locality: Optional[str] = None
    city_tier: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance_km: Optional[float] = None
    rating_tier: str = Field("new_unrated", description="Rating tier per DEC-013: top_rated, highly_rated, rated, new_unrated")
    average_rating: Optional[float] = None
    rating_count: int = 0
    is_verified_profile: bool = False
    coordinate_precision: str = "locality_approximate"
    cost_estimate: CostEstimateResponse
    source_notes: Optional[str] = None


class VendorDiscoveryResponse(BaseModel):
    query_lat: Optional[float] = None
    query_lng: Optional[float] = None
    query_city: Optional[str] = None
    radius_km: float
    category_filter: Optional[str] = None
    total_results: int
    results: List[VendorDiscoveryItem]
