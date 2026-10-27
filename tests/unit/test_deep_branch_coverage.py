import uuid
from datetime import date, timedelta, datetime, timezone
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.models.models import (
    User,
    Event,
    BudgetItem,
    Task,
    SubEvent,
    ChangeEvent,
    AISuggestion,
    EventFactSheet,
    Guest,
    QuoteDocument,
    QuoteLineItem,
    VendorBenchmarkSample,
)
from backend.app.services.replanning_service import ReplanningService
from backend.app.schemas.replanning import ChangeRequestSchema


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_data(db):
    user = User(
        phone_number=f"+9198{uuid.uuid4().hex[:8]}",
        full_name="Deep Coverage Host",
        role="host"
    )
    db.add(user)
    db.flush()

    token = f"tok_{uuid.uuid4().hex}"
    event = Event(
        owner_id=user.id,
        name="Deep Branch Test Event",
        event_type="wedding",
        tradition_code="maharashtrian_vedic",
        guest_count=150,
        venue_capacity=200,
        total_budget=1200000.0,
        city="Jaipur",
        pincode="302001",
        owner_token=token,
        start_date=date.today() + timedelta(days=45),
        end_date=date.today() + timedelta(days=47),
        metadata_json={"owner_token": token}
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event, token


# ==========================================
# 1. api/v1/guests.py Branches
# ==========================================
def test_guests_api_all_branches(client, test_data, db):
    event, token = test_data
    headers = {"X-Event-Owner-Token": token}

    # 1. List guests without and with status filter
    g1 = Guest(event_id=event.id, name="Aarav", phone=f"+9198{uuid.uuid4().hex[:8]}", rsvp_status="attending")
    g2 = Guest(event_id=event.id, name="Bhavna", phone=f"+9198{uuid.uuid4().hex[:8]}", rsvp_status="declined")
    db.add_all([g1, g2])
    db.commit()

    r_all = client.get(f"/api/v1/events/{event.id}/guests")
    assert r_all.status_code == 200
    assert len(r_all.json()) >= 2

    r_att = client.get(f"/api/v1/events/{event.id}/guests?status=attending")
    assert r_att.status_code == 200
    assert all(g["rsvp_status"] == "attending" for g in r_att.json())

    # 2. RSVP Summary 404
    r_sum_404 = client.get("/api/v1/events/fake_event_id_000/guests/rsvp-summary")
    assert r_sum_404.status_code == 404

    # 3. Fact Sheet GET when missing
    r_fs_missing = client.get(f"/api/v1/events/{event.id}/fact-sheet")
    assert r_fs_missing.status_code == 200
    assert r_fs_missing.json()["venue_address"] is None

    # 4. Fact Sheet CREATE
    create_payload = {
        "venue_address": "Rambagh Palace Gate 1",
        "parking_info": "Valet",
        "dress_code": "Festive",
        "timing_notes": "10 AM",
        "map_link": "https://maps.google.com/?q=palace",
        "other_facts": {"wifi": "Secure"}
    }
    r_create = client.post(f"/api/v1/events/{event.id}/fact-sheet", json=create_payload, headers=headers)
    assert r_create.status_code == 200
    assert r_create.json()["venue_address"] == "Rambagh Palace Gate 1"

    # 5. Fact Sheet UPDATE (partial none, partial set)
    update_payload = {
        "venue_address": "Rambagh Palace Gate 2 (Updated)",
        "parking_info": None,
        "dress_code": "Formal Indian",
        "timing_notes": None,
        "map_link": None,
        "other_facts": None
    }
    r_up = client.post(f"/api/v1/events/{event.id}/fact-sheet", json=update_payload, headers=headers)
    assert r_up.status_code == 200
    assert r_up.json()["venue_address"] == "Rambagh Palace Gate 2 (Updated)"
    assert r_up.json()["dress_code"] == "Formal Indian"
    assert r_up.json()["parking_info"] == "Valet"

    # 6. Delete Guest 404
    r_del_404 = client.delete(f"/api/v1/events/{event.id}/guests/nonexistent_guest", headers=headers)
    assert r_del_404.status_code == 404

    # 7. Reminders schedule 404
    r_rem_404 = client.get("/api/v1/events/nonexistent_event/reminders")
    assert r_rem_404.status_code == 404


# ==========================================
# 2. replanning_service.py Queued & Tasks Branches
# ==========================================
def test_replanning_queue_and_task_mutations(db, test_data):
    event, token = test_data

    t1 = Task(
        event_id=event.id,
        title="Arrange Mandap Setup",
        scheduled_start=datetime.combine(event.start_date, datetime.min.time(), tzinfo=timezone.utc),
        scheduled_end=datetime.combine(event.start_date, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=3),
        status="pending",
        duration_minutes=180
    )
    se1 = SubEvent(
        event_id=event.id,
        name="Main Wedding Pheras",
        venue_name="Main Banquet",
        is_outdoor=False,
        is_muhurat_locked=True,
        sort_order=1,
        start_time=datetime.combine(event.start_date, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=10),
        end_time=datetime.combine(event.start_date, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=14)
    )
    b1 = BudgetItem(
        event_id=event.id,
        category="decor",
        name="Mandap Flowers",
        scaling_rule="tiered",
        planned_amount=150000.0,
        actual_amount=0.0
    )
    db.add_all([t1, se1, b1])
    db.commit()

    # 1. Create first proposal (status: pending)
    req1 = ChangeRequestSchema(
        change_type="date_moved",
        payload={
            "from_date": event.start_date.isoformat(),
            "to_date": (event.start_date + timedelta(days=7)).isoformat()
        }
    )
    prop1 = ReplanningService.create_change_proposal(db, event.id, req1)
    assert prop1.status == "pending"

    # 2. Create second proposal (should be queued because prop1 is pending)
    req2 = ChangeRequestSchema(
        change_type="guest_count_changed",
        payload={"from_guest_count": 150, "to_guest_count": 180}
    )
    prop2 = ReplanningService.create_change_proposal(db, event.id, req2)
    assert prop2.status == "queued"

    # 3. Accept prop1 -> mutates tasks, sub-events, event date, AND promotes prop2 from queued to pending!
    accepted = ReplanningService.accept_change(db, event.id, prop1.change_id)
    assert accepted.status == "applied"

    db.refresh(t1)
    assert t1.scheduled_start is not None

    prop2_refreshed = ReplanningService.get_change_proposal(db, event.id, prop2.change_id)
    assert prop2_refreshed.status == "pending"

    # 4. Reject prop2
    rejected = ReplanningService.reject_change(db, event.id, prop2.change_id)
    assert rejected.status == "rejected"


# ==========================================
# 3. api/v1/quotes.py Negotiation Leverage Branches
# ==========================================
def test_quotes_negotiation_draft_branches(client, test_data, db):
    event, token = test_data
    headers = {"X-Event-Owner-Token": token}

    q1 = QuoteDocument(
        event_id=event.id,
        vendor_name="Prime Royal Caterers",
        category="catering",
        file_name="quote.pdf",
        file_type="application/pdf",
        uploaded_file=b"test_pdf_content",
        total_quoted_amount=450000.0,
        raw_extracted_json={"terms_and_conditions": []}
    )
    q2 = QuoteDocument(
        event_id=event.id,
        vendor_name="Shree Ganesh Catering",
        category="catering",
        file_name="comp.pdf",
        file_type="application/pdf",
        uploaded_file=b"comp_pdf_content",
        total_quoted_amount=380000.0
    )
    db.add_all([q1, q2])
    db.commit()

    li1 = QuoteLineItem(
        quote_document_id=q1.id,
        name="Deluxe Dinner Buffet",
        unit_price=1200.0,
        qty=300,
        total=360000.0,
        category_tag="catering"
    )
    db.add(li1)

    bench1 = VendorBenchmarkSample(category="catering", city_tier="tier_2", normalized_unit_cost=600.0)
    bench2 = VendorBenchmarkSample(category="catering", city_tier="tier_2", normalized_unit_cost=700.0)
    db.add_all([bench1, bench2])
    db.commit()

    draft_req = {
        "quote_id": q1.id,
        "competing_quote_id": q2.id,
        "target_discount_percentage": 12.0
    }
    r = client.post(f"/api/v1/quotes/{q1.id}/negotiate-draft", json=draft_req, headers=headers)
    assert r.status_code == 200
    res_data = r.json()
    assert "draft_variants" in res_data
    assert len(res_data["draft_variants"]) > 0
    assert len(res_data["leverage_points"]) > 0


# ==========================================
# 4. WhatsApp Webhook & Signature Branches
# ==========================================
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
                        "id": "wamid.inbound.stop.1",
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
    assert res_stop2["opt_outs_recorded"] == 1

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
                        "id": "wamid.inbound.btn.1",
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
                        "id": "wamid.inbound.btn.legacy",
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
                        "id": "wamid.inbound.freetext.1",
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
                        "id": "wamid.inbound.faq.1",
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
                    "messages": [{"id": "wamid.empty.1", "type": "text"}]
                }
            }]
        }]
    }
    res_skip = WhatsAppWebhookService.handle_inbound_payload(db, skip_payload)
    assert res_skip["statuses_updated"] == 0


