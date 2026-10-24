import uuid
from datetime import date, timedelta, datetime, timezone
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.models.models import User, Event, BudgetItem, Task, SubEvent, ChangeEvent, AISuggestion, EventLog
from backend.app.services.budget_rescaling_engine import BudgetRescalingEngine

client = TestClient(app)


@pytest.fixture
def replanning_event():
    db = SessionLocal()
    # Create test host
    phone = f"+9198{uuid.uuid4().hex[:8]}"
    user = User(
        phone_number=phone,
        full_name="Replanning Test Host",
        role="host"
    )
    db.add(user)
    db.flush()

    # Create event with 150 guests, ₹1,500,000 budget, venue capacity 200
    event = Event(
        owner_id=user.id,
        name="Anand & Pooja Wedding",
        event_type="wedding",
        tradition_code="maharashtrian_vedic",
        guest_count=150,
        venue_capacity=200,
        total_budget=1500000.0,
        city="Pune",
        pincode="411001",
        start_date=date.today() + timedelta(days=60),
        end_date=date.today() + timedelta(days=62),
        status="planning"
    )
    db.add(event)
    db.flush()

    # Create budget items with scaling rules per DEC-018
    items = [
        BudgetItem(
            event_id=event.id,
            category="catering",
            name="Deluxe Wedding Feast",
            planned_amount=450000.0,
            actual_amount=0.0,
            is_paid=False,
            scaling_rule="per_guest"
        ),
        BudgetItem(
            event_id=event.id,
            category="venue",
            name="Heritage Palace Hall",
            planned_amount=300000.0,
            actual_amount=150000.0,
            is_paid=True,
            scaling_rule="fixed"
        ),
        BudgetItem(
            event_id=event.id,
            category="decor",
            name="Floral Mandap & Stage",
            planned_amount=200000.0,
            actual_amount=0.0,
            is_paid=False,
            scaling_rule="tiered"
        ),
        BudgetItem(
            event_id=event.id,
            category="rentals",
            name="Chiavari Chairs & AC Units",
            planned_amount=100000.0,
            actual_amount=0.0,
            is_paid=False,
            scaling_rule="per_guest"
        ),
        BudgetItem(
            event_id=event.id,
            category="photography",
            name="Candid Photo & Cinema",
            planned_amount=150000.0,
            actual_amount=0.0,
            is_paid=False,
            scaling_rule="fixed"
        )
    ]
    for it in items:
        db.add(it)

    # Create tasks
    task1 = Task(
        event_id=event.id,
        title="Finalize Catering Plates",
        scheduled_start=datetime.now(timezone.utc) + timedelta(days=10),
        scheduled_end=datetime.now(timezone.utc) + timedelta(days=11),
        duration_minutes=90,
        assigned_role="Food Lead",
        status="pending"
    )
    db.add(task1)

    # Create sub_event
    sub_event1 = SubEvent(
        event_id=event.id,
        name="Main Muhurat Lagna",
        start_time=datetime.now(timezone.utc) + timedelta(days=60),
        end_time=datetime.now(timezone.utc) + timedelta(days=60, hours=4),
        venue_name="Heritage Palace Hall",
        venue_address="Pune",
        is_muhurat_locked=True,
        sort_order=1
    )
    db.add(sub_event1)

    db.commit()
    event_id = event.id
    db.close()
    return event_id


