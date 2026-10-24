import pytest
from sqlalchemy import text
from backend.app.models.models import Base
from backend.app.db.session import engine

@pytest.fixture(autouse=True, scope="session")
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE events ADD COLUMN owner_token VARCHAR(64);"))
        except Exception:
            pass
    yield
