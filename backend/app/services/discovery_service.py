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
    "overpass.private.coffee",
}


def _validate_safe_outbound_url(url: str) -> None:
    """
    Enforces strict scheme and domain allow-listing on all outbound HTTP requests.
    Prevents Server-Side Request Forgery (SSRF) to internal/private IPs or unvetted hosts.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(
            f"SSRF Guard: Insecure scheme '{parsed.scheme}' blocked. Only HTTPS permitted."
        )
    if parsed.netloc not in ALLOWED_OUTBOUND_DOMAINS:
        raise ValueError(
            f"SSRF Guard: Outbound destination '{parsed.netloc}' not in approved domain allowlist."
        )


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
    if lower.startswith(
        ("node/", "way/", "relation/", "osm node", "osm way", "osm relation", "osm/")
    ):
        return False
    # Filter out pure numbers or address numbers like '14/2', '101'
    if re.match(r"^[\d\s\/\-\.,#]+$", clean):
        return False
    # Filter out generic single-word placeholders with no distinct identity
    return lower not in {
        "unnamed",
        "unknown",
        "venue",
        "banquet",
        "hall",
        "marriage garden",
        "hotel",
        "resort",
        "palace",
    }


def extract_distinctive_tokens(name: str) -> set:
    """Extracts distinctive name tokens, removing common venue descriptor stop words."""
    stop_words = {
        "the",
        "hotel",
        "resort",
        "and",
        "&",
        "palace",
        "hall",
        "banquet",
        "garden",
        "gardens",
        "marriage",
        "jaipur",
        "pune",
        "bengaluru",
        "bangalore",
        "indore",
        "mangal",
        "karyalay",
        "karyalaya",
        "kalyana",
        "mandap",
        "mandapa",
        "mantap",
        "mantapa",
        "convention",
        "centre",
        "center",
        "lawns",
        "lawn",
        "inn",
        "suites",
        "party",
        "plot",
    }
    tokens = set(re.findall(r"[a-z0-9]+", name.lower()))
    distinctive = tokens - stop_words
    return distinctive if distinctive else tokens


# Corporate hotel chains and qualifiers allowable as additions to the same physical venue
ALLOWABLE_CHAIN_QUALIFIERS = {
    "taj",
    "oberoi",
    "itc",
    "leela",
    "hyatt",
    "marriott",
    "radisson",
    "hilton",
    "novotel",
    "westin",
    "sheraton",
    "sofitel",
    "lalit",
    "clarks",
    "road",
    "main",
    "near",
    "opp",
    "opposite",
}

# Generic modifiers / honorifics that are ubiquitous across Indian businesses
# A shared token among these alone NEVER qualifies as a duplicate
GENERIC_NAME_MODIFIERS = {
    "grand",
    "royal",
    "new",
    "classic",
    "star",
    "city",
    "prime",
    "elite",
    "golden",
    "silver",
    "crown",
    "shree",
    "shri",
    "sri",
    "om",
    "sai",
    "jai",
    "best",
    "top",
    "central",
}


def _is_name_or_city_suffix_match(norm1: str, norm2: str) -> bool:
    if norm1 == norm2:
        return True
    if (norm1.startswith(norm2) or norm2.startswith(norm1)) and abs(len(norm1) - len(norm2)) <= 10:
        remainder = norm1.replace(norm2, "") if len(norm1) > len(norm2) else norm2.replace(norm1, "")
        if remainder in {"jaipur", "pune", "bengaluru", "indore", "delhi", "mumbai"}:
            return True
    return False


def _are_tokens_duplicate(toks1: set[str], toks2: set[str]) -> bool:
    if not toks1 or not toks2:
        return False
    if toks1 == toks2:
        return not toks1.issubset(GENERIC_NAME_MODIFIERS)

    shared = toks1 & toks2
    diff = toks1 ^ toks2
    if not shared or shared.issubset(GENERIC_NAME_MODIFIERS):
        return False

    has_substantial_proper_noun = any(
        len(t) >= 4 and t not in GENERIC_NAME_MODIFIERS for t in shared
    )
    if not has_substantial_proper_noun:
        return False
    return bool(diff.issubset(ALLOWABLE_CHAIN_QUALIFIERS))


def are_venues_duplicates(
    name1: str, lat1: float, lng1: float, name2: str, lat2: float, lng2: float
) -> bool:
    """
    Determines whether two venue profiles represent the exact same physical venue.
    Guards strictly against over-merging distinct businesses while ensuring true duplicates
    (e.g., 'Rambagh Palace' vs 'The Rambagh Palace, Jaipur') are cleanly collapsed.
    """
    norm1 = re.sub(r"[^a-z0-9]", "", name1.lower())
    norm2 = re.sub(r"[^a-z0-9]", "", name2.lower())
    if norm1 == norm2:
        return True

    if haversine_distance_km(lat1, lng1, lat2, lng2) > 0.35:
        return False

    if _is_name_or_city_suffix_match(norm1, norm2):
        return True

    toks1 = extract_distinctive_tokens(name1)
    toks2 = extract_distinctive_tokens(name2)
    return _are_tokens_duplicate(toks1, toks2)


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
            with urllib.request.urlopen(req, timeout=4) as resp:  # noqa: S310 # nosec B310
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
            if item.latitude and item.longitude and are_venues_duplicates(
                name1=p.business_name, lat1=p_lat, lng1=p_lng,
                name2=item.business_name, lat2=item.latitude, lng2=item.longitude,
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
            if p.latitude is None or p.longitude is None or not is_valid_venue_name(p.business_name):
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
        resolved_lat, resolved_lng = cls._resolve_coordinates(lat, lng, city)

        if resolved_lat is None or resolved_lng is None:
            query = db.query(VendorProfile)
            if category:
                query = query.filter(VendorProfile.category.ilike(f"%{category.strip()}%"))
            if city:
                query = query.filter(VendorProfile.city.ilike(f"%{city.strip()}%"))
            results = [cls._profile_to_item(p, distance_km=None) for p in query.all()]
            return VendorDiscoveryResponse(
                query_lat=None, query_lng=None, query_city=city, radius_km=radius_km,
                category_filter=category, total_results=len(results), results=results,
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
        results = cls._deduplicate_and_sort_candidates(all_candidates, resolved_lat, resolved_lng, radius_km)

        return VendorDiscoveryResponse(
            query_lat=resolved_lat, query_lng=resolved_lng, query_city=city,
            radius_km=radius_km, category_filter=category, total_results=len(results), results=results,
        )

    @staticmethod
    def _extract_el_coords(el: dict[str, Any]) -> tuple[float, float] | None:
        center = el.get("center") or {}
        lat = el.get("lat") if el.get("lat") is not None else center.get("lat")
        lon = el.get("lon") if el.get("lon") is not None else center.get("lon")
        if lat is not None and lon is not None:
            return float(lat), float(lon)
        return None

    @classmethod
    def _parse_overpass_element(cls, el: dict[str, Any], city_hint: str | None) -> dict[str, Any] | None:
        tags = el.get("tags", {})
        v_name = tags.get("name") or tags.get("name:en")
        if not is_valid_venue_name(v_name):
            return None
        coords = cls._extract_el_coords(el)
        if coords is None:
            return None
        v_lat, v_lon = coords

        locality = None
        for k in ("addr:suburb", "addr:neighbourhood", "addr:street"):
            val = tags.get(k)
            if val:
                locality = str(val)
                break

        return {
            "osm_type": el.get("type", "node"),
            "osm_id": el.get("id"),
            "name": str(v_name).strip(),
            "lat": v_lat,
            "lng": v_lon,
            "locality": locality,
            "city": city_hint.title() if city_hint else (tags.get("addr:city") or "Nearby"),
            "category": "events_venue" if tags.get("amenity") == "events_venue" else "venue",
        }

    @classmethod
    def _query_overpass_mirrors(
        cls, lat: float, lng: float, radius_m: int, city_hint: str | None
    ) -> list[dict]:
        servers = [
            "https://overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter",
            "https://overpass.private.coffee/api/interpreter",
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
        venues = []

        for srv in servers:
            try:
                _validate_safe_outbound_url(srv)
                req = urllib.request.Request(srv, data=overpass_data, headers={"User-Agent": OSM_USER_AGENT})  # noqa: S310
                with urllib.request.urlopen(req, timeout=1.8) as resp:  # noqa: S310 # nosec B310
                    data = json.loads(resp.read().decode("utf-8"))
                    for el in data.get("elements", []):
                        parsed = cls._parse_overpass_element(el, city_hint)
                        if parsed:
                            venues.append(parsed)
                    if venues:
                        break
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError, OSError) as e:
                logger.debug("Overpass query failed on %s: %s", srv, e)
                continue
        return venues

    @classmethod
    def _parse_nominatim_item(
        cls, it: dict[str, Any], target_city: str | None, lat: float, lng: float, radius_km: float
    ) -> dict[str, Any] | None:
        v_name = it.get("name") or it.get("display_name", "").split(",")[0]
        if not is_valid_venue_name(v_name):
            return None
        v_lat, v_lng = float(it.get("lat")), float(it.get("lon"))
        if haversine_distance_km(lat, lng, v_lat, v_lng) > radius_km:
            return None
        return {
            "osm_type": it.get("osm_type", "node"),
            "osm_id": it.get("osm_id"),
            "name": str(v_name).strip(),
            "lat": v_lat,
            "lng": v_lng,
            "locality": it.get("display_name", "").split(",")[1].strip() if "," in it.get("display_name", "") else None,
            "city": target_city or "Nearby",
            "category": "venue",
        }

    @classmethod
    def _resolve_target_city(cls, lat: float, lng: float, city_hint: str | None) -> str | None:
        if city_hint:
            return city_hint
        try:
            rev_url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json"
            _validate_safe_outbound_url(rev_url)
            rev_req = urllib.request.Request(rev_url, headers={"User-Agent": OSM_USER_AGENT})
            with urllib.request.urlopen(rev_req, timeout=3.0) as rev_resp:  # noqa: S310 # nosec B310
                rev_data = json.loads(rev_resp.read().decode("utf-8"))
                addr = rev_data.get("address", {})
                return addr.get("city") or addr.get("town") or addr.get("state_district")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError, OSError) as exc:
            logger.debug("Failed reverse geocoding city lookup: %s", exc)
        return None

    @classmethod
    def _query_nominatim_venues(
        cls, lat: float, lng: float, radius_km: float, city_hint: str | None
    ) -> list[dict]:
        target_city = cls._resolve_target_city(lat, lng, city_hint)
        search_terms = ["marriage garden", "mangal karyalay", "kalyana mantapa", "banquet hall"]
        venues = []
        for term in search_terms:
            query_str = f"{term} {target_city}" if target_city else term
            try:
                url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(query_str)}&format=json&limit=6&countrycodes=in"
                _validate_safe_outbound_url(url)
                req = urllib.request.Request(url, headers={"User-Agent": OSM_USER_AGENT})
                with urllib.request.urlopen(req, timeout=3.5) as resp:  # noqa: S310 # nosec B310
                    for it in json.loads(resp.read().decode("utf-8")):
                        parsed = cls._parse_nominatim_item(it, target_city, lat, lng, radius_km)
                        if parsed:
                            venues.append(parsed)
                    if len(venues) >= 6:
                        break
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError, OSError) as e:
                logger.debug("Nominatim search failed for '%s': %s", query_str, e)
                continue
        return venues

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
                logger.info("Persisted %d new OpenStreetMap venues into vendor_profiles", new_profiles_count)
            except SQLAlchemyError as e:
                db.rollback()
                logger.warning("Failed to commit OSM venues: %s", e)

    @classmethod
    def _fetch_and_persist_osm_venues(
        cls, db: Session, lat: float, lng: float, radius_km: float, city_hint: str | None = None
    ) -> None:
        cache_key = (round(lat, 2), round(lng, 2), int(radius_km), (city_hint or "").lower().strip())
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
    def _profile_to_item(cls, profile: VendorProfile, distance_km: float | None) -> VendorDiscoveryItem:
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
