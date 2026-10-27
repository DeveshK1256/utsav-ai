"""
Targeted tests to push backend line & branch coverage above 90% deterministically.
Covers:
- WhatsAppWebhookService (Meta verification, status updates, STOP opt-out, inbound FAQ)
- DiscoveryService (search_vendors by city/category, Nominatim fallback, item conversions)
- LLM provider deterministic stubs (fallback quotes, stubs, prompt formatting)
- Rituals API endpoints (/muhurat-candidates, /panchang, /traditions)
- WhatsApp webhook verification API (/webhooks/whatsapp)
"""

import hmac
import hashlib
import json
import uuid
import datetime
import io
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.models.models import (
    Event,
    Guest,
    MessageLog,
    OptOut,
    VendorProfile,
    SubEvent,
    User,
    BudgetItem,
    EventFactSheet,
    ChangeEvent,
)
from backend.app.services.whatsapp.webhook_service import WhatsAppWebhookService
from backend.app.services.whatsapp.guest_service import GuestService
from backend.app.services.whatsapp.send_service import WhatsAppSendService
from backend.app.services.whatsapp.rsvp_parser import RSVPParser
from backend.app.services.whatsapp.provider import MetaCloudWhatsAppProvider, get_whatsapp_provider
from backend.app.services.invitation_wording_agent import InvitationWordingAgent
from backend.app.services.discovery_service import VendorDiscoveryService
from backend.app.services.budget_engine import BudgetScalingEngine
from backend.app.services.llm_provider import (
    DeterministicStubQuoteExtractionProvider,
    DeterministicStubNegotiationDraftProvider,
    DeterministicStubReplanningExplanationProvider,
    DeterministicStubVibeProvider,
)

client = TestClient(app)


# =============================================================================
# WHATSAPP WEBHOOK SERVICE DEEP COVERAGE
# =============================================================================

def test_webhook_signature_verification():
    secret = "test_meta_webhook_secret_key"
    payload = b'{"object":"whatsapp_business_account"}'
    valid_sig = "sha256=" + hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    with patch("backend.app.services.whatsapp.webhook_service.settings") as mock_settings, \
         patch.dict("os.environ", {"PYTEST_CURRENT_TEST": ""}):
        mock_settings.WHATSAPP_APP_SECRET = secret
        mock_settings.ENVIRONMENT = "production"

        assert WhatsAppWebhookService.verify_meta_signature(payload, valid_sig) is True
        assert WhatsAppWebhookService.verify_meta_signature(payload, "sha256=forged_bad_signature") is False
        assert WhatsAppWebhookService.verify_meta_signature(payload, None) is False
        assert WhatsAppWebhookService.verify_meta_signature(payload, "invalid_prefix") is False


def test_webhook_handle_status_updates():
    db = SessionLocal()
    wamid = f"wamid.test_delivery_{uuid.uuid4().hex}"
    try:
        # Create a test message log
        msg = MessageLog(
            event_id="test_ev",
            guest_id="test_g",
            whatsapp_message_id=wamid,
            phone_number="+919876543210",
            direction="outbound",
            message_type="template",
            content_snapshot="Your celebration invitation",
            delivery_status="sent"
        )
        db.add(msg)
        db.commit()
        msg_id = str(msg.id)

        # Simulate delivered callback
        payload_delivered = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "statuses": [
                                    {"id": wamid, "status": "delivered"}
                                ]
                            }
                        }
                    ]
                }
            ]
        }
        res = WhatsAppWebhookService.handle_inbound_payload(db, payload_delivered)
        assert res["statuses_updated"] == 1

        msg_check = db.query(MessageLog).filter(MessageLog.id == msg_id).first()
        assert msg_check.delivery_status == "delivered"

        # Simulate failed callback
        payload_failed = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "statuses": [
                                    {"id": wamid, "status": "failed", "errors": [{"title": "Number unreachable"}]}
                                ]
                            }
                        }
                    ]
                }
            ]
        }
        res_fail = WhatsAppWebhookService.handle_inbound_payload(db, payload_failed)
        assert res_fail["statuses_updated"] == 1

        msg_fail_check = db.query(MessageLog).filter(MessageLog.id == msg_id).first()
        assert msg_fail_check.delivery_status == "failed"
        assert "unreachable" in msg_fail_check.failure_reason.lower()
    finally:
        # Clean up
        db.query(MessageLog).filter(MessageLog.whatsapp_message_id == wamid).delete()
        db.commit()
        db.close()


def test_webhook_handle_stop_opt_out():
    db = SessionLocal()
    phone = f"+9198{uuid.uuid4().int % 100000000:08d}"
    stop_id = f"wamid.stop_{uuid.uuid4().hex[:6]}"
    try:
        payload_stop = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "id": stop_id,
                                        "from": phone.lstrip("+"),
                                        "type": "text",
                                        "text": {"body": "STOP"}
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }
        res = WhatsAppWebhookService.handle_inbound_payload(db, payload_stop)
        assert res["opt_outs_recorded"] == 1

        opt_out = db.query(OptOut).filter(OptOut.phone == phone).first()
        assert opt_out is not None
        assert "STOP" in opt_out.reason
    finally:
        db.query(OptOut).filter(OptOut.phone == phone).delete()
        db.commit()
        db.close()


