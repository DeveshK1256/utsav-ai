from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.providers.gemini_provider import GeminiReplanningExplanationProvider

client = TestClient(app)

def test_fallback_signal_when_gemini_fails(monkeypatch):
    # Simulate a 429 quota exhaustion in GeminiReplanningExplanationProvider
    provider = GeminiReplanningExplanationProvider(api_key="mock_key")
    diff_summary = {
        "budget_total_old": 1000000.0,
        "budget_total_delta": 200000.0,
        "budget_total_new": 1200000.0,
        "capacity_exceeded": False,
        "from_guest_count": 100,
        "to_guest_count": 120
    }
    
    # Mock httpx to simulate HTTP 429
    import httpx
    def mock_post(*args, **kwargs):
        req = httpx.Request("POST", "https://mock.url")
        resp = httpx.Response(status_code=429, json={"error": {"code": 429, "message": "Resource exhausted"}}, request=req)
        resp.raise_for_status()
    
    monkeypatch.setattr(httpx.Client, "post", mock_post)
    
    res = provider.generate_explanation_and_mitigations("guest_count_changed", diff_summary, 1500000.0)
    assert "stub_fallback_quota_exhausted" in res["provider_used"]
    assert res["fallback_warning"] is not None
    assert "LOUD ALERT" in res["fallback_warning"]