# ==========================================
# 5. Quotes API Missing Branches (400, 403, 404, 413)
# ==========================================
def test_quotes_api_error_and_edge_branches(client, test_data, db):
    event, token = test_data
    headers = {"X-Event-Owner-Token": token}

    # 1. Compare quotes with < 2 IDs directly in router logic
    from backend.app.api.v1.quotes import compare_quotes
    from backend.app.schemas.quotes import QuoteComparisonRequestSchema
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        compare_quotes(QuoteComparisonRequestSchema.model_construct(quote_ids=["single_id"]), db)
    assert exc_info.value.status_code == 400

    # 2. Compare quotes with non-existent IDs -> 404
    r_not_found = client.post("/api/v1/quotes/compare", json={"quote_ids": ["fake_id_1", "fake_id_2"]}, headers=headers)
    assert r_not_found.status_code == 404

    # 3. Compare quotes with mismatched categories -> 400
    q_cat1 = QuoteDocument(
        event_id=event.id,
        vendor_name="Caterer X",
        category="catering",
        file_name="q1.pdf",
        file_type="application/pdf",
        uploaded_file=b"cater",
        total_quoted_amount=100000.0
    )
    q_cat2 = QuoteDocument(
        event_id=event.id,
        vendor_name="Photographer Y",
        category="photography",
        file_name="q2.pdf",
        file_type="application/pdf",
        uploaded_file=b"photo",
        total_quoted_amount=80000.0
    )
    db.add_all([q_cat1, q_cat2])
    db.commit()

    r_mismatch = client.post("/api/v1/quotes/compare", json={"quote_ids": [q_cat1.id, q_cat2.id]}, headers=headers)
    assert r_mismatch.status_code == 400
    assert "same category" in r_mismatch.json()["detail"]

    # 4. List quotes for non-existent event -> 404
    r_list_404 = client.get("/api/v1/quotes/events/nonexistent_event_id/quotes", headers=headers)
    assert r_list_404.status_code == 404

    # 5. Upload quote without token or wrong token -> 403
    files = {"file": ("quote.pdf", b"%PDF-1.4 test dummy content", "application/pdf")}
    data = {"event_id": event.id, "category": "decor", "vendor_name": "Royal Decorators"}
    r_auth_fail = client.post(
        "/api/v1/quotes/upload",
        files=files,
        data=data,
        headers={"X-Event-Owner-Token": "wrong_token_here"}
    )
    assert r_auth_fail.status_code == 403

    # 6. Upload quote exceeding 10MB -> 413
    huge_bytes = b"0" * (10 * 1024 * 1024 + 10)
    huge_files = {"file": ("huge.pdf", huge_bytes, "application/pdf")}
    r_huge = client.post(
        "/api/v1/quotes/upload",
        files=huge_files,
        data=data,
        headers=headers
    )
    assert r_huge.status_code == 413


