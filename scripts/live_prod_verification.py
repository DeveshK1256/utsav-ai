"""
Comprehensive Live Production Re-Verification Script
Tests live Render backend (https://utsav-ai-ycg2.onrender.com) for:
1. CORS + /env-check
2. Event GET Authorization (403 without token, 200 with token)
3. WhatsApp Webhook Fail-Closed (403 without signature)
4. Discovery Endpoint Live Query
5. Rate Limiting (429 on /api/v1/intake/generate)
"""
import requests
import json
import time

BASE_URL = "https://utsav-ai-ycg2.onrender.com"

def test_cors_and_env_check():
    print("\n--- ITEM 1: CORS & /env-check ---")
    # /env-check
    resp = requests.get(f"{BASE_URL}/env-check", timeout=15)
    print(f"GET /env-check status: {resp.status_code} (Expected: 404)")
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"

    # Forged Origin
    resp = requests.get(f"{BASE_URL}/health", headers={"Origin": "https://evil-attacker.com"}, timeout=15)
    allow_origin = resp.headers.get("access-control-allow-origin")
    print(f"Forged Origin access-control-allow-origin: {allow_origin} (Expected: None)")
    assert allow_origin is None, f"Expected None, got {allow_origin}"

    # Legitimate Origin
    resp = requests.get(f"{BASE_URL}/health", headers={"Origin": "https://utsav-ai.netlify.app"}, timeout=15)
    allow_origin = resp.headers.get("access-control-allow-origin")
    print(f"Legitimate Origin access-control-allow-origin: {allow_origin} (Expected: https://utsav-ai.netlify.app)")
    assert allow_origin == "https://utsav-ai.netlify.app"
    print("ITEM 1 PASSED: CORS whitelist enforced, /env-check removed.")

def test_event_get_auth():
    print("\n--- ITEM 2: Event GET Auth (Live) ---")
    # Create event via live API
    payload = {
        "name": "Live Prod Auth Verification Wedding",
        "event_type": "wedding",
        "city": "Pune",
        "total_budget": 1500000.0,
        "guest_count": 250,
        "host_phone": "+919876543210",
        "host_name": "Test Host"
    }
    resp = requests.post(f"{BASE_URL}/api/v1/events", json=payload, timeout=20)
    print(f"POST /api/v1/events status: {resp.status_code}")
    assert resp.status_code in (200, 201), f"Event creation failed: {resp.status_code} {resp.text}"
    data = resp.json()
    event_id = data.get("id")
    auth_token = data.get("owner_token")
    print(f"Created Event ID: {event_id}")
    print(f"Received auth_token: {auth_token[:8]}... (length: {len(auth_token) if auth_token else 0})")
    assert event_id and auth_token, "Missing event_id or auth_token in creation response"

    # 1. Unauthenticated GET /events/{id} -> Must return 403 Forbidden
    resp_unauth = requests.get(f"{BASE_URL}/api/v1/events/{event_id}", timeout=15)
    print(f"Unauthenticated GET /api/v1/events/{event_id} status: {resp_unauth.status_code} (Expected: 403)")
    assert resp_unauth.status_code == 403, f"Expected 403, got {resp_unauth.status_code}"
    print(f"Unauthenticated error detail: {resp_unauth.json()}")

    # 2. Forged Bearer token GET /events/{id} -> Must return 403 Forbidden
    resp_forged = requests.get(
        f"{BASE_URL}/api/v1/events/{event_id}",
        headers={"Authorization": "Bearer forged-invalid-token-12345"},
        timeout=15
    )
    print(f"Forged Token GET /api/v1/events/{event_id} status: {resp_forged.status_code} (Expected: 403)")
    assert resp_forged.status_code == 403, f"Expected 403, got {resp_forged.status_code}"

    # 3. Authenticated GET /events/{id} -> Must return 200 OK with event data
    resp_auth = requests.get(
        f"{BASE_URL}/api/v1/events/{event_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=15
    )
    print(f"Authenticated GET /api/v1/events/{event_id} status: {resp_auth.status_code} (Expected: 200)")
    assert resp_auth.status_code == 200, f"Expected 200, got {resp_auth.status_code}"
    auth_data = resp_auth.json()
    print(f"Authenticated event name returned: '{auth_data.get('name')}'")
    assert auth_data.get("name") == payload["name"]
    print("ITEM 2 PASSED: Live Event GET requires valid owner auth token.")
    return event_id, auth_token

