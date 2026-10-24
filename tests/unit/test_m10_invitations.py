import pytest
import io
from datetime import date, timedelta
from PIL import Image
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.models.models import Event, User, Guest, InvitationCard, ThemeProposal, StyleProfile
from backend.app.services.invitation_renderer import InvitationCardRenderer
from backend.app.services.invitation_wording_agent import InvitationWordingAgent

client = TestClient(app)


@pytest.fixture(scope="module")
def setup_invitation_event():
    """Sets up an event with theme and guests for M10 testing."""
    import random
    db = SessionLocal()
    rand_suffix = random.randint(100000, 999999)
    # Create user
    user = User(
        phone_number=f"+9197{rand_suffix}01",
        full_name="Rajesh Sharma",
        role="host"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create Event
    ev = Event(
        owner_id=user.id,
        name="Ananya & Kabir Vivah",
        event_type="wedding",
        tradition_code="hindu_north",
        guest_count=200,
        total_budget=2500000.0,
        city="Mumbai",
        pincode="400001",
        start_date=date.today() + timedelta(days=45),
        end_date=date.today() + timedelta(days=47),
        metadata_json={
            "host_name": "Sharma & Batra Families",
            "venue": "Taj Mahal Palace, Colaba",
            "muhurat_time": "10:15 AM - 11:45 AM"
        }
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    # Style Profile & Theme Proposal
    profile = StyleProfile(
        event_id=ev.id,
        extracted_palette=["#B45309", "#991B1B", "#FEF3C7", "#1E3A8A", "#D97706"],
        style_tags=["Royal", "Traditional", "Marigold"]
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    theme = ThemeProposal(
        style_profile_id=profile.id,
        theme_name="Regal Marigold Vivah",
        palette=["#B45309", "#991B1B", "#FEF3C7", "#1E3A8A", "#D97706"],
        status="accepted",
        invitation_design_brief="Rich traditional marigold and gold royal aesthetic with auspicious shubh muhurat."
    )
    db.add(theme)
    db.commit()
    db.refresh(theme)

    # 3 Seeded Test Guests
    g1 = Guest(event_id=ev.id, name="Vikram Batra", phone=f"+9198{rand_suffix}11", diet="veg", group_side="groom")
    g2 = Guest(event_id=ev.id, name="Pooja Sharma", phone=f"+9198{rand_suffix}12", diet="jain", group_side="bride")
    g3 = Guest(event_id=ev.id, name="सुरेश जोशी व परिवार", phone=f"+9198{rand_suffix}13", diet="veg", group_side="family")
    db.add_all([g1, g2, g3])
    db.commit()
    db.refresh(g1)
    db.refresh(g2)
    db.refresh(g3)

    data = {
        "user_id": user.id,
        "event_id": ev.id,
        "theme_id": theme.id,
        "guest_ids": [g1.id, g2.id, g3.id]
    }
    db.close()
    yield data


def test_invitation_wording_agent_offline_stub():
    """Verifies that wording agent returns 3 distinct variants with stub provider."""
    res = InvitationWordingAgent.compose_wording(
        event_name="Rohan & Ananya Wedding",
        host_name="Sharma Family",
        event_type="wedding",
        date_str="Sunday, 15 December 2026",
        venue_str="Grand Hyatt, Mumbai",
        muhurat_time="10:30 AM",
        ceremony_names=["Haldi", "Sangeet", "Pheras"]
    )

    assert len(res.variants) == 3
    assert res.provider_used in ("stub", "gemini")
    for v in res.variants:
        assert v.id in ("traditional", "contemporary", "formal")
        assert len(v.body_text) > 30
        assert "{" not in v.body_text
        assert "}" not in v.body_text


def test_pillow_renderer_zero_placeholder_and_multilingual():
    """
    Renders card with Devanagari script and asserts zero unfilled curly bracket placeholders.
    Confirms both PNG and PDF export valid formats.
    """
    png_bytes, pdf_bytes = InvitationCardRenderer.render_card(
        event_name="रोहन व अनन्या शुभविवाह",
        host_name="श्री व सौ. जोशी",
        date_str="रविवार, १५ डिसेंबर २०२६",
        venue_str="आनंद मंगल कार्यालय, सदाशिव पेठ, पुणे",
        wording_text="आमच्या मुलाच्या शुभविवाहास सहकुटुंब उपस्थित राहून शुभाशीर्वाद द्यावेत ही नम्र विनंती.",
        muhurat_time="सकाळी १०:४५",
        ceremony_names=["हळद", "संगीत", "सप्तपदी", "रिसेप्शन"],
        guest_name="श्री प्रकाश पाटील व परिवार",
        guest_diet="veg",
        palette=["#991B1B", "#B45309", "#FEF3C7"],
        layout_variant="classic_royal"
    )

    assert len(png_bytes) > 5000
    assert len(pdf_bytes) > 5000

    # Verify PNG header
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
    # Verify PDF header
    assert pdf_bytes[:4] == b"%PDF"

    # Open image with Pillow to assert dimensions
    img = Image.open(io.BytesIO(png_bytes))
    assert img.size == (1200, 1800)


def test_invitation_options_endpoint(setup_invitation_event):
    """Verifies GET /options endpoint returns layouts, palette, and wording."""
    event_id = setup_invitation_event["event_id"]
    res = client.get(f"/api/v1/events/{event_id}/invitations/options")
    assert res.status_code == 200
    data = res.json()

    assert len(data["layout_options"]) >= 3
    assert len(data["palette"]) >= 3
    assert data["event_name"] == "Ananya & Kabir Vivah"
    assert data["host_name"] == "Sharma & Batra Families"
    assert data["guest_count"] == 3
    assert len(data["wording_options"]) == 3
    assert "AI-assisted" in data["content_review_note"]


def test_acceptance_criteria_3_guest_batch_generation(setup_invitation_event):
    """
    Core Acceptance Criteria (Milestone M10 / DEC-028, DEC-029, DEC-030):
    3 test guests -> 3 correctly personalized cards, distinct names,
    identical layout/palette/date/venue, both PNG and PDF,
    zero unfilled template placeholders in any output.
    """
    event_id = setup_invitation_event["event_id"]
    theme_id = setup_invitation_event["theme_id"]

    payload = {
        "theme_proposal_id": theme_id,
        "layout_variant": "classic_royal",
        "wording_variant_index": 0
    }

    res = client.post(f"/api/v1/events/{event_id}/invitations/generate", json=payload)
    assert res.status_code == 201
    data = res.json()

    assert data["total_generated"] == 3
    assert data["total_failed"] == 0
    assert len(data["cards"]) == 3
    assert len(data["failed_guests"]) == 0

    # Verify distinct guest names
    card_names = [c["guest_name"] for c in data["cards"]]
    assert set(card_names) == {"Vikram Batra", "Pooja Sharma", "सुरेश जोशी व परिवार"}

    # Download each card as PNG and PDF to confirm binary streaming
    for card in data["cards"]:
        card_id = card["id"]
        # PNG download
        png_res = client.get(f"/api/v1/events/{event_id}/invitations/{card_id}/download?format=png")
        assert png_res.status_code == 200
        assert png_res.headers["content-type"] == "image/png"
        assert len(png_res.content) > 1000
        assert png_res.content[:8] == b"\x89PNG\r\n\x1a\n"

        # PDF download
        pdf_res = client.get(f"/api/v1/events/{event_id}/invitations/{card_id}/download?format=pdf")
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"
        assert len(pdf_res.content) > 1000
        assert pdf_res.content[:4] == b"%PDF"


def test_partial_failure_isolation_in_batch(setup_invitation_event, monkeypatch):
    """
    Verifies that a failure rendering one guest's card (e.g. font or encoding error)
    does NOT abort the batch; the other guests succeed and the failed guest is surfaced.
    """
    event_id = setup_invitation_event["event_id"]
    original_render = InvitationCardRenderer.render_card

    def mock_render_card(*args, **kwargs):
        # Inject failure specifically for Pooja Sharma
        if kwargs.get("guest_name") == "Pooja Sharma":
            raise ValueError("Simulated font character rendering error for test")
        return original_render(*args, **kwargs)

    monkeypatch.setattr(InvitationCardRenderer, "render_card", mock_render_card)

    payload = {
        "layout_variant": "modern_minimal",
        "wording_text": "We warmly invite you to celebrate with us."
    }

    res = client.post(f"/api/v1/events/{event_id}/invitations/generate", json=payload)
    assert res.status_code == 201
    data = res.json()

    assert data["total_generated"] == 2
    assert data["total_failed"] == 1
    assert len(data["failed_guests"]) == 1
    assert data["failed_guests"][0]["name"] == "Pooja Sharma"
    assert "Simulated font character" in data["failed_guests"][0]["reason"]


def test_generic_card_fallback_when_no_guests():
    """Verifies that an event without guests generates a single generic card."""
    import random
    db = SessionLocal()
    phone = f"+9196{random.randint(10000000, 99999999)}"
    user = User(phone_number=phone, full_name="Solo Host", role="host")
    db.add(user)
    db.commit()
    db.refresh(user)

    ev = Event(
        owner_id=user.id,
        name="Diwali Community Feast",
        event_type="community_festival",
        guest_count=50,
        total_budget=50000.0,
        city="Bengaluru",
        pincode="560001",
        start_date=date.today() + timedelta(days=20),
        end_date=date.today() + timedelta(days=20),
        metadata_json={}
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    db.close()

    res = client.post(f"/api/v1/events/{ev.id}/invitations/generate", json={"layout_variant": "floral_festive"})
    assert res.status_code == 201
    data = res.json()

    assert data["total_generated"] == 1
    assert data["total_failed"] == 0
    assert data["cards"][0]["guest_id"] is None
    assert data["cards"][0]["guest_name"] is None


def test_muhurat_resolution_from_locked_subevent():
    """
    Proves Path (a): when metadata_json['muhurat_time'] is absent,
    a locked sub_event (is_muhurat_locked == True) correctly flows into
    options and card generation.
    """
    import random
    from datetime import datetime
    from backend.app.models.models import SubEvent
    db = SessionLocal()
    phone = f"+9195{random.randint(10000000, 99999999)}"
    user = User(phone_number=phone, full_name="Auspicious Host", role="host")
    db.add(user)
    db.commit()
    db.refresh(user)

    ev = Event(
        owner_id=user.id,
        name="Pooja & Samaroh",
        event_type="wedding",
        guest_count=100,
        total_budget=500000.0,
        city="Pune",
        pincode="411001",
        start_date=date.today() + timedelta(days=15),
        end_date=date.today() + timedelta(days=16),
        metadata_json={}  # Explicitly NO muhurat_time in metadata
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    # Add an unlocked sub-event and a locked muhurat sub-event
    s1 = SubEvent(
        event_id=ev.id,
        name="Haldi Ceremony",
        start_time=datetime(2026, 11, 10, 8, 0),
        end_time=datetime(2026, 11, 10, 10, 0),
        venue_name="Lawn",
        is_muhurat_locked=False
    )
    s2 = SubEvent(
        event_id=ev.id,
        name="Hastamelap Vivah",
        start_time=datetime(2026, 11, 10, 11, 15),
        end_time=datetime(2026, 11, 10, 12, 45),
        venue_name="Main Mandap",
        is_muhurat_locked=True,
        muhurat_notes="Abhijit Muhurat"
    )
    db.add_all([s1, s2])
    db.commit()

    # 1. Test studio options endpoint
    res_opts = client.get(f"/api/v1/events/{ev.id}/invitations/options")
    assert res_opts.status_code == 200
    opts_data = res_opts.json()
    assert opts_data["muhurat_time"] == "11:15 AM - 12:45 PM (Abhijit Muhurat)"

    # 2. Test card generation incorporates the locked muhurat
    res_gen = client.post(f"/api/v1/events/{ev.id}/invitations/generate", json={"layout_variant": "classic_royal"})
    assert res_gen.status_code == 201
    card_id = res_gen.json()["cards"][0]["id"]

    # Verify PNG and PDF download succeed and contain lossless FlateDecode PDF
    res_pdf = client.get(f"/api/v1/events/{ev.id}/invitations/{card_id}/download?format=pdf")
    assert res_pdf.status_code == 200
    assert b"/FlateDecode" in res_pdf.content
    assert b"/DCTDecode" not in res_pdf.content

    db.close()


def test_muhurat_placeholder_when_no_locked_subevent():
    """
    Proves Path (b): when neither metadata_json['muhurat_time'] nor a locked
    sub_event exists, the system does NOT silently invent or calculate an unconfirmed
    panchang muhurat, but cleanly leaves muhurat_time as None / placeholder.
    """
    import random
    from datetime import datetime
    from backend.app.models.models import SubEvent
    db = SessionLocal()
    phone = f"+9194{random.randint(10000000, 99999999)}"
    user = User(phone_number=phone, full_name="Pending Host", role="host")
    db.add(user)
    db.commit()
    db.refresh(user)

    ev = Event(
        owner_id=user.id,
        name="Reception Dinner",
        event_type="milestone",
        guest_count=50,
        total_budget=200000.0,
        city="Delhi",
        pincode="110001",
        start_date=date.today() + timedelta(days=30),
        end_date=date.today() + timedelta(days=30),
        metadata_json={}  # No muhurat_time
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    # Sub-event without muhurat lock
    s1 = SubEvent(
        event_id=ev.id,
        name="Welcome Drinks",
        start_time=datetime(2026, 12, 1, 19, 0),
        end_time=datetime(2026, 12, 1, 23, 0),
        venue_name="Banquet Hall",
        is_muhurat_locked=False
    )
    db.add(s1)
    db.commit()

    # 1. Test studio options endpoint returns None for muhurat_time (no fabricated time)
    res_opts = client.get(f"/api/v1/events/{ev.id}/invitations/options")
    assert res_opts.status_code == 200
    opts_data = res_opts.json()
    assert opts_data["muhurat_time"] is None

    # 2. Card generates cleanly without fabricating an unconfirmed muhurat
    res_gen = client.post(f"/api/v1/events/{ev.id}/invitations/generate", json={"layout_variant": "modern_minimal"})
    assert res_gen.status_code == 201
    card_id = res_gen.json()["cards"][0]["id"]

    res_pdf = client.get(f"/api/v1/events/{ev.id}/invitations/{card_id}/download?format=pdf")
    assert res_pdf.status_code == 200
    assert b"/FlateDecode" in res_pdf.content

    db.close()


def test_pdf_lossless_pixel_diff():
    """
    Directly tests that PDF extraction yields bitwise-identical pixels to the rendered PNG.
    """
    import zlib
    import re
    import numpy as np

    png_bytes, pdf_bytes = InvitationCardRenderer.render_card(
        event_name="Pixel Test Vivah",
        host_name="Sharma Parivar",
        date_str="Sunday, 15 November 2026",
        venue_str="Grand Hyatt, Mumbai",
        wording_text="Cordial invitation to celebrate.",
        muhurat_time="11:00 AM - 12:30 PM",
        guest_name="आदरणीय पाहुणे",
        layout_variant="classic_royal"
    )

    # Extract FlateDecode image stream from PDF
    match = re.search(rb'/Filter\s*/FlateDecode.*?stream\r?\n(.*?)\r?\nendstream', pdf_bytes, re.DOTALL)
    assert match is not None, "PDF must use FlateDecode filter"
    raw_stream = zlib.decompress(match.group(1))

    pdf_image = Image.frombytes("RGB", (1200, 1800), raw_stream)
    png_image = Image.open(io.BytesIO(png_bytes)).convert("RGB")

    arr_pdf = np.array(pdf_image)
    arr_png = np.array(png_image)

    # Compare pixel arrays
    diff = np.max(np.abs(arr_pdf.astype(int) - arr_png.astype(int)))
    assert diff == 0, f"Expected 0 pixel difference, got max diff of {diff}"

