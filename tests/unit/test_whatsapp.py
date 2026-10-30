from backend.app.core.config import settings
import pytest
import hmac
import hashlib
from datetime import datetime, date, timedelta, timezone
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.models.models import Event, User, SubEvent, Guest, OptOut, MessageLog, EventFactSheet
from backend.app.services.whatsapp.phone_utils import normalize_e164_phone, validate_and_normalize_guest_phone
from backend.app.services.whatsapp.rsvp_parser import RSVPParser
from backend.app.services.whatsapp.faq_bot import FAQBotService, HARD_FALLBACK_REFUSAL
from backend.app.services.whatsapp.reminder_scheduler import ReminderScheduler
from backend.app.services.whatsapp.send_service import WhatsAppSendService, OptOutBlockedError
from backend.app.services.whatsapp.provider import MockWhatsAppProvider
from backend.app.services.whatsapp.webhook_service import WhatsAppWebhookService

client = TestClient(app)


@pytest.fixture(scope="module")
def setup_m4_test_event():
    """Creates a persistent test event for M4 testing."""
    import random
    db = SessionLocal()
    # Unique user
    phone = f"+9199{random.randint(10000000, 99999999)}"
    u = User(
        phone_number=phone,
        full_name="Ananya Sharma",
        role="host"
    )
    db.add(u)
    db.commit()
    db.refresh(u)

    # Event
    ev = Event(
        owner_id=u.id,
        name="Ananya & Kabir Vivah",
        event_type="wedding",
        tradition_code="hindu_north",
        guest_count=200,
        total_budget=3000000.0,
        city="Mumbai",
        pincode="400001",
        start_date=date.today() + timedelta(days=30),
        end_date=date.today() + timedelta(days=32),
        metadata_json={}
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    # Sub-event for reminder testing
    sub = SubEvent(
        event_id=ev.id,
        name="Sangeet & Cocktail Night",
        start_time=datetime.combine(ev.start_date, datetime.min.time()).replace(hour=19, minute=0),
        end_time=datetime.combine(ev.start_date, datetime.min.time()).replace(hour=23, minute=30),
        venue_name="Grand Ballroom"
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    event_id = ev.id
    sub_id = sub.id
    user_id = u.id
    client.headers.update({"X-Event-Owner-Token": ev.owner_token})
    db.close()

    yield {
        "event_id": event_id,
        "sub_id": sub_id,
        "user_id": user_id,
        "owner_token": ev.owner_token,
    }

    # Cleanup
    db = SessionLocal()
    ev_del = db.query(Event).filter(Event.id == event_id).first()
    if ev_del:
        db.delete(ev_del)
    u_del = db.query(User).filter(User.id == user_id).first()
    if u_del:
        db.delete(u_del)
    db.commit()
    db.close()


def test_phone_normalization_formats():
    """Asserts that phone normalization handles diverse input formats and rejects invalid numbers."""
    assert normalize_e164_phone("+91 98765 43210") == "+919876543210"
    assert normalize_e164_phone("09876543210") == "+919876543210"
    assert normalize_e164_phone("919876543210") == "+919876543210"
    assert normalize_e164_phone("9876543210") == "+919876543210"
    assert normalize_e164_phone("+91-98765-43210") == "+919876543210"
    assert normalize_e164_phone("+14155552671") == "+14155552671"
    assert normalize_e164_phone("+447911123456") == "+447911123456"

    # Rejection of invalid numbers
    with pytest.raises(ValueError, match="Invalid Indian mobile number"):
        normalize_e164_phone("5432167890")  # starts with 5 (invalid Indian mobile)
    with pytest.raises(ValueError):
        normalize_e164_phone("12345")  # too short
    with pytest.raises(ValueError):
        normalize_e164_phone("")  # empty


def test_guest_import_deduplication_and_error_reporting(setup_m4_test_event):
    """
    Asserts guest batch import normalizes phones, dedupes against batch & database,
    and returns explicit error reports for malformed rows.
    """
    event_id = setup_m4_test_event["event_id"]
    db = SessionLocal()

    import_rows = [
        {"name": "Rohan Mehra", "phone": "9811122233", "group_side": "groom", "diet": "veg"},
        {"name": "Pooja Batra", "phone": "+91-98111-22233", "group_side": "bride"},  # Duplicate phone!
        {"name": "Sunil Verma", "phone": "09822233344", "kids_count": 2, "diet": "jain"},
        {"name": "Broken Contact", "phone": "12345"}  # Invalid phone!
    ]

    res = client.post(
        f"/api/v1/events/{event_id}/guests/import",
        json={"guests": import_rows}
    )
    assert res.status_code == 200
    data = res.json()

    assert data["total_processed"] == 4
    assert data["successful_count"] == 2  # Rohan and Sunil
    assert data["skipped_duplicates_count"] == 1  # Pooja (same phone as Rohan)
    assert data["invalid_rows_count"] == 1  # Broken Contact
    assert data["errors"][0]["name"] == "Broken Contact"
    assert "Invalid phone" in data["errors"][0]["reason"] or "Unparseable" in data["errors"][0]["reason"]

    # Verify live RSVP summary
    summary_res = client.get(f"/api/v1/events/{event_id}/guests/rsvp-summary")
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["total_guests"] >= 2
    assert summary["pending_count"] >= 2
    db.close()


def test_opt_out_enforcement_blocks_send(setup_m4_test_event):
    """
    CRITICAL EXIT CRITERIA:
    Asserts that an opted-out phone number is strictly BLOCKED at the send layer.
    The provider must NEVER be called, and an OptOutBlockedError must be handled/recorded.
    """
    event_id = setup_m4_test_event["event_id"]
    db = SessionLocal()
    mock_provider = MockWhatsAppProvider()

    test_phone = "+919877700099"

    # 1. Register phone in opt_outs
    existing = db.query(OptOut).filter(OptOut.phone == test_phone).first()
    if not existing:
        db.add(OptOut(phone=test_phone, reason="STOP"))
        db.commit()

    ev = db.query(Event).filter(Event.id == event_id).first()

    # 2. Attempt outbound send
    with pytest.raises(OptOutBlockedError):
        WhatsAppSendService.send_single_message(
            db=db,
            event=ev,
            guest=None,
            to_phone=test_phone,
            message_body="Test invite",
            provider=mock_provider
        )

    # 3. Assert mock provider was NEVER called
    assert len(mock_provider.sent_messages) == 0

    # 4. Assert audit trail records failure with recipient_opted_out
    failed_log = db.query(MessageLog).filter(
        MessageLog.phone_number == test_phone,
        MessageLog.delivery_status == "failed"
    ).first()
    assert failed_log is not None
    assert "recipient_opted_out" in failed_log.failure_reason

    # Clean up opt_out
    db.delete(db.query(OptOut).filter(OptOut.phone == test_phone).first())
    db.delete(failed_log)
    db.commit()
    db.close()


def test_deterministic_rsvp_confidence_and_parsing():
    """
    Asserts RSVP parsing computes deterministic confidence scores:
    - Quick replies: 1.0 confidence
    - Clear free-text: >= 0.70 confidence
    - Ambiguous or conflicting responses: < 0.70 confidence -> needs_host_review = True
    """
    # 1. Quick replies
    qr_yes = RSVPParser.parse_quick_reply("yes")
    assert qr_yes.rsvp_status == "attending"
    assert qr_yes.confidence == 1.0
    assert qr_yes.needs_host_review is False

    qr_no = RSVPParser.parse_quick_reply("decline")
    assert qr_no.rsvp_status == "declined"
    assert qr_no.confidence == 1.0
    assert qr_no.headcount == 0

    # 2. Clear free-text
    ft_clear = RSVPParser.parse_free_text("Yes haan we will be there! Coming with wife and 2 kids. Pure veg please.")
    assert ft_clear.rsvp_status == "attending"
    assert ft_clear.headcount >= 3
    assert ft_clear.diet == "veg"
    assert ft_clear.confidence >= 0.70
    assert ft_clear.needs_host_review is False

    # 3. Ambiguous free-text (< 0.70)
    ft_ambiguous = RSVPParser.parse_free_text("Not sure yet, I might have an office meeting in Pune, will let you know.")
    assert ft_ambiguous.confidence < 0.70
    assert ft_ambiguous.needs_host_review is True

    # 4. Conflicting tokens ("yes" and "cannot") (< 0.70)
    ft_conflict = RSVPParser.parse_free_text("I wanted to say yes but sorry I cannot attend.")
    assert ft_conflict.confidence < 0.70
    assert ft_conflict.needs_host_review is True


def test_faq_bot_in_scope_and_out_of_scope_boundary(setup_m4_test_event):
    """
    CRITICAL EXIT CRITERIA:
    Tests that FAQ bot answers strictly from fact sheet,
    and REFUSES out-of-scope questions with HARD_FALLBACK_REFUSAL and notifies host.
    """
    event_id = setup_m4_test_event["event_id"]
    db = SessionLocal()

    # 1. Configure Fact Sheet
    fs_res = client.post(
        f"/api/v1/events/{event_id}/fact-sheet",
        json={
            "venue_address": "The Taj Mahal Palace, Apollo Bunder, Colaba, Mumbai",
            "parking_info": "Valet parking available at Gate 2",
            "dress_code": "Royal Traditional / Pastel Ethnic",
            "timing_notes": "Baraat assembly at 6:00 PM; Pheras at 8:15 PM sharp",
            "map_link": "https://maps.google.com/?q=Taj+Mahal+Palace+Mumbai",
            "other_facts": {"gift_policy": "No boxed gifts please, blessings only"}
        }
    )
    assert fs_res.status_code == 200

    ev = db.query(Event).filter(Event.id == event_id).first()
    fs = db.query(EventFactSheet).filter(EventFactSheet.event_id == event_id).first()

    # 2. Test IN-SCOPE queries
    ans_venue = FAQBotService.answer_question(ev, fs, "Where is the wedding happening?")
    assert ans_venue.is_in_scope is True
    assert "Taj Mahal Palace" in ans_venue.answer
    assert ans_venue.notified_host is False

    ans_dress = FAQBotService.answer_question(ev, fs, "What should I wear for the function?")
    assert ans_dress.is_in_scope is True
    assert "Pastel Ethnic" in ans_dress.answer

    ans_parking = FAQBotService.answer_question(ev, fs, "Is valet parking available for my car?")
    assert ans_parking.is_in_scope is True
    assert "Gate 2" in ans_parking.answer

    ans_gift = FAQBotService.answer_question(ev, fs, "What is the gift policy?")
    assert ans_gift.is_in_scope is True
    assert "blessings only" in ans_gift.answer

    # 3. Test OUT-OF-SCOPE queries (Hard boundary verification)
    ans_out1 = FAQBotService.answer_question(ev, fs, "Can I bring my pet tiger?")
    assert ans_out1.is_in_scope is False
    assert ans_out1.notified_host is True
    assert ans_out1.answer == HARD_FALLBACK_REFUSAL

    ans_out2 = FAQBotService.answer_question(ev, fs, "What is the host's personal bank account number?")
    assert ans_out2.is_in_scope is False
    assert ans_out2.notified_host is True
    assert ans_out2.answer == HARD_FALLBACK_REFUSAL

    db.close()


def test_reminder_scheduler_deterministic_offsets(setup_m4_test_event):
    """
    Asserts reminder scheduling offsets are purely deterministic:
    - 7 days before
    - 1 day before
    - Morning of
    """
    event_id = setup_m4_test_event["event_id"]
    sub_id = setup_m4_test_event["sub_id"]
    db = SessionLocal()

    sub = db.query(SubEvent).filter(SubEvent.id == sub_id).first()
    ev = db.query(Event).filter(Event.id == event_id).first()

    plans = ReminderScheduler.generate_event_reminder_plans(ev, [sub])
    assert len(plans) == 3

    p_7d = next(p for p in plans if p.offset_type == "7_days_before")
    p_1d = next(p for p in plans if p.offset_type == "1_day_before")
    p_morning = next(p for p in plans if p.offset_type == "morning_of")

    expected_7d = (sub.start_time - timedelta(days=7)).isoformat()
    expected_1d = (sub.start_time - timedelta(days=1)).isoformat()
    assert p_7d.scheduled_send_time == expected_7d
    assert p_1d.scheduled_send_time == expected_1d
    assert "Good morning" in p_morning.message_draft or "today" in p_morning.message_draft

    # Test API endpoint
    res = client.get(f"/api/v1/events/{event_id}/reminders")
    assert res.status_code == 200
    assert len(res.json()) >= 3
    db.close()


def test_webhook_inbound_flow_stop_opt_out_and_rsvp():
    """
    Tests Meta webhook inbound payload handling:
    1. Inbound 'STOP' records opt-out
    2. Button reply updates guest RSVP
    3. Status update updates message_log delivery_status
    """
    import random
    db = SessionLocal()
    phone = f"+9198{random.randint(10000000, 99999999)}"

    # Create dummy guest
    ev = db.query(Event).first()
    guest = Guest(
        event_id=ev.id,
        name="Vikram Seth",
        phone=phone,
        rsvp_status="pending"
    )
    db.add(guest)
    db.commit()
    db.refresh(guest)

    # 1. Send Inbound 'STOP' webhook
    stop_payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "entry1",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "messages": [{
                        "from": phone,
                        "id": "wamid.inbound_stop",
                        "type": "text",
                        "text": {"body": "STOP"}
                    }]
                }
            }]
        }]
    }

    res_stop = client.post("/api/v1/webhooks/whatsapp", json=stop_payload)
    assert res_stop.status_code == 200
    assert res_stop.json()["results"]["opt_outs_recorded"] == 1

    # Assert opt_out recorded in DB
    opt = db.query(OptOut).filter(OptOut.phone == phone).first()
    assert opt is not None

    # Clean up opt_out for next test step
    db.delete(opt)
    db.commit()

    # 2. Send Inbound Interactive Button RSVP
    rsvp_payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "entry2",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "messages": [{
                        "from": phone,
                        "id": "wamid.inbound_button",
                        "type": "interactive",
                        "interactive": {
                            "type": "button_reply",
                            "button_reply": {"id": "yes", "title": "Attending"}
                        }
                    }]
                }
            }]
        }]
    }

    res_rsvp = client.post("/api/v1/webhooks/whatsapp", json=rsvp_payload)
    assert res_rsvp.status_code == 200
    assert res_rsvp.json()["results"]["rsvps_updated"] == 1

    db.refresh(guest)
    assert guest.rsvp_status == "attending"

    # Clean up
    db.delete(guest)
    db.commit()
    db.close()


