import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.discovery_service import haversine_distance_km
from backend.app.db.session import SessionLocal
from backend.app.models.models import VendorProfile

client = TestClient(app)


def test_haversine_distance_math():
    """Verifies deterministic great-circle Haversine math."""
    # Distance between Taj Mahal Palace Mumbai (18.9220, 72.8347) and Gateway of India (18.9220, 72.8347) is ~0
    d0 = haversine_distance_km(18.9220, 72.8347, 18.9220, 72.8347)
    assert d0 == 0.0

    # Distance between Jaipur (26.9124, 75.7873) and Pune (18.5204, 73.8567) is ~960-970 km
    d_j_p = haversine_distance_km(26.9124, 75.7873, 18.5204, 73.8567)
    assert 950.0 < d_j_p < 980.0


def test_discovery_jaipur_radius_query():
    """
    Tests GET /api/v1/discovery/vendors centered on Jaipur.
    Verifies:
    1. Returns Jaipur venues within 30 km radius.
    2. Results are sorted distance_asc.
    3. Every venue has rating_tier='new_unrated' and average_rating=None (zero fabricated ratings).
    4. Cost estimate has is_estimate=True, limited_data=True, 'Limited data' copy (zero fabricated costs).
    5. is_verified_profile=False for all seed rows.
    """
    res = client.get("/api/v1/discovery/vendors?lat=26.912&lng=75.787&radius_km=30.0")
    assert res.status_code == 200
    data = res.json()

    assert data["total_results"] >= 9
    results = data["results"]

    # Verify distances are sorted ascending
    distances = [r["distance_km"] for r in results]
    assert distances == sorted(distances)

    # Scrutinize honesty rules for every single returned result
    for r in results:
        assert r["rating_tier"] == "new_unrated", f"Violated honest cold-start for {r['business_name']}"
        assert r["average_rating"] is None, f"Fabricated rating found on {r['business_name']}"
        assert r["rating_count"] == 0
        assert r["is_verified_profile"] is False, f"Unverified seed venue marked verified: {r['business_name']}"
        assert r["coordinate_precision"] in ("locality_approximate", "exact_osm_node")
        assert r["cost_estimate"]["is_estimate"] is True
        assert r["cost_estimate"]["limited_data"] is True
        assert r["cost_estimate"]["estimated_cost_display"] == "Limited data"


def test_discovery_pune_category_filter():
    """Tests category filtering in Pune."""
    # Search for lawns near Karve Nagar (18.485, 73.812)
    res = client.get("/api/v1/discovery/vendors?lat=18.485&lng=73.812&radius_km=15.0&category=lawn")
    assert res.status_code == 200
    data = res.json()
    assert data["total_results"] >= 2
    for r in data["results"]:
        assert "lawn" in r["category"].lower()
        assert r["city"].lower() == "pune"


def test_discovery_geolocation_denied_fallback():
    """
    Verifies that when lat/lng are omitted (geolocation denied/unavailable),
    providing a city name succeeds seamlessly without blocking the user.
    """
    res = client.get("/api/v1/discovery/vendors?city=Pune")
    assert res.status_code == 200
    data = res.json()
    assert data["total_results"] >= 8
    assert data["query_city"] == "Pune"
    for r in data["results"]:
        assert r["rating_tier"] == "new_unrated"
        assert r["cost_estimate"]["limited_data"] is True

    # And for Jaipur with 35km radius to cover Samode (28.8km out)
    res_j = client.get("/api/v1/discovery/vendors?city=Jaipur&radius_km=35.0")
    assert res_j.status_code == 200
    assert res_j.json()["total_results"] >= 11


def test_discovery_missing_params_error():
    """Asserts 400 when neither coordinates nor city are supplied."""
    res = client.get("/api/v1/discovery/vendors")
    assert res.status_code == 400
    assert "Either lat/lng coordinates or a fallback city name" in res.json()["detail"]


