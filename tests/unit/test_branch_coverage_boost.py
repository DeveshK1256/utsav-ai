import os
import uuid
from datetime import date, timedelta, datetime, timezone
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image, ImageDraw
from fastapi import HTTPException

from backend.app.db.session import SessionLocal
from backend.app.models.models import (
    User,
    Event,
    BudgetItem,
    Task,
    SubEvent,
    ChangeEvent,
    AISuggestion,
    EventLog,
    EventFactSheet,
    Guest,
    MessageLog,
    OptOut,
    StyleProfile,
    ThemeProposal,
    DecorItem,
)
from backend.app.services.vibe_aggregation_engine import (
    normalize_hex,
    VibeAggregationEngine,
)
from backend.app.schemas.vibe import SingleImageVibeSchema
from backend.app.services.budget_rescaling_engine import (
    BudgetRescalingEngine,
    BudgetItemDiff,
)
from backend.app.services.whatsapp.faq_bot import FAQBotService, HARD_FALLBACK_REFUSAL
from backend.app.services.invitation import (
    hex_to_rgb,
    get_font,
    wrap_text,
    truncate_with_ellipsis,
    InvitationCardRenderer,
)
from backend.app.services.dag import DAGScheduler, TaskNode
from backend.app.services.replanning import ReplanningService
from backend.app.schemas.replanning import (
    ChangeRequestSchema,
    PatchChangeProposalSchema,
)
from backend.app.services.discovery import VendorDiscoveryService
from backend.app.services.vibe_service import VibeService
from backend.app.services.whatsapp.webhook_service import WhatsAppWebhookService


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_event(db_session):
    u = User(
        phone_number=f"+9199{uuid.uuid4().hex[:8]}",
        full_name="Coverage Test Host",
        role="host"
    )
    db_session.add(u)
    db_session.flush()

    ev = Event(
        owner_id=u.id,
        name="Coverage Test Celebration",
        event_type="wedding",
        tradition_code="maharashtrian_vedic",
        guest_count=200,
        venue_capacity=250,
        total_budget=1500000.0,
        city="Jaipur",
        pincode="302001",
        start_date=date.today() + timedelta(days=60),
        end_date=date.today() + timedelta(days=62)
    )
    db_session.add(ev)
    db_session.commit()
    db_session.refresh(ev)
    return ev


# ==========================================
# 1. Vibe Aggregation Engine Tests
# ==========================================
def test_normalize_hex_all_branches():
    assert normalize_hex("") is None
    assert normalize_hex("FFAA00") == "#FFAA00"
    assert normalize_hex("#F0A") == "#FF00AA"
    assert normalize_hex("F0A") == "#FF00AA"
    assert normalize_hex("#123456") == "#123456"
    assert normalize_hex("#ZZZZZZ") is None
    assert normalize_hex("1234") is None
    assert normalize_hex("#12345") is None


def test_vibe_aggregation_empty_and_fallbacks():
    res = VibeAggregationEngine.aggregate_vibe_profiles([])
    assert len(res["extracted_palette"]) == 5
    assert "traditional_indian" in res["style_tags"]
    assert res["text_description"] is None

    v1 = SingleImageVibeSchema(
        palette=["#112233"],
        style_tags=["royal", "heritage"],
        materials=["silk", "marigold_garlands"],
        lighting_mood="warm_candlelight",
        flower_types=["rose"],
        confidence_score=0.9
    )
    res2 = VibeAggregationEngine.aggregate_vibe_profiles(
        [v1],
        text_description="Magnificent royal palace wedding celebration with golden lights",
        overall_mood_words=["Opulent", "Regal"]
    )
    assert len(res2["extracted_palette"]) == 5
    assert res2["extracted_palette"][0] == "#112233"
    assert "royal" in res2["style_tags"]
    assert "Opulent" in res2["mood_words"]
    assert res2["text_description"] is not None


# ==========================================
# 2. Budget Rescaling Engine Tests
# ==========================================
def test_budget_rescaling_scaling_rules_and_tiers():
    assert BudgetRescalingEngine.resolve_scaling_rule("venue") == "fixed"
    assert BudgetRescalingEngine.resolve_scaling_rule("decor") == "tiered"
    assert BudgetRescalingEngine.resolve_scaling_rule("pandal_and_stage") == "tiered"
    assert BudgetRescalingEngine.resolve_scaling_rule("catering") == "per_guest"
    assert BudgetRescalingEngine.resolve_scaling_rule("unknown_cat") == "per_guest"

    mult, name = BudgetRescalingEngine.get_tier_info("nonexistent", 150)
    assert mult == 1.0
    assert "150" in name

    mult_low, name_low = BudgetRescalingEngine.get_tier_info("decor", 50)
    assert mult_low > 0
    mult_high, name_high = BudgetRescalingEngine.get_tier_info("decor", 1000)
    assert mult_high > 0


