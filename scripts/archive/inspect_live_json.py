import httpx
import json

base_url = "https://utsav-ai-ycg2.onrender.com"

# 1. Inspect Muhurat Response
r_muhurat = httpx.get(f"{base_url}/api/v1/rituals/muhurat-candidates?event_date=2024-10-24&latitude=19.0760&longitude=72.8777")
print("=== MUHURAT JSON ===")
print(json.dumps(r_muhurat.json(), indent=2))

# 2. Inspect Merge Response
payload = {
    "primary_tradition_code": "maharashtrian_vedic",
    "secondary_tradition_code": "punjabi_traditional",
    "start_date": "2024-10-24"
}
r_merge = httpx.post(f"{base_url}/api/v1/rituals/merge-traditions", json=payload)
print("=== MERGE JSON ===")
print(json.dumps(r_merge.json(), indent=2))
