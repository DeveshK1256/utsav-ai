import contextlib
import logging
import os
import sys
import threading
from collections.abc import Callable
from typing import Any, cast

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from backend.app.api.v1.discovery import router as discovery_router
from backend.app.api.v1.events import router as events_router
from backend.app.api.v1.intake import router as intake_router
from backend.app.api.v1.invitations import router as invitations_router
from backend.app.api.v1.quotes import router as quotes_router
from backend.app.api.v1.replanning import router as replanning_router
from backend.app.api.v1.rituals import router as rituals_router
from backend.app.api.v1.vibe import router as vibe_router
from backend.app.core.config import settings
from backend.app.core.limiter import limiter

logger = logging.getLogger("uvicorn.error")

app = FastAPI(
    title=f"{settings.PROJECT_NAME} API Engine",
    version=settings.VERSION,
    description="Deterministic GenAI Event Planning Platform for Indian Celebrations",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, cast(Any, _rate_limit_exceeded_handler))

MAX_REQUEST_BODY_BYTES = 10 * 1024 * 1024  # 10 MB strict limit for API payloads


@app.middleware("http")
async def enforce_request_size_limit(request: Request, call_next: Callable[[Request], Any]) -> Response:
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_REQUEST_BODY_BYTES:
                return Response(content="Payload Too Large (exceeds 10MB limit)", status_code=413)
        except ValueError:
            logger.warning("Invalid Content-Length header encountered: %s", content_length)
    return cast(Response, await call_next(request))


@app.middleware("http")
async def add_security_headers(request: Request, call_next: Callable[[Request], Any]) -> Response:
    response = cast(Response, await call_next(request))
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(self), camera=(), microphone=()"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none';"
    return response


