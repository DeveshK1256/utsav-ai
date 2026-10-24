import pytest
from datetime import date, datetime, timedelta
import random
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.models.models import Event, User, SubEvent, InvitationCard
from backend.app.services.invitation_renderer import InvitationCardRenderer

client = TestClient(app)


def test_compose_celebration_happy_path():
    """
    Test 1: Happy Path
    1. Create an event in Pune with empty venue and unlocked sub-events.
    2. Step A: Host selects a venue ('Mahalaxmi Lawns, Karve Nagar').
    3. Step B: Host selects an auspicious muhurat ('11:00 AM - 12:30 PM (Abhijit Muhurat)').
    4. Step C: Card generation automatically reflects confirmed venue and locked muhurat.
    """
    db = SessionLocal()
    phone = f"+9193{random.randint(10000000, 99999999)}"
    user = User(phone_number=phone, full_name="Orchestration Host", role="host")
    db.add(user)
    db.commit()
    db.refresh(user)

    ev = Event(
        owner_id=user.id,
        name="Aarav & Meera Vivah",
        event_type="wedding",
        guest_count=150,
        total_budget=1200000.0,
        city="Pune",
        pincode="411038",
        start_date=date.today() + timedelta(days=25),
        end_date=date.today() + timedelta(days=26),
        metadata_json={}
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    s1 = SubEvent(
        event_id=ev.id,
        name="Lagna Muhurat Samaroh",
        start_time=datetime.now() + timedelta(days=25, hours=10),
        end_time=datetime.now() + timedelta(days=25, hours=13),
        venue_name="TBD",
        is_muhurat_locked=False
    )
    db.add(s1)
    db.commit()

    # Step A: Select Venue
    res_a = client.post(f"/api/v1/events/{ev.id}/compose", json={
        "step": "venue",
        "venue_name": "Mahalaxmi Lawns",
        "venue_locality": "Karve Nagar"
    })
    assert res_a.status_code == 200
    data_a = res_a.json()
    assert data_a["metadata_json"]["venue"] == "Mahalaxmi Lawns, Karve Nagar"
    assert data_a["metadata_json"]["compose_celebration"]["venue_status"] == "shortlist_pick"

    # Step B: Select Muhurat
    res_b = client.post(f"/api/v1/events/{ev.id}/compose", json={
        "step": "timing",
        "muhurat_time": "11:00 AM - 12:30 PM (Abhijit Muhurat)",
        "sub_event_name": "Lagna Muhurat Samaroh"
    })
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["metadata_json"]["muhurat_time"] == "11:00 AM - 12:30 PM (Abhijit Muhurat)"

    # Step C: Invitation Studio Options & Generation (M10 integration)
    res_opt = client.get(f"/api/v1/events/{ev.id}/invitations/options")
    assert res_opt.status_code == 200
    opt_data = res_opt.json()
    assert "Mahalaxmi Lawns, Karve Nagar" in opt_data["venue_str"]
    assert opt_data["muhurat_time"] == "11:00 AM - 12:30 PM (Abhijit Muhurat)"

    # Generate card and verify data flows onto card
    res_gen = client.post(f"/api/v1/events/{ev.id}/invitations/generate", json={"layout_variant": "classic_royal"})
    assert res_gen.status_code == 201
    card_id = res_gen.json()["cards"][0]["id"]

    res_pdf = client.get(f"/api/v1/events/{ev.id}/invitations/{card_id}/download?format=pdf")
    assert res_pdf.status_code == 200
    assert b"/FlateDecode" in res_pdf.content

    db.close()


def test_compose_celebration_all_skips_path():
    """
    Test 2: All-Skips Path
    1. Create an event with no venue and no muhurat.
    2. Host skips venue ('I'll decide later').
    3. Host skips timing ('I'll decide later').
    4. Card generation proceeds without errors and shows clean placeholders ('Venue to be confirmed', no muhurat time).
    """
    db = SessionLocal()
    phone = f"+9192{random.randint(10000000, 99999999)}"
    user = User(phone_number=phone, full_name="Skip Host", role="host")
    db.add(user)
    db.commit()
    db.refresh(user)

    ev = Event(
        owner_id=user.id,
        name="Minimal Milestone Party",
        event_type="milestone",
        guest_count=50,
        total_budget=150000.0,
        city="Jaipur",
        pincode="302001",
        start_date=date.today() + timedelta(days=20),
        end_date=date.today() + timedelta(days=20),
        metadata_json={}
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    # Skip Step A
    res_a = client.post(f"/api/v1/events/{ev.id}/compose", json={
        "step": "venue",
        "skip_venue": True
    })
    assert res_a.status_code == 200
    assert res_a.json()["metadata_json"]["compose_celebration"]["venue_skipped"] is True

    # Skip Step B
    res_b = client.post(f"/api/v1/events/{ev.id}/compose", json={
        "step": "timing",
        "skip_timing": True
    })
    assert res_b.status_code == 200
    assert res_b.json()["metadata_json"]["compose_celebration"]["timing_skipped"] is True

    # Step C: Options & Card generation
    res_opt = client.get(f"/api/v1/events/{ev.id}/invitations/options")
    assert res_opt.status_code == 200
    opt_data = res_opt.json()
    assert "Venue to be confirmed" in opt_data["venue_str"]
    assert opt_data["muhurat_time"] is None  # Zero fabricated time!

    res_gen = client.post(f"/api/v1/events/{ev.id}/invitations/generate", json={"layout_variant": "modern_minimal"})
    assert res_gen.status_code == 201
    assert res_gen.json()["total_generated"] == 1

    db.close()


def test_compose_celebration_partial_path_venue_selected_timing_skipped():
    """
    Test 3: Partial Path
    1. Host selects venue ('Fairmont Jaipur, Kukas').
    2. Host explicitly skips timing.
    3. Card shows 'Fairmont Jaipur, Kukas' for venue, but 'muhurat_time' remains None / placeholder.
       Proves that confirmed venue does NOT cause timing to be fabricated.
    """
    db = SessionLocal()
    phone = f"+9191{random.randint(10000000, 99999999)}"
    user = User(phone_number=phone, full_name="Partial Host", role="host")
    db.add(user)
    db.commit()
    db.refresh(user)

    ev = Event(
        owner_id=user.id,
        name="Royal Sangeet & Reception",
        event_type="wedding",
        guest_count=100,
        total_budget=800000.0,
        city="Jaipur",
        pincode="302028",
        start_date=date.today() + timedelta(days=35),
        end_date=date.today() + timedelta(days=36),
        metadata_json={}
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    # 1. Select Venue
    client.post(f"/api/v1/events/{ev.id}/compose", json={
        "step": "venue",
        "venue_name": "Fairmont Jaipur",
        "venue_locality": "Kukas"
    })

    # 2. Skip Timing
    client.post(f"/api/v1/events/{ev.id}/compose", json={
        "step": "timing",
        "skip_timing": True
    })

    # 3. Check M10 Options
    res_opt = client.get(f"/api/v1/events/{ev.id}/invitations/options")
    assert res_opt.status_code == 200
    opt_data = res_opt.json()

    assert opt_data["venue_str"] == "Fairmont Jaipur, Kukas"
    assert opt_data["muhurat_time"] is None  # Strict verification: no fabricated time

    # 4. Generate card
    res_gen = client.post(f"/api/v1/events/{ev.id}/invitations/generate", json={"layout_variant": "floral_festive"})
    assert res_gen.status_code == 201
    assert res_gen.json()["total_generated"] == 1

    db.close()
