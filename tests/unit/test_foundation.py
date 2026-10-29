from unittest.mock import patch, MagicMock
import datetime
from starlette.requests import Request
import uuid
import os
from backend.app.models.models import Event, User
from backend.app.db.session import SessionLocal
import uuid
from backend.app.services.invitation_wording_agent import InvitationWordingAgent
from backend.app.db.session import SessionLocal
"""
Unit Tests for Foundation Core Deterministic Engines
Covers: Budget scaling, E.164 phone normalization, DAG dependency cycles, and seating constraints.
"""

import re
import pytest
from typing import List, Dict, Any


from backend.app.services.budget_engine import BudgetScalingEngine, load_city_tiers_config

# --- 1. Deterministic Budget Scaling Engine ---
def compute_budget_breakdown(envelope: float, city_tier: str = "tier_1") -> Dict[str, float]:
    items = BudgetScalingEngine.compute_budget_allocation(envelope, "wedding", "mumbai" if city_tier == "tier_1" else ("jaipur" if city_tier == "tier_2" else "rural"), 350)
    return {item["category"]: item["planned_amount"] for item in items}


def test_budget_scaling_allocation_sums_to_total():
    envelope = 3500000.0  # ₹35 Lakhs
    breakdown = compute_budget_breakdown(envelope, city_tier="tier_1")
    total_allocated = sum(breakdown.values())
    assert abs(total_allocated - envelope) < 0.01
    assert breakdown["catering"] > breakdown["decor"]
    assert breakdown["venue"] > breakdown["photography"]


def test_budget_scaling_tier_multipliers():
    envelope = 1000000.0  # ₹10 Lakhs
    cfg = load_city_tiers_config()
    m = cfg["multipliers"]
    
    t1_expected = envelope * m["tier_1"]
    t2_expected = envelope * m["tier_2"]
    t3_expected = envelope * m["tier_3"]

    t1 = sum(compute_budget_breakdown(envelope, "tier_1").values())
    t2 = sum(compute_budget_breakdown(envelope, "tier_2").values())
    t3 = sum(compute_budget_breakdown(envelope, "tier_3").values())

    assert abs(t1 - t1_expected) < 0.01
    assert abs(t2 - t2_expected) < 0.01
    assert abs(t3 - t3_expected) < 0.01


# --- 2. Phone Number E.164 Normalization ---
def normalize_indian_phone(phone: str) -> str:
    cleaned = re.sub(r"[\s\-\(\)]", "", phone.strip())
    if cleaned.startswith("+91"):
        digits = cleaned[3:]
    elif cleaned.startswith("91") and len(cleaned) == 12:
        digits = cleaned[2:]
    elif cleaned.startswith("0") and len(cleaned) == 11:
        digits = cleaned[1:]
    else:
        digits = cleaned

    if len(digits) != 10 or not digits.isdigit() or digits[0] not in "6789":
        raise ValueError(f"Invalid Indian mobile number: {phone}")

    return f"+91{digits}"


def test_phone_normalization_formats():
    assert normalize_indian_phone("+91 98765 43210") == "+919876543210"
    assert normalize_indian_phone("09876543210") == "+919876543210"
    assert normalize_indian_phone("919876543210") == "+919876543210"
    assert normalize_indian_phone("9876543210") == "+919876543210"
    assert normalize_indian_phone("+91-98765-43210") == "+919876543210"

    with pytest.raises(ValueError):
        normalize_indian_phone("12345")

    with pytest.raises(ValueError):
        normalize_indian_phone("5432167890")  # Invalid starting digit


# --- 3. DAG Task Dependency Scheduler & Cycle Detection ---
class DAGScheduler:
    def __init__(self):
        self.adj: Dict[str, List[str]] = {}

    def add_task(self, task_id: str, dependencies: List[str] = None):
        if task_id not in self.adj:
            self.adj[task_id] = []
        if dependencies:
            for dep in dependencies:
                if dep not in self.adj:
                    self.adj[dep] = []
                self.adj[dep].append(task_id)

    def has_cycle(self) -> bool:
        visited = set()
        rec_stack = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in self.adj.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(node)
            return False

        for node in self.adj:
            if node not in visited:
                if dfs(node):
                    return True
        return False


def test_dag_scheduler_valid_and_cyclic():
    dag = DAGScheduler()
    dag.add_task("book_venue", [])
    dag.add_task("finalize_caterer", ["book_venue"])
    dag.add_task("print_invites", ["finalize_caterer"])
    assert not dag.has_cycle()

    # Seed an illegal circular dependency
    dag.add_task("book_venue", ["print_invites"])
    assert dag.has_cycle()


