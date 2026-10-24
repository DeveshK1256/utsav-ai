import math
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.models.models import VendorProfile
from backend.app.schemas.discovery import (
    VendorDiscoveryItem,
    VendorDiscoveryResponse,
    CostEstimateResponse
)


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes great-circle distance between two points on Earth in kilometers
    using the Haversine formula. Pure deterministic math.
    """
    R = 6371.0  # Earth's mean radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)


# Reference coordinates for fallback city centers
CITY_CENTERS = {
    "jaipur": (26.9124, 75.7873),
    "pune": (18.5204, 73.8567),
    "mumbai": (19.0760, 72.8777),
    "delhi": (28.6139, 77.2090),
    "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946),
}


class VendorDiscoveryService:
    """
    Deterministic Geo & Directory discovery engine (F15-Lite).
    Rules:
    1. Zero LLM involvement in distance ranking, geo-filtering, or cost estimation.
    2. 'new_unrated' and 'average_rating: null' are the default, honest states.
    3. Cost is always labeled 'estimate' with 'limited_data: true' pending real quote data.
    """

    @classmethod
    def search_vendors(
        cls,
        db: Session,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        city: Optional[str] = None,
        radius_km: float = 25.0,
        category: Optional[str] = None,
        sort_by: str = "distance_asc"
    ) -> VendorDiscoveryResponse:
        resolved_lat = lat
        resolved_lng = lng

        # Fallback to city center if lat/lng not provided
        if (resolved_lat is None or resolved_lng is None) and city:
            clean_city = city.strip().lower()
            if clean_city in CITY_CENTERS:
                resolved_lat, resolved_lng = CITY_CENTERS[clean_city]

        query = db.query(VendorProfile)

        # Filter by category if specified
        if category:
            clean_cat = category.strip().lower()
            query = query.filter(VendorProfile.category.ilike(f"%{clean_cat}%"))

        # If we have city filtering without coordinates
        if resolved_lat is None or resolved_lng is None:
            if city:
                query = query.filter(VendorProfile.city.ilike(f"%{city.strip()}%"))
            profiles = query.all()

            results: List[VendorDiscoveryItem] = []
            for p in profiles:
                results.append(
                    cls._profile_to_item(p, distance_km=None)
                )

            return VendorDiscoveryResponse(
                query_lat=None,
                query_lng=None,
                query_city=city,
                radius_km=radius_km,
                category_filter=category,
                total_results=len(results),
                results=results
            )

        # Geo-bounded search
        # 1 degree of latitude ~= 111 km
        # 1 degree of longitude ~= 111 km * cos(lat)
        deg_lat = radius_km / 111.0
        rad_lat = math.radians(resolved_lat)
        deg_lng = radius_km / (111.0 * max(0.1, math.cos(rad_lat)))

        min_lat = resolved_lat - deg_lat
        max_lat = resolved_lat + deg_lat
        min_lng = resolved_lng - deg_lng
        max_lng = resolved_lng + deg_lng

        query = query.filter(
            VendorProfile.latitude >= min_lat,
            VendorProfile.latitude <= max_lat,
            VendorProfile.longitude >= min_lng,
            VendorProfile.longitude <= max_lng
        )

        candidates = query.all()

        items_with_distance: List[Tuple[VendorDiscoveryItem, float]] = []
        for p in candidates:
            if p.latitude is not None and p.longitude is not None:
                dist = haversine_distance_km(
                    resolved_lat, resolved_lng,
                    float(p.latitude), float(p.longitude)
                )
                if dist <= radius_km:
                    item = cls._profile_to_item(p, distance_km=dist)
                    items_with_distance.append((item, dist))

        # Sort
        if sort_by == "distance_asc":
            items_with_distance.sort(key=lambda x: x[1])
        else:
            items_with_distance.sort(key=lambda x: x[1])

        results = [item for item, _ in items_with_distance]

        return VendorDiscoveryResponse(
            query_lat=resolved_lat,
            query_lng=resolved_lng,
            query_city=city,
            radius_km=radius_km,
            category_filter=category,
            total_results=len(results),
            results=results
        )

    @staticmethod
    def _profile_to_item(profile: VendorProfile, distance_km: Optional[float]) -> VendorDiscoveryItem:
        # Determine rating tier strictly per DEC-013:
        # If average_rating is None or 0 or rating_count == 0 -> "new_unrated"
        avg_rating = float(profile.average_rating) if profile.average_rating is not None else None
        rating_count = profile.rating_count or 0

        if avg_rating is None or rating_count == 0:
            rating_tier = "new_unrated"
        elif avg_rating >= 4.8 and rating_count >= 15:
            rating_tier = "top_rated"
        elif avg_rating >= 4.0:
            rating_tier = "highly_rated"
        else:
            rating_tier = "rated"

        cost_est = CostEstimateResponse(
            is_estimate=True,
            limited_data=True,
            estimated_cost_display="Limited data"
        )

        return VendorDiscoveryItem(
            id=profile.id,
            business_name=profile.business_name,
            category=profile.category,
            city=profile.city,
            locality=profile.locality,
            city_tier=profile.city_tier,
            latitude=float(profile.latitude) if profile.latitude is not None else None,
            longitude=float(profile.longitude) if profile.longitude is not None else None,
            distance_km=distance_km,
            rating_tier=rating_tier,
            average_rating=avg_rating,
            rating_count=rating_count,
            is_verified_profile=profile.is_verified_profile,
            coordinate_precision=profile.coordinate_precision or "locality_approximate",
            cost_estimate=cost_est,
            source_notes=profile.source_notes
        )