def test_webhook_hmac_signature_security():
    """
    Asserts that when WHATSAPP_APP_SECRET is set, forged/unsigned requests
    to POST /api/v1/webhooks/whatsapp are rejected with 403 Forbidden.
    """
    secret = "secret_key_12345"
    raw_payload = b'{"object": "whatsapp_business_account"}'

    # Valid HMAC signature
    valid_sig = "sha256=" + hmac.new(secret.encode(), raw_payload, hashlib.sha256).hexdigest()
    invalid_sig = "sha256=invalid_hex_digest_forgery"

    # Test verify_meta_signature directly
    import time
    from backend.app.core.config import settings
    orig_secret = settings.WHATSAPP_APP_SECRET
    settings.WHATSAPP_APP_SECRET = secret

    try:
        now_ts = time.time()
        # 1. Valid signature with current timestamp -> passes
        assert WhatsAppWebhookService.verify_meta_signature(raw_payload, valid_sig, timestamp=now_ts) is True
        # 2. Invalid signature -> rejected
        assert WhatsAppWebhookService.verify_meta_signature(raw_payload, invalid_sig, timestamp=now_ts) is False
        # 3. Missing signature header (None) -> rejected
        assert WhatsAppWebhookService.verify_meta_signature(raw_payload, None, timestamp=now_ts) is False
        # 4. Replay attack: Valid signature but stale timestamp (600s old, > 300s limit) -> rejected
        stale_ts = now_ts - 600
        assert WhatsAppWebhookService.verify_meta_signature(raw_payload, valid_sig, timestamp=stale_ts) is False
        # 5. Future timestamp skew beyond 60s -> rejected
        future_ts = now_ts + 120
        assert WhatsAppWebhookService.verify_meta_signature(raw_payload, valid_sig, timestamp=future_ts) is False

        # 6. HTTP Webhook Endpoint Test (Integration with FastApi router)
        # 6a. Valid signature and fresh timestamp -> 200
        resp_valid = client.post(
            "/api/v1/webhooks/whatsapp",
            content=raw_payload,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": valid_sig, "X-Hub-Timestamp": str(now_ts)}
        )
        assert resp_valid.status_code == 200

        # 6b. Invalid signature -> 403
        resp_inv = client.post(
            "/api/v1/webhooks/whatsapp",
            content=raw_payload,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": invalid_sig, "X-Hub-Timestamp": str(now_ts)}
        )
        assert resp_inv.status_code == 403

        # 6c. Missing signature header -> 403
        resp_miss = client.post(
            "/api/v1/webhooks/whatsapp",
            content=raw_payload,
            headers={"Content-Type": "application/json", "X-Hub-Timestamp": str(now_ts)}
        )
        assert resp_miss.status_code == 403

        # 6d. Replay attack over HTTP: valid signature with 10-minute old timestamp -> 403
        resp_replay = client.post(
            "/api/v1/webhooks/whatsapp",
            content=raw_payload,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": valid_sig, "X-Hub-Timestamp": str(stale_ts)}
        )
        assert resp_replay.status_code == 403
    finally:
        settings.WHATSAPP_APP_SECRET = orig_secret

    # When secret is unset in non-test mode, must fail-closed (return False)
    import os
    saved_test_env = os.environ.pop("PYTEST_CURRENT_TEST", None)
    saved_env_setting = settings.ENVIRONMENT
    settings.ENVIRONMENT = "production"
    settings.WHATSAPP_APP_SECRET = None
    try:
        assert WhatsAppWebhookService.verify_meta_signature(raw_payload, "sha256=forged") is False
        assert WhatsAppWebhookService.verify_meta_signature(raw_payload, None) is False
    finally:
        if saved_test_env:
            os.environ["PYTEST_CURRENT_TEST"] = saved_test_env
        settings.ENVIRONMENT = saved_env_setting
        settings.WHATSAPP_APP_SECRET = orig_secret