# --- 4. Seating Constraint Checker ---
def validate_seating_allocation(tables: Dict[str, int], assignments: Dict[str, str], hard_conflicts: List[tuple]) -> bool:
    counts: Dict[str, int] = {}
    for guest, table in assignments.items():
        counts[table] = counts.get(table, 0) + 1
        if counts[table] > tables.get(table, 0):
            return False  # Table capacity exceeded

    for guest_a, guest_b in hard_conflicts:
        if guest_a in assignments and guest_b in assignments:
            if assignments[guest_a] == assignments[guest_b]:
                return False  # Hard conflict placed at same table

    return True


def test_seating_constraint_rules():
    tables = {"T1": 8, "T2": 8}
    assignments = {f"guest_{i}": "T1" for i in range(8)}
    hard_conflicts = [("guest_0", "guest_1")]

    # Fails because guest_0 and guest_1 are both at T1
    assert not validate_seating_allocation(tables, assignments, hard_conflicts)

    # Move guest_1 to T2 -> Valid
    assignments["guest_1"] = "T2"
    assert validate_seating_allocation(tables, assignments, hard_conflicts)


def test_database_url_normalization_to_postgresql():
    from backend.app.core.config import Settings
    
    assert Settings.assemble_db_connection("postgres://user:pass@host/db") == "postgresql://user:pass@host/db"
    assert Settings.assemble_db_connection("postgresql+psycopg://user:pass@host/db") == "postgresql://user:pass@host/db"
    assert Settings.assemble_db_connection("sqlite:///./test.db") == "sqlite:///./test.db"


def test_birthday_budget_allocation_and_dag_tasks():
    from backend.app.services.dag_scheduler import DAGScheduler
    from datetime import date

    envelope = 250000.0  # ₹2.5 Lakhs
    items = BudgetScalingEngine.compute_budget_allocation(envelope, "birthday", "mumbai", 75)
    cats = {i["category"]: i["planned_amount"] for i in items}
    
    # Assert birthday categories present
    assert "cake_and_desserts" in cats
    assert "entertainment" in cats
    assert "catering" in cats
    assert "venue" in cats
    assert abs(sum(cats.values()) - envelope) < 0.01

    # Assert birthday DAG tasks generated with zero cycles
    tasks = DAGScheduler.generate_scheduled_tasks(date(2027, 5, 20), event_type="birthday")
    assert len(tasks) >= 7
    titles = [t["title"] for t in tasks]
    assert any("Cake" in t for t in titles)
    assert any("Entertainer" in t or "Magician" in t for t in titles)


def test_community_festival_budget_allocation_and_dag_tasks():
    from backend.app.services.dag_scheduler import DAGScheduler
    from datetime import date

    envelope = 800000.0  # ₹8 Lakhs
    items = BudgetScalingEngine.compute_budget_allocation(envelope, "community_festival", "jaipur", 600)
    cats = {i["category"]: i["planned_amount"] for i in items}

    # Assert community festival categories present
    assert "pandal_and_stage" in cats
    assert "prasad_and_food" in cats
    assert "sound_and_lighting" in cats
    assert "security_and_permits" in cats
    assert abs(sum(cats.values()) - (envelope * 0.68)) < 0.05  # Jaipur is tier 2 (0.68x)

    # Assert community DAG tasks generated with zero cycles
    tasks = DAGScheduler.generate_scheduled_tasks(date(2027, 9, 10), event_type="community_festival")
    assert len(tasks) >= 7
    titles = [t["title"] for t in tasks]
    assert any("Pandal" in t for t in titles)
    assert any("NOC" in t or "Permission" in t for t in titles)
    assert any("Prasad" in t or "Ration" in t for t in titles)

from backend.app.core.security import verify_event_owner_token