def test_whatsapp_webhook_fail_closed():
    print("\n--- ITEM 3: WhatsApp Webhook Fail-Closed ---")
    webhook_url = f"{BASE_URL}/api/v1/webhooks/whatsapp"
    test_body = {"object": "whatsapp_business_account", "entry": []}

    # 1. No X-Hub-Signature-256 header
    resp_no_sig = requests.post(webhook_url, json=test_body, timeout=15)
    print(f"POST without X-Hub-Signature-256 status: {resp_no_sig.status_code} (Expected: 403)")
    assert resp_no_sig.status_code == 403, f"Expected 403, got {resp_no_sig.status_code}: {resp_no_sig.text}"

    # 2. Invalid X-Hub-Signature-256 header
    resp_bad_sig = requests.post(
        webhook_url,
        json=test_body,
        headers={"X-Hub-Signature-256": "sha256=invalidhexsignature00000000000000000000000000000000000000000000"},
        timeout=15
    )
    print(f"POST with invalid signature status: {resp_bad_sig.status_code} (Expected: 403)")
    assert resp_bad_sig.status_code == 403, f"Expected 403, got {resp_bad_sig.status_code}: {resp_bad_sig.text}"
    print("ITEM 3 PASSED: WhatsApp webhook is strictly fail-closed.")

def test_discovery_live():
    print("\n--- ITEM 4: Discovery Vendors Live ---")
    # Query Pune
    resp = requests.get(f"{BASE_URL}/api/v1/discovery/vendors?city=Pune", timeout=25)
    print(f"GET /api/v1/discovery/vendors?city=Pune status: {resp.status_code}")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    items = data.get("items", [])
    print(f"Discovery returned {len(items)} venues for Pune")
    if items:
        print(f"Sample venue 1: {items[0].get('name')} | lat={items[0].get('latitude')}, lon={items[0].get('longitude')}")
    assert len(items) > 0, "Expected at least 1 venue for Pune"
    print("ITEM 4 PASSED: Discovery endpoint is live and returning venues.")

def test_rate_limiting():
    print("\n--- ITEM 5: Rate Limiting Live ---")
    # /api/v1/intake/generate is limited to 10/minute
    url = f"{BASE_URL}/api/v1/intake/generate"
    payload = {
        "event_type": "wedding",
        "city": "Pune",
        "total_budget": 1000000,
        "guest_count": 100,
        "culture": "marathi"
    }
    statuses = []
    print("Firing 15 rapid POST requests to /api/v1/intake/generate...")
    for i in range(15):
        try:
            r = requests.post(url, json=payload, timeout=5)
            statuses.append(r.status_code)
        except Exception as e:
            statuses.append(f"err:{e}")
        time.sleep(0.05)
    
    print(f"Status codes received: {statuses}")
    has_429 = 429 in statuses
    print(f"HTTP 429 rate limit observed: {has_429}")
    assert has_429, f"Expected 429 rate limit in responses, got {statuses}"
    print("ITEM 5 PASSED: Rate limit actively triggered on live server.")

if __name__ == "__main__":
    test_cors_and_env_check()
    test_event_get_auth()
    test_whatsapp_webhook_fail_closed()
    test_discovery_live()
    test_rate_limiting()
    print("\n>>> ALL LIVE BACKEND VERIFICATION TESTS PASSED SUCCESSFULLY! <<<")
