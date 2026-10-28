from pydantic import BaseModel, Field


class CostEstimateResponse(BaseModel):
    is_estimate: bool = Field(True, description="Always labeled estimate per DEC-014, never actual")
    limited_data: bool = Field(True, description="True when sample size is insufficient or unrated")
    estimated_cost_display: str = Field(
        "Limited data", description="Honest placeholder copy when no real quote data exists"
    )
    min_amount: float | None = None
    max_amount: float | None = None
    currency: str = "INR"


class VendorDiscoveryItem(BaseModel):
    id: str
    business_name: str
    category: str
    city: str
    locality: str | None = None
    city_tier: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    distance_km: float | None = None
    rating_tier: str = Field(
        "new_unrated",
        description="Rating tier per DEC-013: top_rated, highly_rated, rated, new_unrated",
    )
    average_rating: float | None = None
    rating_count: int = 0
    is_verified_profile: bool = False
    coordinate_precision: str = "locality_approximate"
    cost_estimate: CostEstimateResponse
    source_notes: str | None = None


class VendorDiscoveryResponse(BaseModel):
    query_lat: float | None = None
    query_lng: float | None = None
    query_city: str | None = None
    radius_km: float
    category_filter: str | None = None
    total_results: int
    results: list[VendorDiscoveryItem]
