import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from backend.app.services.discovery.dedup import is_valid_venue_name
from backend.app.services.discovery.geo import (
    _validate_safe_outbound_url,
    haversine_distance_km,
)

logger = logging.getLogger(__name__)

OSM_USER_AGENT = "UtsavCelebrationApp/1.0 (utsav.celebrations@gmail.com)"

ALLOWED_OUTBOUND_DOMAINS = {
    "nominatim.openstreetmap.org",
    "overpass-api.de",
    "overpass.kumi.systems",
    "overpass.private.coffee",
}


class OSMClient:
    @staticmethod
    def _extract_el_coords(el: dict[str, Any]) -> tuple[float, float] | None:
        center = el.get("center") or {}
        lat = el.get("lat") if el.get("lat") is not None else center.get("lat")
        lon = el.get("lon") if el.get("lon") is not None else center.get("lon")
        if lat is not None and lon is not None:
            return float(lat), float(lon)
        return None

    @classmethod
    def _parse_overpass_element(
        cls, el: dict[str, Any], city_hint: str | None
    ) -> dict[str, Any] | None:
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
        names_regex = (
            "banquet|marriage garden|mangal karyalay|"
            "kalyana mandap|kalyana mantap|marriage hall"
        )
        hotel_names = "banquet|lawn|marriage|garden|resort|palace|convention"
        ql = (
            f"[out:json][timeout:4];\n"
            f"(\n"
            f'  node["amenity"="events_venue"](around:{radius_m},{lat},{lng});\n'
            f'  node["amenity"="community_centre"](around:{radius_m},{lat},{lng});\n'
            f'  node["tourism"="hotel"]["name"~"{hotel_names}",i]'
            f"(around:{radius_m},{lat},{lng});\n"
            f'  node["name"~"{names_regex}",i]'
            f"(around:{radius_m},{lat},{lng});\n"
            f");\n"
            f"out center 15;"
        )
        overpass_data = urllib.parse.urlencode({"data": ql}).encode("utf-8")
        venues = []

        for srv in servers:
            try:
                _validate_safe_outbound_url(srv)
                req = urllib.request.Request(  # noqa: S310
                    srv, data=overpass_data, headers={"User-Agent": OSM_USER_AGENT}
                )
                with urllib.request.urlopen(req, timeout=1.8) as resp:  # nosec B310 # noqa: S310
                    data = json.loads(resp.read().decode("utf-8"))
                    for el in data.get("elements", []):
                        parsed = cls._parse_overpass_element(el, city_hint)
                        if parsed:
                            venues.append(parsed)
                    if venues:
                        break
            except (
                urllib.error.URLError,
                TimeoutError,
                json.JSONDecodeError,
                KeyError,
                ValueError,
                OSError,
            ) as e:
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
        raw_lat = it.get("lat")
        raw_lng = it.get("lon")
        if raw_lat is None or raw_lng is None:
            return None
        v_lat, v_lng = float(raw_lat), float(raw_lng)
        if haversine_distance_km(lat, lng, v_lat, v_lng) > radius_km:
            return None
        return {
            "osm_type": it.get("osm_type", "node"),
            "osm_id": it.get("osm_id"),
            "name": str(v_name).strip(),
            "lat": v_lat,
            "lng": v_lng,
            "locality": it.get("display_name", "").split(",")[1].strip()
            if "," in it.get("display_name", "")
            else None,
            "city": target_city or "Nearby",
            "category": "venue",
        }

    @classmethod
    def _resolve_target_city(cls, lat: float, lng: float, city_hint: str | None) -> str | None:
        if city_hint:
            return city_hint
        try:
            rev_url = (
                f"https://nominatim.openstreetmap.org/reverse"
                f"?lat={lat}&lon={lng}&format=json"
            )
            _validate_safe_outbound_url(rev_url)
            rev_req = urllib.request.Request(
                rev_url, headers={"User-Agent": OSM_USER_AGENT}
            )
            with urllib.request.urlopen(rev_req, timeout=3.0) as rev_resp:  # nosec B310 # noqa: S310
                rev_data = json.loads(rev_resp.read().decode("utf-8"))
                addr: dict[str, Any] = rev_data.get("address", {})
                city_val = addr.get("city") or addr.get("town") or addr.get("state_district")
                return str(city_val) if city_val else None
        except (
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError,
            KeyError,
            ValueError,
            OSError,
        ) as exc:
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
                url = (
                    f"https://nominatim.openstreetmap.org/search"
                    f"?q={urllib.parse.quote(query_str)}&format=json&limit=6&countrycodes=in"
                )
                _validate_safe_outbound_url(url)
                req = urllib.request.Request(url, headers={"User-Agent": OSM_USER_AGENT})
                with urllib.request.urlopen(req, timeout=3.5) as resp:  # nosec B310 # noqa: S310
                    for it in json.loads(resp.read().decode("utf-8")):
                        parsed = cls._parse_nominatim_item(it, target_city, lat, lng, radius_km)
                        if parsed:
                            venues.append(parsed)
                    if len(venues) >= 6:
                        break
            except (
                urllib.error.URLError,
                TimeoutError,
                json.JSONDecodeError,
                KeyError,
                ValueError,
                OSError,
            ) as e:
                logger.debug("Nominatim search failed for '%s': %s", query_str, e)
                continue
        return venues
