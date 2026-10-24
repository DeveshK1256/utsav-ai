import sys
import time
import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "https://utsav-ai-ycg2.onrender.com/api/v1"

# Known 19 curated seed venues for verification
KNOWN_19_VENUES = [
    # Jaipur (11)
    "Fairmont Jaipur", "Jaipur Marriott Hotel", "ITC Rajputana", "Rambagh Palace",
    "Samode Palace", "Golden Tulip Jaipur", "Royal Palace Marriage Garden & Banquet Hall",
    "Gathbandhan Marriage Garden & Banquet Hall", "Jaipur Exhibition & Convention Centre",
    "Heera Valley Resort", "Chandan Van",
    # Pune (8)
    "Bharti Banquet & Lawn", "Mahalaxmi Lawns", "Ranade's Magenta Lawns",
    "Kalashree Banquets", "Indraprasth Lawns", "Shubharambh Banquet Hall",
    "Shivai Lawns", "Tejomaya Lawns and Banquet"
]

def run_live_verification():
    print("=" * 80)
    print("  UTSAV STAGE 4: COMPREHENSIVE INTEGRATION VERIFICATION (STAGES 1, 3, 4)")
    print("=" * 80)

    with httpx.Client(timeout=60.0) as client:
        # 1. Health check
        print("\n[1] Pinging Render API Health Check...")
        r = client.get("https://utsav-ai-ycg2.onrender.com/health")
        print(f"Health response ({r.status_code}):", r.json())
        assert r.status_code == 200

        # 2. Query Stage 3 Discovery Endpoint for Real Seed Venues (Pune coordinates)
        print("\n[2] Stage 3 Integration: Querying GET /discovery/vendors (Lat 18.5204, Lng 73.8567)...")
        r_disc = client.get(f"{BASE_URL}/discovery/vendors", params={
            "latitude": 18.5204,
            "longitude": 73.8567,
            "radius_km": 25.0
        })
        assert r_disc.status_code == 200, f"Discovery query failed: {r_disc.text}"
        disc_data = r_disc.json()
        venues = disc_data.get("vendors", [])
        print(f"Discovery returned {len(venues)} venues in radius:")
        for v in venues:
            print(f"  • {v['business_name']} ({v.get('locality', 'N/A')}) - {v.get('distance_km', 'N/A')} km [ID: {v['id']}]")

        assert len(venues) > 0, "No venues returned by discovery!"
        chosen_venue = venues[0]  # Nearest real venue
        chosen_venue_id = chosen_venue["id"]
        chosen_venue_name = chosen_venue["business_name"]
        chosen_locality = chosen_venue.get("locality")

        print(f"\nSelected Venue for Step A: '{chosen_venue_name}' ({chosen_locality})")
        assert chosen_venue_name in KNOWN_19_VENUES, f"Venue '{chosen_venue_name}' is not in known 19 seed venues list!"
        print(f"✓ Confirmed: '{chosen_venue_name}' is in the real 19-venue curated seed directory.")

        # 3. Create a test event for Stage 4
        print("\n[3] Creating Live Test Event in Singapore PostgreSQL...")
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

        # 4. Step A Integrity Guard: Verify that arbitrary fake IDs and bare strings are rejected
        print("\n[4] Step A Integrity Guard Check (Rejecting Fake/Bare Venue Strings)...")
        fake_id = "00000000-0000-0000-0000-000000000000"
        r_fake = client.post(f"{BASE_URL}/events/{event_id}/compose", json={
            "step": "venue",
            "vendor_profile_id": fake_id
        })
        print(f"  • Non-existent ID response: {r_fake.status_code} ({r_fake.json().get('detail')})")
        assert r_fake.status_code == 404, "Expected 404 for non-existent vendor_profile_id"

        r_bare = client.post(f"{BASE_URL}/events/{event_id}/compose", json={
            "step": "venue",
            "venue_name": "Fabricated Unverified Banquets"
        })
        print(f"  • Bare unverified string response: {r_bare.status_code} ({r_bare.json().get('detail')})")
        assert r_bare.status_code == 400, "Expected 400 when vendor_profile_id is missing and skip_venue=False"
        print("✓ Confirmed: Step A strictly rejects fabricated venues and unverified strings.")

        # 5. Step A Execution: Persist the real chosen vendor_profile_id
        print(f"\n[5] Step A Execution: Shortlisting '{chosen_venue_name}' via Real vendor_profile_id...")
        r_step_a = client.post(f"{BASE_URL}/events/{event_id}/compose", json={
            "step": "venue",
            "vendor_profile_id": chosen_venue_id
        })
        assert r_step_a.status_code == 200, f"Compose Step A failed: {r_step_a.text}"
        event_after_a = r_step_a.json()
        compose_meta = event_after_a.get("metadata_json", {}).get("compose_celebration", {})
        print("Persisted Compose State after Step A:")
        print(f"  • vendor_profile_id: {compose_meta.get('vendor_profile_id')}")
        print(f"  • venue_name:        {compose_meta.get('venue_name')}")
        print(f"  • venue_locality:    {compose_meta.get('venue_locality')}")
        print(f"  • venue_status:      {compose_meta.get('venue_status')}")
        print(f"  • venue_skipped:     {compose_meta.get('venue_skipped')}")
        assert compose_meta.get("vendor_profile_id") == chosen_venue_id
        assert compose_meta.get("venue_name") == chosen_venue_name
        assert compose_meta.get("venue_status") == "shortlist_pick"
        print("✓ Confirmed: Real vendor_profile_id from Stage 3 successfully persisted.")

        # 6. Stage 1 Integration: Query real M5 ephemeris calculation for muhurat candidates
        print("\n[6] Stage 1 Integration: Querying GET /rituals/muhurat-candidates...")
        r_muhurat = client.get(f"{BASE_URL}/rituals/muhurat-candidates", params={
            "event_date": "2026-11-20",
            "latitude": 18.5204,
            "longitude": 73.8567
        })
        assert r_muhurat.status_code == 200, f"Muhurat calculation failed: {r_muhurat.text}"
        muhurat_data = r_muhurat.json()
        print("Real Computed Panchang Summary for 2026-11-20 (Pune):")
        panchang_summary = muhurat_data.get("panchang_summary", {})
        print(f"  • Sunrise:   {panchang_summary.get('sunrise')}")
        print(f"  • Sunset:    {panchang_summary.get('sunset')}")
        print(f"  • Tithi:     {panchang_summary.get('tithi')}")
        print(f"  • Nakshatra: {panchang_summary.get('nakshatra')}")
        print(f"  • Rahu Kaal: {panchang_summary.get('rahu_kaal')}")

        candidate_windows = muhurat_data.get("candidate_windows", [])
        print(f"\nAstronomical Candidate Windows ({len(candidate_windows)} calculated):")
        for idx, cw in enumerate(candidate_windows):
            print(f"  [{idx + 1}] {cw['name']}: {cw['start_time']} - {cw['end_time']} ({cw['quality']})")

        assert len(candidate_windows) > 0, "No candidate windows returned by ephemeris engine!"
        chosen_window = candidate_windows[0]
        chosen_time_str = f"{chosen_window['start_time']} - {chosen_window['end_time']} ({chosen_window['name']})"
        print(f"\nSelected Live Computed Muhurat for Step B: '{chosen_time_str}'")

        # 7. Step B Execution: Confirm real computed muhurat
        print("\n[7] Step B Execution: Confirming Real Computed Muhurat in Compose Celebration...")
        r_step_b = client.post(f"{BASE_URL}/events/{event_id}/compose", json={
            "step": "timing",
            "muhurat_time": chosen_time_str,
            "muhurat_locked": True,
            "timing_skipped": False
        })
        assert r_step_b.status_code == 200, f"Compose Step B failed: {r_step_b.text}"
        event_after_b = r_step_b.json()
        meta_b = event_after_b.get("metadata_json", {})
        print("Persisted Metadata after Step B:")
        print(f"  • muhurat_time:   {meta_b.get('muhurat_time')}")
        print(f"  • muhurat_locked: {meta_b.get('compose_celebration', {}).get('muhurat_locked')}")
        assert meta_b.get("muhurat_time") == chosen_time_str
        assert meta_b.get("compose_celebration", {}).get("muhurat_locked") is True
        print("✓ Confirmed: Live ephemeris computed muhurat successfully persisted and locked.")

        # 8. Step C: Verify M10 Invitation Studio Auto-Wiring
        print("\n[8] Step C: Verifying Invitation Options Auto-Wiring from Stages 1 & 3...")
        r_opt = client.get(f"{BASE_URL}/events/{event_id}/invitations/options")
        assert r_opt.status_code == 200, f"Options query failed: {r_opt.text}"
        options = r_opt.json()
        print("Logistics consumed by Invitation Studio:")
        print(f"  • Confirmed Venue:   {options.get('venue_str')}")
        print(f"  • Confirmed Muhurat: {options.get('muhurat_time')}")
        assert chosen_venue_name in str(options.get("venue_str"))
        assert chosen_window["start_time"] in str(options.get("muhurat_time"))
        print("✓ Confirmed: Invitation Studio consumed both real Stage 3 venue and real Stage 1 muhurat.")

        # 9. Generate Card & Verify Formats
        print("\n[9] Generating Card via M10 Pillow Service...")
        r_gen = client.post(f"{BASE_URL}/events/{event_id}/invitations/generate", json={
            "layout_variant": "classic_royal",
            "wording_variant_index": 0
        })
        assert r_gen.status_code in (200, 201), f"Card generation failed: {r_gen.text}"
        batch = r_gen.json()
        cards = batch.get("cards", [])
        assert len(cards) > 0
        card_id = cards[0]["id"]
        print(f"Generated Card ID: {card_id}")

        r_png = client.get(f"{BASE_URL}/events/{event_id}/invitations/{card_id}/download?format=png")
        assert r_png.status_code == 200 and r_png.content.startswith(b"\x89PNG\r\n\x1a\n")
        print(f"  ✓ PNG downloaded: {len(r_png.content)} bytes (Magic: \\x89PNG confirmed)")

        r_pdf = client.get(f"{BASE_URL}/events/{event_id}/invitations/{card_id}/download?format=pdf")
        assert r_pdf.status_code == 200 and r_pdf.content.startswith(b"%PDF")
        assert b"/FlateDecode" in r_pdf.content, "PDF is not using lossless FlateDecode compression!"
        print(f"  ✓ PDF downloaded: {len(r_pdf.content)} bytes (Magic: %PDF & Lossless FlateDecode confirmed)")

        # 10. Verify All-Skips Flow (Zero Hallucination)
        print("\n[10] Verifying All-Skips Flow (Zero Hallucination Guarantee)...")
        r_skip_ev = client.post(f"{BASE_URL}/events", json={
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
        })
        skip_id = r_skip_ev.json()["id"]

        client.post(f"{BASE_URL}/events/{skip_id}/compose", json={"step": "venue", "skip_venue": True})
        client.post(f"{BASE_URL}/events/{skip_id}/compose", json={"step": "timing", "skip_timing": True})

        r_skip_opt = client.get(f"{BASE_URL}/events/{skip_id}/invitations/options")
        skip_opts = r_skip_opt.json()
        print("Skip Details in Invitation Studio:")
        print(f"  • Venue:   {skip_opts.get('venue_str')}")
        print(f"  • Muhurat: {skip_opts.get('muhurat_time')}")
        assert "to be confirmed" in skip_opts.get("venue_str", "")
        assert skip_opts.get("muhurat_time") is None
        print("✓ Confirmed: Venue is honest placeholder and Muhurat is None when skipped.")

        print("\n" + "=" * 80)
        print("   ALL STAGE 4 INTEGRATION CHECKS (STAGES 1, 3, 4) PASSED 100% GREEN!")
        print("=" * 80)

if __name__ == "__main__":
    run_live_verification()
