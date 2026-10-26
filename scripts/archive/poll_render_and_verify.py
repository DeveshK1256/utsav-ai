import httpx
import time

base_url = "https://utsav-ai-ycg2.onrender.com"

print("Waiting for Render to deploy commit b198ab6...")
for attempt in range(1, 30):
    try:
        r = httpx.get(f"{base_url}/api/v1/rituals/traditions", timeout=15.0)
        if r.status_code == 200:
            data = r.json()
            # Check if all traditions have is_verified == False
            maha = next((t for t in data if t.get("code") == "maharashtrian_vedic"), None)
            if maha and maha.get("is_verified") is False and "AI-drafted" in (maha.get("verification_source") or ""):
                print(f"[Attempt {attempt}] New commit b198ab6 is LIVE on Render!")
                break
            else:
                print(f"[Attempt {attempt}] Old version still live (maha is_verified={maha.get('is_verified') if maha else 'None'}). Waiting 10s...")
        else:
            print(f"[Attempt {attempt}] HTTP {r.status_code}. Waiting 10s...")
    except Exception as e:
        print(f"[Attempt {attempt}] Error: {e}. Waiting 10s...")
    time.sleep(10)

print("\nRunning live verification checks...")
# Check merge-traditions
payload = {
    "primary_tradition_code": "maharashtrian_vedic",
    "secondary_tradition_code": "punjabi_traditional",
    "start_date": "2024-10-24"
}
r_merge = httpx.post(f"{base_url}/api/v1/rituals/merge-traditions", json=payload, timeout=60.0)
print(f"Merge status: {r_merge.status_code}")
merge_data = r_merge.json()
print("Fusion Title:", merge_data.get("fusion_title"))
print("Primary Tradition:", merge_data.get("primary_tradition"))
print("Secondary Tradition:", merge_data.get("secondary_tradition"))
print("Content Accuracy Disclaimer:", merge_data.get("content_accuracy_disclaimer"))
print("Timing Disclaimer:", merge_data.get("timing_disclaimer"))
print("Run of show length:", len(merge_data.get("run_of_show", [])))
for idx, c in enumerate(merge_data.get("run_of_show", []), 1):
    print(f"  {idx}. [{c.get('origin_tradition')}] {c.get('name')} (Day {c.get('day_offset')}, {c.get('start_time')})")

print("\nDone!")