def test_acceptance_criteria_guest_count_150_to_220(replanning_event):
    """
    Acceptance Test specified in M2 Brief:
    Simulate guest_count_changed 150 -> 220.
    1. Assert catering and rentals scale proportionally (220/150).
    2. Assert venue and photography remain fixed.
    3. Assert capacity exceeded warning since venue_capacity (200) < 220.
    4. Assert DB is UNTOUCHED before accept.
    5. Assert DB is mutated after accept.
    """
    event_id = replanning_event

    # 1. Submit proposal
    res = client.post(
        f"/api/v1/events/{event_id}/changes",
        json={
            "change_type": "guest_count_changed",
            "payload": {
                "from_guest_count": 150,
                "to_guest_count": 220
            }
        }
    )
    assert res.status_code == 201, res.text
    data = res.json()

    assert data["change_type"] == "guest_count_changed"
    assert data["status"] == "pending"
    change_id = data["change_id"]

    # 2. Check capacity alert
    assert data["capacity_warning"] is not None
    assert "220" in data["capacity_warning"]
    assert "200" in data["capacity_warning"]
    assert "20" in data["capacity_warning"]

    # 3. Check scaling calculations
    diffs = {d["category"]: d for d in data["budget_diff"]}

    # Catering: 450,000 * (220/150) = 660,000
    catering = diffs["catering"]
    assert catering["scaling_rule"] == "per_guest"
    assert catering["old_amount"] == 450000.0
    assert catering["new_amount"] == 660000.0
    assert catering["difference"] == 210000.0
    assert "450000.00 * (220/150)" in catering["formula"]

    # Rentals: 100,000 * (220/150) = 146,666.67
    rentals = diffs["rentals"]
    assert rentals["scaling_rule"] == "per_guest"
    assert rentals["old_amount"] == 100000.0
    assert rentals["new_amount"] == pytest.approx(146666.67, 0.01)

    # Venue: Fixed contract
    venue = diffs["venue"]
    assert venue["scaling_rule"] == "fixed"
    assert venue["new_amount"] == venue["old_amount"] == 300000.0
    assert venue["difference"] == 0.0

    # Photography: Fixed contract
    photo = diffs["photography"]
    assert photo["scaling_rule"] == "fixed"
    assert photo["new_amount"] == photo["old_amount"] == 150000.0
    assert photo["difference"] == 0.0

    # Decor: Tiered step check
    decor = diffs["decor"]
    assert decor["scaling_rule"] == "tiered"
    # Tier for 150 is Standard Banquet (1.00), tier for 220 is also Standard Banquet (1.00) -> 200,000 * (1.00/1.00) = 200,000
    assert decor["new_amount"] == 200000.0
    assert "Standard Banquet" in decor["formula"]
    assert "Remains in" in decor["formula"]

    # 4. Verify DB is completely UNTOUCHED prior to accept
    db = SessionLocal()
    ev = db.query(Event).filter(Event.id == event_id).first()
    assert ev.guest_count == 150  # Still 150!
    cat_db = [b for b in ev.budget_items if b.category == "catering"][0]
    assert float(cat_db.planned_amount) == 450000.0  # Still 450,000!
    db.close()

    # 5. User accepts proposal
    accept_res = client.post(f"/api/v1/events/{event_id}/changes/{change_id}/accept")
    assert accept_res.status_code == 200
    assert accept_res.json()["status"] == "applied"

    # 6. Verify DB IS mutated after accept
    db = SessionLocal()
    ev_updated = db.query(Event).filter(Event.id == event_id).first()
    assert ev_updated.guest_count == 220  # Mutated to 220!
    cat_db_updated = [b for b in ev_updated.budget_items if b.category == "catering"][0]
    assert float(cat_db_updated.planned_amount) == 660000.0  # Mutated to 660,000!

    # Verify EventLog recorded
    logs = db.query(EventLog).filter(EventLog.event_id == event_id).all()
    assert any("guest_count_changed" in l.action_type for l in logs)
    db.close()


