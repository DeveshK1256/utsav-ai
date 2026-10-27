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
    assert "X-XSS-Protection" not in res.headers
    assert "max-age=" in res.headers.get("Strict-Transport-Security", "")
    assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert res.headers.get("Permissions-Policy") == "geolocation=(self), camera=(), microphone=()"
    assert res.headers.get("Content-Security-Policy") == "default-src 'none'; frame-ancestors 'none';"


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


def test_cors_allow_list_enforcement():
    """Validates CORS allow-list permits trusted origins and rejects unauthorized domains."""
    # 1. Allowed Production Domain
    res_prod = client.options(
        "/api/v1/discovery/vendors?city=Pune",
        headers={"Origin": "https://utsav-ai.netlify.app", "Access-Control-Request-Method": "GET"}
    )
    assert res_prod.headers.get("access-control-allow-origin") == "https://utsav-ai.netlify.app"

    # 2. Allowed Localhost Domain
    res_local = client.options(
        "/api/v1/discovery/vendors?city=Pune",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"}
    )
    assert res_local.headers.get("access-control-allow-origin") == "http://localhost:3000"

    # 3. Disallowed Malicious Domain
    res_evil = client.options(
        "/api/v1/discovery/vendors?city=Pune",
        headers={"Origin": "https://attacker-controlled-site.xyz", "Access-Control-Request-Method": "GET"}
    )
    assert "access-control-allow-origin" not in res_evil.headers


def test_request_body_size_limit_enforcement():
    """Validates that payloads exceeding the 10MB limit are immediately rejected with 413."""
    oversized_length = str(15 * 1024 * 1024)  # 15MB
    res = client.post(
        "/api/v1/intake/calculate-budget",
        headers={"Content-Length": oversized_length, "Content-Type": "application/json"},
        content=b"{}"
    )
    assert res.status_code == 413
    assert "Payload Too Large" in res.text


def test_public_endpoint_rate_limiting():
    """Validates that SlowAPI rate limiting protects public intake endpoints against abuse."""
    from backend.app.core.limiter import limiter
    limiter.reset()

    # Hit intake generate endpoint up to limit (20/minute)
    responses = []
    valid_payload = {
        "name": "Rate Limit Flood Celebration",
        "host_name": "Test Flooder",
        "phone_number": "+919988776655",
        "event_type": "wedding",
        "tradition_code": "maharashtrian_vedic",
        "guest_count": 100,
        "total_budget": 500000.0,
        "city": "Pune",
        "pincode": "411001",
        "start_date": "2026-12-01",
        "end_date": "2026-12-02"
    }
    for _ in range(25):
        r = client.post(
            "/api/v1/intake/generate",
            json=valid_payload
        )
        responses.append(r.status_code)

    # At least one request after 20 must encounter 429 Too Many Requests
    assert 429 in responses

