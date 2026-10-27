import datetime
import io
import os
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from starlette.requests import Request
from backend.app.core.config import settings
from backend.app.core.security import verify_event_owner_token
from backend.app.db.session import SessionLocal
from backend.app.main import app
from backend.app.models.models import ChangeEvent, Event, QuoteDocument, User
from backend.app.services.budget_engine import BudgetScalingEngine

client = TestClient(app)


def test_budget_engine_fuzzy_event_type_branches():
    """Covers lines 117-126 of budget_engine.py for string matching branches."""
    # 1. Birthday
    b_items = BudgetScalingEngine.compute_budget_allocation(500000.0, "grand birthday party", "Mumbai", 100)
    assert len(b_items) > 0

    # 2. Community / Festival / Mela / Ganesh
    f_items = BudgetScalingEngine.compute_budget_allocation(500000.0, "society ganesh festival", "Pune", 500)
    assert len(f_items) > 0

    # 3. Milestone Anniversary
    a_items = BudgetScalingEngine.compute_budget_allocation(500000.0, "silver anniversary gala", "Delhi", 150)
    assert len(a_items) > 0

    # 4. Puja / Pooja / Havan
    p_items = BudgetScalingEngine.compute_budget_allocation(200000.0, "griha pravesh pooja", "Jaipur", 50)
    assert len(p_items) > 0

    # 5. Generic fallback -> wedding
    w_items = BudgetScalingEngine.compute_budget_allocation(1000000.0, "unrecognized custom gathering", "Bangalore", 200)
    assert len(w_items) > 0


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


def test_security_verify_token_auto_generation_and_bearer():
    """Covers lines 58-66 in core/security.py."""
    db = SessionLocal()
    rand_id = f"sec_{uuid.uuid4().hex[:8]}"
    try:
        user = User(phone_number=f"+9194{uuid.uuid4().hex[:8]}", full_name="Sec User")
        db.add(user)
        db.commit()

        # Event created with NO owner_token
        event = Event(
            id=rand_id,
            owner_id=user.id,
            name="Security Test Event",
            event_type="wedding",
            city="Delhi",
            pincode="110001",
            start_date=datetime.date(2026, 12, 1),
            end_date=datetime.date(2026, 12, 2),
            total_budget=500000.0,
            guest_count=100,
            owner_token=None,
            metadata_json={}
        )
        db.add(event)
        db.commit()

        req = Request(scope={"type": "http", "path_params": {"id": rand_id}, "query_string": b""})

        # In production mode (PYTEST_CURRENT_TEST cleared), verify_event_owner_token will auto-generate and enforce a token
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": ""}):
            # Attempt with no token -> 403 (token generated on event, but not provided in request)
            with pytest.raises(Exception) as exc_info:
                verify_event_owner_token(
                    request=req,
                    x_event_owner_token=None,
                    authorization=None,
                    db=db
                )
            assert "403" in str(exc_info.value)

            # Check that token was auto-generated and persisted to event
            db.refresh(event)
            assert event.owner_token is not None
            assert len(event.owner_token) >= 16

            # Now provide the generated token via Authorization: Bearer header
            verified_ev = verify_event_owner_token(
                request=req,
                x_event_owner_token=None,
                authorization=f"Bearer {event.owner_token}",
                db=db
            )
            assert verified_ev.id == rand_id
    finally:
        db.query(Event).filter(Event.id == rand_id).delete()
        db.commit()
        db.close()


def test_replanning_reject_and_error_branches():
    """Covers lines 84-87, 101-105, 121-124 in api/v1/replanning.py."""
    db = SessionLocal()
    ev_id = f"rep_{uuid.uuid4().hex[:8]}"
    token = f"tok_{uuid.uuid4().hex[:8]}"
    headers = {"X-Event-Owner-Token": token}
    try:
        user = User(phone_number=f"+9193{uuid.uuid4().hex[:8]}", full_name="Replan Host")
        db.add(user)
        db.commit()

        ev = Event(
            id=ev_id,
            owner_id=user.id,
            name="Replan Branches Event",
            event_type="wedding",
            city="Pune",
            pincode="411001",
            owner_token=token,
            start_date=datetime.date(2026, 12, 1),
            end_date=datetime.date(2026, 12, 2),
            total_budget=800000.0,
            guest_count=150,
            metadata_json={"owner_token": token}
        )
        db.add(ev)
        db.commit()

        # Submit change
        c_res = client.post(
            f"/api/v1/events/{ev_id}/changes",
            json={"change_type": "guest_count_changed", "payload": {"to_guest_count": 220}},
            headers=headers
        )
        assert c_res.status_code == 201
        change_id = c_res.json()["change_id"]

        # Reject change proposal
        rej_res = client.post(f"/api/v1/events/{ev_id}/changes/{change_id}/reject", headers=headers)
        assert rej_res.status_code == 200
        assert rej_res.json()["status"] == "rejected"

        # Reject non-existent change -> 400/404
        rej_404 = client.post(f"/api/v1/events/{ev_id}/changes/fake_change_id_123/reject", headers=headers)
        assert rej_404.status_code in (400, 404)

        # Patch non-existent change -> 400/404
        patch_404 = client.patch(
            f"/api/v1/events/{ev_id}/changes/fake_change_id_123",
            json={"manual_overrides": {"note": "Invalid"}},
            headers=headers
        )
        assert patch_404.status_code in (400, 404)
    finally:
        db.query(ChangeEvent).filter(ChangeEvent.event_id == ev_id).delete()
        db.query(Event).filter(Event.id == ev_id).delete()
        db.commit()
        db.close()


