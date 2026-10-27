
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.discovery import VendorDiscoveryResponse
from backend.app.services.discovery_service import VendorDiscoveryService

router = APIRouter(prefix="/discovery", tags=["Vendor & Venue Discovery (F15-Lite)"])


@router.get("/vendors", response_model=VendorDiscoveryResponse)
def get_nearby_vendors(
    lat: float | None = Query(None, description="Latitude for geo-radius query"),
    lng: float | None = Query(None, description="Longitude for geo-radius query"),
    city: str | None = Query(None, description="City name fallback if geolocation consent is denied or unavailable"),
    radius_km: float = Query(25.0, ge=1.0, le=100.0, description="Search radius in kilometers"),
    category: str | None = Query(None, description="Optional vendor category filter (e.g. venue, lawn, banquet)"),
    sort: str = Query("distance_asc", description="Sort order: distance_asc"),
    db: Session = Depends(get_db)
):
    """
    Returns nearby vendors/venues ranked by distance.
    Rules:
    - Pure deterministic geo query with Haversine distance math.
    - Zero fabricated ratings: all unreviewed vendors return rating_tier='new_unrated' and average_rating=null.
    - Zero fabricated cost: cost_estimate returns {is_estimate: true, limited_data: true}.
    - If lat/lng are omitted, falls back to city center coordinates or city-name matching.
    """
    if lat is None and lng is None and not city:
        raise HTTPException(
            status_code=400,
            detail="Either lat/lng coordinates or a fallback city name must be provided."
        )

    return VendorDiscoveryService.search_vendors(
        db=db,
        lat=lat,
        lng=lng,
        city=city,
        radius_km=radius_km,
        category=category,
        sort_by=sort
    )


@router.get("/geocode")
def geocode_location(
    q: str = Query(..., min_length=2, description="City name or 6-digit Indian pincode to geocode via OpenStreetMap")
):
    """
    Converts a manual city name or 6-digit pincode to coordinates using OpenStreetMap Nominatim.
    Free, no API key, zero-billing, strictly respects 1 req/sec policy with identification header.
    """
    res = VendorDiscoveryService.geocode_query(q)
    if not res:
        raise HTTPException(
            status_code=404,
            detail=f"Could not resolve coordinates for '{q}' in OpenStreetMap. Please verify spelling or try city name."
        )
    lat, lng, display_name = res
    return {
        "query": q,
        "lat": lat,
        "lng": lng,
        "display_name": display_name
    }

