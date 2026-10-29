import json
import logging
import math
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models.models import VendorProfile
from backend.app.schemas.discovery import (
    CostEstimateResponse,
    VendorDiscoveryItem,
    VendorDiscoveryResponse,
)
from backend.app.services.discovery.dedup import (
    are_venues_duplicates,
    is_valid_venue_name,
)
from backend.app.services.discovery.geo import (
    CITY_CENTERS,
    _validate_safe_outbound_url,
    haversine_distance_km,
)
from backend.app.services.discovery.osm_client import OSMClient

logger = logging.getLogger(__name__)

OSM_USER_AGENT = "UtsavCelebrationApp/1.0 (utsav.celebrations@gmail.com)"

_OVERPASS_CACHE: dict = {}
_OVERPASS_CACHE_LOCK = threading.Lock()
OVERPASS_CACHE_TTL_SECONDS = 15 * 60  # 15 minutes

ALLOWED_OUTBOUND_DOMAINS = {
    "nominatim.openstreetmap.org",
    "overpass-api.de",
    "overpass.kumi.systems",
    "overpass.private.coffee",
}


class VendorDiscoveryService:
    """
    Deterministic Geo & Directory discovery engine (F15-Lite).
    Rules:
    1. Zero LLM involvement in distance ranking, geo-filtering, or cost estimation.
    2. 'new_unrated' and 'average_rating: null' are the default, honest states.
    3. Cost is always labeled 'estimate' with 'limited_data: true' pending real quote data.
    4. Free nationwide venue discovery via OpenStreetMap (Overpass API + Nominatim).
    5. Curated seed venues (Jaipur/Pune) serve as high-confidence baseline and merge seamlessly.
    """

    @classmethod
    def geocode_query(cls, query_text: str) -> tuple[float, float, str] | None:
        """
        Geocodes a manual city name or 6-digit Indian pincode using OpenStreetMap Nominatim.
        Free, zero-billing, strictly adheres to 1 req/sec policy with identification header.
        Returns: (latitude, longitude, display_name) or None.
        """
        clean_text = query_text.strip().lower()
        if clean_text in CITY_CENTERS:
            lat, lng = CITY_CENTERS[clean_text]
            return (lat, lng, query_text.strip().title())

        try:
            url = (
                f"https://nominatim.openstreetmap.org/search"
                f"?q={urllib.parse.quote(query_text)}&format=json&countrycodes=in&limit=1"
            )
            _validate_safe_outbound_url(url)
            req = urllib.request.Request(url, headers={"User-Agent": OSM_USER_AGENT})
            with urllib.request.urlopen(req, timeout=4) as resp:  # nosec B310 # noqa: S310
                data = json.loads(resp.read().decode("utf-8"))
                if data and len(data) > 0:
                    first = data[0]
                    return (
                        float(first["lat"]),
                        float(first["lon"]),
                        first.get("display_name", query_text),
                    )
        except (
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError,
            KeyError,
            IndexError,
            ValueError,
            OSError,
        ) as e:
            logger.warning("Nominatim geocode failed for '%s': %s", query_text, e)
        return None

    @classmethod
    def _resolve_coordinates(
        cls, lat: float | None, lng: float | None, city: str | None
    ) -> tuple[float | None, float | None]:
        if lat is not None and lng is not None:
            return lat, lng
        if not city:
            return None, None
        clean_city = city.strip().lower()
        if clean_city in CITY_CENTERS:
            return CITY_CENTERS[clean_city]
        geocoded = cls.geocode_query(city)
        if geocoded:
            return geocoded[0], geocoded[1]
        return None, None

    @classmethod
    def _is_candidate_duplicate(
        cls, p: VendorProfile, accepted: list[tuple[VendorDiscoveryItem, float]]
    ) -> bool:
        p_lat, p_lng = float(p.latitude or 0.0), float(p.longitude or 0.0)
        for item, _ in accepted:
            if (
                item.latitude
                and item.longitude
                and are_venues_duplicates(
                    name1=p.business_name,
                    lat1=p_lat,
                    lng1=p_lng,
                    name2=item.business_name,
                    lat2=item.latitude,
                    lng2=item.longitude,
                )
            ):
                return True
        return False

    @classmethod
    def _deduplicate_and_sort_candidates(
        cls, candidates: list[VendorProfile], lat: float, lng: float, radius_km: float
    ) -> list[VendorDiscoveryItem]:
        def candidate_priority(p: VendorProfile) -> int:
            notes = (p.source_notes or "").lower()
            if "pickyourtrail" in notes or "venuelook" in notes:
                return 0
            return 1 if p.is_verified_profile else 2

        sorted_candidates = sorted(candidates, key=candidate_priority)
        accepted: list[tuple[VendorDiscoveryItem, float]] = []
        seen_names = set()

        for p in sorted_candidates:
            if (
                p.latitude is None
                or p.longitude is None
                or not is_valid_venue_name(p.business_name)
            ):
                continue

            dist = haversine_distance_km(lat, lng, float(p.latitude), float(p.longitude))
            if dist > radius_km:
                continue

            norm_name = re.sub(r"[^a-z0-9]", "", p.business_name.lower())
            if norm_name in seen_names or cls._is_candidate_duplicate(p, accepted):
                continue

            seen_names.add(norm_name)
            accepted.append((cls._profile_to_item(p, distance_km=dist), dist))

        accepted.sort(key=lambda x: x[1])
        return [item for item, _ in accepted]

    @classmethod
    def search_vendors(
        cls,
        db: Session,
        lat: float | None = None,
        lng: float | None = None,
        city: str | None = None,
        radius_km: float = 25.0,
        category: str | None = None,
        sort_by: str = "distance_asc",
    ) -> VendorDiscoveryResponse:
        _ = sort_by
        resolved_lat, resolved_lng = cls._resolve_coordinates(lat, lng, city)

        if resolved_lat is None or resolved_lng is None:
            query = db.query(VendorProfile)
            if category:
                query = query.filter(VendorProfile.category.ilike(f"%{category.strip()}%"))
            if city:
                query = query.filter(VendorProfile.city.ilike(f"%{city.strip()}%"))
            results = [cls._profile_to_item(p, distance_km=None) for p in query.all()]
            return VendorDiscoveryResponse(
                query_lat=None,
                query_lng=None,
                query_city=city,
                radius_km=radius_km,
                category_filter=category,
                total_results=len(results),
                results=results,
            )

        deg_lat = radius_km / 111.0
        rad_lat = math.radians(resolved_lat)
        deg_lng = radius_km / (111.0 * max(0.1, math.cos(rad_lat)))

        db_query = db.query(VendorProfile).filter(
            VendorProfile.latitude >= resolved_lat - deg_lat,
            VendorProfile.latitude <= resolved_lat + deg_lat,
            VendorProfile.longitude >= resolved_lng - deg_lng,
            VendorProfile.longitude <= resolved_lng + deg_lng,
        )
        if category:
            db_query = db_query.filter(VendorProfile.category.ilike(f"%{category.strip()}%"))

        cls._fetch_and_persist_osm_venues(
            db=db, lat=resolved_lat, lng=resolved_lng, radius_km=radius_km, city_hint=city
        )

        all_candidates = db_query.all()
        results = cls._deduplicate_and_sort_candidates(
            all_candidates, resolved_lat, resolved_lng, radius_km
        )

        return VendorDiscoveryResponse(
            query_lat=resolved_lat,
            query_lng=resolved_lng,
            query_city=city,
            radius_km=radius_km,
            category_filter=category,
            total_results=len(results),
            results=results,
        )

    @staticmethod
    def _extract_el_coords(el: dict[str, Any]) -> tuple[float, float] | None:
        return OSMClient._extract_el_coords(el)

    @classmethod
    def _parse_overpass_element(
        cls, el: dict[str, Any], city_hint: str | None
    ) -> dict[str, Any] | None:
        return OSMClient._parse_overpass_element(el, city_hint)

    @classmethod
    def _query_overpass_mirrors(
        cls, lat: float, lng: float, radius_m: int, city_hint: str | None
    ) -> list[dict[str, Any]]:
        return OSMClient._query_overpass_mirrors(lat, lng, radius_m, city_hint)

    @classmethod
    def _parse_nominatim_item(
        cls, it: dict[str, Any], target_city: str | None, lat: float, lng: float, radius_km: float
    ) -> dict[str, Any] | None:
        return OSMClient._parse_nominatim_item(it, target_city, lat, lng, radius_km)

    @classmethod
    def _resolve_target_city(cls, lat: float, lng: float, city_hint: str | None) -> str | None:
        return OSMClient._resolve_target_city(lat, lng, city_hint)

    @classmethod
    def _query_nominatim_venues(
        cls, center_lat: float, center_lng: float, radius_km: float, city_hint: str | None
    ) -> list[dict[str, Any]]:
        return OSMClient._query_nominatim_venues(center_lat, center_lng, radius_km, city_hint)

    @classmethod
    def _persist_discovered_osm_venues(cls, db: Session, osm_venues: list[dict]) -> None:
        new_profiles_count = 0
        for v in osm_venues:
            if not is_valid_venue_name(v.get("name")):
                continue
            osm_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"osm_{v['osm_type']}_{v['osm_id']}"))
            existing = db.query(VendorProfile).filter(VendorProfile.id == osm_uuid).first()
            if not existing:
                profile = VendorProfile(
                    id=osm_uuid,
                    business_name=v["name"][:200],
                    category=v["category"][:50],
                    latitude=v["lat"],
                    longitude=v["lng"],
                    city=v["city"][:100],
                    locality=v["locality"][:150] if v["locality"] else None,
                    city_tier="tier_2",
                    is_verified_profile=False,
                    average_rating=None,
                    rating_count=0,
                    coordinate_precision="exact_osm_node",
                    source_notes=f"OpenStreetMap (Real OSM Record: {v['osm_type']}/{v['osm_id']})",
                )
                db.add(profile)
                new_profiles_count += 1

        if new_profiles_count > 0:
            try:
                db.commit()
                logger.info(
                    "Persisted %d new OpenStreetMap venues into vendor_profiles", new_profiles_count
                )
            except SQLAlchemyError as e:
                db.rollback()
                logger.warning("Failed to commit OSM venues: %s", e)

    @classmethod
    def _fetch_and_persist_osm_venues(
        cls, db: Session, lat: float, lng: float, radius_km: float, city_hint: str | None = None
    ) -> None:
        cache_key = (
            round(lat, 2),
            round(lng, 2),
            int(radius_km),
            (city_hint or "").lower().strip(),
        )
        now = time.time()

        with _OVERPASS_CACHE_LOCK:
            if cache_key in _OVERPASS_CACHE:
                cached_time, _ = _OVERPASS_CACHE[cache_key]
                if now - cached_time < OVERPASS_CACHE_TTL_SECONDS:
                    logger.info("Overpass in-process TTL cache HIT for key %s", cache_key)
                    return

        radius_m = int(min(radius_km, 35.0) * 1000)
        osm_venues = cls._query_overpass_mirrors(lat, lng, radius_m, city_hint)
        if not osm_venues:
            osm_venues = cls._query_nominatim_venues(lat, lng, radius_km, city_hint)

        cls._persist_discovered_osm_venues(db, osm_venues)

        with _OVERPASS_CACHE_LOCK:
            _OVERPASS_CACHE[cache_key] = (now, osm_venues)

    @staticmethod
    def _resolve_rating_tier(avg_rating: float | None, rating_count: int) -> str:
        if avg_rating is None or rating_count == 0:
            return "new_unrated"
        if avg_rating >= 4.8 and rating_count >= 15:
            return "top_rated"
        if avg_rating >= 4.0:
            return "highly_rated"
        return "rated"

    @classmethod
    def _profile_to_item(
        cls, profile: VendorProfile, distance_km: float | None
    ) -> VendorDiscoveryItem:
        avg_rating = float(profile.average_rating) if profile.average_rating is not None else None
        rating_count = profile.rating_count or 0
        rating_tier = cls._resolve_rating_tier(avg_rating, rating_count)

        cost_est = CostEstimateResponse(
            is_estimate=True, limited_data=True, estimated_cost_display="Limited data"
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
            is_verified_profile=bool(profile.is_verified_profile or False),
            coordinate_precision=profile.coordinate_precision or "locality_approximate",
            cost_estimate=cost_est,
            source_notes=profile.source_notes,
        )