def test_infeasibility_guards(replanning_event):
    """
    Asserts infeasible changes are caught and blocked with clear explanation:
    - Target date in the past
    - Budget cut below committed vendor contracts
    - Negative/zero guest count
    """
    event_id = replanning_event

    # 1. Past date
    past_date = (date.today() - timedelta(days=5)).isoformat()
    res1 = client.post(
        f"/api/v1/events/{event_id}/changes",
        json={
            "change_type": "date_moved",
            "payload": {
                "from_date": (date.today() + timedelta(days=60)).isoformat(),
                "to_date": past_date
            }
        }
    )
    assert res1.status_code == 201
    data1 = res1.json()
    assert data1["status"] == "blocked_infeasible"
    assert "earlier than today" in data1["infeasibility_reason"]

    # Verify cannot accept infeasible proposal
    accept_res = client.post(f"/api/v1/events/{event_id}/changes/{data1['change_id']}/accept")
    assert accept_res.status_code == 400

    # 2. Budget cut below committed contracts (venue is paid ₹150,000)
    res2 = client.post(
        f"/api/v1/events/{event_id}/changes",
        json={
            "change_type": "budget_cut",
            "payload": {
                "from_budget": 1500000.0,
                "to_budget": 100000.0  # Less than ₹150,000 committed!
            }
        }
    )
    assert res2.status_code == 201
    data2 = res2.json()
    assert data2["status"] == "blocked_infeasible"
    assert "already committed/paid" in data2["infeasibility_reason"]

    # 3. Invalid zero guest count
    res3 = client.post(
        f"/api/v1/events/{event_id}/changes",
        json={
            "change_type": "guest_count_changed",
            "payload": {
                "from_guest_count": 150,
                "to_guest_count": 0
            }
        }
    )
    assert res3.status_code == 201
    data3 = res3.json()
    assert data3["status"] == "blocked_infeasible"
    assert "positive integer" in data3["infeasibility_reason"]


def test_conflicting_changes_queueing_and_promotion(replanning_event):
    """
    Tests queueing mechanics:
    - If Change 1 is pending, Change 2 is queued.
    - When Change 1 is rejected, Change 2 is promoted to pending.
    """
    event_id = replanning_event

    # Create Change 1
    res1 = client.post(
        f"/api/v1/events/{event_id}/changes",
        json={
            "change_type": "vendor_cancelled",
            "payload": {
                "category": "photography",
                "vendor_name": "Studio Royal"
            }
        }
    )
    assert res1.status_code == 201
    data1 = res1.json()
    assert data1["status"] == "pending"
    change_1_id = data1["change_id"]

    # Create Change 2 while Change 1 is still pending
    res2 = client.post(
        f"/api/v1/events/{event_id}/changes",
        json={
            "change_type": "venue_unavailable",
            "payload": {
                "venue_name": "Heritage Palace Hall",
                "reason": "Water logging"
            }
        }
    )
    assert res2.status_code == 201
    data2 = res2.json()
    assert data2["status"] == "queued"
    change_2_id = data2["change_id"]

    # Reject Change 1
    rej1 = client.post(f"/api/v1/events/{event_id}/changes/{change_1_id}/reject")
    assert rej1.status_code == 200
    assert rej1.json()["status"] == "rejected"

    # Verify Change 2 got promoted to pending!
    get2 = client.get(f"/api/v1/events/{event_id}/changes/{change_2_id}")
    assert get2.status_code == 200
    assert get2.json()["status"] == "pending"


def test_manual_override_patching(replanning_event):
    """
    Tests user ability to patch/override proposed budget numbers before acceptance.
    """
    event_id = replanning_event

    # Create change
    res = client.post(
        f"/api/v1/events/{event_id}/changes",
        json={
            "change_type": "guest_count_changed",
            "payload": {
                "from_guest_count": 150,
                "to_guest_count": 180
            }
        }
    )
    data = res.json()
    change_id = data["change_id"]
    catering_item = [d for d in data["budget_diff"] if d["category"] == "catering"][0]
    catering_id = catering_item["budget_item_id"]

    # User overrides catering to ₹500,000 instead of computed 540,000
    patch_res = client.patch(
        f"/api/v1/events/{event_id}/changes/{change_id}",
        json={
            "budget_overrides": {
                catering_id: 500000.0
            }
        }
    )
    assert patch_res.status_code == 200
    patched_data = patch_res.json()
    patched_catering = [d for d in patched_data["budget_diff"] if d["budget_item_id"] == catering_id][0]
    assert patched_catering["new_amount"] == 500000.0
    assert "User manual override" in patched_catering["formula"]


