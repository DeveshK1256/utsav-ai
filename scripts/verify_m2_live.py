import json
import sys
import urllib.request
import urllib.error
from datetime import date, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RENDER_BASE = "https://utsav-ai-ycg2.onrender.com/api/v1"
DB_URL = "postgresql://utsav_db_nrue_user:FDjZCVInjYxzZc2tmvc5bjuPrrPA65Rx@dpg-dbcddfmq1p3s73d2ug20-a.singapore-postgres.render.com/utsav_db_nrue"

def api_request(url: str, method: str = "GET", data: dict = None):
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(err_body)
        except Exception:
            return e.code, {"raw_error": err_body}

def main():
    print("=== LIVE VERIFICATION: MILESTONE M2 (F1 REPLANNING ENGINE) ===")
    print(f"Target Render Service: {RENDER_BASE}")
    print(f"Target Database: Singapore Managed PostgreSQL (Render)")

    engine = create_engine(DB_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    # Step 1: Create Test Event on Render
    print("\n--- Step 1: Create Live Test Event ---")
    event_payload = {
        "name": "Live Plan B Verification Wedding",
        "event_type": "wedding",
        "guest_count": 150,
        "total_budget": 1500000.0,
        "city": "Pune",
        "pincode": "411001",
        "host_phone": "+919876543299",
        "host_name": "M2 Live Tester",
        "start_date": (date.today() + timedelta(days=60)).isoformat(),
        "end_date": (date.today() + timedelta(days=62)).isoformat()
    }
    status, ev_res = api_request(f"{RENDER_BASE}/events", method="POST", data=event_payload)
    print(f"Create Event Status: {status}")
    event_id = ev_res["id"]
    print(f"Created Event ID: {event_id} (guest_count=150, budget=1500000)")

    # Set venue_capacity=200 and seed budget items directly in live DB
    with engine.connect() as conn:
        conn.execute(
            text("UPDATE events SET venue_capacity = 200 WHERE id = :id"),
            {"id": event_id}
        )
        # Seed 4 budget items
        conn.execute(
            text("""
                INSERT INTO budget_items (id, event_id, category, name, planned_amount, actual_amount, is_paid, scaling_rule, created_at)
                VALUES
                (gen_random_uuid()::text, :id, 'catering', 'Royal Maharajah Banquet', 450000.00, 0.00, false, 'per_guest', NOW()),
                (gen_random_uuid()::text, :id, 'venue', 'Heritage Grand Ballroom', 300000.00, 150000.00, true, 'fixed', NOW()),
                (gen_random_uuid()::text, :id, 'decor', 'Vedic Floral Mandap', 200000.00, 0.00, false, 'tiered', NOW()),
                (gen_random_uuid()::text, :id, 'rentals', 'AC Units & Royal Seating', 100000.00, 0.00, false, 'per_guest', NOW())
            """),
            {"id": event_id}
        )
        conn.commit()

    # Step 2: Request Replanning Proposal: guest_count_changed 150 -> 220
    print("\n--- Step 2: Submit Change Proposal (150 -> 220 guests, venue_capacity=200) ---")
    change_req = {
        "change_type": "guest_count_changed",
        "payload": {
            "from_guest_count": 150,
            "to_guest_count": 220
        }
    }
    status, proposal = api_request(f"{RENDER_BASE}/events/{event_id}/changes", method="POST", data=change_req)
    print(f"Proposal Response Status: {status}")
    change_id = proposal["change_id"]
    print(f"Change ID: {change_id}")
    print(f"Proposal Status: {proposal['status']}")
    print(f"Capacity Alert: {proposal['capacity_warning']}")
    print(f"AI Explanation: {proposal['explanation']}")
    print(f"Mitigations Count: {len(proposal.get('mitigation_suggestions', []))}")
    print(f"Budget Old: ₹{proposal['budget_total_old']:,.2f} -> New: ₹{proposal['budget_total_new']:,.2f} (Delta: ₹{proposal['budget_total_delta']:+,.2f})")

    diffs = {d["category"]: d for d in proposal["budget_diff"]}
    print("\nItemized Deterministic Diffs:")
    for cat, d in diffs.items():
        print(f"  [{cat}] Rule: {d['scaling_rule']} | Old: ₹{d['old_amount']:,.2f} -> New: ₹{d['new_amount']:,.2f} (Diff: ₹{d['difference']:+,.2f})")
        print(f"         Formula: {d['formula']}")

    # Assertions on Proposal
    assert proposal["status"] == "pending", f"Expected pending, got {proposal['status']}"
    assert proposal["capacity_warning"] is not None and "220" in proposal["capacity_warning"], "Missing capacity warning"
    assert diffs["catering"]["new_amount"] == 660000.0, f"Expected 660000 catering, got {diffs['catering']['new_amount']}"
    assert diffs["venue"]["new_amount"] == 300000.0, "Venue must remain fixed"

    # Step 3: Verify Master DB is UNTOUCHED before accept
    print("\n--- Step 3: Verify Zero Pre-Accept DB Mutations ---")
    with engine.connect() as conn:
        res = conn.execute(text("SELECT guest_count FROM events WHERE id = :id"), {"id": event_id}).scalar()
        print(f"Live DB events.guest_count before accept: {res} (Must be 150)")
        assert res == 150, f"DB was prematurely mutated! Got {res}"

        cat_amt = conn.execute(
            text("SELECT planned_amount FROM budget_items WHERE event_id = :id AND category = 'catering'"),
            {"id": event_id}
        ).scalar()
        print(f"Live DB catering planned_amount before accept: ₹{cat_amt:,.2f} (Must be ₹450,000.00)")
        assert float(cat_amt) == 450000.0, "Catering budget prematurely mutated!"

    # Step 4: Accept Proposal via Live API
    print("\n--- Step 4: Explicit User Acceptance (/accept) ---")
    status, accept_res = api_request(f"{RENDER_BASE}/events/{event_id}/changes/{change_id}/accept", method="POST")
    print(f"Accept Response Status: {status}")
    print(f"Updated Proposal Status: {accept_res['status']}")
    assert accept_res["status"] == "applied", f"Expected applied, got {accept_res['status']}"

    # Step 5: Verify Live DB IS Atomic-Mutated After Accept
    print("\n--- Step 5: Verify Database Atomic Mutations After Accept ---")
    with engine.connect() as conn:
        res_after = conn.execute(text("SELECT guest_count FROM events WHERE id = :id"), {"id": event_id}).scalar()
        print(f"Live DB events.guest_count after accept: {res_after} (Expected: 220)")
        assert res_after == 220, f"DB guest_count failed to update! Got {res_after}"

        cat_amt_after = conn.execute(
            text("SELECT planned_amount FROM budget_items WHERE event_id = :id AND category = 'catering'"),
            {"id": event_id}
        ).scalar()
        print(f"Live DB catering planned_amount after accept: ₹{cat_amt_after:,.2f} (Expected: ₹660,000.00)")
        assert float(cat_amt_after) == 660000.0, "Catering failed to update!"

        log_count = conn.execute(
            text("SELECT count(*) FROM event_log WHERE event_id = :id AND action_type LIKE 'change_proposal_applied%'"),
            {"id": event_id}
        ).scalar()
        print(f"Live DB audit log records written: {log_count}")
        assert log_count > 0, "Missing event_log record!"

    # Step 6: Test Infeasibility Gating Live
    print("\n--- Step 6: Test Infeasibility Guard Live ---")
    infeasible_req = {
        "change_type": "date_moved",
        "payload": {
            "from_date": (date.today() + timedelta(days=60)).isoformat(),
            "to_date": (date.today() - timedelta(days=10)).isoformat() # Past date!
        }
    }
    status, infeasible_res = api_request(f"{RENDER_BASE}/events/{event_id}/changes", method="POST", data=infeasible_req)
    print(f"Infeasible Submit Status: {status}")
    print(f"Infeasible Proposal Status: {infeasible_res['status']}")
    print(f"Infeasibility Reason: {infeasible_res['infeasibility_reason']}")
    assert infeasible_res["status"] == "blocked_infeasible"
    assert "earlier than today" in infeasible_res["infeasibility_reason"]

    # Attempt to accept blocked proposal
    status_bad, bad_accept = api_request(
        f"{RENDER_BASE}/events/{event_id}/changes/{infeasible_res['change_id']}/accept",
        method="POST"
    )
    print(f"Attempt to accept infeasible proposal returned HTTP {status_bad} (Must be 400)")
    assert status_bad == 400, f"Infeasible accept should be 400, got {status_bad}"

    # Step 7: Clean Up Test Event
    print("\n--- Step 7: Clean Up Live Verification Event ---")
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM events WHERE id = :id"), {"id": event_id})
        conn.commit()
    print(f"Cleaned up event {event_id}. Verification complete with zero leftover records.")
    print("\n>>> ALL M2 LIVE PRODUCTION ACCEPTANCE CHECKS PASSED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    main()