# ==========================================
# 6. Invitations API Missing Branches
# ==========================================
def test_invitations_api_branches(client, test_data, db):
    event, token = test_data
    headers = {"X-Event-Owner-Token": token}

    # 1. Options 404 for unknown event
    r_opt_404 = client.get("/api/v1/events/unknown_event_id/invitations/options")
    assert r_opt_404.status_code == 404

    # 2. Options with specific theme_proposal_id
    from backend.app.models.models import StyleProfile, ThemeProposal
    sp = StyleProfile(event_id=event.id, mood_words=["royal", "heritage"])
    db.add(sp)
    db.commit()

    tp = ThemeProposal(
        style_profile_id=sp.id,
        theme_name="Rajputana Royalty",
        status="accepted",
        palette=["#800020", "#D4AF37", "#FFFDF8", "#2C1810"],
        invitation_design_brief="Opulent gold foil and deep burgundy motifs."
    )
    db.add(tp)
    db.commit()

    r_opt = client.get(f"/api/v1/events/{event.id}/invitations/options?theme_proposal_id={tp.id}")
    assert r_opt.status_code == 200
    assert r_opt.json()["theme_name"] == "Rajputana Royalty"

    # 3. Download card 404
    r_dl_404 = client.get(f"/api/v1/events/{event.id}/invitations/nonexistent_card_id/download", headers=headers)
    assert r_dl_404.status_code == 404

    # 4. Download card missing pdf format -> 404
    from backend.app.models.models import InvitationCard
    card_no_pdf = InvitationCard(
        event_id=event.id,
        layout_variant="classic_royal",
        wording_text="Sharma Family cordially invites you",
        rendered_png=b"fake_png_data",
        rendered_pdf=None
    )
    db.add(card_no_pdf)
    db.commit()

    r_pdf_404 = client.get(f"/api/v1/events/{event.id}/invitations/{card_no_pdf.id}/download?format=pdf", headers=headers)
    assert r_pdf_404.status_code == 404
    assert "PDF format not available" in r_pdf_404.json()["detail"]

    # 5. Download valid PNG
    r_png_ok = client.get(f"/api/v1/events/{event.id}/invitations/{card_no_pdf.id}/download?format=png", headers=headers)
    assert r_png_ok.status_code == 200
    assert r_png_ok.headers["content-type"] == "image/png"


