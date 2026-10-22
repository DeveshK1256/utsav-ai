import pytest
from backend.app.models.models import Base
from backend.app.db.session import engine

@pytest.fixture(autouse=True, scope="session")
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
