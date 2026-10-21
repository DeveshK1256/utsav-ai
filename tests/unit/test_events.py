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
    assert data["name"] == "Local Test Wedding"
    assert data["city"] == "Mumbai"

    # 2. Get Event
    get_res = client.get(f"/api/v1/events/{event_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == event_id

    # 3. Delete Event
    del_res = client.delete(f"/api/v1/events/{event_id}")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True

    # 4. Verify Deleted
    get_again = client.get(f"/api/v1/events/{event_id}")
    assert get_again.status_code == 404