def test_quotes_api_edge_case_and_error_branches():
    """Covers lines 70-73, 105-108, 277-280, 360-363, 370-375, 380-383 in api/v1/quotes.py."""
    db = SessionLocal()
    ev_id = f"q_ev_{uuid.uuid4().hex[:8]}"
    token = f"tok_{uuid.uuid4().hex[:8]}"
    headers = {"X-Event-Owner-Token": token}
    try:
        user = User(phone_number=f"+9192{uuid.uuid4().hex[:8]}", full_name="Quote Host")
        db.add(user)
        db.commit()

        ev = Event(
            id=ev_id,
            owner_id=user.id,
            name="Quote Edge Event",
            event_type="wedding",
            city="Pune",
            pincode="411001",
            owner_token=token,
            start_date=datetime.date(2026, 12, 1),
            end_date=datetime.date(2026, 12, 2),
            total_budget=800000.0,
            guest_count=150,
            metadata_json={"owner_token": token}
        )
        db.add(ev)
        db.commit()

        # 1. Upload quote to non-existent event -> 404
        dummy_file = ("quote.pdf", io.BytesIO(b"%PDF dummy"), "application/pdf")
        res_404_up = client.post(
            "/api/v1/quotes/upload",
            data={"event_id": "non_existent_event_id"},
            files={"file": dummy_file},
            headers={"X-Event-Owner-Token": "some_token"}
        )
        assert res_404_up.status_code == 404

        # 2. Upload file exceeding 10MB -> 413
        large_bytes = b"0" * (10 * 1024 * 1024 + 1024)
        large_file = ("huge.pdf", io.BytesIO(large_bytes), "application/pdf")
        res_413 = client.post(
            "/api/v1/quotes/upload",
            data={"event_id": ev_id},
            files={"file": large_file},
            headers=headers
        )
        assert res_413.status_code == 413

        # 3. List quotes for non-existent event -> 404
        res_list_404 = client.get("/api/v1/quotes/events/non_existent_event_id")
        assert res_list_404.status_code == 404

        # 4. Compare with less than 2 quotes -> 400/422
        res_cmp_1 = client.post("/api/v1/quotes/compare", json={"quote_ids": ["q1"]})
        assert res_cmp_1.status_code in (400, 422)

        # 5. Compare with non-existent quote IDs -> 404
        res_cmp_missing = client.post("/api/v1/quotes/compare", json={"quote_ids": ["q_non_1", "q_non_2"]})
        assert res_cmp_missing.status_code == 404

        # 6. Compare quotes with mismatched categories -> 400
        q1 = QuoteDocument(
            id=f"q_c_{uuid.uuid4().hex[:8]}",
            event_id=ev_id,
            vendor_name="Caterer Vendor",
            category="caterer",
            total_quoted_amount=200000.0,
            file_name="c.pdf",
            file_type="application/pdf",
            uploaded_file=b"c",
            raw_extracted_json={}
        )
        q2 = QuoteDocument(
            id=f"q_d_{uuid.uuid4().hex[:8]}",
            event_id=ev_id,
            vendor_name="Decorator Vendor",
            category="decorator",
            total_quoted_amount=150000.0,
            file_name="d.pdf",
            file_type="application/pdf",
            uploaded_file=b"d",
            raw_extracted_json={}
        )
        db.add_all([q1, q2])
        db.commit()

        res_mismatch = client.post("/api/v1/quotes/compare", json={"quote_ids": [q1.id, q2.id]})
        assert res_mismatch.status_code == 400
        assert "same category" in res_mismatch.json()["detail"].lower()
    finally:
        db.query(QuoteDocument).filter(QuoteDocument.event_id == ev_id).delete()
        db.query(Event).filter(Event.id == ev_id).delete()
        db.commit()
        db.close()


def test_intake_and_rituals_extra_branches():
    # 1. Rituals panchang valid and invalid coordinates
    res_panch = client.get("/api/v1/rituals/panchang?event_date=2026-11-20&latitude=18.5204&longitude=73.8567")
    assert res_panch.status_code == 200
    pdata = res_panch.json()
    assert "tithi" in pdata
    assert "nakshatra" in pdata

    res_panch_bad = client.get("/api/v1/rituals/panchang?event_date=2026-11-20&latitude=999.0&longitude=73.8567")
    assert res_panch_bad.status_code == 400

    # 2. Intake calculate-budget error path
    with patch.object(BudgetScalingEngine, "compute_budget_allocation", side_effect=ValueError("Invalid allocation parameter")):
        res_calc_err = client.post("/api/v1/intake/calculate-budget", json={
            "total_budget": 500000.0,
            "city": "Pune",
            "guest_count": 100,
            "event_type": "wedding"
        })
        assert res_calc_err.status_code == 400
        assert "Invalid allocation parameter" in res_calc_err.json()["detail"]

