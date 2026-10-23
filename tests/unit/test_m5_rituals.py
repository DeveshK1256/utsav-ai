"""
Unit tests for Milestone M5 - F2 Cultural & Ritual Intelligence.
Tests astronomical panchang provider (DEC-027), curated tradition validation,
multi-tradition fusion merge agent, and priest-guide generation.
"""

from datetime import date
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.panchang_service import default_panchang_provider, EphemPanchangProvider
from backend.app.services.tradition_merge_service import TraditionMergeService
from backend.app.db.session import SessionLocal
from backend.app.models.models import Tradition, RitualItem, Event, User


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_ephem_panchang_provider_deterministic_delhi():
    """Validates deterministic ephemeris calculations for New Delhi on 2024-10-24."""
    test_date = date(2024, 10, 24)
    res = default_panchang_provider.calculate_panchang(
        event_date=test_date,
        latitude=28.6139,
        longitude=77.2090,
        elevation_meters=216.0
    )

    assert res["date"] == "2024-10-24"
    assert res["sunrise"].startswith("06:27")
    assert res["sunset"].startswith("17:42")
    assert res["daylight_duration_seconds"] > 40000

    # Rahu Kaal: Thursday is 6th octile
    rahu = res["rahu_kaal"]
    assert rahu["octile_index"] == 6
    assert rahu["is_inauspicious"] is True
    assert rahu["start"].startswith("13:29")
    assert rahu["end"].startswith("14:53")

    # Tithi: Krishna Ashtami
    assert res["tithi"]["name"] == "Krishna Ashtami"
    assert res["tithi"]["paksha"] == "Krishna"

    # Nakshatra
    assert "name" in res["nakshatra"]

    # Ayanamsha: Chitrapaksha (Lahiri) ~24.20°
    assert res["ayanamsha"]["system"] == "Chitrapaksha (Lahiri)"
    assert 24.15 <= res["ayanamsha"]["degrees"] <= 24.25

    # Priest Disclaimer must be present
    assert "ALWAYS confirm your final wedding pheras" in res["priest_disclaimer"]


def test_ephem_panchang_provider_wednesday_abhijit_caution():
    """Verifies that Wednesday calculates Abhijit with traditional caution note."""
    # 2024-04-17 was a Wednesday (Ram Navami)
    test_date = date(2024, 4, 17)
    res = default_panchang_provider.calculate_panchang(
        event_date=test_date,
        latitude=28.6139,
        longitude=77.2090,
        elevation_meters=216.0
    )

    assert res["sunrise"].startswith("05:53")
    assert res["sunset"].startswith("18:48")
    assert res["tithi"]["name"] == "Shukla Navami"
    assert res["abhijit_muhurat"]["is_auspicious"] is False
    assert "caution" in res["abhijit_muhurat"]
    assert res["abhijit_muhurat"]["caution"] is not None


def test_panchang_api_bounds_validation(client):
    """Checks that invalid latitude/longitude triggers HTTP 400."""
    resp = client.get("/api/v1/rituals/panchang?event_date=2024-10-24&latitude=999.0&longitude=77.0")
    assert resp.status_code == 400
    assert "Latitude must be in [-90, 90]" in resp.json()["detail"]


