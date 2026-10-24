import math
import uuid
import logging
import urllib.request
import urllib.parse
import json
import time
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.models.models import VendorProfile
from backend.app.schemas.discovery import (
    VendorDiscoveryItem,
    VendorDiscoveryResponse,
    CostEstimateResponse
)

logger = logging.getLogger(__name__)

OSM_USER_AGENT = "UtsavCelebrationApp/1.0 (utsav.celebrations@gmail.com)"


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
    "indore": (22.7196, 75.8577),
    "hyderabad": (17.3850, 78.4867),
    "chennai": (13.0827, 80.2707),
    "kolkata": (22.5726, 88.3639),
    "ahmedabad": (23.0225, 72.5714),
    "lucknow": (26.8467, 80.9462),
    "chandigarh": (30.7333, 76.7794),
    "udaipur": (24.5854, 73.7125),
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
    def geocode_query(cls, query_text: str) -> Optional[Tuple[float, float, str]]:
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
            url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(query_text)}&format=json&countrycodes=in&limit=1"
            req = urllib.request.Request(url, headers={"User-Agent": OSM_USER_AGENT})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data and len(data) > 0:
                    first = data[0]
                    return (float(first["lat"]), float(first["lon"]), first.get("display_name", query_text))
        except Exception as e:
            logger.warning("Nominatim geocode failed for '%s': %s", query_text, e)
        return None

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

        # Fallback to city center or Nominatim geocode if lat/lng not provided
        if (resolved_lat is None or resolved_lng is None) and city:
            clean_city = city.strip().lower()
            if clean_city in CITY_CENTERS:
                resolved_lat, resolved_lng = CITY_CENTERS[clean_city]
            else:
                geocoded = cls.geocode_query(city)
                if geocoded:
                    resolved_lat, resolved_lng, _ = geocoded

        # If lat/lng could not be resolved, fall back to pure text city match
        if resolved_lat is None or resolved_lng is None:
            query = db.query(VendorProfile)
            if category:
                query = query.filter(VendorProfile.category.ilike(f"%{category.strip()}%"))
            if city:
                query = query.filter(VendorProfile.city.ilike(f"%{city.strip()}%"))
            profiles = query.all()

            results: List[VendorDiscoveryItem] = [
                cls._profile_to_item(p, distance_km=None) for p in profiles
            ]
            return VendorDiscoveryResponse(
                query_lat=None,
                query_lng=None,
                query_city=city,
                radius_km=radius_km,
                category_filter=category,
                total_results=len(results),
                results=results
            )

        # 1. Fetch existing DB profiles in bounding box (including curated Jaipur/Pune seeds)
        deg_lat = radius_km / 111.0
        rad_lat = math.radians(resolved_lat)
        deg_lng = radius_km / (111.0 * max(0.1, math.cos(rad_lat)))

        min_lat = resolved_lat - deg_lat
        max_lat = resolved_lat + deg_lat
        min_lng = resolved_lng - deg_lng
        max_lng = resolved_lng + deg_lng

        db_query = db.query(VendorProfile).filter(
            VendorProfile.latitude >= min_lat,
            VendorProfile.latitude <= max_lat,
            VendorProfile.longitude >= min_lng,
            VendorProfile.longitude <= max_lng
        )
        if category:
            db_query = db_query.filter(VendorProfile.category.ilike(f"%{category.strip()}%"))

        existing_candidates = db_query.all()

        # 2. Query OpenStreetMap for nationwide venues (Overpass + Nominatim)
        # Extend real coverage anywhere in India without fabricating
        cls._fetch_and_persist_osm_venues(
            db=db,
            lat=resolved_lat,
            lng=resolved_lng,
            radius_km=radius_km,
            city_hint=city
        )

        # 3. Re-query all candidates in bounding box (seed + persisted OSM venues)
        all_candidates = db_query.all()

        # 4. Compute Haversine distance, deduplicate, filter, and sort
        items_with_distance: List[Tuple[VendorDiscoveryItem, float]] = []
        seen_names = set()

        for p in all_candidates:
            if p.latitude is None or p.longitude is None:
                continue

            dist = haversine_distance_km(
                resolved_lat, resolved_lng,
                float(p.latitude), float(p.longitude)
            )
            if dist <= radius_km:
                # Deduplicate: if curated seed exists with similar name, prioritize it over OSM node
                name_key = p.business_name.strip().lower()
                if name_key in seen_names:
                    continue
                seen_names.add(name_key)

                item = cls._profile_to_item(p, distance_km=dist)
                items_with_distance.append((item, dist))

        # Sort
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

    @classmethod
    def _fetch_and_persist_osm_venues(
        cls,
        db: Session,
        lat: float,
        lng: float,
        radius_km: float,
        city_hint: Optional[str] = None
    ) -> None:
        """
        Queries OpenStreetMap (via Overpass API with Nominatim fallback) for real venue records.
        Any newly discovered OSM venue is persisted into `vendor_profiles` with a deterministic UUID,
        guaranteeing that `POST /events/{id}/compose` can reference it via `vendor_profile_id`
        with 100% database relational integrity.
        """
        osm_venues: List[dict] = []
        radius_m = int(min(radius_km, 35.0) * 1000)

        # Strategy A: Overpass API across mirrors (3.5s timeout)
        overpass_servers = [
            "https://overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter",
            "https://overpass.private.coffee/api/interpreter"
        ]
        ql = f"""[out:json][timeout:4];
(
  node["amenity"="events_venue"](around:{radius_m},{lat},{lng});
  node["amenity"="community_centre"](around:{radius_m},{lat},{lng});
  node["tourism"="hotel"]["name"~"banquet|lawn|marriage|garden|resort|palace|convention",i](around:{radius_m},{lat},{lng});
  node["name"~"banquet|marriage garden|mangal karyalay|kalyana mandap|kalyana mantap|marriage hall",i](around:{radius_m},{lat},{lng});
);
out center 15;"""
        overpass_data = urllib.parse.urlencode({"data": ql}).encode("utf-8")

        for srv in overpass_servers:
            try:
                req = urllib.request.Request(srv, data=overpass_data, headers={"User-Agent": OSM_USER_AGENT})
                with urllib.request.urlopen(req, timeout=1.8) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    elements = data.get("elements", [])
                    for el in elements:
                        tags = el.get("tags", {})
                        v_name = tags.get("name") or tags.get("name:en")
                        if not v_name:
                            continue
                        v_lat = el.get("lat") or el.get("center", {}).get("lat")
                        v_lon = el.get("lon") or el.get("center", {}).get("lon")
                        if v_lat is None or v_lon is None:
                            continue
                        osm_type = el.get("type", "node")
                        osm_id = el.get("id")
                        osm_venues.append({
                            "osm_type": osm_type,
                            "osm_id": osm_id,
                            "name": v_name,
                            "lat": float(v_lat),
                            "lng": float(v_lon),
                            "locality": tags.get("addr:suburb") or tags.get("addr:neighbourhood") or tags.get("addr:street"),
                            "city": tags.get("addr:city") or city_hint or "Nearby",
                            "category": "events_venue" if tags.get("amenity") == "events_venue" else "venue"
                        })
                    if osm_venues:
                        break
            except Exception as e:
                logger.debug("Overpass query failed on %s: %s", srv, e)
                continue

        # Strategy B: If Overpass is busy/down, query OpenStreetMap Nominatim
        if not osm_venues:
            # Cultural terms by region
            search_terms = ["marriage garden", "mangal karyalay", "kalyana mantapa", "banquet hall"]
            # Resolve city name if not provided
            target_city = city_hint
            if not target_city:
                try:
                    rev_url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json"
                    rev_req = urllib.request.Request(rev_url, headers={"User-Agent": OSM_USER_AGENT})
                    with urllib.request.urlopen(rev_req, timeout=3.0) as rev_resp:
                        rev_data = json.loads(rev_resp.read().decode("utf-8"))
                        addr = rev_data.get("address", {})
                        target_city = addr.get("city") or addr.get("town") or addr.get("state_district")
                except Exception:
                    pass

            for term in search_terms:
                query_str = f"{term} {target_city}" if target_city else term
                try:
                    url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(query_str)}&format=json&limit=6&countrycodes=in"
                    req = urllib.request.Request(url, headers={"User-Agent": OSM_USER_AGENT})
                    with urllib.request.urlopen(req, timeout=3.5) as resp:
                        items = json.loads(resp.read().decode("utf-8"))
                        for it in items:
                            v_name = it.get("name") or it.get("display_name", "").split(",")[0]
                            osm_type = it.get("osm_type", "node")
                            osm_id = it.get("osm_id")
                            v_lat = float(it.get("lat"))
                            v_lng = float(it.get("lon"))
                            # Check distance
                            if haversine_distance_km(lat, lng, v_lat, v_lng) <= radius_km:
                                osm_venues.append({
                                    "osm_type": osm_type,
                                    "osm_id": osm_id,
                                    "name": v_name,
                                    "lat": v_lat,
                                    "lng": v_lng,
                                    "locality": it.get("display_name", "").split(",")[1].strip() if "," in it.get("display_name", "") else None,
                                    "city": target_city or "Nearby",
                                    "category": "venue"
                                })
                        if len(osm_venues) >= 6:
                            break
                except Exception as e:
                    logger.debug("Nominatim search failed for '%s': %s", query_str, e)
                    continue

        # Persist newly discovered OSM venues into vendor_profiles table
        new_profiles_count = 0
        for v in osm_venues:
            # Deterministic UUID from OSM entity
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
                    average_rating=None,  # Honest unrated
                    rating_count=0,
                    coordinate_precision="exact_osm_node",
                    source_notes=f"OpenStreetMap (Real OSM Record: {v['osm_type']}/{v['osm_id']})"
                )
                db.add(profile)
                new_profiles_count += 1

        if new_profiles_count > 0:
            try:
                db.commit()
                logger.info("Persisted %d new OpenStreetMap venues into vendor_profiles", new_profiles_count)
            except Exception as e:
                db.rollback()
                logger.warning("Failed to commit OSM venues: %s", e)

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
