import httpx
import time

api_base = "https://utsav-ai-ycg2.onrender.com/api/v1"
print("Checking Render deployment for F15-Lite discovery endpoint...")
for i in range(12):
    try:
        r = httpx.get(f"{api_base}/discovery/vendors?city=Jaipur", timeout=20.0)
        print(f"Attempt {i+1}: HTTP {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"SUCCESS! Total venues in Jaipur: {data['total_results']}")
            for v in data["results"][:4]:
                print(f"  • {v['business_name']} ({v['category']}) - Rating Tier: {v['rating_tier']} - Cost: {v['cost_estimate']['estimated_cost_display']}")
            break
    except Exception as e:
        print(f"Attempt {i+1} waiting: {e}")
    time.sleep(10)