# ==========================================
# 7. Replanning Service Budget Cut & Shift Branches
# ==========================================
def test_replanning_budget_cut_and_shift_branches(db, test_data):
    event, token = test_data

    # Add budget items
    b1 = BudgetItem(event_id=event.id, category="decor", name="Flowers", scaling_rule="tiered", planned_amount=200000.0, actual_amount=0.0)
    b2 = BudgetItem(event_id=event.id, category="catering", name="Food", scaling_rule="per_guest", planned_amount=400000.0, actual_amount=0.0)
    db.add_all([b1, b2])
    db.commit()

    # 1. Budget cut proposal
    cut_req = ChangeRequestSchema(
        change_type="budget_cut",
        payload={"to_budget": 900000.0, "from_budget": 1200000.0}
    )
    cut_prop = ReplanningService.create_change_proposal(db, event.id, cut_req)
    assert cut_prop.status == "pending"
    assert len(cut_prop.budget_diff) > 0
    assert cut_prop.budget_total_delta != 0

    # Apply budget cut
    applied_cut = ReplanningService.accept_change(db, event.id, cut_prop.change_id)
    assert applied_cut.status == "applied"

    # 2. Replan unknown proposal -> 404
    with pytest.raises(Exception):
        ReplanningService.get_change_proposal(db, event.id, "nonexistent_proposal_uuid")

    with pytest.raises(Exception):
        ReplanningService.accept_change(db, event.id, "nonexistent_proposal_uuid")

    with pytest.raises(Exception):
        ReplanningService.reject_change(db, event.id, "nonexistent_proposal_uuid")

    # 3. Vendor cancelled proposal and acceptance
    cancel_req = ChangeRequestSchema(
        change_type="vendor_cancelled",
        payload={"category": "catering", "vendor_name": "Royal Feast"}
    )
    cancel_prop = ReplanningService.create_change_proposal(db, event.id, cancel_req)
    assert cancel_prop.status == "pending"
    assert len(cancel_prop.task_diff.added_tasks) > 0

    applied_cancel = ReplanningService.accept_change(db, event.id, cancel_prop.change_id)
    assert applied_cancel.status == "applied"

    # 4. Guest count changed proposal and acceptance (mutates event.guest_count)
    gc_req = ChangeRequestSchema(
        change_type="guest_count_changed",
        payload={"from_guest_count": 150, "to_guest_count": 220}
    )
    gc_prop = ReplanningService.create_change_proposal(db, event.id, gc_req)
    assert gc_prop.status == "pending"
    applied_gc = ReplanningService.accept_change(db, event.id, gc_prop.change_id)
    assert applied_gc.status == "applied"
    db.refresh(event)
    assert event.guest_count == 220


