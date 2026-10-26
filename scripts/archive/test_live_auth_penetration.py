import urllib.request
import urllib.error
import json
import sys

BASE_URL = "https://utsav-ai-ycg2.onrender.com"

def run_test():
    print(f"Testing live event authorization against {BASE_URL}...")

    # Step 1: Create an event
    create_payload = json.dumps({
        "name": "Live Penetration Test Vivah",
        "event_type": "wedding",
        "guest_count": 100,
        "total_budget": 500000.0,
        "city": "Pune",
        "pincode": "411038",
        "host_phone": "+919988776655",
        "host_name": "Auth Security Tester"
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/events",
        data=create_payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            event_id = data.get("id")
            owner_token = data.get("owner_token")
            print(f"1. Event created: status={resp.status}, id={event_id}")
            print(f"   owner_token received upon creation: {bool(owner_token)} (len={len(owner_token) if owner_token else 0})")
            assert owner_token is not None, "FAILED: owner_token not returned upon creation!"
    except Exception as e:
        print(f"Error creating event: {e}")
        return False

    # Step 2: Unauthenticated GET - verify owner_token is masked (None/null)
    req_get = urllib.request.Request(f"{BASE_URL}/api/v1/events/{event_id}")
    with urllib.request.urlopen(req_get) as resp:
        get_data = json.loads(resp.read().decode())
        masked_token = get_data.get("owner_token")
        print(f"2. Unauthenticated GET /events/{event_id}: status={resp.status}")
        print(f"   owner_token in unauthenticated response: {masked_token}")
        assert masked_token is None, f"FAILED: owner_token was leaked to unauthenticated reader! {masked_token}"

    # Step 3: Unauthenticated DELETE - must FAIL with 401 or 403
    print(f"3. Attempting unauthenticated DELETE /events/{event_id}...")
    req_del_unauth = urllib.request.Request(f"{BASE_URL}/api/v1/events/{event_id}", method="DELETE")
    unauth_delete_failed = False
    try:
        with urllib.request.urlopen(req_del_unauth) as resp:
            print(f"   CRITICAL VULNERABILITY STILL ACTIVE: Unauthenticated DELETE succeeded with status {resp.status}!")
            return False
    except urllib.error.HTTPError as e:
        print(f"   Unauthenticated DELETE correctly rejected with HTTP {e.code}: {e.read().decode()}")
        if e.code in (401, 403):
            unauth_delete_failed = True
        else:
            print(f"   Unexpected HTTP error code: {e.code}")

    assert unauth_delete_failed, "FAILED: Unauthenticated delete did not return 401 or 403!"

    # Step 4: Authenticated DELETE with X-Event-Owner-Token - must SUCCEED with 200
    print(f"4. Attempting authenticated DELETE with X-Event-Owner-Token...")
    req_del_auth = urllib.request.Request(
        f"{BASE_URL}/api/v1/events/{event_id}",
        method="DELETE",
        headers={"X-Event-Owner-Token": owner_token}
    )
    try:
        with urllib.request.urlopen(req_del_auth) as resp:
            del_data = json.loads(resp.read().decode())
            print(f"   Authenticated DELETE succeeded: status={resp.status}, response={del_data}")
            assert resp.status == 200
    except Exception as e:
        print(f"FAILED authenticated DELETE: {e}")
        return False

    print("\nPROVEN: Live Event Authorization lockdown is fully active and verified!")
    return True

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
