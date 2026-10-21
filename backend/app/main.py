from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.api.v1.intake import router as intake_router

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


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "utsav-backend",
        "version": settings.VERSION
    }
