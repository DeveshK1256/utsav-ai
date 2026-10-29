from backend.app.services.whatsapp.send_service import WhatsAppSendService
"""Unit tests for guests router and guest coordination service.
Mirrors backend/app/routers/guests.py and backend/app/services/whatsapp/guest_service.py.
"""
import datetime
from datetime import date, timedelta, timezone
import io
import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
client = TestClient(app)

from backend.app.core.config import settings
from backend.app.db.session import SessionLocal
from backend.app.main import app
from backend.app.models.models import (
    BudgetItem,
    ChangeEvent,
    Event,
    EventFactSheet,
    Guest,
    MessageLog,
    OptOut,
    SubEvent,
    User,
)
from backend.app.services.whatsapp.guest_service import GuestService
from backend.app.services.whatsapp.rsvp_parser import RSVPParser



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
            start_date=date(2026, 11, 20),
            end_date=date(2026, 11, 21),
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
            start_date=date(2026, 11, 20),
            end_date=date(2026, 11, 21),
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
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 3),
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
