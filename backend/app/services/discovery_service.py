import json
import logging
import math
import re
import threading
import time
import urllib.parse
import urllib.request
import uuid

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models.models import VendorProfile
from backend.app.schemas.discovery import (
    CostEstimateResponse,
    VendorDiscoveryItem,
    VendorDiscoveryResponse,
)

logger = logging.getLogger(__name__)

OSM_USER_AGENT = "UtsavCelebrationApp/1.0 (utsav.celebrations@gmail.com)"

# In-Process Free-Tier TTL Cache (15-Minute Expiry per DEC-035)
# Key: (round(lat, 2), round(lng, 2), int(radius_km), (city_hint or "").lower().strip())
# Value: (timestamp, list_of_osm_venues)
_OVERPASS_CACHE: dict = {}
_OVERPASS_CACHE_LOCK = threading.Lock()
OVERPASS_CACHE_TTL_SECONDS = 15 * 60  # 15 minutes


ALLOWED_OUTBOUND_DOMAINS = {
    "nominatim.openstreetmap.org",
    "overpass-api.de",
    "overpass.kumi.systems",
    "overpass.private.coffee"
}


def _validate_safe_outbound_url(url: str) -> None:
    """
    Enforces strict scheme and domain allow-listing on all outbound HTTP requests.
    Prevents Server-Side Request Forgery (SSRF) to internal/private IPs or unvetted hosts.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"SSRF Guard: Insecure scheme '{parsed.scheme}' blocked. Only HTTPS permitted.")
    if parsed.netloc not in ALLOWED_OUTBOUND_DOMAINS:
        raise ValueError(f"SSRF Guard: Outbound destination '{parsed.netloc}' not in approved domain allowlist.")


def is_valid_venue_name(name: str | None) -> bool:
    """
    Filters out nameless, un-named, pure address/digits, raw ID fallbacks,
    or generic placeholder OSM results so only properly-named real celebration places reach the UI.
    """
    if not name or not isinstance(name, str):
        return False
    clean = name.strip()
    if len(clean) < 3:
        return False
    if not any(c.isalpha() for c in clean):
        return False
    lower = clean.lower()
    # Filter out raw OSM identifiers and fallbacks
    if lower.startswith(("node/", "way/", "relation/", "osm node", "osm way", "osm relation", "osm/")):
        return False
    # Filter out pure numbers or address numbers like '14/2', '101'
    if re.match(r"^[\d\s\/\-\.,#]+$", clean):
        return False
    # Filter out generic single-word placeholders with no distinct identity
    return lower not in {"unnamed", "unknown", "venue", "banquet", "hall", "marriage garden", "hotel", "resort", "palace"}


def extract_distinctive_tokens(name: str) -> set:
    """Extracts distinctive name tokens, removing common venue descriptor stop words."""
    stop_words = {
        "the", "hotel", "resort", "and", "&", "palace", "hall", "banquet",
        "garden", "gardens", "marriage", "jaipur", "pune", "bengaluru",
        "bangalore", "indore", "mangal", "karyalay", "karyalaya", "kalyana",
        "mandap", "mandapa", "mantap", "mantapa", "convention", "centre", "center",
        "lawns", "lawn", "inn", "suites", "party", "plot"
    }
    tokens = set(re.findall(r"[a-z0-9]+", name.lower()))
    distinctive = tokens - stop_words
    return distinctive if distinctive else tokens


# Corporate hotel chains and qualifiers allowable as additions to the same physical venue
ALLOWABLE_CHAIN_QUALIFIERS = {
    "taj", "oberoi", "itc", "leela", "hyatt", "marriott", "radisson",
    "hilton", "novotel", "westin", "sheraton", "sofitel", "lalit",
    "clarks", "road", "main", "near", "opp", "opposite"
}

# Generic modifiers / honorifics that are ubiquitous across Indian businesses
# A shared token among these alone NEVER qualifies as a duplicate
GENERIC_NAME_MODIFIERS = {
    "grand", "royal", "new", "classic", "star", "city", "prime", "elite",
    "golden", "silver", "crown", "shree", "shri", "sri", "om", "sai", "jai",
    "best", "top", "central"
}


def are_venues_duplicates(
    name1: str, lat1: float, lng1: float,
    name2: str, lat2: float, lng2: float
) -> bool:
    """
    Determines whether two venue profiles represent the exact same physical venue.
    Guards strictly against over-merging distinct businesses while ensuring true duplicates
    (e.g., 'Rambagh Palace' vs 'The Rambagh Palace, Jaipur') are cleanly collapsed.
    """
    # 1. Exact normalized alphanumeric match (ignoring case, spaces, punctuation)
    norm1 = re.sub(r"[^a-z0-9]", "", name1.lower())
    norm2 = re.sub(r"[^a-z0-9]", "", name2.lower())
    if norm1 == norm2:
        return True

    # Check physical distance
    dist_km = haversine_distance_km(lat1, lng1, lat2, lng2)
    # Beyond 350 meters, two venues are never considered the same physical venue
    if dist_km > 0.35:
        return False

    # Normalized prefix/suffix match with city name (e.g. 'rambaghpalacejaipur' vs 'rambaghpalace')
    if (norm1.startswith(norm2) or norm2.startswith(norm1)) and abs(len(norm1) - len(norm2)) <= 10:
        remainder = norm1.replace(norm2, "") if len(norm1) > len(norm2) else norm2.replace(norm1, "")
        if remainder in {"jaipur", "pune", "bengaluru", "indore", "delhi", "mumbai"}:
            return True

    toks1 = extract_distinctive_tokens(name1)
    toks2 = extract_distinctive_tokens(name2)

    if not toks1 or not toks2:
        return False

    # 2. Distinctive token set equality (e.g. {'rambagh'} == {'rambagh'}, {'jw', 'marriott'} == {'jw', 'marriott'})
    if toks1 == toks2:
        # If the ONLY tokens are generic modifiers (e.g. {'royal'} or {'grand'}),
        # do NOT merge without exact normalized match
        # Specific brand/proper noun match
        return not toks1.issubset(GENERIC_NAME_MODIFIERS)

    # 3. Subset match with corporate chain qualifiers (e.g. {'taj', 'rambagh'} vs {'rambagh'})
    shared = toks1 & toks2
    diff = toks1 ^ toks2

    # If shared tokens are only generic modifiers (e.g. 'shree', 'sai', 'royal', 'grand'), do NOT merge
    if not shared or shared.issubset(GENERIC_NAME_MODIFIERS):
        return False

    # Must share at least one substantial specific proper noun (>= 4 chars, not generic)
    has_substantial_proper_noun = any(len(t) >= 4 and t not in GENERIC_NAME_MODIFIERS for t in shared)
    if not has_substantial_proper_noun:
        return False

    # If all differing tokens are allowable hotel chain/qualifiers, they are the same physical venue
    return bool(diff.issubset(ALLOWABLE_CHAIN_QUALIFIERS))


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
            url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(query_text)}&format=json&countrycodes=in&limit=1"
            _validate_safe_outbound_url(url)
            req = urllib.request.Request(url, headers={"User-Agent": OSM_USER_AGENT})
            with urllib.request.urlopen(req, timeout=4) as resp:  # nosec B310
                data = json.loads(resp.read().decode("utf-8"))
                if data and len(data) > 0:
                    first = data[0]
                    return (float(first["lat"]), float(first["lon"]), first.get("display_name", query_text))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, IndexError, ValueError, OSError) as e:
            logger.warning("Nominatim geocode failed for '%s': %s", query_text, e)
        return None

    @classmethod
    def search_vendors(
        cls,
        db: Session,
        lat: float | None = None,
        lng: float | None = None,
        city: str | None = None,
        radius_km: float = 25.0,
        category: str | None = None,
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

            results: list[VendorDiscoveryItem] = [
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

        db_query.all()

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

        # 4. Compute Haversine distance, deduplicate, filter nameless/garbage, and sort
        # Prioritize curated baseline seeds (pickyourtrail/venuelook) first so duplicates from OSM are dropped
        def candidate_priority(p: VendorProfile) -> int:
            notes = (p.source_notes or "").lower()
            if "pickyourtrail" in notes or "venuelook" in notes:
                return 0  # Curated seed (highest priority)
            if p.is_verified_profile:
                return 1
            return 2      # External OSM record

        sorted_candidates = sorted(all_candidates, key=candidate_priority)

        accepted_items: list[tuple[VendorDiscoveryItem, float]] = []
        seen_normalized_names = set()

        for p in sorted_candidates:
            if p.latitude is None or p.longitude is None:
                continue

            # Check 2: Filter nameless/garbage/raw-ID venues
            if not is_valid_venue_name(p.business_name):
                continue

            dist = haversine_distance_km(
                resolved_lat, resolved_lng,
                float(p.latitude), float(p.longitude)
            )
            if dist > radius_km:
                continue

            # Deduplication: Check against already accepted higher-priority venues
            # Match A: exact normalized alphanumeric string
            norm_name = re.sub(r"[^a-z0-9]", "", p.business_name.lower())
            if norm_name in seen_normalized_names:
                continue

            # Match B: Intelligent deduplication (spatial proximity + specific proper nouns)
            # Guards strictly against over-merging distinct businesses with short or generic words
            p_lat = float(p.latitude)
            p_lng = float(p.longitude)

            is_duplicate = False
            for accepted_item, _ in accepted_items:
                if accepted_item.latitude and accepted_item.longitude and are_venues_duplicates(
                    name1=p.business_name,
                    lat1=p_lat,
                    lng1=p_lng,
                    name2=accepted_item.business_name,
                    lat2=accepted_item.latitude,
                    lng2=accepted_item.longitude
                ):
                    logger.info(
                        "Deduplicating duplicate venue '%s' against higher-priority '%s'",
                        p.business_name, accepted_item.business_name
                    )
                    is_duplicate = True
                    break

            if is_duplicate:
                continue

            seen_normalized_names.add(norm_name)
            item = cls._profile_to_item(p, distance_km=dist)
            accepted_items.append((item, dist))

        # Sort by distance
        accepted_items.sort(key=lambda x: x[1])
        results = [item for item, _ in accepted_items]

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
        city_hint: str | None = None
    ) -> None:
        """
        Queries OpenStreetMap (via Overpass API with Nominatim fallback) for real venue records.
        Uses in-process thread-safe TTL caching (15 minutes) to avoid redundant external network round trips.
        Any newly discovered OSM venue is persisted into `vendor_profiles` with a deterministic UUID,
        guaranteeing that `POST /events/{id}/compose` can reference it via `vendor_profile_id`
        with 100% database relational integrity.
        """
        cache_key = (round(lat, 2), round(lng, 2), int(radius_km), (city_hint or "").lower().strip())
        now = time.time()

        with _OVERPASS_CACHE_LOCK:
            if cache_key in _OVERPASS_CACHE:
                cached_time, _ = _OVERPASS_CACHE[cache_key]
                if now - cached_time < OVERPASS_CACHE_TTL_SECONDS:
                    logger.info("Overpass in-process TTL cache HIT for key %s (age: %.1fs) - skipping external network query", cache_key, now - cached_time)
                    return

        osm_venues: list[dict] = []
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
                _validate_safe_outbound_url(srv)
                req = urllib.request.Request(srv, data=overpass_data, headers={"User-Agent": OSM_USER_AGENT})
                with urllib.request.urlopen(req, timeout=1.8) as resp:  # nosec B310
                    data = json.loads(resp.read().decode("utf-8"))
                    elements = data.get("elements", [])
                    for el in elements:
                        tags = el.get("tags", {})
                        v_name = tags.get("name") or tags.get("name:en")
                        if not is_valid_venue_name(v_name):
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
                            "name": v_name.strip(),
                            "lat": float(v_lat),
                            "lng": float(v_lon),
                            "locality": tags.get("addr:suburb") or tags.get("addr:neighbourhood") or tags.get("addr:street") or (tags.get("addr:city") if city_hint and tags.get("addr:city") != city_hint else None),
                            "city": city_hint.title() if city_hint else (tags.get("addr:city") or "Nearby"),
                            "category": "events_venue" if tags.get("amenity") == "events_venue" else "venue"
                        })
                    if osm_venues:
                        break
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError, OSError) as e:
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
                    _validate_safe_outbound_url(rev_url)
                    rev_req = urllib.request.Request(rev_url, headers={"User-Agent": OSM_USER_AGENT})
                    with urllib.request.urlopen(rev_req, timeout=3.0) as rev_resp:  # nosec B310
                        rev_data = json.loads(rev_resp.read().decode("utf-8"))
                        addr = rev_data.get("address", {})
                        target_city = addr.get("city") or addr.get("town") or addr.get("state_district")
                except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError, OSError) as exc:
                    logger.debug("Failed reverse geocoding city lookup: %s", exc)

            for term in search_terms:
                query_str = f"{term} {target_city}" if target_city else term
                try:
                    url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(query_str)}&format=json&limit=6&countrycodes=in"
                    _validate_safe_outbound_url(url)
                    req = urllib.request.Request(url, headers={"User-Agent": OSM_USER_AGENT})
                    with urllib.request.urlopen(req, timeout=3.5) as resp:  # nosec B310
                        items = json.loads(resp.read().decode("utf-8"))
                        for it in items:
                            v_name = it.get("name") or it.get("display_name", "").split(",")[0]
                            if not is_valid_venue_name(v_name):
                                continue
                            osm_type = it.get("osm_type", "node")
                            osm_id = it.get("osm_id")
                            v_lat = float(it.get("lat"))
                            v_lng = float(it.get("lon"))
                            # Check distance
                            if haversine_distance_km(lat, lng, v_lat, v_lng) <= radius_km:
                                osm_venues.append({
                                    "osm_type": osm_type,
                                    "osm_id": osm_id,
                                    "name": v_name.strip(),
                                    "lat": v_lat,
                                    "lng": v_lng,
                                    "locality": it.get("display_name", "").split(",")[1].strip() if "," in it.get("display_name", "") else None,
                                    "city": target_city or "Nearby",
                                    "category": "venue"
                                })
                        if len(osm_venues) >= 6:
                            break
                except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError, OSError) as e:
                    logger.debug("Nominatim search failed for '%s': %s", query_str, e)
                    continue

        # Persist newly discovered OSM venues into vendor_profiles table
        new_profiles_count = 0
        for v in osm_venues:
            if not is_valid_venue_name(v.get("name")):
                continue
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
            except SQLAlchemyError as e:
                db.rollback()
                logger.warning("Failed to commit OSM venues: %s", e)

        # Store in in-process TTL cache
        with _OVERPASS_CACHE_LOCK:
            _OVERPASS_CACHE[cache_key] = (now, osm_venues)

    @staticmethod
    def _profile_to_item(profile: VendorProfile, distance_km: float | None) -> VendorDiscoveryItem:
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
            is_verified_profile=bool(profile.is_verified_profile or False),
            coordinate_precision=profile.coordinate_precision or "locality_approximate",
            cost_estimate=cost_est,
            source_notes=profile.source_notes
        )
