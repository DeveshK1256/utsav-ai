import time
import httpx

BASE_URL = "https://utsav-ai-ycg2.onrender.com/api/v1"

def run_live_verification():
    print("=" * 80)
    print("       UTSAV STAGE 4: COMPOSE CELEBRATION LIVE API VERIFICATION")
    print("=" * 80)

    # 1. Health check
    print("\n[1] Pinging Render API Health Check...")
    with httpx.Client(timeout=60.0) as client:
        try:
            r = client.get("https://utsav-ai-ycg2.onrender.com/health")
            print(f"Health response ({r.status_code}):", r.json())
        except Exception as e:
            print("Failed to reach health endpoint:", e)
            return

        # 2. Create a test event for Stage 4
        print("\n[2] Creating Live Test Event in Singapore PostgreSQL...")
        event_payload = {
            "name": "Ananya & Kabir Stage 4 Wedding",
            "event_type": "wedding",
            "tradition": "marathi",
            "city": "Pune",
            "city_tier": "tier_1",
            "guest_count": 250,
            "total_budget": 1500000.0,
            "start_date": "2026-11-20",
            "end_date": "2026-11-22",
            "owner_name": "Kabir Deshmukh",
            "owner_phone": "+919876543210"
        }
        r = client.post(f"{BASE_URL}/events", json=event_payload)
        assert r.status_code in (200, 201), f"Event creation failed: {r.text}"
        event = r.json()
        event_id = event["id"]
        print(f"Created Event ID: {event_id} ({event['name']})")

        # 3. Step A: Shortlist Venue via Compose Celebration
        print("\n[3] Step A — Shortlisting Venue (Sunny's World, Pashan-Sus Road)...")
        compose_step_a = {
            "step": "venue",
            "venue_name": "Sunny's World",
            "venue_locality": "Pashan-Sus Road, Pune",
            "venue_skipped": False
        }
        r = client.post(f"{BASE_URL}/events/{event_id}/compose", json=compose_step_a)
        assert r.status_code == 200, f"Compose Step A failed: {r.text}"
        event_after_a = r.json()
        compose_meta = event_after_a.get("metadata_json", {}).get("compose_celebration", {})
        print("Persisted Compose State after Step A:", compose_meta)
        assert compose_meta.get("venue_name") == "Sunny's World"
        assert compose_meta.get("venue_status") == "shortlist_pick", f"Expected shortlist_pick, got {compose_meta.get('venue_status')}"

        # 4. Step B: Confirm Muhurat Window
        print("\n[4] Step B — Confirming Muhurat Window (सकाळी १०:१५ ते दुपारी १२:००)...")
        compose_step_b = {
            "step": "timing",
            "muhurat_time": "सकाळी १०:१५ ते दुपारी १२:००",
            "muhurat_locked": True,
            "timing_skipped": False
        }
        r = client.post(f"{BASE_URL}/events/{event_id}/compose", json=compose_step_b)
        assert r.status_code == 200, f"Compose Step B failed: {r.text}"
        event_after_b = r.json()
        meta_b = event_after_b.get("metadata_json", {})
        print("Persisted Metadata after Step B:", meta_b.get("compose_celebration"))
        assert meta_b.get("muhurat_time") == "सकाळी १०:१५ ते दुपारी १२:००"

        # 5. Step C: Verify Invitation Options seamlessly consumes Stage 4 outputs
        print("\n[5] Step C — Verifying Invitation Options Auto-Wiring...")
        r = client.get(f"{BASE_URL}/events/{event_id}/invitations/options")
        assert r.status_code == 200, f"Options query failed: {r.text}"
        options = r.json()
        event_details = options.get("event_details", {})
        print("Event Details consumed by Invitation Studio:")
        print(f"  • Confirmed Venue: {event_details.get('venue')}")
        print(f"  • Confirmed Muhurat: {event_details.get('muhurat_time')}")
        assert "Sunny's World" in str(event_details.get('venue'))
        assert "सकाळी १०:१५" in str(event_details.get('muhurat_time'))

        # 6. Generate Invitation Card
        print("\n[6] Generating Invitation Card via M10 Pillow Service...")
        gen_payload = {
            "layout_variant": "classic_royal",
            "wording_variant_index": 0
        }
        r = client.post(f"{BASE_URL}/events/{event_id}/invitations/generate", json=gen_payload)
        assert r.status_code == 200, f"Card generation failed: {r.text}"
        cards = r.json()
        print(f"Generated {len(cards)} card(s). First card ID: {cards[0]['id']}")
        card_id = cards[0]["id"]

        # 7. Download PNG & PDF and verify magic bytes
        print("\n[7] Verifying Download Formats & Magic Bytes...")
        r_png = client.get(f"{BASE_URL}/events/{event_id}/invitations/{card_id}/download?format=png")
        assert r_png.status_code == 200
        assert r_png.content.startswith(b"\x89PNG\r\n\x1a\n"), "Invalid PNG magic header"
        print(f"  ✓ PNG downloaded successfully: {len(r_png.content)} bytes (Magic: PNG header confirmed)")

        r_pdf = client.get(f"{BASE_URL}/events/{event_id}/invitations/{card_id}/download?format=pdf")
        assert r_pdf.status_code == 200
        assert r_pdf.content.startswith(b"%PDF"), "Invalid PDF magic header"
        print(f"  ✓ PDF downloaded successfully: {len(r_pdf.content)} bytes (Magic: %PDF header confirmed)")

        # 8. Skip-flow verification on second event
        print("\n[8] Verifying All-Skips Flow (Zero Hallucination Guarantee)...")
        skip_event_payload = {
            "name": "Pooja All-Skips Celebration",
            "event_type": "birthday",
            "tradition": "general",
            "city": "Jaipur",
            "city_tier": "tier_2",
            "guest_count": 50,
            "total_budget": 200000.0,
            "start_date": "2026-12-05",
            "end_date": "2026-12-05",
            "owner_name": "Pooja Sharma",
            "owner_phone": "+919876543211"
        }
        r = client.post(f"{BASE_URL}/events", json=skip_event_payload)
        skip_event = r.json()
        skip_id = skip_event["id"]

        # Skip venue
        client.post(f"{BASE_URL}/events/{skip_id}/compose", json={"step": "venue", "venue_skipped": True})
        # Skip timing
        client.post(f"{BASE_URL}/events/{skip_id}/compose", json={"step": "timing", "timing_skipped": True})

        r_skip_opt = client.get(f"{BASE_URL}/events/{skip_id}/invitations/options")
        skip_details = r_skip_opt.json().get("event_details", {})
        print("Skip Details in Invitation Studio:")
        print(f"  • Venue: {skip_details.get('venue')}")
        print(f"  • Muhurat: {skip_details.get('muhurat_time')}")
        assert skip_details.get("venue") is None
        assert skip_details.get("muhurat_time") is None
        print("  ✓ Zero hallucination confirmed: Venue and Muhurat correctly None when skipped!")

        print("\n" + "=" * 80)
        print("       ALL STAGE 4 LIVE VERIFICATION CHECKS PASSED GREEN!")
        print("=" * 80)

if __name__ == "__main__":
    run_live_verification()