def test_budget_rescaling_guest_count_change_validations():
    with pytest.raises(ValueError, match="old_guest_count must be > 0"):
        BudgetRescalingEngine.rescale_for_guest_count_change(0, 100, [])
    with pytest.raises(ValueError, match="new_guest_count must be > 0"):
        BudgetRescalingEngine.rescale_for_guest_count_change(100, -5, [])

    class DummyItem:
        def __init__(self, id, cat, name, amt, rule=None):
            self.id = id
            self.category = cat
            self.name = name
            self.planned_amount = amt
            self.scaling_rule = rule

    items = [
        DummyItem("b1", "venue", "Palace Hall", 200000.0, "fixed"),
        DummyItem("b2", "catering", "Royal Buffet", 300000.0, "per_guest"),
        DummyItem("b3", "decor", "Mandap Floral", 150000.0, None),
    ]

    res = BudgetRescalingEngine.rescale_for_guest_count_change(
        old_guest_count=200,
        new_guest_count=250,
        budget_items=items,
        venue_capacity=220
    )
    assert res.capacity_warning is not None
    assert "250" in res.capacity_warning
    assert res.total_new > res.total_old


def test_budget_rescaling_budget_cut_validations():
    with pytest.raises(ValueError, match="must be strictly less than"):
        BudgetRescalingEngine.rescale_for_budget_cut(100000.0, 100000.0, [])
    with pytest.raises(ValueError, match="must be positive"):
        BudgetRescalingEngine.rescale_for_budget_cut(100000.0, 0.0, [])

    class DummyBudgetItem:
        def __init__(self, id, cat, name, amt, is_paid=False, actual_amount=0.0):
            self.id = id
            self.category = cat
            self.name = name
            self.planned_amount = amt
            self.is_paid = is_paid
            self.actual_amount = actual_amount
            self.scaling_rule = "fixed"

    items = [
        DummyBudgetItem("b1", "venue", "Advance Deposit", 50000.0, is_paid=True),
        DummyBudgetItem("b2", "catering", "Dinner Buffet", 100000.0, is_paid=False),
        DummyBudgetItem("b3", "decor", "Stage Lighting", 50000.0, is_paid=False, actual_amount=0.0),
    ]

    res = BudgetRescalingEngine.rescale_for_budget_cut(
        from_budget=200000.0,
        to_budget=140000.0,
        budget_items=items
    )
    assert res.total_old == 200000.0
    b1_res = [i for i in res.items if i.budget_item_id == "b1"][0]
    assert b1_res.new_amount == 50000.0
    assert "Locked/Paid" in b1_res.formula


# ==========================================
# 3. WhatsApp FAQ Bot Tests
# ==========================================
def test_faq_bot_all_branches(db_session, test_event):
    resp_empty = FAQBotService.answer_question(test_event, None, "   ")
    assert resp_empty.is_in_scope is True
    assert resp_empty.source_field == "greeting"

    resp_none = FAQBotService.answer_question(test_event, None, "What time is dinner?")
    assert resp_none.is_in_scope is False
    assert resp_none.answer == HARD_FALLBACK_REFUSAL

    fs = EventFactSheet(
        event_id=test_event.id,
        venue_address="123 Palace Road, Jaipur",
        map_link="https://maps.google.com/?q=palace",
        parking_info="Free valet available at Gate 2",
        dress_code="Traditional Rajasthani festive",
        timing_notes="Baraat at 4 PM, Pheras at 7 PM",
        other_facts={"wifi_password": "UtsavGuest2026", "hotel_shuttle": "Every 30 mins"}
    )
    db_session.add(fs)
    db_session.commit()

    r_venue = FAQBotService.answer_question(test_event, fs, "Where is the venue location?")
    assert "123 Palace Road" in r_venue.answer
    assert "https://maps.google.com" in r_venue.answer
    assert r_venue.source_field == "venue_address"

    r_park = FAQBotService.answer_question(test_event, fs, "Is there parking available?")
    assert "Gate 2" in r_park.answer

    r_dress = FAQBotService.answer_question(test_event, fs, "What is the dress code or what to wear?")
    assert "Rajasthani festive" in r_dress.answer

    r_time = FAQBotService.answer_question(test_event, fs, "What are the timings and schedule?")
    assert "Baraat at 4 PM" in r_time.answer

    r_map = FAQBotService.answer_question(test_event, fs, "Can you send the directions link?")
    assert "https://maps.google.com" in r_map.answer

    r_wifi = FAQBotService.answer_question(test_event, fs, "What is the wifi password?")
    assert "UtsavGuest2026" in r_wifi.answer

    r_date = FAQBotService.answer_question(test_event, fs, "Which date is the event?")
    assert test_event.name in r_date.answer
    assert r_date.source_field == "event.start_date"

    r_unknown = FAQBotService.answer_question(test_event, fs, "Can I bring my pet iguana?")
    assert r_unknown.is_in_scope is False
    assert r_unknown.answer == HARD_FALLBACK_REFUSAL