def test_date_moved_and_vendor_cancelled_handlers(replanning_event):
    """
    Tests date_moved shifts tasks/sub_events and vendor_cancelled adds replacement tasks.
    """
    event_id = replanning_event

    # 1. Date moved test
    future_start = (date.today() + timedelta(days=60)).isoformat()
    moved_start = (date.today() + timedelta(days=70)).isoformat()

    res_date = client.post(
        f"/api/v1/events/{event_id}/changes",
        json={
            "change_type": "date_moved",
            "payload": {
                "from_date": future_start,
                "to_date": moved_start
            }
        }
    )
    assert res_date.status_code == 201
    data_date = res_date.json()
    assert len(data_date["task_diff"]["moved_tasks"]) > 0
    assert data_date["task_diff"]["moved_tasks"][0]["days_shifted"] == 10

    # Accept date move
    client.post(f"/api/v1/events/{event_id}/changes/{data_date['change_id']}/accept")
    db = SessionLocal()
    ev = db.query(Event).filter(Event.id == event_id).first()
    assert ev.start_date.isoformat() == moved_start
    db.close()


def test_tiered_decor_scaling_stepping_to_large_tier(replanning_event):
    """
    Tests tiered decor scaling across tier boundaries (150 -> 300 guests).
    150 guests: multiplier 1.00 (Standard Banquet)
    300 guests: multiplier 1.40 (Large Lawn / Ballroom)
    Decor amount: 200,000 * (1.40/1.00) = 280,000.
    """
    event_id = replanning_event

    res = client.post(
        f"/api/v1/events/{event_id}/changes",
        json={
            "change_type": "guest_count_changed",
            "payload": {
                "from_guest_count": 150,
                "to_guest_count": 300
            }
        }
    )
    assert res.status_code == 201
    data = res.json()
    decor = [d for d in data["budget_diff"] if d["category"] == "decor"][0]
    assert decor["new_amount"] == 280000.0
    assert "Stepped from" in decor["formula"]
    assert "Large Lawn / Ballroom" in decor["formula"]


def test_intake_generated_event_fixed_category_scaling_regression():
    """
    REGRESSION TEST: Events synthesized through the intake wizard (/intake/generate)
    must preserve DEC-018 scaling rules on budget items.
    Specifically asserts that fixed categories (venue, photography, entertainment, rituals)
    do NOT scale under guest-count changes when invoked through /events/{id}/changes.
    """
    import random
    unique_phone = f"+9198{random.randint(10000000, 99999999)}"
    intake_payload = {
        "name": "Regression Test Royal Vivah",
        "host_name": "Test Host",
        "phone_number": unique_phone,
        "event_type": "wedding",
        "tradition_code": "marwari_traditional",
        "guest_count": 280,
        "total_budget": 5200000.0,
        "city": "Jaipur",
        "pincode": "302001",
        "start_date": (date.today() + timedelta(days=60)).isoformat(),
        "end_date": (date.today() + timedelta(days=62)).isoformat()
    }

    # 1. Generate master plan via real intake endpoint
    gen_res = client.post("/api/v1/intake/generate", json=intake_payload)
    assert gen_res.status_code == 201
    gen_data = gen_res.json()
    event_id = gen_data["event_id"]
    auth_headers = {"X-Event-Owner-Token": gen_data["owner_token"]} if gen_data.get("owner_token") else {}

    try:
        # 2. Trigger Guest Surge (280 -> 330 guests) via the exact Live Scenario Simulator endpoint
        sim_res = client.post(
            f"/api/v1/events/{event_id}/changes",
            json={
                "change_type": "guest_count_changed",
                "payload": {
                    "from_guest_count": 280,
                    "to_guest_count": 330
                }
            },
            headers=auth_headers
        )
        assert sim_res.status_code == 201
        proposal = sim_res.json()
        diffs = {d["category"]: d for d in proposal["budget_diff"]}

        # Assert fixed categories do NOT scale
        assert diffs["venue"]["scaling_rule"] == "fixed"
        assert diffs["venue"]["old_amount"] == diffs["venue"]["new_amount"]
        assert diffs["venue"]["difference"] == 0.0
        assert "Fixed contract rate" in diffs["venue"]["formula"]

        assert diffs["photography"]["scaling_rule"] == "fixed"
        assert diffs["photography"]["old_amount"] == diffs["photography"]["new_amount"]
        assert diffs["photography"]["difference"] == 0.0

        assert diffs["entertainment"]["scaling_rule"] == "fixed"
        assert diffs["entertainment"]["old_amount"] == diffs["entertainment"]["new_amount"]
        assert diffs["entertainment"]["difference"] == 0.0

        assert diffs["rituals"]["scaling_rule"] == "fixed"
        assert diffs["rituals"]["old_amount"] == diffs["rituals"]["new_amount"]
        assert diffs["rituals"]["difference"] == 0.0

        # Assert catering scales linearly
        assert diffs["catering"]["scaling_rule"] == "per_guest"
        expected_catering = round(diffs["catering"]["old_amount"] * (330 / 280), 2)
        assert diffs["catering"]["new_amount"] == expected_catering
        assert diffs["catering"]["difference"] > 0

        # Assert decor (280 -> 330 guests) remains in the 251-500 tier (multiplier 1.40)
        assert diffs["decor"]["scaling_rule"] == "tiered"
        assert diffs["decor"]["old_amount"] == diffs["decor"]["new_amount"]
        assert diffs["decor"]["difference"] == 0.0

        # Assert user-friendly decor formula string
        decor_formula = diffs["decor"]["formula"]
        assert "Remains in 'Large Lawn / Ballroom (251-500 guests)'" in decor_formula
        assert "280→330 guests" in decor_formula
        assert "no change" in decor_formula
        assert "1.40/1.40" not in decor_formula

    finally:
        # Cleanup
        client.delete(f"/api/v1/events/{event_id}", headers=auth_headers)


