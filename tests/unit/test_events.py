from datetime import datetime, timezone, timedelta
from backend.app.models.models import SubEvent
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.session import get_db, SessionLocal

client = TestClient(app)


def test_events_crud_endpoints():
    # 1. Create Event
    create_payload = {
        "name": "Local Test Wedding",
        "event_type": "wedding",
        "guest_count": 200,
        "total_budget": 2500000.0,
        "city": "Mumbai",
        "pincode": "400001",
        "host_phone": "+919999988888",
        "host_name": "Local Test Host"
    }
    res = client.post("/api/v1/events", json=create_payload)
    assert res.status_code == 201
    data = res.json()
    event_id = data["id"]
    owner_token = data.get("owner_token")
    assert owner_token is not None and len(owner_token) == 64
    assert data["name"] == "Local Test Wedding"
    assert data["city"] == "Mumbai"

    # 2. Get Event without auth is rejected (403 Forbidden)
    get_res = client.get(f"/api/v1/events/{event_id}")
    assert get_res.status_code == 403
    assert "Forbidden" in get_res.json()["detail"]

    # Get Event with query param token is REJECTED (CWE-598 compliance)
    get_query_res = client.get(f"/api/v1/events/{event_id}?owner_token={owner_token}")
    assert get_query_res.status_code == 403
    assert "Forbidden" in get_query_res.json()["detail"]

    # Get Event with valid auth token header succeeds
    get_auth_res = client.get(f"/api/v1/events/{event_id}", headers={"X-Event-Owner-Token": owner_token})
    assert get_auth_res.status_code == 200
    assert get_auth_res.json()["owner_token"] == owner_token

    # 3. Unauthenticated Delete Event must be rejected (403 Forbidden)
    unauth_del = client.delete(f"/api/v1/events/{event_id}")
    assert unauth_del.status_code == 403
    assert "Forbidden" in unauth_del.json()["detail"]

    # 4. Authenticated Delete Event succeeds
    del_res = client.delete(f"/api/v1/events/{event_id}", headers={"X-Event-Owner-Token": owner_token})
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True

    # 5. Verify Deleted
    get_again = client.get(f"/api/v1/events/{event_id}")
    assert get_again.status_code == 404

import json
import uuid
from unittest.mock import MagicMock, patch


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
