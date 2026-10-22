import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.api.v1.intake import router as intake_router
from backend.app.api.v1.events import router as events_router
from backend.app.api.v1.quotes import router as quotes_router

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