def test_curated_traditions_verification_flags(client):
    """Verifies that curated traditions are explicitly marked verified or unverified with sources."""
    resp = client.get("/api/v1/rituals/traditions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 8

    tradition_map = {t["code"]: t for t in data}
    assert "maharashtrian_vedic" in tradition_map
    assert "south_indian_iyer" in tradition_map
    assert "punjabi_sikh" in tradition_map
    assert "contemporary_secular" in tradition_map

    # Liturgical traditions must be verified with cited sources
    assert tradition_map["maharashtrian_vedic"]["is_verified"] is True
    assert tradition_map["maharashtrian_vedic"]["verification_source"] is not None
    assert tradition_map["south_indian_iyer"]["is_verified"] is True
    assert tradition_map["punjabi_sikh"]["is_verified"] is True

    # Contemporary template must be marked unverified
    assert tradition_map["contemporary_secular"]["is_verified"] is False
    assert "Not verified" in tradition_map["contemporary_secular"]["verification_source"]


def test_tradition_samagri_checklist_endpoint(client):
    """Verifies itemized samagri checklist retrieval with vernacular names and quantities."""
    resp = client.get("/api/v1/rituals/traditions/maharashtrian_vedic/samagri")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tradition"]["code"] == "maharashtrian_vedic"
    assert data["total_items"] >= 10

    item_names = [i["item_name"] for i in data["items"]]
    assert any("Antarpat" in n for n in item_names)
    assert any("Mundavalya" in n for n in item_names)
    assert any("Akshata" in n for n in item_names)

    # Check that regional vernacular script exists
    assert any(i["regional_name"] and "मुंडावळ्या" in i["regional_name"] for i in data["items"])


def test_multi_tradition_merge_iyer_and_punjabi(client):
    """Tests cross-cultural fusion merge between Tamil Brahmin Iyer and Punjabi Sikh."""
    resp = client.post(
        "/api/v1/rituals/merge-traditions",
        json={
            "primary_tradition_code": "south_indian_iyer",
            "secondary_tradition_code": "punjabi_sikh"
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "Tamil Brahmin Iyer" in data["fusion_title"]
    assert "Punjabi Anand Karaj" in data["fusion_title"]

    # Reconciled samagri checklist checks
    items = data["samagri_items"]
    assert len(items) > 10

    # Ensure source_tradition is tagged on every single item
    for item in items:
        assert "source_tradition" in item
        assert item["source_tradition"] in [
            "Shared Vedic / Common",
            "Tamil Brahmin Iyer Kalyanam",
            "Punjabi Anand Karaj"
        ]

    # Shared common items (e.g. ghee / akshata) should be labeled Shared Vedic
    shared_items = [i for i in items if i["source_tradition"] == "Shared Vedic / Common"]
    assert len(shared_items) >= 1

    # Family alignment points must flag timing & dietary divergence
    alignments = data["family_alignment_points"]
    assert len(alignments) >= 2
    issue_titles = [a["issue"] for a in alignments]
    assert any("Timing" in title or "Venue" in title for title in issue_titles)
    assert any("Dietary" in title for title in issue_titles)


def test_event_pandit_guide_endpoint(client):
    """Tests generating a complete pandit guide for a real event."""
    db = SessionLocal()
    try:
        # Create user and test event
        user = db.query(User).first()
        if not user:
            user = User(
                id="test-priest-user-1",
                phone_number="+919876543299",
                email="priest@utsav.ai",
                full_name="Priest Host"
            )
            db.add(user)
            db.commit()

        event = Event(
            id="test-pandit-event-1",
            owner_id=user.id,
            name="Aarav & Ananya Vivah",
            event_type="wedding",
            tradition_code="maharashtrian_vedic",
            guest_count=250,
            total_budget=1500000,
            city="Mumbai",
            pincode="400001",
            start_date=date(2026, 11, 20),
            end_date=date(2026, 11, 22),
            status="planning"
        )
        db.add(event)
        db.commit()

        resp = client.get(f"/api/v1/rituals/events/{event.id}/pandit-guide")
        assert resp.status_code == 200
        data = resp.json()

        assert data["event_name"] == "Aarav & Ananya Vivah"
        assert data["city"] == "Mumbai"
        assert "panchang_and_muhurat" in data
        assert "sunrise" in data["panchang_and_muhurat"]
        assert "samagri_checklist" in data
        assert len(data["samagri_checklist"]) >= 10
        assert "ALWAYS confirm your final wedding pheras" in data["disclaimer"]
    finally:
        db.query(Event).filter(Event.id == "test-pandit-event-1").delete()
        db.commit()
        db.close()
