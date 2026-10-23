"""
Unit tests for Milestone M5 - F2 Cultural & Ritual Intelligence.
Tests astronomical panchang provider (DEC-027), 8 curated traditions validation,
spec acceptance scenario: Maharashtrian x Punjabi fusion merge,
ritual task generation via DAG scheduler, and candidate muhurat windows.
"""

from datetime import date
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.panchang_service import default_panchang_provider
from backend.app.db.session import SessionLocal
from backend.app.models.models import Tradition, RitualItem, Event, User, Task


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


def test_all_8_curated_traditions_per_spec(client):
    """Verifies that all 8 traditions from original spec exist and are truthfully marked is_verified: False."""
    resp = client.get("/api/v1/rituals/traditions")
    assert resp.status_code == 200
    data = resp.json()

    codes = {t["code"] for t in data}
    expected_8 = {
        "maharashtrian_vedic",
        "punjabi_traditional",
        "bengali_vedic",
        "tamil_brahmin_hindu",
        "gujarati_hindu",
        "muslim_nikah",
        "christian_traditional",
        "telugu_hindu"
    }
    assert expected_8.issubset(codes), f"Missing traditions: {expected_8 - codes}"

    tradition_map = {t["code"]: t for t in data}
    for code in expected_8:
        t = tradition_map[code]
        # Truthfulness check: all AI-drafted traditions must be unverified
        assert t["is_verified"] is False, f"Tradition {code} must be is_verified: False pending human review"
        assert t["verification_source"] == "AI-drafted baseline, pending community/priest review"
        assert t["item_count"] >= 7


def test_tradition_samagri_checklist_endpoint(client):
    """Verifies itemized samagri checklist retrieval with vernacular names and quantities."""
    resp = client.get("/api/v1/rituals/traditions/maharashtrian_vedic/samagri")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tradition"]["code"] == "maharashtrian_vedic"
    assert data["tradition"]["is_verified"] is False
    assert data["tradition"]["verification_source"] == "AI-drafted baseline, pending community/priest review"
    assert "content_accuracy_disclaimer" in data
    assert data["total_items"] >= 10

    item_names = [i["item_name"] for i in data["items"]]
    assert any("Antarpat" in n for n in item_names)
    assert any("Mundavalya" in n for n in item_names)
    assert any("Akshata" in n for n in item_names)
    assert any(i["regional_name"] and "मुंडावळ्या" in i["regional_name"] for i in data["items"])


