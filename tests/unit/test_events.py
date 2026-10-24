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

    # 2. Get Event without auth (masks owner_token)
    get_res = client.get(f"/api/v1/events/{event_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == event_id
    assert get_res.json()["owner_token"] is None

    # Get Event with auth token returns owner_token
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
