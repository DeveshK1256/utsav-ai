import urllib.request

from backend.app.services.discovery.dedup import (
    ALLOWABLE_CHAIN_QUALIFIERS,
    GENERIC_NAME_MODIFIERS,
    are_venues_duplicates,
    extract_distinctive_tokens,
    is_valid_venue_name,
)
from backend.app.services.discovery.geo import (
    CITY_CENTERS,
    _validate_safe_outbound_url,
    haversine_distance_km,
)
from backend.app.services.discovery.service import (
    _OVERPASS_CACHE,
    _OVERPASS_CACHE_LOCK,
    OVERPASS_CACHE_TTL_SECONDS,
    VendorDiscoveryService,
)

__all__ = [
    "ALLOWABLE_CHAIN_QUALIFIERS",
    "CITY_CENTERS",
    "GENERIC_NAME_MODIFIERS",
    "OVERPASS_CACHE_TTL_SECONDS",
    "_OVERPASS_CACHE",
    "_OVERPASS_CACHE_LOCK",
    "VendorDiscoveryService",
    "_validate_safe_outbound_url",
    "are_venues_duplicates",
    "extract_distinctive_tokens",
    "haversine_distance_km",
    "is_valid_venue_name",
    "urllib",
]