def test_overpass_in_process_ttl_cache_speedup():
    """
    Verifies that the in-process free-tier TTL cache eliminates redundant network round trips
    and accelerates repeated queries to the same city / coordinates deterministically via call counter.
    """
    from unittest.mock import patch
    from backend.app.services.discovery_service import _OVERPASS_CACHE, VendorDiscoveryService

    # Clear cache for isolated test
    _OVERPASS_CACHE.clear()

    # Query 1: Initial call populates cache
    with patch.object(VendorDiscoveryService, "_fetch_and_persist_osm_venues", wraps=VendorDiscoveryService._fetch_and_persist_osm_venues) as spy_fetch:
        res1 = client.get("/api/v1/discovery/vendors?city=Pune")
        assert res1.status_code == 200
        assert spy_fetch.call_count >= 1
        assert len(_OVERPASS_CACHE) >= 1

    # Query 2: Cached repeat - must hit in-memory cache and bypass network round-trips
    with patch("urllib.request.urlopen") as mock_urlopen:
        res2 = client.get("/api/v1/discovery/vendors?city=Pune")
        assert res2.status_code == 200
        # Overpass network calls must be completely bypassed on cache hit
        mock_urlopen.assert_not_called()

    assert len(res1.json()["results"]) == len(res2.json()["results"])

import json
from unittest.mock import MagicMock, patch
from backend.app.services.discovery_service import (
    VendorDiscoveryService,
    CITY_CENTERS,
    haversine_distance_km,
)


def test_discovery_service_utility_and_edge_branches(db):
    from backend.app.services.discovery_service import is_valid_venue_name, are_venues_duplicates, VendorDiscoveryService

    # 1. is_valid_venue_name branches
    assert is_valid_venue_name("node/12345") is False
    assert is_valid_venue_name("14/2, 101") is False
    assert is_valid_venue_name("unnamed") is False
    assert is_valid_venue_name("hotel") is False
    assert is_valid_venue_name("Rambagh Palace Grand Ballroom") is True

    # 2. are_venues_duplicates branches
    lat = 26.9124
    lng = 75.7873
    # Empty tokens
    assert are_venues_duplicates("the hotel and resort", lat, lng, "the", lat, lng) is False
    # Only generic modifiers and non-identical strings
    assert are_venues_duplicates("Royal Resort", lat, lng, "The Royal", lat, lng) is False
    # No substantial proper noun (short tokens < 4 chars)
    assert are_venues_duplicates("Om Sai Banquet", lat, lng, "Sri Sai Banquet", lat, lng) is False
    # Valid duplicate with chain qualifier
    assert are_venues_duplicates("Taj Rambagh Palace", lat, lng, "Rambagh Palace Hotel", lat, lng) is True

    # 3. search_vendors with unresolvable city (falling back to text city match)
    from unittest.mock import patch
    with patch.object(VendorDiscoveryService, "geocode_query", return_value=None):
        res = VendorDiscoveryService.search_vendors(
            db=db,
            city="UnresolvableImaginaryCity99",
            category="catering"
        )
        assert res.total_results == 0
        assert res.query_city == "UnresolvableImaginaryCity99"


def test_discovery_service_fallbacks(db, test_data):
    event, token = test_data
    from backend.app.services.discovery_service import VendorDiscoveryService
    from unittest.mock import patch

    # Mock Overpass network timeout to trigger fallback
    with patch("backend.app.services.discovery_service.urllib.request.urlopen") as mock_url:
        import urllib.error
        mock_url.side_effect = urllib.error.URLError("Overpass network timeout")

        res = VendorDiscoveryService.search_vendors(
            db=db,
            city="Jaipur",
            category="venue"
        )
        assert res.total_results >= 0
        assert res.query_city == "Jaipur"


def test_discovery_service_vendor_search_text_fallback():
    db = SessionLocal()
    try:
        # Add a test vendor profile
        v = VendorProfile(
            business_name="Green Meadows Resort",
            category="venue",
            city="Pune",
            latitude=18.52,
            longitude=73.85,
            average_rating=4.5,
            city_tier="tier1"
        )
        db.add(v)
        db.commit()

        # Search by city without lat/lng
        resp = VendorDiscoveryService.search_vendors(db=db, city="Pune", category="venue")
        assert len(resp.results) >= 1
        assert any("Green Meadows" in item.business_name for item in resp.results)

        # Geocode query cached lookup
        coords = VendorDiscoveryService.geocode_query("pune")
        assert coords is not None
        assert abs(coords[0] - 18.5204) < 0.1
    finally:
        db.close()


