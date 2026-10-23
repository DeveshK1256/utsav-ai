import io
import os
import sys
import json
import uuid
import random
from datetime import date, timedelta, datetime, timezone
import httpx
from PIL import Image
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RENDER_BASE = "https://utsav-ai-ycg2.onrender.com/api/v1"
LIVE_DB_URL = "postgresql://utsav_db_nrue_user:FDjZCVInjYxzZc2tmvc5bjuPrrPA65Rx@dpg-dbcddfmq1p3s73d2ug20-a.singapore-postgres.render.com/utsav_db_nrue"

def main():
    print("=" * 80)
    print("LIVE VERIFICATION: MILESTONE M10 (F16 INVITATION CARD GENERATOR)")
    print(f"Target Render API: {RENDER_BASE}")
    print(f"Target Database: Singapore Managed PostgreSQL (Render)")
    print("=" * 80)

    engine = create_engine(LIVE_DB_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    test_user_id = str(uuid.uuid4())
    test_event_id = str(uuid.uuid4())
    test_profile_id = str(uuid.uuid4())
    test_theme_id = str(uuid.uuid4())
    test_guest_ids = [str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())]

    try:
        # Step 1: Seed User and Event in Live Postgres
        print("\n--- Step 1: Create Live Test Event & Confirmed Theme in Singapore DB ---")
        phone_suffix = random.randint(10000000, 99999999)
        db.execute(text("""
            INSERT INTO users (id, phone_number, full_name, role, preferred_language, created_at, updated_at)
            VALUES (:id, :phone, 'M10 Live Host', 'host', 'mr', NOW(), NOW());
        """), {"id": test_user_id, "phone": f"+9199{phone_suffix}"})

        start_dt = date.today() + timedelta(days=60)
        end_dt = date.today() + timedelta(days=62)
        meta = json.dumps({
            "host_name": "श्री व सौ. जोशी आणि परिवार",
            "venue": "आनंद मंगल कार्यालय, सदाशिव पेठ, पुणे",
            "muhurat_time": "सकाळी १०:४५ ते दुपारी १२:१५"
        })

        db.execute(text("""
            INSERT INTO events (id, owner_id, name, event_type, tradition_code, guest_count, total_budget, city, pincode, start_date, end_date, status, metadata_json, created_at)
            VALUES (:id, :owner_id, 'रोहन व अनन्या शुभविवाह', 'wedding', 'maharashtrian_vedic', 250, 2500000.0, 'Pune', '411030', :sdate, :edate, 'planning', :meta, NOW());
        """), {
            "id": test_event_id,
            "owner_id": test_user_id,
            "sdate": start_dt,
            "edate": end_dt,
            "meta": meta
        })

        # Style profile & Accepted Theme Proposal
        palette_json = json.dumps(["#991B1B", "#B45309", "#FEF3C7", "#1E3A8A", "#D97706"])
        tags_json = json.dumps(["Royal", "Traditional", "Marigold"])
        mood_json = json.dumps(["festive", "auspicious"])
        empty_refs = json.dumps([])
        db.execute(text("""
            INSERT INTO style_profiles (id, event_id, uploaded_image_refs, extracted_palette, style_tags, mood_words, text_description, created_at)
            VALUES (:id, :event_id, :refs, :palette, :tags, :mood, 'Royal traditional theme', NOW());
        """), {
            "id": test_profile_id,
            "event_id": test_event_id,
            "refs": empty_refs,
            "palette": palette_json,
            "tags": tags_json,
            "mood": mood_json
        })

        genres_json = json.dumps(["shehnai", "classical"])
        db.execute(text("""
            INSERT INTO theme_proposals (id, style_profile_id, theme_name, palette, playlist_genres, status, invitation_design_brief, created_at)
            VALUES (:id, :pid, 'राजेशाही झेंडू व कुंकू विवाह', :palette, :genres, 'accepted', 'पारंपरिक महाराष्ट्रीयन राजेशाही विवाह निमंत्रण पत्रिका.', NOW());
        """), {"id": test_theme_id, "pid": test_profile_id, "palette": palette_json, "genres": genres_json})

        # Step 2: Seed 3 Test Guests (including Devanagari script name)
        print("\n--- Step 2: Seed 3 Test Guests in Live DB ---")
        guest_specs = [
            (test_guest_ids[0], "Vikram Malhotra", f"+9198{random.randint(10000000, 99999999)}", "veg"),
            (test_guest_ids[1], "Dr. Aditi Sen", f"+9198{random.randint(10000000, 99999999)}", "jain"),
            (test_guest_ids[2], "श्री रमेश काळे व परिवार", f"+9198{random.randint(10000000, 99999999)}", "veg")
        ]

        for gid, gname, gphone, gdiet in guest_specs:
            db.execute(text("""
                INSERT INTO guests (id, event_id, name, phone, diet, rsvp_status, mobility_needs, kids_count, headcount, accommodation, language, needs_host_review, created_at, updated_at)
                VALUES (:id, :event_id, :name, :phone, :diet, 'pending', FALSE, 0, 1, FALSE, 'en', FALSE, NOW(), NOW());
            """), {"id": gid, "event_id": test_event_id, "name": gname, "phone": gphone, "diet": gdiet})

        db.commit()
        print(f"Created event {test_event_id} with 3 test guests:")
        for _, gn, gp, gd in guest_specs:
            print(f"  • {gn} ({gd}) - {gp}")

        # Step 3: Call Live Options Endpoint
        print("\n--- Step 3: Test GET /invitations/options on Render ---")
        with httpx.Client(timeout=30.0) as client:
            opt_res = client.get(f"{RENDER_BASE}/events/{test_event_id}/invitations/options")
            assert opt_res.status_code == 200, f"Options failed: {opt_res.text}"
            opt_data = opt_res.json()
            print("Layout options available:", [l["id"] for l in opt_data["layout_options"]])
            print(f"Theme: {opt_data.get('theme_name')}, Palette: {opt_data.get('palette')}")
            print(f"Wording variants generated ({opt_data.get('provider_used')}): {len(opt_data.get('wording_options', []))}")
            for w in opt_data.get("wording_options", []):
                print(f"  - [{w['id']}] {w['title']}: {w['body_text'][:70]}...")

            # Step 4: Call Live Batch Generation Endpoint
            print("\n--- Step 4: Test POST /invitations/generate on Render (3-guest batch) ---")
            gen_payload = {
                "theme_proposal_id": test_theme_id,
                "layout_variant": "classic_royal",
                "wording_variant_index": 0
            }
            gen_res = client.post(f"{RENDER_BASE}/events/{test_event_id}/invitations/generate", json=gen_payload)
            assert gen_res.status_code == 201, f"Generation failed: {gen_res.text}"
            gen_data = gen_res.json()

            print(f"Batch generation success! Total generated: {gen_data['total_generated']}, Total failed: {gen_data['total_failed']}")
            assert gen_data["total_generated"] == 3
            assert gen_data["total_failed"] == 0

            cards = gen_data["cards"]
            generated_names = [c["guest_name"] for c in cards]
            print(f"Cards generated for guests: {generated_names}")
            assert set(generated_names) == {"Vikram Malhotra", "Dr. Aditi Sen", "श्री रमेश काळे व परिवार"}

            # Step 5: Download & Visually Inspect Output for Devanagari Guest Card
            print("\n--- Step 5: Download & Visually Inspect Rendered Output ---")
            devanagari_card = next(c for c in cards if c["guest_name"] == "श्री रमेश काळे व परिवार")
            card_id = devanagari_card["id"]

            png_url = f"{RENDER_BASE}/events/{test_event_id}/invitations/{card_id}/download?format=png"
            pdf_url = f"{RENDER_BASE}/events/{test_event_id}/invitations/{card_id}/download?format=pdf"

            png_resp = client.get(png_url)
            assert png_resp.status_code == 200, f"PNG download failed: {png_resp.status_code}"
            assert png_resp.headers["content-type"] == "image/png"
            png_bytes = png_resp.content

            pdf_resp = client.get(pdf_url)
            assert pdf_resp.status_code == 200, f"PDF download failed: {pdf_resp.status_code}"
            assert pdf_resp.headers["content-type"] == "application/pdf"
            pdf_bytes = pdf_resp.content

            print(f"Downloaded PNG: {len(png_bytes)} bytes (Valid PNG header: {png_bytes[:8] == b'\x89PNG\r\n\x1a\n'})")
            print(f"Downloaded PDF: {len(pdf_bytes)} bytes (Valid PDF header: {pdf_bytes[:4] == b'%PDF'})")

            # Load into Pillow and inspect
            img = Image.open(io.BytesIO(png_bytes))
            print(f"Image format: {img.format}, Size: {img.size}, Mode: {img.mode}")
            assert img.size == (1200, 1800)

            # Save sample to artifacts directory for visual evidence
            artifact_dir = r"C:\Users\deves\.gemini\antigravity\brain\57333fd6-3848-479e-98dc-d6c0861fdff7"
            out_png_path = os.path.join(artifact_dir, "m10_rendered_invitation_devanagari.png")
            with open(out_png_path, "wb") as f:
                f.write(png_bytes)
            print(f"Saved visual artifact to {out_png_path}")

            # Verify no template placeholders leaked in raw wording text
            assert "{" not in devanagari_card["wording_preview"]
            assert "}" not in devanagari_card["wording_preview"]
            print("Verified: Zero template curly bracket placeholders leaked in card wording!")

    finally:
        # Step 6: Clean up live test data
        print("\n--- Step 6: Cleanup Live Test Records ---")
        try:
            db.rollback()
            db.execute(text("DELETE FROM events WHERE id = :id;"), {"id": test_event_id})
            db.execute(text("DELETE FROM users WHERE id = :id;"), {"id": test_user_id})
            db.commit()
            print("Cleaned up live test event and user successfully!")
        except Exception as e:
            print(f"Cleanup error (non-fatal): {e}")
        db.close()

    print("\n" + "=" * 80)
    print("ALL LIVE VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    main()