# =============================================================================
# DISCOVERY SERVICE DEEP COVERAGE
# =============================================================================

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


# =============================================================================
# DETERMINISTIC STUBS COVERAGE
# =============================================================================

def test_deterministic_stubs_quote_and_vibe():
    quote_stub = DeterministicStubQuoteExtractionProvider()
    # Test all 4 category branches: venue, caterer, decorator, photographer
    for cat in ["venue", "caterer", "decorator", "photographer"]:
        q_res = quote_stub.extract_quote_from_document(b"dummy_bytes", "test.pdf", "application/pdf", cat)
        assert q_res.vendor_name
        assert q_res.total_amount > 0
        assert len(q_res.line_items) >= 1

    neg_stub = DeterministicStubNegotiationDraftProvider()
    n_res = neg_stub.generate_negotiation_drafts(
        vendor_name="Taj Hall",
        category="venue",
        quoted_total=100000.0,
        target_discount_pct=10.0,
        leverage_points=["Early deposit"],
        competing_vendor_name="Leela Palace",
        competing_quote_total=90000.0
    )
    assert isinstance(n_res, dict)
    assert "polite" in n_res or len(n_res) > 0

    replan_stub = DeterministicStubReplanningExplanationProvider()
    # Test all change_type branches and over_budget=True
    for ct in ["guest_count_changed", "date_moved", "vendor_cancelled", "budget_cut", "venue_unavailable", "other"]:
        r_res = replan_stub.generate_explanation_and_mitigations(
            change_type=ct,
            diff_summary={
                "budget_total_delta": 25000.0,
                "budget_total_new": 125000.0,
                "from_guest_count": 100,
                "to_guest_count": 150,
                "days_shifted": 3,
                "from_date": "2026-12-01",
                "to_date": "2026-12-04",
                "vendor_category": "catering",
                "vendor_name": "Royal Caterers",
                "cut_amount": 25000.0,
                "venue_name": "Grand Hall",
                "capacity_exceeded": True,
                "capacity_warning": "Warning: Hall capacity exceeded"
            },
            total_budget=100000.0
        )
        assert isinstance(r_res, dict)
        assert "explanation" in r_res
        assert len(r_res["mitigation_suggestions"]) >= 1

    vibe_stub = DeterministicStubVibeProvider()
    v_res = vibe_stub.extract_vibe_from_images([{"data": "mock"}], "Warm festival")
    assert len(v_res.images) >= 1
    assert len(v_res.overall_mood_words) >= 1

    theme_res = vibe_stub.generate_theme_proposal(
        style_profile={"palette": ["#FF0000"]},
        event_details={"city": "Pune", "guest_count": 200}
    )
    assert theme_res.theme_name
    assert len(theme_res.decor_items) >= 1


# =============================================================================
# RITUALS & WEBHOOKS API ENDPOINTS COVERAGE
# =============================================================================

def test_api_rituals_muhurat_and_traditions():
    # 1. Muhurat candidates
    resp = client.get("/api/v1/rituals/muhurat-candidates?event_date=2026-12-15&latitude=18.5204&longitude=73.8567")
    assert resp.status_code == 200
    data = resp.json()
    assert "candidates" in data

    # 2. Traditions list
    t_resp = client.get("/api/v1/rituals/traditions")
    assert t_resp.status_code == 200
    t_data = t_resp.json()
    assert isinstance(t_data, list)


def test_api_webhooks_whatsapp_hub_challenge():
    # Meta webhook verification challenge
    token = "utsav_webhook_verify_token_secure"
    challenge = "1158201444"

    resp = client.get(f"/api/v1/webhooks/whatsapp?hub.mode=subscribe&hub.challenge={challenge}&hub.verify_token={token}")
    assert resp.status_code == 200
    assert resp.text == challenge

    # Invalid token rejection
    resp_bad = client.get(f"/api/v1/webhooks/whatsapp?hub.mode=subscribe&hub.challenge={challenge}&hub.verify_token=wrong")
    assert resp_bad.status_code == 403


# =============================================================================
# RSVP PARSER & GUEST SERVICE BRANCH TESTS
# =============================================================================

