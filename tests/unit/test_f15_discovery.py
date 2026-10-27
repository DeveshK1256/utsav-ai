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