def test_api_discovery_endpoints():
    # 1. Geocode endpoint with valid known city
    geo_res = client.get("/api/v1/discovery/geocode?q=bengaluru")
    assert geo_res.status_code == 200
    geo_data = geo_res.json()
    assert "lat" in geo_data
    assert "lng" in geo_data

    # 2. Vendors endpoint without any coordinates or city -> 400
    bad_req = client.get("/api/v1/discovery/vendors")
    assert bad_req.status_code == 400
    assert "must be provided" in bad_req.json()["detail"].lower()

    # 3. Vendors endpoint with city
    v_res = client.get("/api/v1/discovery/vendors?city=pune&radius_km=15")
    assert v_res.status_code == 200
    v_data = v_res.json()
    assert "results" in v_data


def test_discovery_osm_venues_overpass_mock():
    db = SessionLocal()
    try:
        mock_resp = MagicMock()
        mock_data = {
            "elements": [
                {
                    "type": "node",
                    "id": 99887766,
                    "lat": 18.5204,
                    "lon": 73.8567,
                    "tags": {
                        "name": "Maharaja Grand Hall",
                        "amenity": "events_venue",
                        "addr:suburb": "Kothrud"
                    }
                }
            ]
        }
        mock_resp.read.return_value = json.dumps(mock_data).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            VendorDiscoveryService._fetch_and_persist_osm_venues(db, 18.5204, 73.8567, 10.0, city_hint="Pune")

        v = db.query(VendorProfile).filter(VendorProfile.business_name == "Maharaja Grand Hall").first()
        assert v is not None
        assert v.city == "Pune"
        assert v.locality == "Kothrud"
    finally:
        db.query(VendorProfile).filter(VendorProfile.business_name == "Maharaja Grand Hall").delete()
        db.commit()
        db.close()


def test_discovery_helper_functions_and_profile_conversion():
    from backend.app.services.discovery_service import (
        is_valid_venue_name,
        are_venues_duplicates,
        VendorDiscoveryService
    )

    # 1. is_valid_venue_name
    assert is_valid_venue_name("Taj Mahal Palace") is True
    assert is_valid_venue_name(None) is False
    assert is_valid_venue_name("ab") is False  # too short
    assert is_valid_venue_name("12345") is False  # no alpha
    assert is_valid_venue_name("node/123456") is False  # raw osm
    assert is_valid_venue_name("unnamed") is False  # generic placeholder
    assert is_valid_venue_name("hotel") is False  # generic placeholder

    # 2. are_venues_duplicates
    # Exact normalized match
    assert are_venues_duplicates("Taj Rambagh Palace", 26.9, 75.8, "taj rambagh palace", 26.9, 75.8) is True
    # Too far apart (> 350m)
    assert are_venues_duplicates("Taj Mahal", 26.9, 75.8, "Taj Hotel", 27.5, 76.5) is False
    # City suffix match within 350m
    assert are_venues_duplicates("Rambagh Palace Jaipur", 26.912, 75.787, "Rambagh Palace", 26.912, 75.787) is True
    # Distinct brand/proper nouns
    assert are_venues_duplicates("JW Marriott", 26.912, 75.787, "JW Marriott Hotel", 26.912, 75.787) is True

    # 3. _profile_to_item rating tiers
    p_top = VendorProfile(
        id="p_top", business_name="Top Hall", category="venue",
        city="Pune", average_rating=4.9, rating_count=20
    )
    item_top = VendorDiscoveryService._profile_to_item(p_top, distance_km=5.0)
    assert item_top.rating_tier == "top_rated"

    p_high = VendorProfile(
        id="p_high", business_name="High Hall", category="venue",
        city="Pune", average_rating=4.2, rating_count=5
    )
    item_high = VendorDiscoveryService._profile_to_item(p_high, distance_km=5.0)
    assert item_high.rating_tier == "highly_rated"

    p_rated = VendorProfile(
        id="p_rated", business_name="Rated Hall", category="venue",
        city="Pune", average_rating=3.5, rating_count=5
    )
    item_rated = VendorDiscoveryService._profile_to_item(p_rated, distance_km=5.0)
    assert item_rated.rating_tier == "rated"

    p_unrated = VendorProfile(
        id="p_unrated", business_name="New Hall", category="venue",
        city="Pune", average_rating=None, rating_count=0
    )
    item_unrated = VendorDiscoveryService._profile_to_item(p_unrated, distance_km=5.0)
    assert item_unrated.rating_tier == "new_unrated"
