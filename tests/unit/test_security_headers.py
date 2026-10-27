from fastapi.testclient import TestClient
from fastapi import HTTPException
import pytest
import secrets
from backend.app.main import app
from backend.app.core.security import verify_event_owner_token, generate_owner_token
from backend.app.models.models import Event, User
from backend.app.db.session import SessionLocal

client = TestClient(app)

def test_security_headers_present_on_responses():
    """Verify all mandatory security headers are attached to API responses."""
    res = client.get("/health")
    assert res.status_code == 200
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert res.headers.get("X-XSS-Protection") == "1; mode=block"
    assert "max-age=" in res.headers.get("Strict-Transport-Security", "")
    assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "frame-ancestors 'none'" in res.headers.get("Content-Security-Policy", "")


def test_verify_event_owner_token_unit():
    """Verify verify_event_owner_token error and success behaviors."""
    db = SessionLocal()
    try:
        # 1. Missing event_id in request
        class DummyRequest:
            path_params = {}
            query_params = {}

        with pytest.raises(HTTPException) as exc1:
            verify_event_owner_token(DummyRequest(), db=db)
        assert exc1.value.status_code == 400

        # 2. Event not found
        class DummyRequest404:
            path_params = {"event_id": "non_existent_event_9999"}
            query_params = {}

        with pytest.raises(HTTPException) as exc2:
            verify_event_owner_token(DummyRequest404(), db=db)
        assert exc2.value.status_code == 404

        # 3. Create test event with token
        import datetime
        rand_suffix = secrets.token_hex(4)
        user = User(phone_number=f"+9199{rand_suffix[:8]}", full_name="Sec User", email=f"sec_{rand_suffix}@example.com")
        db.add(user)
        db.commit()

        token = generate_owner_token()
        event = Event(
            id="sec_test_evt_1",
            name="Security Test Wedding",
            owner_id=user.id,
            owner_token=token,
            event_type="wedding",
            guest_count=100,
            total_budget=500000.0,
            city="Pune",
            pincode="411001",
            start_date=datetime.date(2026, 12, 1),
            end_date=datetime.date(2026, 12, 2),
            metadata_json={"owner_token": token}
        )
        db.add(event)
        db.commit()

        class DummyRequestWithId:
            path_params = {"event_id": event.id}
            query_params = {}

        # 4. Missing token -> 403
        with pytest.raises(HTTPException) as exc3:
            verify_event_owner_token(DummyRequestWithId(), x_event_owner_token=None, authorization=None, db=db)
        assert exc3.value.status_code == 403

        # 5. Invalid token -> 403
        with pytest.raises(HTTPException) as exc4:
            verify_event_owner_token(DummyRequestWithId(), x_event_owner_token="wrong_token", authorization=None, db=db)
        assert exc4.value.status_code == 403

        # 6. Valid X-Event-Owner-Token header -> success
        res_header = verify_event_owner_token(DummyRequestWithId(), x_event_owner_token=token, authorization=None, db=db)
        assert res_header.id == event.id

        # 7. Valid Authorization Bearer header -> success
        res_bearer = verify_event_owner_token(DummyRequestWithId(), x_event_owner_token=None, authorization=f"Bearer {token}", db=db)
        assert res_bearer.id == event.id
    finally:
        db.query(Event).filter(Event.id == "sec_test_evt_1").delete()
        if 'user' in locals():
            db.query(User).filter(User.id == user.id).delete()
        db.commit()
        db.close()

