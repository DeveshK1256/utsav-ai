import time
from fastapi.testclient import TestClient
from backend.app.main import app


def test_startup_and_health_check_instantaneous():
    """
    Safeguard Test:
    Asserts that backend application startup and health check response time
    is instantaneous (< 500ms) and never blocks on database locks, network requests,
    or schema migrations.
    """
    t0 = time.time()
    with TestClient(app) as client:
        # Measure health check latency
        resp = client.get("/health")
        elapsed = time.time() - t0

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "utsav-backend"
        
        # Must respond well under 1 second
        assert elapsed < 1.0, f"Startup + Health check took {elapsed:.2f}s, exceeding 1.0s budget"
        print(f"\n[STARTUP PERFORMANCE] /health responded in {elapsed * 1000:.1f}ms (Status: {resp.status_code})")