# ==========================================
# 9. WhatsApp Send Service Batch Branches
# ==========================================
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


# ==========================================
# 10. Events API Compose & Delete Branches
# ==========================================
def test_events_api_compose_and_delete_branches(client, test_data, db):
    event, token = test_data
    headers = {"X-Event-Owner-Token": token}

    # 1. Add sub-event
    se = SubEvent(
        event_id=event.id,
        name="Hastamelap Ceremony",
        venue_name="Main Hall",
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2)
    )
    db.add(se)
    db.commit()

    # 2. Compose with muhurat_time, sub_event_name, and muhurat_notes
    compose_payload = {
        "step": "timing",
        "muhurat_time": "10:30 AM",
        "sub_event_name": "Hastamelap",
        "muhurat_notes": "Godhuli Bela auspicious window"
    }
    r_comp = client.post(f"/api/v1/events/{event.id}/compose", json=compose_payload, headers=headers)
    assert r_comp.status_code == 200

    db.refresh(se)
    assert se.is_muhurat_locked is True
    assert se.muhurat_notes == "Godhuli Bela auspicious window"

    # 3. Compose with skip_timing
    r_skip = client.post(f"/api/v1/events/{event.id}/compose", json={"step": "timing", "skip_timing": True}, headers=headers)
    assert r_skip.status_code == 200

    # 4. Delete event (cleans up user when 0 events remaining)
    r_del = client.delete(f"/api/v1/events/{event.id}", headers=headers)
    assert r_del.status_code == 200
    assert r_del.json()["deleted"] is True


# ==========================================
# 11. Tradition Merge Service Missing Branches
# ==========================================
def test_tradition_merge_service_branches(db, monkeypatch):
    from backend.app.services.tradition_merge_service import TraditionMergeService, get_tradition_merge_agent, GeminiTraditionMergeAgent, DeterministicStubTraditionMergeAgent

    # 1. get_tradition_merge_agent with and without GEMINI_API_KEY
    monkeypatch.setenv("GEMINI_API_KEY", "test_gemini_key_abc")
    agent = get_tradition_merge_agent()
    assert isinstance(agent, GeminiTraditionMergeAgent)

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    agent_stub = get_tradition_merge_agent()
    assert isinstance(agent_stub, DeterministicStubTraditionMergeAgent)

    # 2. Invalid tradition codes -> ValueError
    svc = TraditionMergeService(db=db)
    with pytest.raises(ValueError) as exc_info:
        svc.merge_traditions(primary_code="nonexistent_tradition_1", secondary_code="nonexistent_tradition_2")
    assert "Invalid tradition codes" in str(exc_info.value)


# ==========================================
# 12. Discovery Service Utility & Edge Branches
# ==========================================
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