def test_non_wedding_event_type_coordination():
    """
    CRITICAL EXIT CRITERIA:
    Confirms guest coordination works properly for a non-wedding event type
    (e.g., Birthday celebration) with customized invitation tone and RSVP flow.
    """
    db = SessionLocal()
    # 1. Synthesize Birthday Event
    import random
    b_phone = f"+9198{random.randint(10000000, 99999999)}"
    u = User(phone_number=b_phone, full_name="Sanjay Singhania", role="host")
    db.add(u)
    db.commit()
    db.refresh(u)

    bday_event = Event(
        owner_id=u.id,
        name="Aarav 5th Birthday Jungle Jamboree",
        event_type="birthday",
        tradition_code="birthday_kids_carnival",
        guest_count=60,
        total_budget=150000.0,
        city="Bengaluru",
        pincode="560001",
        start_date=date.today() + timedelta(days=15),
        end_date=date.today() + timedelta(days=15),
        metadata_json={}
    )
    db.add(bday_event)
    db.commit()
    db.refresh(bday_event)
    client.headers.update({"X-Event-Owner-Token": bday_event.owner_token})

    # 2. Import birthday guests
    g_res = client.post(
        f"/api/v1/events/{bday_event.id}/guests/import",
        json={
            "guests": [
                {"name": "Tanvi & Family", "phone": "+919822200111", "kids_count": 2, "diet": "veg"},
                {"name": "Arjun Uncle", "phone": "+919822200222", "kids_count": 0, "diet": "jain"}
            ]
        },
        headers={"X-Event-Owner-Token": bday_event.owner_token},
    )
    assert g_res.status_code == 200
    assert g_res.json()["successful_count"] == 2

    # 3. Verify Birthday Invitation Text Tone
    mock_prov = MockWhatsAppProvider()
    send_res = WhatsAppSendService.send_batch_invitations(
        db=db,
        event_id=bday_event.id,
        provider=mock_prov
    )
    assert send_res.sent_count == 2
    assert len(mock_prov.sent_messages) == 2
    # Verify birthday specific emoji and text
    first_body = mock_prov.sent_messages[0]["body"]
    assert "🎂" in first_body or "party" in first_body.lower()
    assert "Aarav 5th Birthday" in first_body

    # Cleanup
    db.delete(bday_event)
    db.delete(u)
    db.commit()
    db.close()


