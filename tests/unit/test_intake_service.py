import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.base import Base
from backend.app.models.models import Event, SubEvent, BudgetItem, Task, User
from backend.app.schemas.intake import IntakeRequestSchema
from backend.app.services.intake_service import IntakeService, normalize_indian_phone
from backend.app.services.budget_engine import BudgetScalingEngine
from backend.app.services.dag_scheduler import DAGScheduler, TaskNode


@pytest.fixture
def db_session():
    # Use SQLite in-memory for fast deterministic tests
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_budget_scaling_engine_exact_sum():
    # Test Tier 1 (1.0x)
    envelope = 5000000.0  # ₹50 Lakhs
    items = BudgetScalingEngine.compute_budget_allocation(envelope, "wedding", "Mumbai", 400)
    total_allocated = sum(item["planned_amount"] for item in items)
    assert abs(total_allocated - envelope) < 0.01

    # Test Tier 2 (0.68x)
    items_t2 = BudgetScalingEngine.compute_budget_allocation(envelope, "wedding", "Jaipur", 400)
    total_t2 = sum(item["planned_amount"] for item in items_t2)
    assert abs(total_t2 - (envelope * 0.68)) < 0.01


def test_dag_scheduler_cycle_prevention():
    # Healthy tasks
    healthy = [
        TaskNode("t1", "Venue", 60, -30, "Host", dependencies=[]),
        TaskNode("t2", "Caterer", 60, -20, "Host", dependencies=["t1"]),
    ]
    assert not DAGScheduler.check_cycles(healthy)

    # Cyclic tasks
    cyclic = [
        TaskNode("t1", "Task 1", 60, -30, "Host", dependencies=["t2"]),
        TaskNode("t2", "Task 2", 60, -20, "Host", dependencies=["t1"]),
    ]
    assert DAGScheduler.check_cycles(cyclic)


def test_intake_service_generates_complete_master_plan(db_session):
    payload = IntakeRequestSchema(
        name="Rohan & Ananya's Grand Wedding",
        host_name="Rohan Joshi",
        phone_number="+91 98220 12345",
        event_type="wedding",
        tradition_code="maharashtrian_vedic",
        guest_count=350,
        total_budget=3500000.0,
        city="Pune",
        pincode="411001",
        start_date=date(2027, 11, 12),
        end_date=date(2027, 11, 14)
    )

    plan = IntakeService.generate_master_plan(db_session, payload)

    # Assertions
    assert plan.event_id is not None
    assert plan.owner_name == "Rohan Joshi"
    assert plan.city_tier == "tier_1"
    assert "Auspicious timings" in plan.elder_verification_disclaimer
    assert len(plan.sub_events) >= 3
    assert len(plan.budget_breakdown) >= 5
    assert len(plan.tasks) >= 5

    # Check database persistence
    event_in_db = db_session.query(Event).filter(Event.id == plan.event_id).first()
    assert event_in_db is not None
    assert event_in_db.name == "Rohan & Ananya's Grand Wedding"

    # Verify user was created
    user_in_db = db_session.query(User).filter(User.phone_number == "+919822012345").first()
    assert user_in_db is not None

    # Check that at least one sub-event is marked muhurat locked
    assert any(se.is_muhurat_locked for se in plan.sub_events)
