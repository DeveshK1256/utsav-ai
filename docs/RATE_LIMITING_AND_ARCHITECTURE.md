# Architecture & Production Deployment Specification

## 1. Hosting Architecture & Runtime Environment

The production deployment of Utsav AI is hosted across two decoupled services:

1. **Frontend:** Deployed to **Netlify** (`https://utsav-ai.netlify.app`).
   - Built with Next.js 16 with all 15 routes pre-rendered as Static HTML / Static Site Generation (`○ Static` / `● SSG`).
   - Served globally via Netlify's Multi-Region Edge CDN with 0ms server-side compute delay.
   - Strict Content Security Policy (CSP), Referrer-Policy, and Permissions-Policy deployed at the CDN edge via `_headers` and `netlify.toml`.
   - Client components interact with the live FastAPI backend over HTTPS using explicit Bearer and `X-Event-Owner-Token` headers.

2. **Backend:** Deployed to **Render** (`https://utsav-ai-ycg2.onrender.com`).
   - Containerized FastAPI ASGI application running under Uvicorn.
   - Database: Persistent SQLite (free tier single-instance) or managed PostgreSQL.
   - API endpoints enforce strict CORS (only allowing the production Netlify domain and local development origins), HSTS (`max-age=63072000; includeSubDomains; preload`), `X-Content-Type-Options: nosniff`, and `frame-ancestors: 'none'`.

---

## 2. Rate Limiting Architecture & Scaling Governance

### Current Implementation: In-Memory SlowAPI
- Implemented via `slowapi` (`backend/app/core/limiter.py`) wrapped around FastAPI route handlers.
- Key function: `get_remote_address` (IP-based rate tracking, with awareness of `X-Forwarded-For` from reverse proxies).
- Default global limit: `120 requests/minute`.
- Dedicated critical endpoints:
  - `/api/v1/quotes/upload`: Stricter limits to protect OCR / LLM token spend.
  - `/api/v1/auth/*`: Protected against credential brute-forcing.

### Known Architectural Limitation: Multi-Instance In-Memory Store
> [!NOTE]
> SlowAPI defaults to an in-process in-memory key-value store (`memory://`).
> In a multi-worker or horizontally autoscaling deployment (e.g., Render autoscaling clusters, Google Cloud Run dynamic instances, or Kubernetes replica sets), **each worker or container maintains an independent memory bucket**.

**Implications:**
1. A client distributing requests across $N$ independent instances can theoretically consume up to $N \times \text{limit}$ requests per minute if requests are evenly round-robined.
2. In the current production deployment (single Render web service container), this in-memory store is fully centralized and strictly enforces the 120 req/min cap.
3. **Enterprise Migration Path:** For clustered or multi-instance autoscaling, configure a shared Redis instance:
   ```python
   # Migration to distributed rate limiting:
   limiter = Limiter(
       key_func=get_remote_address,
       default_limits=["120/minute"],
       storage_uri=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
       enabled=True
   )
   ```