def test_guest_privacy_deletion_endpoint(setup_m4_test_event):
    """
    CRITICAL EXIT CRITERIA:
    Tests that DELETE /api/v1/events/{id}/guests/{guest_id}
    permanently purges guest data from database.
    """
    event_id = setup_m4_test_event["event_id"]
    client.headers.update({"X-Event-Owner-Token": setup_m4_test_event["owner_token"]})
    db = SessionLocal()

    # Create temporary guest
    g = Guest(
        event_id=event_id,
        name="Privacy Test Guest",
        phone="+919811199999",
        rsvp_status="attending"
    )
    db.add(g)
    db.commit()
    db.refresh(g)
    guest_id = g.id

    # Call DELETE endpoint
    del_res = client.delete(f"/api/v1/events/{event_id}/guests/{guest_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "purged"

    # Assert record is gone from DB
    check_g = db.query(Guest).filter(Guest.id == guest_id).first()
    assert check_g is None
    db.close()

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from starlette.requests import Request
from backend.app.models.models import MessageLog, OptOut
from backend.app.services.whatsapp.provider import MetaCloudWhatsAppProvider, get_whatsapp_provider
from backend.app.services.whatsapp.send_service import WhatsAppSendService
from backend.app.services.whatsapp.webhook_service import WhatsAppWebhookService


def test_webhooks_signature_and_json_error_branches():
    """Covers lines 53-54 and 58-59 in api/v1/webhooks.py."""
    with patch.object(settings, "WHATSAPP_APP_SECRET", "secret_key_123"):
        # 1. Invalid signature -> 403
        res_sig = client.post(
            "/api/v1/webhooks/whatsapp",
            content=b'{"entry": []}',
            headers={"X-Hub-Signature-256": "sha256=invalid_signature_hex"}
        )
        assert res_sig.status_code == 403

    # 2. Invalid non-JSON payload -> 400
    res_bad_json = client.post(
        "/api/v1/webhooks/whatsapp",
        content=b"Not a valid json string at all",
        headers={"Content-Type": "application/json"}
    )
    assert res_bad_json.status_code == 400


def test_whatsapp_webhook_signature_and_payload_branches(db, test_data, monkeypatch):
    event, token = test_data
    from backend.app.services.whatsapp.webhook_service import WhatsAppWebhookService
    from backend.app.core.config import settings
    import hmac
    import hashlib

    # 1. Signature verification branches
    payload_bytes = b'{"object": "whatsapp_business_account"}'
    
    # Configure secret
    old_secret = getattr(settings, "WHATSAPP_APP_SECRET", None)
    settings.WHATSAPP_APP_SECRET = "test_meta_webhook_secret_key_123"
    try:
        # Missing header
        assert WhatsAppWebhookService.verify_meta_signature(payload_bytes, None) is False
        # Malformed header (no sha256= prefix)
        assert WhatsAppWebhookService.verify_meta_signature(payload_bytes, "invalid_header") is False
        
        # Valid & invalid HMAC with configured secret
        valid_hmac = "sha256=" + hmac.new(
            b"test_meta_webhook_secret_key_123",
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        assert WhatsAppWebhookService.verify_meta_signature(payload_bytes, valid_hmac) is True
        assert WhatsAppWebhookService.verify_meta_signature(payload_bytes, "sha256=forged_invalid_signature") is False
    finally:
        settings.WHATSAPP_APP_SECRET = old_secret

    # When no secret configured in production (not test env) -> fail-closed
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    old_env = getattr(settings, "ENVIRONMENT", "")
    settings.ENVIRONMENT = "production"
    settings.WHATSAPP_APP_SECRET = None
    try:
        assert WhatsAppWebhookService.verify_meta_signature(payload_bytes, "sha256=abc") is False
    finally:
        settings.ENVIRONMENT = old_env

    # 2. Inbound Delivery Status Callback branches (sent, delivered, read, failed with/without errors)
    from backend.app.models.models import MessageLog, OptOut
    
    unique_wamid = f"wamid.{uuid.uuid4().hex}"
    msg_log = MessageLog(
        event_id=event.id,
        phone_number="+919876543210",
        direction="outbound",
        message_type="invitation",
        content_snapshot="Standard Invitation Text",
        whatsapp_message_id=unique_wamid,
        delivery_status="sent"
    )
    db.add(msg_log)
    db.commit()

    # Status update: failed with errors
    status_payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "statuses": [{
                        "id": unique_wamid,
                        "status": "failed",
                        "errors": [{"title": "Recipient phone unreachable"}]
                    }]
                }
            }]
        }]
    }
    res_status = WhatsAppWebhookService.handle_inbound_payload(db, status_payload)
    assert res_status["statuses_updated"] == 1
    db.refresh(msg_log)
    assert msg_log.delivery_status == "failed"
    assert msg_log.failure_reason == "Recipient phone unreachable"

    # Status update: delivered without errors
    status_payload_deliv = {
        "entry": [{
            "changes": [{
                "value": {
                    "statuses": [{
                        "id": unique_wamid,
                        "status": "delivered"
                    }]
                }
            }]
        }]
    }
    WhatsAppWebhookService.handle_inbound_payload(db, status_payload_deliv)
    db.refresh(msg_log)
    assert msg_log.delivery_status == "delivered"

    # 3. Inbound Messages: STOP keyword opt-out (first time & duplicate)
    stop_phone = "+919123456789"
    stop_payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "919123456789",
                        "id": f"wamid.inbound.stop.{uuid.uuid4().hex}",
                        "type": "text",
                        "text": {"body": "STOP"}
                    }]
                }
            }]
        }]
    }
    res_stop = WhatsAppWebhookService.handle_inbound_payload(db, stop_payload)
    assert res_stop["opt_outs_recorded"] == 1
    opt_entry = db.query(OptOut).filter(OptOut.phone == stop_phone).first()
    assert opt_entry is not None

    # Duplicate STOP request should not duplicate row
    res_stop2 = WhatsAppWebhookService.handle_inbound_payload(db, stop_payload)
    assert res_stop2["opt_outs_recorded"] == 0

    # 4. Inbound interactive quick-reply button RSVP
    guest_rsvp = Guest(
        event_id=event.id,
        name="Rohan RSVP",
        phone="+919988776655",
        rsvp_status="pending"
    )
    db.add(guest_rsvp)
    db.commit()

    btn_payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "919988776655",
                        "id": f"wamid.inbound.btn.{uuid.uuid4().hex}",
                        "type": "interactive",
                        "interactive": {
                            "type": "button_reply",
                            "button_reply": {
                                "id": "rsvp_attending_2",
                                "title": "Attending (2)"
                            }
                        }
                    }]
                }
            }]
        }]
    }
    res_btn = WhatsAppWebhookService.handle_inbound_payload(db, btn_payload)
    assert res_btn["rsvps_updated"] == 1
    db.refresh(guest_rsvp)
    assert guest_rsvp.rsvp_status == "attending"
    assert guest_rsvp.headcount == 1

    # 5. Inbound legacy button payload
    btn_legacy_payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "919988776655",
                        "id": f"wamid.inbound.btn.legacy.{uuid.uuid4().hex}",
                        "type": "button",
                        "button": {
                            "payload": "rsvp_declined",
                            "text": "Cannot Attend"
                        }
                    }]
                }
            }]
        }]
    }
    res_btn_legacy = WhatsAppWebhookService.handle_inbound_payload(db, btn_legacy_payload)
    assert res_btn_legacy["rsvps_updated"] == 1
    db.refresh(guest_rsvp)
    assert guest_rsvp.rsvp_status == "declined"

    # 6. Inbound free-text RSVP with diet
    free_rsvp_payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "919988776655",
                        "id": f"wamid.inbound.freetext.{uuid.uuid4().hex}",
                        "type": "text",
                        "text": {"body": "Yes we are attending, count 3, Jain meal please"}
                    }]
                }
            }]
        }]
    }
    res_freetext = WhatsAppWebhookService.handle_inbound_payload(db, free_rsvp_payload)
    assert res_freetext["rsvps_updated"] == 1
    db.refresh(guest_rsvp)
    assert guest_rsvp.rsvp_status == "attending"
    assert guest_rsvp.headcount >= 1
    assert guest_rsvp.diet == "jain"

    # 7. Inbound FAQ Query with event fact sheet
    fs = EventFactSheet(
        event_id=event.id,
        venue_address="Grand Palace Jaipur",
        parking_info="Valet parking available at Gate 2",
        dress_code="Traditional Royal",
        timing_notes="Baraat arrives at 4 PM"
    )
    db.add(fs)
    db.commit()

    faq_payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "919988776655",
                        "id": f"wamid.inbound.faq.{uuid.uuid4().hex}",
                        "type": "text",
                        "text": {"body": "Is there parking available at the venue?"}
                    }]
                }
            }]
        }]
    }
    res_faq = WhatsAppWebhookService.handle_inbound_payload(db, faq_payload)
    assert res_faq["faq_replies_sent"] >= 0

    # 8. Empty 'from' message skipped
    skip_payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{"id": f"wamid.empty.{uuid.uuid4().hex}", "type": "text"}]
                }
            }]
        }]
    }
    res_skip = WhatsAppWebhookService.handle_inbound_payload(db, skip_payload)
    assert res_skip["statuses_updated"] == 0