# ==========================================
# 4. Invitation Renderer Tests
# ==========================================
def test_invitation_renderer_helpers_and_cards():
    assert hex_to_rgb(None) == (180, 83, 9)
    assert hex_to_rgb("invalid") == (180, 83, 9)
    assert hex_to_rgb("#FFF") == (255, 255, 255)
    assert hex_to_rgb("#00FF00") == (0, 255, 0)
    assert hex_to_rgb("#ZZZZZZ") == (180, 83, 9)

    font = get_font("nonexistent_path/fake_font.ttf", 20)
    assert font is not None

    dummy_img = Image.new("RGB", (500, 500))
    draw = ImageDraw.Draw(dummy_img)
    assert wrap_text("", font, 200, draw) == []
    wrapped = wrap_text("Short line", font, 400, draw)
    assert len(wrapped) == 1
    long_wrapped = wrap_text("A very long sentence that definitely exceeds the tiny max width provided here", font, 80, draw)
    assert len(long_wrapped) > 1

    assert truncate_with_ellipsis("Hello", font, 500, draw) == "Hello"
    trunc = truncate_with_ellipsis("A very long guest name that should be clipped with ellipsis", font, 100, draw)
    assert trunc.endswith("...")

    png_bytes, pdf_bytes = InvitationCardRenderer.render_card(
        event_name="Sharma Celebration",
        host_name="Sharma Family",
        date_str="Sunday, 15 November 2026",
        venue_str="Grand Ball Room, Rambagh Palace, Jaipur, Rajasthan",
        wording_text="We invite you to celebrate the holy union",
        muhurat_time="11:30 AM to 1:00 PM",
        guest_name="Shri Rajendra Sharma",
        palette=["#800020", "#D4AF37", "#E2725B"]
    )
    assert len(png_bytes) > 100
    assert len(pdf_bytes) > 100


# ==========================================
# 5. DAG Scheduler Tests
# ==========================================
def test_dag_scheduler_cycle_detection_and_templates():
    today = date(2026, 12, 1)
    bday_events = DAGScheduler.get_sub_events_for_tradition("birthday", today, event_type="birthday")
    assert len(bday_events) > 0

    comm_events = DAGScheduler.get_sub_events_for_tradition("community", today, event_type="community_festival")
    assert len(comm_events) > 0

    n1 = TaskNode("t1", "Task 1", 10, 60, "Coord")
    n2 = TaskNode("t2", "Task 2", 9, 60, "Coord", dependencies=["t1"])
    assert DAGScheduler.check_cycles([n1, n2]) is False

    n3 = TaskNode("t3", "Task 3", 8, 60, "Coord", dependencies=["t2"])
    n1.dependencies = ["t3"]
    assert DAGScheduler.check_cycles([n1, n2, n3]) is True

    ritual_tasks = DAGScheduler.generate_ritual_samagri_tasks(
        today,
        tradition_code="maharashtrian_vedic",
        secondary_tradition_code="gujarati_hindu",
        db=None
    )
    assert len(ritual_tasks) > 0
    assert any("Samagri" in t["title"] for t in ritual_tasks)


