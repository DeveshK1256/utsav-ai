from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import settings

# Bounded connection arguments: prevent indefinite hangs on remote databases
connect_args = (
    {"check_same_thread": False}
    if "sqlite" in settings.DATABASE_URL
    else {"connect_timeout": 5, "options": "-c statement_timeout=10000 -c lock_timeout=5000"}
)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_timeout=10,
    pool_recycle=300,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
