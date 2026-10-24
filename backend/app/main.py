import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.api.v1.intake import router as intake_router
from backend.app.api.v1.events import router as events_router
from backend.app.api.v1.quotes import router as quotes_router
from backend.app.api.v1.replanning import router as replanning_router
from backend.app.api.v1.vibe import router as vibe_router
from backend.app.api.v1.rituals import router as rituals_router
from backend.app.api.v1.invitations import router as invitations_router
from backend.app.api.v1.discovery import router as discovery_router

app = FastAPI(
    title=f"{settings.PROJECT_NAME} API Engine",
    version=settings.VERSION,
    description="Deterministic GenAI Event Planning Platform for Indian Celebrations"
)

# CORS Middleware (supports local development on localhost:3000 and production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    except Exception as exc:
        import logging
        logging.getLogger("uvicorn.error").error(
            "Failed to conditionally register M4 WhatsApp router, skipping: %s", exc
        )


@app.on_event("startup")
def run_db_backfill_on_startup():
    """
    Idempotent data integrity safeguard: ensure all existing budget_items rows
    in the active database conform to canonical DEC-018 scaling rules,
    and guarantee all M0-M4 tables exist.
    """
    try:
        from backend.app.db.session import engine
        from backend.app.db.base import Base
        import backend.app.models.models
        Base.metadata.create_all(bind=engine)

        from sqlalchemy import text
        with engine.begin() as conn:
            # Idempotently add missing columns in PostgreSQL if they don't exist
            if engine.dialect.name == "postgresql":
                conn.execute(text("ALTER TABLE traditions ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;"))
                conn.execute(text("ALTER TABLE traditions ADD COLUMN IF NOT EXISTS verification_source VARCHAR(255);"))
                conn.execute(text("ALTER TABLE ritual_items ADD COLUMN IF NOT EXISTS ritual_name VARCHAR(100);"))
                conn.execute(text("ALTER TABLE ritual_items ADD COLUMN IF NOT EXISTS category VARCHAR(50) DEFAULT 'puja_samagri';"))
                conn.execute(text("ALTER TABLE ritual_items ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;"))
                conn.execute(text("ALTER TABLE events ADD COLUMN IF NOT EXISTS secondary_tradition_code VARCHAR(50);"))

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

            # Enforce truthfulness in cultural verification status: All traditions and ritual items
            # are AI-drafted starting baselines and MUST be marked is_verified = FALSE pending real community review.
            conn.execute(text("UPDATE traditions SET is_verified = FALSE, verification_source = 'AI-drafted baseline, pending community/priest review';"))
            conn.execute(text("UPDATE ritual_items SET is_verified = FALSE;"))

        # Seed curated cultural traditions & ritual items if needed
        from backend.app.db.seed_traditions import seed_cultural_traditions
        seed_cultural_traditions()
    except Exception as exc:
        import logging
        logging.getLogger("uvicorn.error").exception("Startup migration/backfill error: %s", exc)


@app.get("/health")
def health_check():
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    return {
        "status": "healthy",
        "service": "utsav-backend",
        "version": settings.VERSION,
        "active_llm_provider": "gemini" if bool(gemini_key) else "stub"
    }


@app.get("/env-check")
def env_check():
    all_keys = sorted(list(os.environ.keys()))
    matching_keys = [
        k for k in all_keys
        if any(term in k.upper() for term in ["GEMINI", "GOOGLE", "LLM", "API", "KEY", "AI"])
    ]
    return {
        "all_env_key_names": all_keys,
        "matching_env_keys": matching_keys,
        "has_gemini_api_key": bool(os.getenv("GEMINI_API_KEY")),
        "has_google_api_key": bool(os.getenv("GOOGLE_API_KEY")),
        "has_database_url": bool(os.getenv("DATABASE_URL"))
    }
