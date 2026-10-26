import io
import time
import requests
from PIL import Image, ImageDraw

RENDER_URL = "https://utsav-ai-ycg2.onrender.com"

def create_sample_inspiration_image(primary_color, accent_color, label):
    img = Image.new("RGB", (600, 400), color=primary_color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([(50, 50), (550, 350)], outline=accent_color, width=8)
    draw.ellipse([(200, 100), (400, 300)], fill=accent_color)
    draw.text((80, 70), f"Aesthetic Sample: {label}", fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

def wait_for_deploy():
    print("Checking Render deployment for M3 Vibe-to-Plan endpoints...", flush=True)
    for attempt in range(40):
        try:
            resp = requests.get(f"{RENDER_URL}/openapi.json", timeout=10)
            if resp.status_code == 200:
                schema = resp.json()
                paths = schema.get("paths", {})
                if "/api/v1/events/{event_id}/vibe/upload" in paths:
                    print("Render deployment active with M3 endpoints live!", flush=True)
                    return True
        except Exception as e:
            print(f"Waiting... ({e})", flush=True)
        time.sleep(10)
    raise RuntimeError("Timed out waiting for Render deployment.")

def run_live_verification():
    wait_for_deploy()

    # 1. Check health
    health = requests.get(f"{RENDER_URL}/health", timeout=10).json()
    print(f"\n1. Health Check: {health}")
    assert health["active_llm_provider"] == "gemini", f"Expected gemini, got {health['active_llm_provider']}"

    # 2. Create Event
    print("\n2. Creating test event in Jaipur (250 guests, Rs. 15,00,000 budget)...", flush=True)
    event_payload = {
        "name": "Live Verification Royal Palace Wedding",
        "event_type": "Wedding",
        "city": "Jaipur",
        "guest_count": 250,
        "total_budget": 1500000.0,
        "host_name": "Rohan & Meera",
        "host_phone": "+919988776655"
    }
    event_res = requests.post(f"{RENDER_URL}/api/v1/events", json=event_payload, timeout=15)
    assert event_res.status_code == 201, f"Create event failed: {event_res.text}"
    event_data = event_res.json()
    event_id = event_data["id"]
    print(f"Created event: {event_id}", flush=True)

    try:
        # 3. Upload 2 sample inspiration images
        print("\n3. Uploading 2 inspiration images to /vibe/upload...", flush=True)
        img1 = create_sample_inspiration_image("#800020", "#FFD700", "Royal Marigold & Antique Gold")
        img2 = create_sample_inspiration_image("#FF9933", "#2E8B57", "Vibrant Rajasthani Courtyard")

        files = [
            ("files", ("inspiration_1.jpg", img1, "image/jpeg")),
            ("files", ("inspiration_2.jpg", img2, "image/jpeg"))
        ]
        data = {
            "text_description": "Traditional Royal Rajasthani palace wedding with warm marigold yellow, deep burgundy, and vintage brass lamps."
        }

        upload_res = requests.post(
            f"{RENDER_URL}/api/v1/events/{event_id}/vibe/upload",
            files=files,
            data=data,
            timeout=60
        )
        assert upload_res.status_code == 201, f"Upload failed: {upload_res.text}"
        profile = upload_res.json()
        profile_id = profile["profile_id"]
        print(f"Created Style Profile: {profile_id}", flush=True)
        print(f"Extracted Palette: {profile['extracted_palette']}", flush=True)
        print(f"Style Descriptors: {profile['style_tags']}", flush=True)
        print(f"Mood Keywords: {profile['mood_words']}", flush=True)
        assert len(profile["extracted_palette"]) == 5
        assert profile["uploaded_image_count"] == 2

        # 4. Generate Theme Proposal
        print(f"\n4. Generating concrete theme proposal via live Gemini model...", flush=True)
        theme_res = requests.post(
            f"{RENDER_URL}/api/v1/events/{event_id}/vibe/{profile_id}/generate-theme",
            timeout=90
        )
        assert theme_res.status_code == 201, f"Generate theme failed: {theme_res.text}"
        theme = theme_res.json()
        print(f"Theme Name: {theme['theme_name']}", flush=True)
        print(f"Provider Used: {theme['provider_used']}", flush=True)
        print(f"Fallback Warning: {theme['fallback_warning']}", flush=True)
        print(f"Culinary Direction: {theme['menu_direction']}", flush=True)
        print(f"Playlist Genres: {theme['playlist_genres']}", flush=True)
        print(f"Dress Code: {theme['dress_code_suggestion']}", flush=True)
        print(f"Invitation Brief: {theme['invitation_design_brief']}", flush=True)
        print(f"Total Decor Items Proposed: {len(theme['decor_items'])}", flush=True)
        assert len(theme["decor_items"]) >= 10, f"Expected >=10 items, got {len(theme['decor_items'])}"

        # Print all decor items with formula & cost resolution
        print("\n--- Proposed Decor Elements ---", flush=True)
        for idx, item in enumerate(theme["decor_items"], 1):
            print(f"{idx}. [{item['category']}] {item['name']} | Formula: '{item['quantity_formula']}' -> Qty: {item['computed_quantity']} | Cost: Rs. {item['cost_range_low']:,.0f} - Rs. {item['cost_range_high']:,.0f} ({item['cost_tier']}) | Sourcing: {item['sourcing_type']}", flush=True)

        # 5. Fetch Mood Board Collage
        print(f"\n5. Fetching generated Pillow mood board collage...", flush=True)
        mb_res = requests.get(f"{RENDER_URL}/api/v1/events/{event_id}/vibe/{profile_id}/moodboard", timeout=20)
        assert mb_res.status_code == 200, f"Moodboard failed: {mb_res.status_code}"
        assert mb_res.headers["content-type"] == "image/jpeg"
        print(f"Moodboard received: {len(mb_res.content)} bytes JPEG image.", flush=True)

        # 6. Granular Acceptance: Accept first decor item
        first_item = theme["decor_items"][0]
        item_id = first_item["id"]
        print(f"\n6. Accepting decor item '{first_item['name']}' ({item_id})...", flush=True)
        accept_res = requests.post(f"{RENDER_URL}/api/v1/events/{event_id}/vibe/decor-items/{item_id}/accept", timeout=15)
        assert accept_res.status_code == 200, f"Accept failed: {accept_res.text}"
        accepted_item = accept_res.json()
        print(f"Accepted item status: {accepted_item['status']}", flush=True)
        print(f"Linked BudgetItem ID: {accepted_item['budget_item_id']}", flush=True)
        print(f"Linked Task ID: {accepted_item['task_id']}", flush=True)
        assert accepted_item["status"] == "accepted"
        assert accepted_item["budget_item_id"] is not None
        assert accepted_item["task_id"] is not None

        # 7. Granular Rejection: Reject second decor item
        second_item = theme["decor_items"][1]
        print(f"\n7. Rejecting decor item '{second_item['name']}'...", flush=True)
        reject_res = requests.post(f"{RENDER_URL}/api/v1/events/{event_id}/vibe/decor-items/{second_item['id']}/reject", timeout=15)
        assert reject_res.status_code == 200
        assert reject_res.json()["status"] == "rejected"
        print(f"Item rejected successfully.", flush=True)

        print("\n M3 ACCEPTANCE CRITERIA VERIFIED LIVE IN PRODUCTION!", flush=True)

    finally:
        print(f"\nCleaning up test event {event_id}...", flush=True)
        del_res = requests.delete(f"{RENDER_URL}/api/v1/events/{event_id}", timeout=15)
        print(f"Deleted event: {del_res.status_code}", flush=True)

if __name__ == "__main__":
    run_live_verification()