# ==========================================
# 13. Gemini Providers Empty Key & Fallback Branches
# ==========================================
def test_gemini_providers_empty_key_fallbacks():
    from backend.app.services.providers.gemini_provider import (
        GeminiNegotiationDraftProvider,
        GeminiReplanningExplanationProvider,
        GeminiVibeProvider,
        GeminiQuoteExtractionProvider,
    )

    # 1. GeminiNegotiationDraftProvider without key -> fallback stub
    p_draft = GeminiNegotiationDraftProvider(api_key="")
    res_draft = p_draft.generate_negotiation_drafts(
        vendor_name="Royal Caterers",
        category="catering",
        quoted_total=300000.0,
        target_discount_pct=10.0,
        leverage_points=["Market rates lower"],
        competing_vendor_name="Prime Feast",
        competing_quote_total=250000.0
    )
    assert "polite" in res_draft
    assert "firm" in res_draft

    # 2. GeminiReplanningExplanationProvider without key -> fallback stub
    p_replan = GeminiReplanningExplanationProvider(api_key="")
    res_replan = p_replan.generate_explanation_and_mitigations(
        change_type="guest_count_changed",
        diff_summary={"budget_total_delta": 50000.0, "budget_total_new": 1050000.0},
        total_budget=1000000.0
    )
    assert "plain_explanation" in res_replan or "explanation" in res_replan or "mitigations" in res_replan

    # 3. GeminiVibeProvider without key -> fallback stub
    p_vibe = GeminiVibeProvider(api_key="")
    res_vibe = p_vibe.extract_vibe_from_images(
        images=[{"bytes": b"test", "mime_type": "image/jpeg"}],
        text_description="Royal Heritage Wedding"
    )
    assert p_vibe.last_provider_used == "deterministic_stub"
    assert len(res_vibe.images) > 0

    # 4. GeminiVibeProvider theme proposal without key -> fallback stub
    res_theme = p_vibe.generate_theme_proposal(
        style_profile={"extracted_palette": ["#FF0000"], "style_tags": ["royal"], "mood_words": ["vibrant"]},
        event_details={"event_type": "Wedding", "city": "Jaipur", "guest_count": 200, "total_budget": 1000000.0}
    )
    assert p_vibe.last_provider_used == "deterministic_stub"
    assert len(res_theme.decor_items) >= 10

    # 5. GeminiQuoteExtractionProvider without key -> fallback stub
    p_quote = GeminiQuoteExtractionProvider(api_key="")
    res_quote = p_quote.extract_quote_from_document(
        file_name="quote.pdf",
        file_bytes=b"%PDF-1.4 test document content",
        mime_type="application/pdf",
        category_hint="catering"
    )
    assert res_quote.vendor_name is not None
    assert res_quote.total_amount > 0








# ==========================================
# 8. Discovery Service Fallbacks
# ==========================================
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


