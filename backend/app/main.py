import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

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
from backend.app.db.seed_traditions import seed_cultural_traditions
from backend.app.db.session import SessionLocal
from scripts.seed_vendor_discovery import seed_vendor_profiles

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    application.state.database_ready = False
    application.state.database_error = None
    try:
        _background_db_backfill()
    except SQLAlchemyError:
        application.state.database_error = "Database initialization failed"
        logger.exception("Database initialization failed during application startup")
    else:
        application.state.database_ready = True
    yield


app = FastAPI(
    title=f"{settings.PROJECT_NAME} API Engine",
    version=settings.VERSION,
    description="Deterministic GenAI Event Planning Platform for Indian Celebrations",
    lifespan=lifespan,
)
app.state.database_ready = False
app.state.database_error = None

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, cast(Any, _rate_limit_exceeded_handler))

MAX_REQUEST_BODY_BYTES = 10 * 1024 * 1024  # 10 MB strict limit for API payloads


class RequestSizeLimitMiddleware:
    """Reject request bodies above the limit, including chunked requests."""

    def __init__(self, app: Callable[..., Any], max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[..., Awaitable[dict[str, Any]]],
        send: Callable[..., Awaitable[None]],
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        if self._content_length_exceeds_limit(content_length):
            await self._send_rejection(send)
            return

        receive_with_limit, send_with_limit, was_rejected = self._wrap_io(receive, send)
        await self.app(scope, receive_with_limit, send_with_limit)
        if was_rejected():
            await self._send_rejection(send)

    def _content_length_exceeds_limit(self, content_length: bytes | None) -> bool:
        if not content_length:
            return False
        try:
            return int(content_length) > self.max_body_bytes
        except ValueError:
            logger.warning("Invalid Content-Length header encountered")
            return False

    def _wrap_io(
        self,
        receive: Callable[..., Awaitable[dict[str, Any]]],
        send: Callable[..., Awaitable[None]],
    ) -> tuple[
        Callable[..., Awaitable[dict[str, Any]]],
        Callable[..., Awaitable[None]],
        Callable[[], bool],
    ]:
        received_bytes = 0
        rejected = False

        async def receive_with_limit() -> dict[str, Any]:
            nonlocal received_bytes, rejected
            message = cast(dict[str, Any], await receive())
            if message.get("type") == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > self.max_body_bytes:
                    rejected = True
                    return {"type": "http.disconnect"}
            return message

        async def send_with_limit(message: dict[str, Any]) -> None:
            if not rejected:
                await send(message)

        return receive_with_limit, send_with_limit, lambda: rejected

    @staticmethod
    async def _send_rejection(send: Callable[..., Awaitable[None]]) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [(b"content-type", b"text/plain; charset=utf-8")],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b"Payload Too Large (exceeds 10MB limit)",
            }
        )


app.add_middleware(RequestSizeLimitMiddleware, max_body_bytes=MAX_REQUEST_BODY_BYTES)


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
if settings.ENABLE_M4_WHATSAPP:
    try:
        from backend.app.api.v1.guests import router as guests_router
        from backend.app.api.v1.webhooks import router as webhooks_router

        app.include_router(guests_router, prefix=settings.API_V1_STR)
        app.include_router(webhooks_router, prefix=settings.API_V1_STR)
    except (ImportError, AttributeError, ValueError):
        logger.exception("Failed to conditionally register M4 WhatsApp router, skipping")


def _background_db_backfill() -> None:
    """Run explicit reference-data seeding after migrations have been applied."""
    db = SessionLocal()
    try:
        seed_cultural_traditions(db=db)
        seed_vendor_profiles(ensure_schema=False)
    finally:
        db.close()


@app.api_route("/health", methods=["GET", "HEAD"])
def health_check() -> dict[str, Any]:
    return cast(
        dict[str, Any],
        {
            "status": "healthy" if app.state.database_ready else "degraded",
            "service": "utsav-backend",
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "database": "sqlite_dev" if "sqlite" in settings.DATABASE_URL else "postgresql_ready",
        },
    )


@app.api_route("/readyz", methods=["GET", "HEAD"])
def readiness_check() -> Response:
    if not app.state.database_ready:
        return Response(content="Database is not ready", status_code=503)
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("Database readiness probe failed")
        return Response(content="Database is not ready", status_code=503)
    finally:
        db.close()
    return Response(content="Ready", status_code=200)