# CORS Middleware (restricted to real Netlify production domain, previews, and local development)
ALLOWED_ORIGINS = [
    "https://utsav-ai.netlify.app",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https:\/\/.*--utsav-ai\.netlify\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(intake_router, prefix=settings.API_V1_STR)
app.include_router(events_router, prefix=settings.API_V1_STR)
app.include_router(quotes_router, prefix=settings.API_V1_STR)
app.include_router(replanning_router, prefix=settings.API_V1_STR)
app.include_router(vibe_router, prefix=settings.API_V1_STR)
app.include_router(rituals_router, prefix=settings.API_V1_STR)
app.include_router(invitations_router, prefix=settings.API_V1_STR)
app.include_router(discovery_router, prefix=settings.API_V1_STR)

# M4 WhatsApp guest coordination (feature-flagged and defensively isolated per pause guidelines)
ENABLE_M4_WHATSAPP = os.getenv("ENABLE_M4_WHATSAPP", "true").lower() in ("true", "1", "yes")
if ENABLE_M4_WHATSAPP:
    try:
        from backend.app.api.v1.guests import router as guests_router
        from backend.app.api.v1.webhooks import router as webhooks_router

        app.include_router(guests_router, prefix=settings.API_V1_STR)
        app.include_router(webhooks_router, prefix=settings.API_V1_STR)
    except (ImportError, AttributeError, ValueError) as exc:
        logger.error("Failed to conditionally register M4 WhatsApp router, skipping: %s", exc)


def _background_db_backfill() -> None:
    """
    Asynchronous background database backfill and initialization.
    Runs in a detached daemon thread so the web server can bind port $PORT
    and respond to /health immediately within milliseconds of boot,
    completely immune to remote DB connection latency or table lock contention.
    """
    logger.info("Starting background DB schema check and backfill...")
    try:
        from sqlalchemy import text

        from backend.app.db.base import Base
        from backend.app.db.session import SessionLocal, engine

        # 1. Ensure tables exist
        Base.metadata.create_all(bind=engine)

        # 2. Schema migrations & scaling rules
        with engine.begin() as conn:
            if engine.dialect.name == "postgresql":
                conn.execute(text("ALTER TABLE traditions ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;"))
                conn.execute(text("ALTER TABLE traditions ADD COLUMN IF NOT EXISTS verification_source VARCHAR(255);"))
                conn.execute(text("ALTER TABLE ritual_items ADD COLUMN IF NOT EXISTS ritual_name VARCHAR(100);"))
                conn.execute(text("ALTER TABLE ritual_items ADD COLUMN IF NOT EXISTS category VARCHAR(50) DEFAULT 'puja_samagri';"))
                conn.execute(text("ALTER TABLE ritual_items ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;"))
                conn.execute(text("ALTER TABLE events ADD COLUMN IF NOT EXISTS secondary_tradition_code VARCHAR(50);"))
                conn.execute(text("ALTER TABLE events ADD COLUMN IF NOT EXISTS owner_token VARCHAR(64);"))
            elif engine.dialect.name == "sqlite":
                with contextlib.suppress(SQLAlchemyError, OperationalError):
                    conn.execute(text("ALTER TABLE events ADD COLUMN owner_token VARCHAR(64);"))

            conn.execute(text("""
                UPDATE budget_items
                SET scaling_rule = CASE
                    WHEN lower(category) IN ('venue', 'photography', 'entertainment', 'rituals', 'ritual_priest') THEN 'fixed'
                    WHEN lower(category) IN ('decor', 'sound_light', 'sound_and_lighting') THEN 'tiered'
                    WHEN lower(category) IN ('catering', 'rentals', 'wardrobe', 'gifts_favors', 'invitations', 'logistics', 'contingency') THEN 'per_guest'
                    ELSE 'per_guest'
                END
                WHERE scaling_rule IS NULL
                   OR (scaling_rule = 'per_guest' AND lower(category) IN ('venue', 'photography', 'entertainment', 'rituals', 'ritual_priest', 'decor', 'sound_light', 'sound_and_lighting'))
                   OR (scaling_rule = 'fixed' AND lower(category) IN ('decor', 'sound_light', 'sound_and_lighting', 'catering', 'rentals', 'wardrobe', 'gifts_favors', 'invitations', 'logistics', 'contingency'));
            """))

            conn.execute(text("UPDATE traditions SET is_verified = FALSE, verification_source = 'AI-drafted baseline, pending community/priest review' WHERE is_verified IS NULL OR is_verified = TRUE;"))
            conn.execute(text("UPDATE ritual_items SET is_verified = FALSE WHERE is_verified IS NULL OR is_verified = TRUE;"))

        # 3. Seed traditions and baseline venues idempotently
        db = SessionLocal()
        try:
            from backend.app.db.seed_traditions import seed_cultural_traditions
            seed_cultural_traditions(db=db)

            from scripts.seed_vendor_discovery import seed_vendor_profiles
            seed_vendor_profiles()
        finally:
            db.close()

        logger.info("Background DB schema check and backfill completed successfully.")
    except (SQLAlchemyError, OperationalError, OSError, ValueError) as exc:
        logger.warning("Background DB backfill encountered an issue (non-fatal, server remains healthy): %s", exc)


@app.on_event("startup")
def run_db_backfill_on_startup() -> None:
    """
    Fast, non-blocking startup handler.
    Spawns DB backfill in a detached daemon thread so Uvicorn immediately
    binds to 0.0.0.0:$PORT and answers health checks without delay.
    """
    thread = threading.Thread(target=_background_db_backfill, daemon=True, name="db-backfill-worker")
    thread.start()
    if "pytest" in sys.modules or os.getenv("TESTING") == "true":
        thread.join(timeout=10.0)
    logger.info("Launched background DB initialization thread. Web server is ready to bind port.")


@app.get("/health")
def health_check() -> dict[str, Any]:
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    return {
        "status": "healthy",
        "service": "utsav-backend",
        "version": settings.VERSION,
        "environment": os.getenv("ENVIRONMENT", "production"),
        "gemini_configured": bool(gemini_key and not gemini_key.startswith("test_")),
        "database": "sqlite_dev" if "sqlite" in settings.DATABASE_URL else "postgresql_ready",
    }