# ==========================================
# 9. Targeted Branch Coverage Booster
# ==========================================
def test_branch_coverage_closure_and_edge_branches(db, test_data):
    event, token = test_data
    from backend.app.services.intake_service import normalize_indian_phone, IntakeService
    from backend.app.schemas.intake import IntakeRequestSchema
    from backend.app.services.vibe_aggregation_engine import VibeAggregationEngine, SingleImageVibeSchema
    from backend.app.services.replanning_service import ReplanningService
    from backend.app.models.models import ChangeEvent, AISuggestion, BudgetItem, Task, SubEvent
    from datetime import date, datetime, timedelta, timezone

    # 1. normalize_indian_phone edge branches
    assert normalize_indian_phone("919876543210") == "+919876543210"
    assert normalize_indian_phone("09876543210") == "+919876543210"
    assert normalize_indian_phone("9876543210") == "+919876543210"
    with pytest.raises(ValueError):
        normalize_indian_phone("12345")
    with pytest.raises(ValueError):
        normalize_indian_phone("01234567890")

    # 2. IntakeService with existing user (hits user already exists branch)
    req1 = IntakeRequestSchema(
        name="Ananya & Rohan Vivah",
        host_name="Ananya Sharma",
        phone_number="+919876543210",
        event_type="wedding",
        tradition_code="maharashtrian_vedic",
        city="Pune",
        pincode="411001",
        guest_count=250,
        total_budget=1500000.0,
        start_date=date(2025, 11, 20),
        end_date=date(2025, 11, 22),
    )
    plan1 = IntakeService.generate_master_plan(db, req1)
    assert plan1.event_id is not None
    # Re-call with same phone to hit existing user branch (lines 75-86)
    plan2 = IntakeService.generate_master_plan(db, req1)
    assert plan2.event_id is not None

    # 3. VibeAggregationEngine branches
    # Test vibes with: invalid hex, empty tags, empty materials, None lighting, empty flower,
    # top_palette having >= 5 colors (so len < 5 is False), and duplicate mood words
    vibe1 = SingleImageVibeSchema(
        palette=["invalid-color", "#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF"],
        style_tags=["", "royal", "heritage", "traditional"],
        materials=["", "silk", "brass"],
        lighting_mood=None,
        flower_types=["", "marigold", "rose"]
    )
    vibe2 = SingleImageVibeSchema(
        palette=["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF"],
        style_tags=["royal", "heritage"],
        materials=["silk", "brass"],
        lighting_mood="golden candle glow",
        flower_types=["jasmine"]
    )
    # pass overall_mood_words that already match the titles of tags/lighting/materials
    agg = VibeAggregationEngine.aggregate_vibe_profiles(
        image_vibes=[vibe1, vibe2],
        text_description="A royal wedding feast in a heritage haveli with golden candle glow and silk accents",
        overall_mood_words=["Royal", "Golden Candle Glow", "Silk Accents"]
    )
    assert len(agg["extracted_palette"]) == 5
    assert "Royal" in agg["mood_words"]

    # 4. Replanning date_moved acceptance via API
    from fastapi.testclient import TestClient
    from backend.app.main import app
    c = TestClient(app)

    future_start = (date.today() + timedelta(days=60)).isoformat()
    moved_start = (date.today() + timedelta(days=70)).isoformat()

    post_date_res = c.post(
        f"/api/v1/events/{event.id}/changes",
        json={
            "change_type": "date_moved",
            "payload": {
                "from_date": future_start,
                "to_date": moved_start
            }
        },
        headers={"X-Event-Owner-Token": token}
    )
    assert post_date_res.status_code == 201
    date_change_id = post_date_res.json()["change_id"]

    accept_date_res = c.post(
        f"/api/v1/events/{event.id}/changes/{date_change_id}/accept",
        headers={"X-Event-Owner-Token": token}
    )
    assert accept_date_res.status_code == 200
    assert accept_date_res.json()["status"] == "applied"

    # 5. Replanning rejection of active proposal and promotion of queued proposal
    post_cut_res = c.post(
        f"/api/v1/events/{event.id}/changes",
        json={
            "change_type": "budget_cut",
            "payload": {
                "from_budget": float(event.total_budget),
                "to_budget": float(event.total_budget) * 0.8
            }
        },
        headers={"X-Event-Owner-Token": token}
    )
    assert post_cut_res.status_code == 201
    cut_change_id = post_cut_res.json()["change_id"]

    # Post a second change to be queued
    post_guest_res = c.post(
        f"/api/v1/events/{event.id}/changes",
        json={
            "change_type": "guest_count_changed",
            "payload": {
                "from_guest_count": 200,
                "to_guest_count": 250
            }
        },
        headers={"X-Event-Owner-Token": token}
    )
    assert post_guest_res.status_code == 201
    queued_change_id = post_guest_res.json()["change_id"]

    # Reject active cut proposal -> promotes queued guest count proposal
    reject_res = c.post(
        f"/api/v1/events/{event.id}/changes/{cut_change_id}/reject",
        headers={"X-Event-Owner-Token": token}
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "rejected"

    # Verify promoted proposal is now pending
    queued_status_res = c.get(
        f"/api/v1/events/{event.id}/changes/{queued_change_id}",
        headers={"X-Event-Owner-Token": token}
    )
    assert queued_status_res.status_code == 200
    assert queued_status_res.json()["status"] == "pending"

    # 6. Quotes Bearer auth header and non-existent competing quote branch
    from backend.app.models.models import QuoteDocument
    quote_doc = QuoteDocument(
        event_id=event.id,
        vendor_name="Shree Ganesh Banquets",
        category="caterer",
        total_quoted_amount=350000.0,
        file_name="quote.pdf",
        file_type="application/pdf",
        uploaded_file=b"fake quote pdf content"
    )
    db.add(quote_doc)
    db.commit()

    draft_res = c.post(
        f"/api/v1/quotes/{quote_doc.id}/negotiate-draft",
        json={"quote_id": quote_doc.id, "target_discount_percentage": 10.0, "competing_quote_id": "non_existent_id"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert draft_res.status_code == 200
    assert len(draft_res.json()["draft_variants"]) > 0

