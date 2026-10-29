from datetime import date, timedelta
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.app.db.session import SessionLocal, engine
from backend.app.main import _background_db_backfill, app
from backend.app.models.models import Base, Event, User


@pytest.fixture(autouse=True, scope="session")
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE events ADD COLUMN owner_token VARCHAR(64);"))
        except Exception:
            pass
    _background_db_backfill()
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_event_data(db):
    user = User(
        phone_number=f"+9198{uuid.uuid4().hex[:8]}",
        full_name="Test Host",
        role="host",
    )
    db.add(user)
    db.flush()

    token = f"tok_{uuid.uuid4().hex}"
    event = Event(
        owner_id=user.id,
        name="Test Celebration Event",
        event_type="wedding",
        tradition_code="maharashtrian_vedic",
        guest_count=150,
        venue_capacity=200,
        total_budget=1200000.0,
        city="Jaipur",
        pincode="302001",
        owner_token=token,
        start_date=date.today() + timedelta(days=45),
        end_date=date.today() + timedelta(days=47),
        metadata_json={"owner_token": token},
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event, token


# Maintain alias for backward compatibility with existing tests
@pytest.fixture
def test_data(sample_event_data):
    return sample_event_data