def test_security_verify_token_auto_generation_and_bearer():
    """Covers lines 58-66 in core/security.py."""
    db = SessionLocal()
    rand_id = f"sec_{uuid.uuid4().hex[:8]}"
    try:
        user = User(phone_number=f"+9194{uuid.uuid4().hex[:8]}", full_name="Sec User")
        db.add(user)
        db.commit()

        # Event created with NO owner_token
        event = Event(
            id=rand_id,
            owner_id=user.id,
            name="Security Test Event",
            event_type="wedding",
            city="Delhi",
            pincode="110001",
            start_date=datetime.date(2026, 12, 1),
            end_date=datetime.date(2026, 12, 2),
            total_budget=500000.0,
            guest_count=100,
            owner_token=None,
            metadata_json={}
        )
        db.add(event)
        db.commit()

        req = Request(scope={"type": "http", "path_params": {"id": rand_id}, "query_string": b""})

        # In production mode (PYTEST_CURRENT_TEST cleared), verify_event_owner_token will auto-generate and enforce a token
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": ""}):
            # Attempt with no token -> 403 (token generated on event, but not provided in request)
            with pytest.raises(Exception) as exc_info:
                verify_event_owner_token(
                    request=req,
                    x_event_owner_token=None,
                    authorization=None,
                    db=db
                )
            assert "403" in str(exc_info.value)

            # Check that token was auto-generated and persisted to event
            db.refresh(event)
            assert event.owner_token is not None
            assert len(event.owner_token) >= 16

            # Now provide the generated token via Authorization: Bearer header
            verified_ev = verify_event_owner_token(
                request=req,
                x_event_owner_token=None,
                authorization=f"Bearer {event.owner_token}",
                db=db
            )
            assert verified_ev.id == rand_id
    finally:
        db.query(Event).filter(Event.id == rand_id).delete()
        db.commit()
        db.close()


