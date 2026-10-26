import time
from fastapi.testclient import TestClient
from backend.app.main import app


def test_startup_and_health_check_instantaneous():
    """
    Safeguard Test:
    Asserts that backend application startup and health check response time
    is instantaneous and never blocks on database locks, network requests,
    or schema migrations.
    
    Distinguishes cold TestClient initialization (mounting middleware stack,
    spawning background threads, and route compiling) from steady-state
    health check execution.
    """
    t0 = time.perf_counter()
    with TestClient(app) as client:
        t_startup = (time.perf_counter() - t0) * 1000

        # Measure first health check call
        t1 = time.perf_counter()
        resp = client.get("/health")
        t_first = (time.perf_counter() - t1) * 1000

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "utsav-backend"

        # Measure steady-state health check calls (pure route execution)
        subsequent_times = []
        for _ in range(5):
            ts = time.perf_counter()
            r = client.get("/health")
            assert r.status_code == 200
            subsequent_times.append((time.perf_counter() - ts) * 1000)

        mean_steady_ms = sum(subsequent_times) / len(subsequent_times)
        print(f"\n[PERFORMANCE BREAKDOWN]")
        print(f"  - TestClient / App Startup: {t_startup:.1f}ms")
        print(f"  - First /health call (cold middleware stack): {t_first:.1f}ms")
        print(f"  - Steady-state /health calls (mean of 5): {mean_steady_ms:.2f}ms (min: {min(subsequent_times):.2f}ms)")

        # Steady-state health check must be well under 50ms (in-memory route)
        assert mean_steady_ms < 50.0, f"Steady-state health check took {mean_steady_ms:.2f}ms, exceeding 50ms budget"
        # Total cold boot to first response must be well under 2.5s (Python import/route tree build)
        total_cold_time = (t_startup + t_first) / 1000
        assert total_cold_time < 2.5, f"Cold boot to first response took {total_cold_time:.2f}s"