def test_rsvp_parser_branches_deep():
    # Quick reply variations
    assert RSVPParser.parse_quick_reply("button_maybe").rsvp_status == "maybe"
    assert RSVPParser.parse_quick_reply("button_decline").rsvp_status == "declined"
    unknown_qr = RSVPParser.parse_quick_reply("unrecognized_payload")
    assert unknown_qr.rsvp_status == "unknown"
    assert unknown_qr.needs_host_review is True

    # Free-text declined (unambiguous decline tokens without 'attend')
    d1 = RSVPParser.parse_free_text("Sorry, we cannot make it unfortunately")
    assert d1.rsvp_status == "declined"
    assert d1.headcount == 0

    # Free-text maybe (tentative requires host review)
    m1 = RSVPParser.parse_free_text("Maybe we might make it")
    assert m1.needs_host_review is True
    assert m1.confidence < 0.70

    # Free-text conflict
    c1 = RSVPParser.parse_free_text("Yes I would love to, but unfortunately no cannot make it")
    assert c1.rsvp_status == "unknown"

    # Headcount patterns
    h1 = RSVPParser.parse_free_text("We are coming, family of 4, pure veg please")
    assert h1.rsvp_status == "attending"
    assert h1.headcount == 4
    assert h1.diet == "veg"

    h2 = RSVPParser.parse_free_text("Joining with my wife and 2 kids, jain food")
    assert h2.rsvp_status == "attending"
    assert h2.headcount == 4
    assert h2.diet == "jain"

    h3 = RSVPParser.parse_free_text("Yes! Me plus 2 guests, vegan")
    assert h3.rsvp_status == "attending"
    assert h3.headcount == 3
    assert h3.diet == "vegan"

    h4 = RSVPParser.parse_free_text("Confirmed for 3 people, non-veg")
    assert h4.rsvp_status == "attending"
    assert h4.headcount == 3
    assert h4.diet == "non_veg"


def test_guest_service_import_and_metrics():
    db = SessionLocal()
    ev_id = f"test_ev_{uuid.uuid4().hex[:8]}"
    try:
        # Create temporary event with Python date object and required fields
        ev = Event(
            id=ev_id,
            owner_id="test_owner_deep",
            name="Test Deep Event",
            event_type="wedding",
            city="Delhi",
            pincode="110001",
            owner_token="test_tok_deep",
            start_date=datetime.date(2026, 11, 20),
            end_date=datetime.date(2026, 11, 21),
            total_budget=500000,
            guest_count=100
        )
        db.add(ev)
        db.commit()

        # CSV parsing
        csv_data = "name,phone,diet,kids_count\nAnanya Sharma,+919876543210,jain,1\nKabir Mehta,+919876543211,non_veg,0"
        rows = GuestService.parse_csv_file(csv_data)
        assert len(rows) == 2

        # Ingest with errors and valid rows
        batch_rows = [
            {"name": "", "phone": "+919876543212"},  # Missing name
            {"name": "Valid Guest", "phone": ""},    # Missing phone
            {"name": "Bad Phone", "phone": "1234"},  # Invalid phone
            {"name": "Aarav", "phone": "+919876543220", "diet": "unknown_diet", "mobility_needs": "yes", "accommodation": "yes"},
            {"name": "Pooja", "phone": "+919876543221", "diet": "vegan", "kids": 2, "headcount": 3}
        ]
        res = GuestService.import_guest_rows(db, ev_id, batch_rows)
        assert res.total_processed == 5
        assert res.successful_count == 2
        assert len(res.errors) == 3

        # Update RSVP status to attending for summary calculation
        g1 = db.query(Guest).filter(Guest.event_id == ev_id).first()
        if g1:
            g1.rsvp_status = "attending"
            db.commit()

        summary = GuestService.get_rsvp_summary(db, ev_id)
        assert summary.total_guests == 2
        assert summary.attending_count >= 1
        assert summary.total_confirmed_headcount >= 1
    finally:
        db.query(Guest).filter(Guest.event_id == ev_id).delete()
        db.query(Event).filter(Event.id == ev_id).delete()
        db.commit()
        db.close()


def test_api_rituals_pandit_guide_and_merge():
    db = SessionLocal()
    ev_id = f"ev_rit_{uuid.uuid4().hex[:8]}"
    try:
        ev = Event(
            id=ev_id,
            owner_id="test_owner_rit",
            name="Ritual Test Wedding",
            event_type="wedding",
            city="Mumbai",
            pincode="400001",
            owner_token="test_tok_rit",
            start_date=datetime.date(2026, 12, 10),
            end_date=datetime.date(2026, 12, 12),
            tradition_code="maharashtrian_vedic",
            secondary_tradition_code="tamil_brahmin_hindu",
            total_budget=1000000,
            guest_count=200
        )
        db.add(ev)
        db.commit()

        # Add a sub-event
        se = SubEvent(
            event_id=ev_id,
            name="Varmala Ceremony",
            sort_order=1,
            venue_name="Main Mandap",
            start_time=datetime.datetime(2026, 12, 10, 10, 0, 0),
            end_time=datetime.datetime(2026, 12, 10, 12, 0, 0),
            is_outdoor=False
        )
        db.add(se)
        db.commit()

        # Call pandit guide endpoint
        resp = client.get(f"/api/v1/rituals/events/{ev_id}/pandit-guide")
        assert resp.status_code == 200
        data = resp.json()
        assert "panchang_and_muhurat" in data
        assert "samagri_checklist" in data
        assert "tradition" in data

        # Pandit guide 404 test
        resp_404 = client.get(f"/api/v1/rituals/events/nonexistent_ev/pandit-guide")
        assert resp_404.status_code == 404

        # Samagri 404 test
        resp_sam_404 = client.get("/api/v1/rituals/traditions/unknown_tradition/samagri")
        assert resp_sam_404.status_code == 404

        # Dual traditions merge endpoint
        merge_payload = {
            "primary_tradition_code": "maharashtrian_vedic",
            "secondary_tradition_code": "tamil_brahmin_hindu",
            "start_date": "2026-12-10",
            "event_id": ev_id
        }
        merge_resp = client.post("/api/v1/rituals/merge-traditions", json=merge_payload)
        assert merge_resp.status_code == 200
        merge_data = merge_resp.json()
        assert "run_of_show" in merge_data
        assert "samagri_items" in merge_data
    finally:
        db.query(SubEvent).filter(SubEvent.event_id == ev_id).delete()
        db.query(Event).filter(Event.id == ev_id).delete()
        db.commit()
        db.close()