def test_birthday_replanning_guest_surge_scales_cake_and_desserts():
    """
    Asserts that M2 Replanning Engine correctly rescales birthday events:
    - 'cake_and_desserts' must scale linearly per_guest (* new_guests / old_guests)
    - 'entertainment' and 'venue' must remain fixed (contract rate, difference == 0.0)
    - 'decor' must resolve to tiered
    """
    import random
    suffix = random.randint(1000, 9999)
    phone = f"+91981111{suffix}"

    # 1. Synthesize Birthday Event
    create_res = client.post(
        "/api/v1/intake/generate",
        json={
            "name": "Vivaan 6th Birthday Carnival",
            "host_name": "Meera Sen",
            "phone_number": phone,
            "event_type": "birthday",
            "tradition_code": "birthday_kids_carnival",
            "guest_count": 75,
            "total_budget": 200000.0,
            "city": "Mumbai",
            "pincode": "400050",
            "start_date": "2027-06-10",
            "end_date": "2027-06-10"
        }
    )
    assert create_res.status_code == 201
    create_data = create_res.json()
    event_id = create_data["event_id"]
    auth_headers = {"X-Event-Owner-Token": create_data["owner_token"]} if create_data.get("owner_token") else {}

    try:
        # 2. Trigger Guest Surge (75 -> 100 guests)
        replan_res = client.post(
            f"/api/v1/events/{event_id}/changes",
            json={
                "change_type": "guest_count_changed",
                "payload": {
                    "from_guest_count": 75,
                    "to_guest_count": 100
                }
            },
            headers=auth_headers
        )
        assert replan_res.status_code == 201
        data = replan_res.json()
        diffs = {d["category"]: d for d in data["budget_diff"]}

        # Assert cake_and_desserts scales per_guest
        assert "cake_and_desserts" in diffs
        cake = diffs["cake_and_desserts"]
        assert cake["scaling_rule"] == "per_guest"
        expected_cake = round(cake["old_amount"] * (100 / 75), 2)
        assert cake["new_amount"] == expected_cake
        assert cake["difference"] > 0
        assert "(100/75)" in cake["formula"]

        # Assert entertainment remains fixed
        assert "entertainment" in diffs
        ent = diffs["entertainment"]
        assert ent["scaling_rule"] == "fixed"
        assert ent["difference"] == 0.0
        assert "Fixed contract rate" in ent["formula"]

        # Assert venue remains fixed
        assert "venue" in diffs
        assert diffs["venue"]["scaling_rule"] == "fixed"
        assert diffs["venue"]["difference"] == 0.0

        # Assert decor is tiered
        assert "decor" in diffs
        assert diffs["decor"]["scaling_rule"] == "tiered"
    finally:
        client.delete(f"/api/v1/events/{event_id}", headers=auth_headers)