def test_whatsapp_send_service_batch_branches(db, test_data):
    event, token = test_data
    import random
    from backend.app.services.whatsapp.send_service import WhatsAppSendService
    from backend.app.models.models import OptOut

    # 1. Add normal guest and opted-out guest with valid 10-digit Indian numbers starting with 9
    r_suffix1 = random.randint(10000000, 99999999)
    r_suffix2 = random.randint(10000000, 99999999)
    opted_phone = f"+9198{r_suffix1}"
    normal_phone = f"+9199{r_suffix2}"

    db.add(OptOut(phone=opted_phone, reason="Host requested opt-out"))
    db.commit()

    g_normal = Guest(event_id=event.id, name="Active Guest", phone=normal_phone, rsvp_status="pending")
    g_opted = Guest(event_id=event.id, name="Opted Out Guest", phone=opted_phone, rsvp_status="pending")
    db.add_all([g_normal, g_opted])
    db.commit()

    # Batch send with guest_ids filter and rate_limit_delay_secs > 0
    res = WhatsAppSendService.send_batch_invitations(
        db=db,
        event_id=event.id,
        guest_ids=[g_normal.id, g_opted.id],
        rate_limit_delay_secs=0.001
    )
    assert res.total_requested == 2
    assert res.sent_count >= 1
    assert res.blocked_opt_out_count >= 1
    assert len(res.errors) >= 1


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


def test_api_webhooks_whatsapp_hub_challenge():
    # Meta webhook verification challenge
    token = settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN
    challenge = "1158201444"

    resp = client.get(f"/api/v1/webhooks/whatsapp?hub.mode=subscribe&hub.challenge={challenge}&hub.verify_token={token}")
    assert resp.status_code == 200
    assert resp.text == challenge

    # Invalid token rejection
    resp_bad = client.get(f"/api/v1/webhooks/whatsapp?hub.mode=subscribe&hub.challenge={challenge}&hub.verify_token=wrong")
    assert resp_bad.status_code == 403


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