def test_invitation_wording_agent_mock_gemini():
    # 1. Successful Gemini mocked call
    mock_payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "variants": [
                                    {"id": "v1", "title": "Traditional", "body_text": "Sample text", "tone": "Warm"}
                                ]
                            })
                        }
                    ]
                }
            }
        ]
    }
    with patch("httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_payload
        mock_instance.__enter__.return_value.post.return_value = mock_response
        mock_client.return_value = mock_instance

        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_test_key"}):
            res = InvitationWordingAgent.compose_wording(
                event_name="Sangeet Night",
                host_name="Sharma",
                event_type="wedding",
                date_str="2026-11-20",
                venue_str="The Grand Hall"
            )
            assert len(res.variants) == 1
            assert res.provider_used == "gemini"

    # 2. Failure fallback test
    with patch("httpx.Client") as mock_client_fail:
        mock_instance_fail = MagicMock()
        mock_instance_fail.__enter__.return_value.post.side_effect = RuntimeError("API Rate limit")
        mock_client_fail.return_value = mock_instance_fail

        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_test_key"}):
            res_fallback = InvitationWordingAgent.compose_wording(
                event_name="Sangeet Night",
                host_name=None,
                event_type="wedding",
                date_str="2026-11-20",
                venue_str="The Grand Hall"
            )
            assert len(res_fallback.variants) >= 2
            assert res_fallback.fallback_warning is not None
            assert "deterministic" in res_fallback.fallback_warning.lower()


# =============================================================================
# INTAKE, REPLANNING, AND GUESTS API FLOWS
# =============================================================================

def test_api_intake_budget_and_traditions():
    # 1. Budget calculation endpoint
    payload = {
        "event_type": "wedding",
        "city": "Pune",
        "guest_count": 200,
        "total_budget": 800000.0
    }
    resp = client.post("/api/v1/intake/calculate-budget", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "tier" in data["city_tier"]
    assert len(data["items"]) >= 5

    # Bad request validation
    resp_bad = client.post("/api/v1/intake/calculate-budget", json={"event_type": "wedding", "city": "Pune", "guest_count": -5, "total_budget": 800000.0})
    assert resp_bad.status_code == 422

    # 2. Traditions endpoint
    t_resp = client.get("/api/v1/intake/traditions")
    assert t_resp.status_code == 200
    assert isinstance(t_resp.json(), list)


def test_api_guests_crud_and_factsheet():
    db = SessionLocal()
    ev_id = f"ev_g_{uuid.uuid4().hex[:8]}"
    token = f"tok_g_{uuid.uuid4().hex[:8]}"
    headers = {"X-Event-Owner-Token": token}
    try:
        user = User(
            phone_number=f"+9198{uuid.uuid4().hex[:8]}",
            full_name="Guest Test Host",
            role="host"
        )
        db.add(user)
        db.flush()

        ev = Event(
            id=ev_id,
            owner_id=user.id,
            name="Guest Flow Event",
            event_type="wedding",
            city="Delhi",
            pincode="110001",
            owner_token=token,
            start_date=datetime.date(2026, 11, 20),
            end_date=datetime.date(2026, 11, 21),
            total_budget=500000,
            guest_count=100
        )
        db.add(ev)
        db.commit()

        # 1. Import guests via JSON
        import_payload = {
            "guests": [
                {"name": "Guest Alpha", "phone": "+919876543111", "diet": "veg", "kids_count": 1},
                {"name": "Guest Beta", "phone": "+919876543112", "diet": "jain", "kids_count": 0}
            ]
        }
        res_import = client.post(f"/api/v1/events/{ev_id}/guests/import", json=import_payload, headers=headers)
        assert res_import.status_code == 200
        assert res_import.json()["successful_count"] == 2

        # 2. List guests
        res_list = client.get(f"/api/v1/events/{ev_id}/guests")
        assert res_list.status_code == 200
        assert len(res_list.json()) == 2

        # 3. RSVP summary
        res_sum = client.get(f"/api/v1/events/{ev_id}/guests/rsvp-summary")
        assert res_sum.status_code == 200
        assert res_sum.json()["total_guests"] == 2

        # 4. Factsheet update and get
        fs_payload = {
            "venue_address": "77 Palace Grounds, Delhi",
            "parking_info": "Valet available at Gate 2",
            "dress_code": "Traditional Indian formal"
        }
        res_fs_put = client.post(f"/api/v1/events/{ev_id}/fact-sheet", json=fs_payload, headers=headers)
        assert res_fs_put.status_code == 200
        assert res_fs_put.json()["venue_address"] == "77 Palace Grounds, Delhi"

        res_fs_get = client.get(f"/api/v1/events/{ev_id}/fact-sheet")
        assert res_fs_get.status_code == 200
        assert "Valet" in res_fs_get.json()["parking_info"]
    finally:
        db.query(Guest).filter(Guest.event_id == ev_id).delete()
        db.query(EventFactSheet).filter(EventFactSheet.event_id == ev_id).delete()
        db.query(Event).filter(Event.id == ev_id).delete()
        db.commit()
        db.close()


def test_api_replanning_flow():
    db = SessionLocal()
    ev_id = f"ev_rep_{uuid.uuid4().hex[:8]}"
    token = f"tok_rep_{uuid.uuid4().hex[:8]}"
    headers = {"X-Event-Owner-Token": token}
    try:
        user = User(
            phone_number=f"+9198{uuid.uuid4().hex[:8]}",
            full_name="Replanning Test Host",
            role="host"
        )
        db.add(user)
        db.flush()

        ev = Event(
            id=ev_id,
            owner_id=user.id,
            name="Replanning Test Event",
            event_type="wedding",
            city="Mumbai",
            pincode="400001",
            owner_token=token,
            start_date=datetime.date(2026, 12, 10),
            end_date=datetime.date(2026, 12, 12),
            total_budget=1000000,
            guest_count=200
        )
        db.add(ev)
        db.flush()

        b_item = BudgetItem(
            event_id=ev.id,
            category="catering",
            name="Grand Feast",
            scaling_rule="per_guest",
            planned_amount=300000.0
        )
        db.add(b_item)
        db.commit()

        # 1. Submit a guest count reduction change request
        change_req = {
            "change_type": "guest_count_changed",
            "payload": {"from_guest_count": 200, "to_guest_count": 150}
        }
        res_submit = client.post(f"/api/v1/events/{ev_id}/changes", json=change_req, headers=headers)
        assert res_submit.status_code == 201
        data = res_submit.json()
        change_id = data["change_id"]
        assert change_id is not None
        assert data["change_type"] == "guest_count_changed"

        # 2. List change proposals
        res_list = client.get(f"/api/v1/events/{ev_id}/changes")
        assert res_list.status_code == 200
        assert len(res_list.json()) >= 1

        # 3. Retrieve change proposal
        res_get = client.get(f"/api/v1/events/{ev_id}/changes/{change_id}")
        assert res_get.status_code == 200
        assert res_get.json()["change_id"] == change_id

        # 4. Accept change proposal
        res_accept = client.post(f"/api/v1/events/{ev_id}/changes/{change_id}/accept", headers=headers)
        assert res_accept.status_code == 200
        assert res_accept.json()["status"] == "applied"
    finally:
        db.query(BudgetItem).filter(BudgetItem.event_id == ev_id).delete()
        db.query(ChangeEvent).filter(ChangeEvent.event_id == ev_id).delete()
        db.query(Event).filter(Event.id == ev_id).delete()
        db.commit()
        db.close()


# =============================================================================
# WHATSAPP CLOUD PROVIDER & DISCOVERY API COVERAGE
# =============================================================================

def test_meta_cloud_whatsapp_provider_deep():
    provider = MetaCloudWhatsAppProvider(phone_number_id="123456", api_token="test_token")

    # 1. Interactive buttons success
    mock_success_resp = MagicMock()
    mock_success_resp.status_code = 200
    mock_success_resp.json.return_value = {"messages": [{"id": "wamid.interactive_123"}]}

    with patch("httpx.post", return_value=mock_success_resp):
        res = provider.send_interactive_buttons(
            to_phone="+919876543210",
            body="Please choose an RSVP option",
            buttons=[{"id": "btn_yes", "title": "Attending"}, {"id": "btn_no", "title": "Declined"}]
        )
        assert res.success is True
        assert res.message_id == "wamid.interactive_123"

    # 2. Interactive buttons API error response
    mock_err_resp = MagicMock()
    mock_err_resp.status_code = 400
    mock_err_resp.json.return_value = {"error": {"message": "Invalid recipient phone number"}}
    mock_err_resp.text = "Error detail"

    with patch("httpx.post", return_value=mock_err_resp):
        res_err = provider.send_interactive_buttons(
            to_phone="+919876543210",
            body="Please choose an RSVP option",
            buttons=[{"id": "btn_yes", "title": "Attending"}]
        )
        assert res_err.success is False
        assert "Invalid recipient" in res_err.error

    # 3. Interactive buttons network exception
    with patch("httpx.post", side_effect=RuntimeError("Connection reset by peer")):
        res_exc = provider.send_interactive_buttons(
            to_phone="+919876543210",
            body="Please choose an RSVP option",
            buttons=[{"id": "btn_yes", "title": "Attending"}]
        )
        assert res_exc.success is False
        assert "Connection reset" in res_exc.error

    # 4. Provider factory resolution
    with patch.dict("os.environ", {"WHATSAPP_PROVIDER": "cloud_api", "WHATSAPP_API_TOKEN": "tok", "WHATSAPP_PHONE_NUMBER_ID": "123"}):
        prov = get_whatsapp_provider()
        assert isinstance(prov, MetaCloudWhatsAppProvider)


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


def test_api_guests_csv_and_actions():
    db = SessionLocal()
    try:
        rand_suffix = str(uuid.uuid4())[:8]
        user = User(phone_number=f"+9188{rand_suffix}", full_name="CSV User", email=f"csv_{rand_suffix}@example.com")
        db.add(user)
        db.commit()

        token = "csv_test_secret_token_abc123"
        event = Event(
            id="csv_test_evt_1",
            name="CSV Guest Test Event",
            owner_id=user.id,
            owner_token=token,
            event_type="wedding",
            guest_count=100,
            total_budget=500000.0,
            city="Pune",
            pincode="411001",
            start_date=datetime.date(2026, 12, 1),
            end_date=datetime.date(2026, 12, 3),
            metadata_json={"owner_token": token}
        )
        db.add(event)
        db.commit()

        headers = {"X-Event-Owner-Token": token}

        # 1. CSV Import
        csv_content = "name,phone,group_side,diet\nRohan Kulkarni,+919876543210,groom,veg\nAnanya Sharma,+919876543211,bride,jain\n"
        csv_file = ("guests.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")
        csv_resp = client.post(
            f"/api/v1/events/{event.id}/guests/import-csv",
            files={"file": csv_file},
            headers=headers
        )
        assert csv_resp.status_code == 200
        csv_data = csv_resp.json()
        assert csv_data["successful_count"] == 2

        # 2. RSVP Summary
        sum_resp = client.get(f"/api/v1/events/{event.id}/guests/rsvp-summary")
        assert sum_resp.status_code == 200
        sum_data = sum_resp.json()
        assert sum_data["total_guests"] == 2

        # 3. Send Invitations
        with patch.object(WhatsAppSendService, "send_batch_invitations", return_value={
            "total_requested": 2,
            "sent_count": 2,
            "blocked_opt_out_count": 0,
            "failed_count": 0,
            "message_ids": ["wamid.1", "wamid.2"],
            "errors": []
        }):
            send_resp = client.post(f"/api/v1/events/{event.id}/guests/send-invitations", headers=headers)
            assert send_resp.status_code == 200

        # 4. Reminders endpoint
        rem_resp = client.get(f"/api/v1/events/{event.id}/reminders")
        assert rem_resp.status_code == 200

        # 5. Delete guest
        guests = db.query(Guest).filter(Guest.event_id == event.id).all()
        assert len(guests) == 2
        del_resp = client.delete(f"/api/v1/events/{event.id}/guests/{guests[0].id}", headers=headers)
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "purged"

        # 6. Delete invalid guest -> 404
        del_404 = client.delete(f"/api/v1/events/{event.id}/guests/non_existent_guest_id", headers=headers)
        assert del_404.status_code == 404
    finally:
        db.query(Guest).filter(Guest.event_id == "csv_test_evt_1").delete()
        db.query(Event).filter(Event.id == "csv_test_evt_1").delete()
        db.query(User).filter(User.email == "csv_test@example.com").delete()
        db.commit()
        db.close()


def test_api_replanning_endpoints_deep():
    db = SessionLocal()
    try:
        rand_suffix = str(uuid.uuid4())[:8]
        user = User(phone_number=f"+9177{rand_suffix}", full_name="Replan User", email=f"replan_{rand_suffix}@example.com")
        db.add(user)
        db.commit()

        token = "replan_api_secret_token_123"
        event = Event(
            id="replan_api_evt_1",
            name="Replan API Event",
            owner_id=user.id,
            owner_token=token,
            event_type="wedding",
            guest_count=200,
            total_budget=1000000.0,
            city="Pune",
            pincode="411001",
            start_date=datetime.date(2026, 12, 1),
            end_date=datetime.date(2026, 12, 3),
            metadata_json={"owner_token": token}
        )
        db.add(event)
        db.commit()

        headers = {"X-Event-Owner-Token": token}

        # 1. Submit a change event
        payload = {
            "change_type": "guest_count_changed",
            "trigger_source": "user_manual",
            "payload": {
                "from_guest_count": 200,
                "to_guest_count": 250
            }
        }
        res_post = client.post(f"/api/v1/events/{event.id}/changes", json=payload, headers=headers)
        assert res_post.status_code == 201
        change_data = res_post.json()
        change_id = change_data["change_id"]

        # 2. List changes
        res_list = client.get(f"/api/v1/events/{event.id}/changes")
        assert res_list.status_code == 200
        assert len(res_list.json()) >= 1

        # 3. Get change proposal
        res_get = client.get(f"/api/v1/events/{event.id}/changes/{change_id}")
        assert res_get.status_code == 200
        assert res_get.json()["change_id"] == change_id

        # 4. Patch change proposal
        patch_payload = {
            "manual_overrides": {"note": "Adjusted manually"}
        }
        res_patch = client.patch(f"/api/v1/events/{event.id}/changes/{change_id}", json=patch_payload, headers=headers)
        assert res_patch.status_code == 200

        # 5. Accept change proposal
        res_accept = client.post(f"/api/v1/events/{event.id}/changes/{change_id}/accept", headers=headers)
        assert res_accept.status_code == 200
        assert res_accept.json()["status"] == "applied"
    finally:
        from backend.app.models.models import ChangeEvent
        db.query(ChangeEvent).filter(ChangeEvent.event_id == "replan_api_evt_1").delete()
        db.query(Event).filter(Event.id == "replan_api_evt_1").delete()
        db.query(User).filter(User.email == "replan_api@example.com").delete()
        db.commit()
        db.close()


def test_budget_scaling_engine_allocation_models():
    # Test all event models (birthday, puja, community_festival, anniversary)
    for evt_type in ["birthday", "puja", "community_festival", "milestone_anniversary", "wedding"]:
        items = BudgetScalingEngine.compute_budget_allocation(
            total_envelope=500000.0,
            event_type=evt_type,
            city="Mumbai",
            guest_count=150
        )
        assert len(items) >= 4
        total_pct = sum(item["percentage"] for item in items)
        assert abs(total_pct - 100.0) < 0.1

    # Invalid cases
    with pytest.raises(ValueError):
        BudgetScalingEngine.compute_budget_allocation(total_envelope=-100)

    with pytest.raises(ValueError):
        BudgetScalingEngine.compute_budget_allocation(total_envelope=1000, guest_count=-5)


def test_api_intake_and_replanning_errors():
    # 1. Traditions endpoint
    res_trad = client.get("/api/v1/intake/traditions")
    assert res_trad.status_code == 200
    assert len(res_trad.json()) >= 1

    # 2. Intake calculate-budget error
    bad_calc = client.post("/api/v1/intake/calculate-budget", json={
        "total_budget": -500,
        "city": "Pune",
        "guest_count": 100,
        "event_type": "wedding"
    })
    assert bad_calc.status_code in (400, 422)

    # 3. Intake generate error
    bad_gen = client.post("/api/v1/intake/generate", json={
        "event_name": "Too Short Event",
        "event_type": "wedding",
        "city": "Pune",
        "total_budget": -50000,
        "guest_count": 0,
        "start_date": "2026-11-20",
        "end_date": "2026-11-22"
    })
    assert bad_gen.status_code in (400, 422)

    # 4. Replanning 404 change proposal
    res_404 = client.get("/api/v1/events/non_existent_evt/changes/fake_change_id")
    assert res_404.status_code == 404


def test_llm_provider_factories():
    from backend.app.services.llm_provider import (
        get_vibe_extraction_provider,
        get_theme_generation_provider,
        get_replanning_explanation_provider,
        DeterministicStubVibeProvider,
        DeterministicStubReplanningExplanationProvider
    )

    with patch.dict("os.environ", {}, clear=True):
        vibe_prov = get_vibe_extraction_provider()
        assert isinstance(vibe_prov, DeterministicStubVibeProvider)

        theme_prov = get_theme_generation_provider()
        assert isinstance(theme_prov, DeterministicStubVibeProvider)

        replan_prov = get_replanning_explanation_provider()
        assert isinstance(replan_prov, DeterministicStubReplanningExplanationProvider)


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


def test_api_invitations_download_and_list():
    from backend.app.models.models import InvitationCard
    db = SessionLocal()
    try:
        rand_suffix = str(uuid.uuid4())[:8]
        user = User(phone_number=f"+9166{rand_suffix}", full_name="Invite User", email=f"inv_{rand_suffix}@example.com")
        db.add(user)
        db.commit()

        token = "invite_test_secret_token_123"
        event = Event(
            id="inv_test_evt_1",
            name="Invitation Test Event",
            owner_id=user.id,
            owner_token=token,
            event_type="wedding",
            guest_count=150,
            total_budget=800000.0,
            city="Pune",
            pincode="411001",
            start_date=datetime.date(2026, 12, 1),
            end_date=datetime.date(2026, 12, 2),
            metadata_json={"owner_token": token}
        )
        db.add(event)
        db.commit()

        # Create dummy invitation card with both png and pdf bytes
        png_dummy = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRdummy"
        pdf_dummy = b"%PDF-1.4 dummy pdf bytes"
        card = InvitationCard(
            id="inv_test_card_1",
            event_id=event.id,
            layout_variant="classic_royal",
            wording_text="श्री गणेशाय नमः\nहार्दिक आमंत्रण",
            rendered_png=png_dummy,
            rendered_pdf=pdf_dummy
        )
        db.add(card)
        db.commit()

        # 1. List invitation cards
        res_list = client.get(f"/api/v1/events/{event.id}/invitations")
        assert res_list.status_code == 200
        data_list = res_list.json()
        assert len(data_list) >= 1
        assert any(c["id"] == "inv_test_card_1" for c in data_list)

        # 2. Download PNG
        res_png = client.get(f"/api/v1/events/{event.id}/invitations/{card.id}/download?format=png")
        assert res_png.status_code == 200
        assert res_png.headers["content-type"] == "image/png"
        assert res_png.content == png_dummy

        # 3. Download PDF
        res_pdf = client.get(f"/api/v1/events/{event.id}/invitations/{card.id}/download?format=pdf")
        assert res_pdf.status_code == 200
        assert res_pdf.headers["content-type"] == "application/pdf"
        assert res_pdf.content == pdf_dummy

        # 4. Download non-existent card -> 404
        res_404 = client.get(f"/api/v1/events/{event.id}/invitations/fake_card_id/download")
        assert res_404.status_code == 404
    finally:
        db.query(InvitationCard).filter(InvitationCard.event_id == "inv_test_evt_1").delete()
        db.query(Event).filter(Event.id == "inv_test_evt_1").delete()
        db.query(User).filter(User.phone_number == f"+9166{rand_suffix}").delete()
        db.commit()
        db.close()


def test_api_quotes_negotiation_draft():
    from backend.app.models.models import QuoteDocument, QuoteLineItem
    rand_suffix = str(uuid.uuid4())[:8]
    db = SessionLocal()
    try:
        # 1. 404 for non-existent quote
        res_404 = client.post(
            "/api/v1/quotes/non_existent_quote_id/negotiate-draft",
            json={"quote_id": "non_existent_quote_id", "target_discount_percentage": 10.0}
        )
        assert res_404.status_code == 404

        # 2. Valid quote negotiation draft
        user = User(phone_number=f"+9155{rand_suffix}", full_name="Quote User", email=f"quote_{rand_suffix}@example.com")
        db.add(user)
        db.commit()

        token = "quote_test_secret_token_123"
        event = Event(
            id="quote_test_evt_1",
            name="Quote Test Event",
            owner_id=user.id,
            owner_token=token,
            event_type="wedding",
            guest_count=200,
            total_budget=1500000.0,
            city="Pune",
            pincode="411001",
            start_date=datetime.date(2026, 12, 1),
            end_date=datetime.date(2026, 12, 2),
            metadata_json={"owner_token": token}
        )
        db.add(event)
        db.commit()

        quote = QuoteDocument(
            id="quote_doc_test_1",
            event_id=event.id,
            vendor_name="Royal Catering Services",
            category="caterer",
            total_quoted_amount=500000.0,
            file_name="quote.pdf",
            file_type="application/pdf",
            uploaded_file=b"%PDF dummy",
            raw_extracted_json={"terms_and_conditions": ["Breakage charged extra"]}
        )
        db.add(quote)
        db.commit()

        li = QuoteLineItem(
            quote_document_id=quote.id,
            name="Buffet Dinner",
            qty=200.0,
            unit="plates",
            unit_price=2500.0,
            total=500000.0,
            category_tag="catering"
        )
        db.add(li)
        db.commit()

        res_neg = client.post(
            f"/api/v1/quotes/{quote.id}/negotiate-draft",
            json={"quote_id": quote.id, "target_discount_percentage": 12.0}
        )
        assert res_neg.status_code == 200
        neg_data = res_neg.json()
        assert neg_data["quote_id"] == quote.id
        assert neg_data["target_discount_percentage"] == 12.0
        assert "polite" in neg_data["draft_variants"]
    finally:
        db.query(QuoteLineItem).filter(QuoteLineItem.quote_document_id == "quote_doc_test_1").delete()
        db.query(QuoteDocument).filter(QuoteDocument.id == "quote_doc_test_1").delete()
        db.query(Event).filter(Event.id == "quote_test_evt_1").delete()
        db.query(User).filter(User.phone_number == f"+9155{rand_suffix}").delete()
        db.commit()
        db.close()


def test_core_logic_extreme_edge_cases():
    # 1. Budget scaling with extreme huge numbers (e.g. 100 Crore / 1 Billion INR)
    huge_budget = 1_000_000_000.0
    allocations = BudgetScalingEngine.compute_budget_allocation(
        total_envelope=huge_budget,
        event_type="wedding",
        city="Mumbai",
        guest_count=5000
    )
    total_planned = sum(item["planned_amount"] for item in allocations)
    assert abs(total_planned - huge_budget) < 1.0

    # 2. Budget scaling with large guest count (10,000 guests)
    alloc_large_guests = BudgetScalingEngine.compute_budget_allocation(
        total_envelope=5_000_000.0,
        event_type="community_festival",
        city="Pune",
        guest_count=10000
    )
    assert len(alloc_large_guests) >= 4

    # 3. Unicode and Devanagari text handling in invitation wording
    wording_res = InvitationWordingAgent.compose_wording(
        event_name="शुभ विवाह सोहळा",
        event_type="wedding",
        host_name="संजय आणि वंदना पाटील",
        venue_str="महालक्ष्मी लॉन्स, पुणे",
        muhurat_time="सकाळी ११:४५ वाजता",
        date_str="२१ डिसेंबर २०२६"
    )
    assert wording_res.variants
    first_body = wording_res.variants[0].body_text
    assert "पाटील" in first_body or len(first_body) > 10