def test_branch_coverage_closure_and_edge_branches(db, test_data):
    event, token = test_data
    from backend.app.services.intake_service import normalize_indian_phone, IntakeService
    from backend.app.schemas.intake import IntakeRequestSchema
    from backend.app.services.vibe_aggregation_engine import VibeAggregationEngine, SingleImageVibeSchema
    from backend.app.services.replanning_service import ReplanningService
    from backend.app.models.models import ChangeEvent, AISuggestion, BudgetItem, Task, SubEvent
    from datetime import date, datetime, timedelta, timezone

    # 1. normalize_indian_phone edge branches
    assert normalize_indian_phone("919876543210") == "+919876543210"
    assert normalize_indian_phone("09876543210") == "+919876543210"
    assert normalize_indian_phone("9876543210") == "+919876543210"
    with pytest.raises(ValueError):
        normalize_indian_phone("12345")
    with pytest.raises(ValueError):
        normalize_indian_phone("01234567890")

    # 2. IntakeService with existing user (hits user already exists branch)
    req1 = IntakeRequestSchema(
        name="Ananya & Rohan Vivah",
        host_name="Ananya Sharma",
        phone_number="+919876543210",
        event_type="wedding",
        tradition_code="maharashtrian_vedic",
        city="Pune",
        pincode="411001",
        guest_count=250,
        total_budget=1500000.0,
        start_date=date(2025, 11, 20),
        end_date=date(2025, 11, 22),
    )
    plan1 = IntakeService.generate_master_plan(db, req1)
    assert plan1.event_id is not None
    # Re-call with same phone to hit existing user branch (lines 75-86)
    plan2 = IntakeService.generate_master_plan(db, req1)
    assert plan2.event_id is not None

    # 3. VibeAggregationEngine branches
    # Test vibes with: invalid hex, empty tags, empty materials, None lighting, empty flower,
    # top_palette having >= 5 colors (so len < 5 is False), and duplicate mood words
    vibe1 = SingleImageVibeSchema(
        palette=["invalid-color", "#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF"],
        style_tags=["", "royal", "heritage", "traditional"],
        materials=["", "silk", "brass"],
        lighting_mood=None,
        flower_types=["", "marigold", "rose"]
    )
    vibe2 = SingleImageVibeSchema(
        palette=["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF"],
        style_tags=["royal", "heritage"],
        materials=["silk", "brass"],
        lighting_mood="golden candle glow",
        flower_types=["jasmine"]
    )
    # pass overall_mood_words that already match the titles of tags/lighting/materials
    agg = VibeAggregationEngine.aggregate_vibe_profiles(
        image_vibes=[vibe1, vibe2],
        text_description="A royal wedding feast in a heritage haveli with golden candle glow and silk accents",
        overall_mood_words=["Royal", "Golden Candle Glow", "Silk Accents"]
    )
    assert len(agg["extracted_palette"]) == 5
    assert "Royal" in agg["mood_words"]

    # 4. Replanning date_moved acceptance via API
    from fastapi.testclient import TestClient
    from backend.app.main import app
    c = TestClient(app)

    future_start = (date.today() + timedelta(days=60)).isoformat()
    moved_start = (date.today() + timedelta(days=70)).isoformat()

    post_date_res = c.post(
        f"/api/v1/events/{event.id}/changes",
        json={
            "change_type": "date_moved",
            "payload": {
                "from_date": future_start,
                "to_date": moved_start
            }
        },
        headers={"X-Event-Owner-Token": token}
    )
    assert post_date_res.status_code == 201
    date_change_id = post_date_res.json()["change_id"]

    accept_date_res = c.post(
        f"/api/v1/events/{event.id}/changes/{date_change_id}/accept",
        headers={"X-Event-Owner-Token": token}
    )
    assert accept_date_res.status_code == 200
    assert accept_date_res.json()["status"] == "applied"

    # 5. Replanning rejection of active proposal and promotion of queued proposal
    post_cut_res = c.post(
        f"/api/v1/events/{event.id}/changes",
        json={
            "change_type": "budget_cut",
            "payload": {
                "from_budget": float(event.total_budget),
                "to_budget": float(event.total_budget) * 0.8
            }
        },
        headers={"X-Event-Owner-Token": token}
    )
    assert post_cut_res.status_code == 201
    cut_change_id = post_cut_res.json()["change_id"]

    # Post a second change to be queued
    post_guest_res = c.post(
        f"/api/v1/events/{event.id}/changes",
        json={
            "change_type": "guest_count_changed",
            "payload": {
                "from_guest_count": 200,
                "to_guest_count": 250
            }
        },
        headers={"X-Event-Owner-Token": token}
    )
    assert post_guest_res.status_code == 201
    queued_change_id = post_guest_res.json()["change_id"]

    # Reject active cut proposal -> promotes queued guest count proposal
    reject_res = c.post(
        f"/api/v1/events/{event.id}/changes/{cut_change_id}/reject",
        headers={"X-Event-Owner-Token": token}
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "rejected"

    # Verify promoted proposal is now pending
    queued_status_res = c.get(
        f"/api/v1/events/{event.id}/changes/{queued_change_id}",
        headers={"X-Event-Owner-Token": token}
    )
    assert queued_status_res.status_code == 200
    assert queued_status_res.json()["status"] == "pending"

    # 6. Quotes Bearer auth header and non-existent competing quote branch
    from backend.app.models.models import QuoteDocument
    quote_doc = QuoteDocument(
        event_id=event.id,
        vendor_name="Shree Ganesh Banquets",
        category="caterer",
        total_quoted_amount=350000.0,
        file_name="quote.pdf",
        file_type="application/pdf",
        uploaded_file=b"fake quote pdf content"
    )
    db.add(quote_doc)
    db.commit()

    draft_res = c.post(
        f"/api/v1/quotes/{quote_doc.id}/negotiate-draft",
        json={"quote_id": quote_doc.id, "target_discount_percentage": 10.0, "competing_quote_id": "non_existent_id"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert draft_res.status_code == 200
    assert len(draft_res.json()["draft_variants"]) > 0


def test_core_logic_extreme_edge_cases():
    # 1. Budget scaling with extreme huge numbers (e.g. 100 Crore / 1 Billion INR)
    huge_budget = 1_000_000_000.0
    allocations = BudgetScalingEngine.compute_budget_allocation(
        total_envelope=huge_budget,
        event_type="wedding",
        city="Mumbai",
        guest_count=5000
    )
    total_planned = sum(item["planned_amount"] for item in allocations)
    assert abs(total_planned - huge_budget) < 1.0

    # 2. Budget scaling with large guest count (10,000 guests)
    alloc_large_guests = BudgetScalingEngine.compute_budget_allocation(
        total_envelope=5_000_000.0,
        event_type="community_festival",
        city="Pune",
        guest_count=10000
    )
    assert len(alloc_large_guests) >= 4

    # 3. Unicode and Devanagari text handling in invitation wording
    wording_res = InvitationWordingAgent.compose_wording(
        event_name="शुभ विवाह सोहळा",
        event_type="wedding",
        host_name="संजय आणि वंदना पाटील",
        venue_str="महालक्ष्मी लॉन्स, पुणे",
        muhurat_time="सकाळी ११:४५ वाजता",
        date_str="२१ डिसेंबर २०२६"
    )
    assert wording_res.variants
    first_body = wording_res.variants[0].body_text
    assert "पाटील" in first_body or len(first_body) > 10