def test_spec_acceptance_scenario_maharashtrian_x_punjabi(client):
    """
    Core Spec Acceptance Test:
    A Maharashtrian x Punjabi wedding produces a merged sequence
    with each ceremony correctly labeled by origin tradition.
    """
    resp = client.post(
        "/api/v1/rituals/merge-traditions",
        json={
            "primary_tradition_code": "maharashtrian_vedic",
            "secondary_tradition_code": "punjabi_traditional",
            "start_date": "2026-11-20",
            "notes": "Bride is Maharashtrian, groom is Punjabi"
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "Maharashtrian" in data["fusion_title"]
    assert "Punjabi" in data["fusion_title"]

    # Verification integrity check
    assert data["primary_tradition"]["is_verified"] is False
    assert data["secondary_tradition"]["is_verified"] is False
    assert data["primary_tradition"]["verification_source"] == "AI-drafted baseline, pending community/priest review"
    assert data["secondary_tradition"]["verification_source"] == "AI-drafted baseline, pending community/priest review"
    assert "content_accuracy_disclaimer" in data
    assert "AI-drafted as a starting point" in data["content_accuracy_disclaimer"]
    assert "NOT been reviewed by any priest" in data["content_accuracy_disclaimer"]

    # 1. Run-of-show verification
    ceremonies = data["run_of_show"]
    assert len(ceremonies) >= 5

    # Check origin labels on every ceremony
    origins = [c["origin_tradition"] for c in ceremonies]
    assert any("Maharashtrian" in o for o in origins), "Must have ceremonies with Maharashtrian origin"
    assert any("Punjabi" in o for o in origins), "Must have ceremonies with Punjabi origin"
    assert any("Shared" in o or "Combined" in o for o in origins), "Must have shared ceremonies"

    for c in ceremonies:
        assert c["origin_tradition"] in [
            "Maharashtrian Vedic Lagna",
            "Punjabi Traditional Vivah / Anand Karaj",
            "Shared / Combined"
        ]
        assert "start_time" in c
        assert "duration_hours" in c
        assert "cultural_significance" in c

    # Specific ceremony checks
    ceremony_names = [c["name"] for c in ceremonies]
    assert any("Jaggo" in name for name in ceremony_names)
    assert any("Simant Pujan" in name or "Antarpat" in name for name in ceremony_names)
    assert any("Saptapadi" in name or "Laavan" in name for name in ceremony_names)

    # 2. Family alignment points
    alignments = data["family_alignment_points"]
    assert len(alignments) >= 3
    issue_titles = [a["issue"] for a in alignments]
    assert any("Entrance" in title for title in issue_titles)
    assert any("Dining" in title for title in issue_titles)
    assert any("Wardrobe" in title or "Adornment" in title for title in issue_titles)


def test_generate_ritual_tasks_in_dag(client):
    """Verifies generating ritual tasks attached as tasks rows via the DAG scheduler pattern."""
    db = SessionLocal()
    try:
        user = db.query(User).first()
        if not user:
            user = User(
                id="test-dag-user-1",
                phone_number="+919876543211",
                email="dag@utsav.ai",
                full_name="DAG Test Host"
            )
            db.add(user)
            db.commit()

        event = Event(
            id="test-ritual-task-event-1",
            owner_id=user.id,
            name="Rohit & Priya Fusion Vivah",
            event_type="wedding",
            tradition_code="maharashtrian_vedic",
            secondary_tradition_code="punjabi_traditional",
            guest_count=300,
            total_budget=2000000,
            city="Pune",
            pincode="411001",
            start_date=date(2026, 12, 10),
            end_date=date(2026, 12, 12),
            status="planning"
        )
        db.add(event)
        db.commit()

        resp = client.post(f"/api/v1/rituals/events/{event.id}/generate-tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["tasks_created_count"] >= 5

        # Check DB directly
        db_tasks = db.query(Task).filter(Task.event_id == event.id).all()
        assert len(db_tasks) >= 5
        task_titles = [t.title for t in db_tasks]
        assert any("Procure Ritual Samagri" in t for t in task_titles)
        assert any(t.assigned_role == "Family Elder / Ritual Lead" for t in db_tasks)
    finally:
        db.query(Task).filter(Task.event_id == "test-ritual-task-event-1").delete()
        db.query(Event).filter(Event.id == "test-ritual-task-event-1").delete()
        db.commit()
        db.close()


def test_muhurat_candidates_endpoint(client):
    """Verifies calculation of morning, midday, and twilight candidate muhurats with elevated disclaimer."""
    resp = client.get("/api/v1/rituals/muhurat-candidates?event_date=2024-10-24&latitude=28.6139&longitude=77.2090")
    assert resp.status_code == 200
    data = resp.json()

    assert data["event_date"] == "2024-10-24"
    assert "candidates" in data
    assert len(data["candidates"]) == 3

    candidate_ids = [c["id"] for c in data["candidates"]]
    assert "muhurat-morning" in candidate_ids
    assert "muhurat-abhijit" in candidate_ids
    assert "muhurat-godhuli" in candidate_ids

    # Elevated disclaimer must be prominent
    assert "ALWAYS confirm your final wedding pheras" in data["elevated_disclaimer"]
    assert "prohibited_window" in data["rahu_kaal_prohibited_window"] or "-" in data["rahu_kaal_prohibited_window"]