# ==========================================
# 6. Replanning Service Infeasibility & Mutations
# ==========================================
def test_replanning_infeasibility_checks(db_session, test_event):
    res1 = ReplanningService._check_infeasibility(test_event, "guest_count_changed", {"to_guest_count": 0})
    assert "positive integer" in res1

    res2 = ReplanningService._check_infeasibility(test_event, "guest_count_changed", {"to_guest_count": 15000})
    assert "maximum supported event scale" in res2

    res3 = ReplanningService._check_infeasibility(test_event, "date_moved", {})
    assert "to_date" in res3

    res4 = ReplanningService._check_infeasibility(test_event, "date_moved", {"to_date": "not-a-date"})
    assert "Invalid date format" in res4

    past_d = (date.today() - timedelta(days=10)).isoformat()
    res5 = ReplanningService._check_infeasibility(test_event, "date_moved", {"to_date": past_d})
    assert "Cannot move event date to the past" in res5

    today_iso = test_event.start_date.isoformat()
    res6 = ReplanningService._check_infeasibility(test_event, "date_moved", {"to_date": today_iso, "from_date": today_iso})
    assert "identical" in res6

    res7 = ReplanningService._check_infeasibility(test_event, "budget_cut", {})
    assert "to_budget" in res7

    res8 = ReplanningService._check_infeasibility(test_event, "budget_cut", {"to_budget": "abc"})
    assert "Invalid target budget" in res8

    res9 = ReplanningService._check_infeasibility(test_event, "budget_cut", {"to_budget": -100})
    assert "strictly positive" in res9

    res10 = ReplanningService._check_infeasibility(test_event, "budget_cut", {"to_budget": float(test_event.total_budget) + 1000})
    assert "must be strictly less than" in res10

    res11 = ReplanningService._check_infeasibility(test_event, "vendor_cancelled", {})
    assert "category is required" in res11

    res12 = ReplanningService._check_infeasibility(test_event, "venue_unavailable", {})
    assert "Venue name is required" in res12


def test_replanning_lifecycle_accept_reject_patch(db_session, test_event):
    b1 = BudgetItem(
        event_id=test_event.id,
        category="catering",
        name="Catering Buffet",
        scaling_rule="per_guest",
        planned_amount=300000.0,
        actual_amount=0.0
    )
    b2 = BudgetItem(
        event_id=test_event.id,
        category="venue",
        name="Main Banquet",
        scaling_rule="fixed",
        planned_amount=200000.0,
        actual_amount=0.0
    )
    db_session.add_all([b1, b2])
    db_session.commit()

    req = ChangeRequestSchema(
        change_type="guest_count_changed",
        payload={"from_guest_count": 200, "to_guest_count": 250}
    )
    prop = ReplanningService.create_change_proposal(db_session, test_event.id, req)
    assert prop.change_id is not None
    assert prop.status == "pending"

    patch_req = PatchChangeProposalSchema(
        budget_overrides={b1.id: 350000.0}
    )
    patched = ReplanningService.patch_change(db_session, test_event.id, prop.change_id, patch_req)
    assert patched.budget_total_new > 0

    accepted = ReplanningService.accept_change(db_session, test_event.id, prop.change_id)
    assert accepted.status == "applied"
    db_session.refresh(test_event)
    assert test_event.guest_count == 250

    req_date = ChangeRequestSchema(
        change_type="date_moved",
        payload={
            "from_date": test_event.start_date.isoformat(),
            "to_date": (test_event.start_date + timedelta(days=14)).isoformat()
        }
    )
    prop2 = ReplanningService.create_change_proposal(db_session, test_event.id, req_date)
    rejected = ReplanningService.reject_change(db_session, test_event.id, prop2.change_id)
    assert rejected.status == "rejected"

    with pytest.raises(ValueError, match="not found"):
        ReplanningService.get_change_proposal(db_session, test_event.id, "fake_id")

    with pytest.raises(ValueError, match="Must be 'pending'"):
        ReplanningService.accept_change(db_session, test_event.id, prop2.change_id)

    with pytest.raises(ValueError, match="Must be pending"):
        ReplanningService.patch_change(db_session, test_event.id, prop2.change_id, patch_req)


# ==========================================
# 7. WhatsApp Webhook Branches
# ==========================================
def test_whatsapp_webhook_branches(db_session, test_event):
    g = Guest(
        event_id=test_event.id,
        name="Rohan Verma",
        phone="+919876543210",
        rsvp_status="pending",
        headcount=1
    )
    db_session.add(g)
    db_session.commit()

    unique_wamid = f"wamid_{uuid.uuid4().hex}"
    msg_log = MessageLog(
        guest_id=g.id,
        event_id=test_event.id,
        phone_number=g.phone,
        direction="outbound",
        message_type="invitation",
        content_snapshot="Invitation text",
        whatsapp_message_id=unique_wamid,
        delivery_status="sent"
    )
    db_session.add(msg_log)
    db_session.commit()

    payload_status = {
        "entry": [{
            "changes": [{
                "value": {
                    "statuses": [{
                        "id": unique_wamid,
                        "status": "failed",
                        "errors": [{"title": "Number not registered on WhatsApp"}]
                    }]
                }
            }]
        }]
    }
    res_st = WhatsAppWebhookService.handle_inbound_payload(db_session, payload_status)
    assert res_st["statuses_updated"] == 1
    db_session.refresh(msg_log)
    assert msg_log.delivery_status == "failed"
    assert "Number not registered" in msg_log.failure_reason

    payload_reply = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "919876543210",
                        "id": "wamid_in_1",
                        "type": "interactive",
                        "interactive": {
                            "type": "button_reply",
                            "button_reply": {
                                "id": "rsvp:attending:count=3",
                                "title": "Attending (3)"
                            }
                        }
                    }]
                }
            }]
        }]
    }
    res_in = WhatsAppWebhookService.handle_inbound_payload(db_session, payload_reply)
    assert res_in["rsvps_updated"] == 1
    db_session.refresh(g)
    assert g.rsvp_status == "attending"
    assert g.headcount == 1

    payload_stop = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "919876543210",
                        "id": "wamid_in_2",
                        "type": "text",
                        "text": {"body": "STOP"}
                    }]
                }
            }]
        }]
    }
    res_stop = WhatsAppWebhookService.handle_inbound_payload(db_session, payload_stop)
    assert res_stop["opt_outs_recorded"] == 1
    opt = db_session.query(OptOut).filter(OptOut.phone == "+919876543210").first()
    assert opt is not None

    res_stop2 = WhatsAppWebhookService.handle_inbound_payload(db_session, payload_stop)
    assert res_stop2["opt_outs_recorded"] == 1


def test_whatsapp_webhook_signature_verification():
    import hmac
    import hashlib
    from backend.app.core.config import settings

    secret = "my_super_secret_webhook_key_123"
    raw_body = b'{"object":"whatsapp_business_account","entry":[]}'

    with patch.object(settings, "WHATSAPP_APP_SECRET", secret):
        # 1. Valid signature
        valid_digest = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        assert WhatsAppWebhookService.verify_meta_signature(raw_body, f"sha256={valid_digest}") is True

        # 2. Tampered body
        tampered_body = b'{"object":"whatsapp_business_account","entry":[{"forged":true}]}'
        assert WhatsAppWebhookService.verify_meta_signature(tampered_body, f"sha256={valid_digest}") is False

        # 3. Missing header
        assert WhatsAppWebhookService.verify_meta_signature(raw_body, None) is False

        # 4. Header without sha256= prefix
        assert WhatsAppWebhookService.verify_meta_signature(raw_body, valid_digest) is False

        # 5. Invalid signature value
        assert WhatsAppWebhookService.verify_meta_signature(raw_body, "sha256=invalidhash000") is False

    # 6. Unconfigured secret in non-test mode (fails closed)
    with patch.object(settings, "WHATSAPP_APP_SECRET", None), \
         patch.dict(os.environ, {"PYTEST_CURRENT_TEST": ""}), \
         patch.object(settings, "ENVIRONMENT", "production"):
        assert WhatsAppWebhookService.verify_meta_signature(raw_body, "sha256=somehash") is False


# ==========================================
# 8. Discovery & Vibe Service Branches
# ==========================================
def test_discovery_service_geocoding_and_venues(db_session):
    res = VendorDiscoveryService.geocode_query("jaipur")
    assert res is not None
    assert abs(res[0] - 26.9124) < 0.1

    search_res = VendorDiscoveryService.search_vendors(
        db_session,
        lat=None,
        lng=None,
        city="NonexistentCity",
        category="Catering"
    )
    assert search_res is not None
    assert search_res.query_lat is None


def test_vibe_service_not_found_branches(db_session):
    with pytest.raises(HTTPException) as exc:
        VibeService.get_moodboard(db_session, "nonexistent_profile_id")
    assert exc.value.status_code == 404

    with pytest.raises(HTTPException) as exc2:
        VibeService.accept_decor_item(db_session, "nonexistent_decor_id")
    assert exc2.value.status_code == 404

    with pytest.raises(HTTPException) as exc3:
        VibeService.reject_decor_item(db_session, "nonexistent_decor_id")
    assert exc3.value.status_code == 404
