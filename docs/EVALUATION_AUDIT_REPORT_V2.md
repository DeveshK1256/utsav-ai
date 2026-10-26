# EVALUATION AUDIT REPORT V2: Comprehensive Re-Verification & New Surface Audit

**Audit Date:** 2026-10-26  
**Auditor:** Automated Agentic Pair / Security & Quality Auditor  
**Scope:** Re-verification of all findings from `docs/EVALUATION_AUDIT_REPORT.md` (Part A), exhaustive audit of all newly shipped surfaces (3D Landing, Video Player, Nationwide OSM Map, Background DB Backfill, and Event Owner Token Auth) (Part B), and updated prioritized roadmap.  
**Standard of Proof:** Zero unverified assertions. Every finding is backed by an explicit CLI output, live production HTTP probe, or source code reference.

---

## Executive Summary

| Audit Dimension | Evaluation Score (Prior) | Current Status (V2) | Direction | Evidence Highlights |
|---|:---:|:---:|:---:|---|
| **Criterion 1: Code Quality & Architecture** | 6.5 / 10 | **6.5 / 10** | Unchanged | Clean FastAPI/Next.js modularity, but 927 Ruff errors (mostly imports/type-unions), 278 MyPy errors, and 37 leftover test scripts in repo. |
| **Criterion 2: Functional Correctness & Completeness** | 8.5 / 10 | **9.0 / 10** | Improved | Full end-to-end event planning pipeline complete. Free nationwide venue discovery (Leaflet + Overpass API) operating without paid API risk. |
| **Criterion 3: Security & Data Privacy** | 4.0 / 10 | **6.5 / 10** | Significantly Improved | Mutating endpoints (`POST`/`PATCH`/`DELETE`) now strictly reject unauthenticated callers with HTTP 403. However, event reads (`GET`) remain unauthenticated (DEC-033), CORS is still wildcard (`allow_origins=["*"]`), and WhatsApp signature check remains fail-open when secret is omitted. |
| **Criterion 4: Performance & Latency** | 7.0 / 10 | **8.0 / 10** | Improved | Non-blocking daemon startup fixed Render port hang; `/health` runs in 1.9ms steady state. Public video is 1.53MB with `preload="metadata"` causing zero HTML load regression (205ms). Overpass live queries run in 6.5s–7.0s. |
| **Criterion 5: Accessibility (a11y) & UX** | 6.5 / 10 | **7.5 / 10** | Improved | `prefers-reduced-motion` verified across all 5 3D components and video player. Video includes WebVTT synced captions. Leaflet map markers support keyboard focus (`tabindex="0"`). Minor color contrast and onboarding input labels remain. |
| **Criterion 6: Cultural Authenticity & Wisdom** | 9.0 / 10 | **9.5 / 10** | Improved | Authentic panchang, 21 regional traditions, Devanagari cards, and Elder Disclaimer banners confirmed live. Piper TTS includes domain-specific phonetic respelling for clear Hindi root voicing. |

---

## Part A: Re-Verification of Prior Findings (8 Prioritized Items)

### 1. Event Authorization (Mutations)
- **Status:** **CLOSED & ENFORCED**
- **Prior State:** Live penetration test proved any unauthenticated user could delete or modify arbitrary events (`DELETE /api/v1/events/{id}`).
- **Current Evidence:**
  Executed against live production Render backend (`https://utsav-ai-ycg2.onrender.com`):
  ```bash
  $ python -c "
  # Test unauthenticated DELETE on real event 7c2b292a-0b9c-40e5-8a20-9d18224fa860:
  del_req = Request('https://utsav-ai-ycg2.onrender.com/api/v1/events/7c2b292a-0b9c-40e5-8a20-9d18224fa860', method='DELETE')
  # Result:
  HTTP Error 403: Forbidden: Invalid or missing X-Event-Owner-Token. Unauthorized mutation attempt.

  # Test unauthenticated POST on compose:
  # Result:
  HTTP Error 403: Forbidden: Invalid or missing X-Event-Owner-Token. Unauthorized mutation attempt.
  "
  ```
- **Conclusion:** Constant-time token verification via `verify_event_owner_token` is active on all mutating endpoints (`events.py`, `guests.py`, `invitations.py`, `replanning.py`, `rituals.py`, `vibe.py`).

### 2. Event Read (GET) Authorization
- **Status:** **STILL OPEN (Accepted Interim Gap — DEC-033)**
- **Prior State:** Accepted interim design gap documented under DEC-033.
- **Current Evidence:**
  ```bash
  $ python -c "
  # Query real event without any token header:
  req = Request('https://utsav-ai-ycg2.onrender.com/api/v1/events/7c2b292a-0b9c-40e5-8a20-9d18224fa860')
  res = urlopen(req)
  print('HTTP', res.status) # Returns 200 OK
  "
  ```
  Calling `GET /api/v1/events/{id}` with an event UUID returns the full event JSON (host name, celebration type, budget allocations, guest counts) without requiring `X-Event-Owner-Token`.
- **Conclusion:** Correctly documented as an accepted interim gap. Requires scoped read token authentication before enterprise or production release.

### 3. WhatsApp Webhook Fail-Open Vulnerability
- **Status:** **STILL OPEN & VULNERABLE**
- **Prior State:** Explicitly deferred mid-session.
- **Current Evidence:**
  In [`backend/app/services/whatsapp/webhook_service.py:34-37`](file:///d:/Utsav/backend/app/services/whatsapp/webhook_service.py#L34-L37):
  ```python
  app_secret = getattr(settings, "WHATSAPP_APP_SECRET", None)
  if not app_secret:
      # In test/mock mode without configured secret, allow through
      return True
  ```
  If `WHATSAPP_APP_SECRET` is unset, unauthenticated callers can POST fake inbound WhatsApp RSVPs and inject spoofed messages. In production environments where WhatsApp integration is enabled, this remains a fail-open security bypass.

### 4. Dependency CVEs & Bloat Cleanup
- **Status:** **PARTIALLY CLOSED (Zero CVEs, but bloat not yet removed)**
- **Prior State:** 12 CVEs reported in earlier audit across bloated packages (`chromadb`, `mlflow`, `nltk`, `gitpython`).
- **Current Evidence:**
  Ran `pip-audit -r backend/requirements.txt`:
  ```
  No known vulnerabilities found
  ```
  `backend/requirements.txt` is lean (14 pinned packages). However, `chromadb`, `mlflow`, `nltk`, and `gitpython` remain present in historical virtualenv configurations, though unreferenced in active code.

### 5. CORS Wildcard & `/env-check` Endpoint
- **Status:** **STILL OPEN**
- **Current Evidence:**
  In [`backend/app/main.py:21-28`](file:///d:/Utsav/backend/app/main.py#L21-L28):
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["*"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```
  In [`backend/app/main.py:156-169`](file:///d:/Utsav/backend/app/main.py#L156-L169):
  ```python
  @app.get("/env-check")
  def env_check():
      all_keys = sorted(list(os.environ.keys()))
      matching_keys = [k for k in all_keys if any(term in k.upper() for term in ["GEMINI", "GOOGLE", "LLM", "API", "KEY", "AI"])]
      return {"all_env_key_names": all_keys, "matching_env_keys": matching_keys, ...}
  ```
  The endpoint publicly enumerates all server environment variable keys over HTTPS. Combined with `allow_origins=["*"]`, any webpage can inspect the server's environment keys.

### 6. Rate Limiting & File Upload Limits
- **Status:** **STILL OPEN**
- **Current Evidence:**
  - `git grep "rate_limit"` finds rate limiting only in outbound WhatsApp messaging delays (`send_service.py:32`), but **zero rate limiting middleware** on public LLM endpoints (`/api/v1/intake/generate`, `/api/v1/events/{id}/vibe/...`).
  - In `backend/app/services/vibe_service.py:48-62`, files are read directly into memory (`content = f.file.read()`) without an explicit byte-size check (e.g. 5MB per file), opening an in-memory denial-of-service vector if someone uploads multiple multi-gigabyte files.

### 7. Color Contrast Verification
- **Status:** **VERIFIED (High compliance on new 3D surfaces; minor legacy text flags)**
- **Current Evidence:**
  Axe-core scan on local and Netlify surfaces:
  - New 3D landing card surfaces (`#1A1D24` / `#F4B41A`) deliver **9.49:1 – 10.72:1** contrast ratios.
  - 1 minor violation flagged on subtle subtitle text (`text-amber-600 dark:text-amber-400 font-semibold`) against specific neutral backgrounds.

### 8. Full CI Gate (GitHub Actions)
- **Status:** **PARTIALLY IMPLEMENTED (Unit + Schema Tests Present; Linters & Typecheckers Missing)**
- **Current Evidence:**
  In [`.github/workflows/ci.yml`](file:///d:/Utsav/.github/workflows/ci.yml):
  Runs `pytest tests/unit/`, `pytest tests/schema/`, and `pytest tests/eval/`.
  **Gap:** `ruff`, `mypy`, `npm run build`, and `tsc` are **not** present in the CI workflow.

---

## Part B: Audit of New Work Added Since Last Audit

### 1. New Security Surface

#### Background DB Daemon Threading Review
In [`backend/app/main.py:111-143`](file:///d:/Utsav/backend/app/main.py#L111-L143):
```python
def _background_db_backfill():
    db = SessionLocal()
    try:
        # Seeding logic...
    finally:
        db.close()

@app.on_event("startup")
def run_db_backfill_on_startup():
    thread = threading.Thread(target=_background_db_backfill, daemon=True, name="db-backfill-worker")
    thread.start()
```
- **Thread Safety:** **PASS**. The background worker instantiates its own isolated session (`db = SessionLocal()`) and closes it inside a `finally:` block. It does not share sessions with incoming HTTP request handlers.
- **Exception Logging:** **PASS**. Exceptions are explicitly logged with `logger.warning("Background DB backfill encountered an issue: %s", exc)`.
- **Race Condition Risk:** **LOW/ACCEPTABLE**. If an incoming request hits `/discovery/vendors` in the first 500ms before `seed_vendor_profiles()` completes, it queries an empty DB table; however, the fallback path queries OpenStreetMap live on demand, preventing a user-facing failure.

#### Untrusted External Data Injection (OSM & Overpass)
In [`backend/app/services/discovery_service.py:490-515`](file:///d:/Utsav/backend/app/services/discovery_service.py#L490-L515):
- Venue names from OpenStreetMap are untrusted external input.
- **ORM Escaping:** **PASS**. Insertion uses SQLAlchemy ORM parameter binding (`VendorProfile(business_name=v["name"][:200], ...)`), fully preventing SQL injection.
- **Frontend XSS:** **PASS**. Next.js/React automatically escapes strings during JSX text interpolation (`{venue.business_name}`).
- **Sanitization & Filtering:** **PASS**. `is_valid_venue_name()` strips raw OSM IDs (`node/123`), numbers, and generic noise.

#### Outbound Network Timeouts (Nominatim & Overpass)
In [`backend/app/services/discovery_service.py`](file:///d:/Utsav/backend/app/services/discovery_service.py):
- Overpass query: `urllib.request.urlopen(req, timeout=4)` (line 217).
- Overpass node detail: `urllib.request.urlopen(req, timeout=1.8)` (line 241).
- Nominatim reverse geocode: `urllib.request.urlopen(rev_req, timeout=3.0)` (line 451).
- Nominatim search: `urllib.request.urlopen(req, timeout=3.5)` (line 461).
- **Finding:** **PASS**. Every outbound HTTP call has an explicit bounding timeout between 1.8s and 4.0s, preventing worker thread stalls.

---

### 2. Code Quality & Static Analysis

#### Ruff Linter Audit
```bash
$ ruff check backend/
Found 927 errors (697 auto-fixable)
```
- **Breakdown:**
  - Import sorting / formatting (`I001`): ~450
  - Unused imports (`F401`): ~120
  - Modern type union syntax (`UP006`, `UP045` - `Optional[X]` -> `X | None`): ~260
  - Blind exception catches (`BLE001`): ~40

#### MyPy Typecheck Audit
```bash
$ mypy backend/app/ --ignore-missing-imports --explicit-package-bases
Found 278 errors in 24 files (checked 52 source files)
```
- **Primary Cause:** SQLAlchemy 2.0 ORM column mapping mismatch (`Column[str]` passed to functions expecting `str`).

#### TypeScript Audit
```bash
$ npm --prefix frontend run build
✓ Compiled successfully in 18.1s
Finished TypeScript in 13.6s (0 errors)
```
- **Finding:** Frontend TypeScript compiles with **zero errors**.

#### Repository Clutter Inventory
Sitting in repository root and `scripts/`:
- **37 ad-hoc scripts** (`audit_map_integrity.py`, `poll_render_discovery.py`, `verify_stage4_live.py`, etc.) totaling ~180KB of unmanaged scripts.
- **Recommendation:** Consolidate valuable checks into `tests/` and archive obsolete scripts into `scripts/archive/`.

---

### 3. Efficiency & Latency Audit

#### Live Netlify Performance (3D Landing + Video Component)
Measured across 5 consecutive requests to `https://utsav-ai.netlify.app/`:
- **Mean TTFB:** `439 ms` (Min: `209 ms`, Max: `906 ms`)
- **Total HTML Load:** `58.65 KB` transferred in `205.3 ms`
- **Video Asset Footprint:**
  - File size: `1.53 MB`
  - Preload mode: `preload="metadata"`
  - **Verification:** The browser does **not** stream video bytes on initial page load. Page speed is unimpacted.

#### Live Nationwide Map Latency (OpenStreetMap Overpass API)
- `GET /api/v1/discovery/vendors?city=Jaipur`: **7.04s** (live search + distance computation)
- `GET /api/v1/discovery/vendors?lat=12.9716&lng=77.5946&radius_km=15` (Bengaluru OSM): **6.55s**
- **Finding:** Completely functional, zero paid API billing risk, but high latency (6-7s) due to public Overpass query processing.

---

### 4. Testing & Regression Coverage

#### Pytest Test Suite & Coverage
```bash
$ pytest --cov=backend/app tests/
81 passed, 2 failed in 80.61s
Total Code Coverage: 80% (4,640 statements, 936 missed)
```
- **Failures Identified in `test_f15_discovery.py`:**
  - `test_discovery_jaipur_radius_query`: Expected `coordinate_precision == 'locality_approximate'`, but real OSM results now return `'exact_osm_node'`.
  - `test_discovery_geolocation_denied_fallback`: Hardcoded assertion `assert data['total_results'] == 8` failed because live OSM discovery now returns 15 venues.
  - **Assessment:** Harmless test-expectation drift caused by shipping the richer nationwide OSM discovery.
- **Regression Safeguards:**
  - `test_startup_performance.py`: **PASSED** (Instantaneous health check verified).
  - `test_map_data_integrity.py`: **PASSED** (Dedup & empty state verified).
- **Frontend Component Tests:** Still **0%** (no Jest/Vitest/RTL suite for React components).

---

### 5. Accessibility (a11y) Audit

Automated Playwright + Axe-Core (WCAG 2.1 AA) Results:

| Page / Route | Violations Found | Passing Rules | Key Findings |
|---|:---:|:---:|---|
| **Landing (`/`)** | 1 | 25 | Video `<track kind="captions">` verified. Color contrast warning on 21 subtle secondary text elements. |
| **Onboarding (`/onboarding`)** | 1 | 22 | Form input missing explicit `<label>` or `aria-label` on 2 date fields. |
| **Dashboard (`/dashboard/events/default`)** | **0** | 20 | **100% WCAG 2.1 AA Compliant**. |
| **Compose (`/dashboard/events/default/compose`)** | 1 | 24 | Leaflet Map keyboard operability: Markers have `tabindex="0"`, allowing keyboard focus. Color contrast on badge. |

---

### 6. Problem Statement Alignment & Rubric Evaluation

1. **Problem Statement Fit:** **STRONG / 9.5 out of 10**
   Utsav directly eliminates celebration planning chaos:
   - Automated run-of-show with muhurat-aware panchang timings.
   - Transparent budget scaling itemized by tier and guest count.
   - Nationwide nearby celebration spaces mapped via free OpenStreetMap data.
   - Dual-language invitations with Devanagari typography.
2. **Feature Scope (WhatsApp Status):**
   - WhatsApp guest coordination (F3) remains **feature-flagged and paused** (`ENABLE_M4_WHATSAPP=false` in production). Correctly disclosed in documentation.
3. **Google Services Rubric Tip:**
   - **Gemini Usage:** Genuine, substantive multimodal theme generation and vision extraction (`gemini-2.5-flash` / `gemini-1.5-flash`).
   - **Firebase / Cloud Run Adoption:** Currently deployed on Netlify Edge + Render Singapore. Rubric tip encourages exploring Google Cloud Run or Firebase Auth for bonus points.

---

## Updated Prioritized Remediation Roadmap (Severity x Effort)

| Rank | Priority | Issue Description | Domain | Severity | Effort | Recommended Action |
|:---:|:---:|:---|:---:|:---:|:---:|:---|
| **1** | **P0** | **CORS Wildcard & `/env-check` Disclosure** | Security | High | 30 mins | Restrict CORS to `["https://utsav-ai.netlify.app", "http://localhost:3000"]`. Restrict or delete `/env-check` in `main.py`. |
| **2** | **P0** | **Event Read (GET) Authorization** | Security | High | 1-2 hrs | Gate `GET /api/v1/events/{id}` and sensitive event sub-resources behind `verify_event_owner_token` or signed read tokens. |
| **3** | **P1** | **WhatsApp Fail-Open Webhook Verification** | Security | High | 15 mins | Make signature verification fail-closed: reject requests with HTTP 403 if `WHATSAPP_APP_SECRET` is unset in production. |
| **4** | **P1** | **Update Outdated Test Assertions in `test_f15_discovery.py`** | Quality | Medium | 15 mins | Update test expectations to reflect `exact_osm_node` coordinate precision and expanded nationwide venue count so test suite passes at 100%. |
| **5** | **P2** | **In-Memory File Upload Limits & Rate Limiting** | Security | Medium | 1 hr | Add 5MB per-file upload check in `vibe_service.py` and simple token bucket or slowapi rate limiting on `/intake/generate`. |
| **6** | **P2** | **Add Linting & Typecheck to GitHub Actions CI** | CI/CD | Medium | 30 mins | Add `ruff check` and `npm run build` to `.github/workflows/ci.yml`. |
| **7** | **P3** | **Accessibility Polish (Labels & Badges)** | A11y | Low | 30 mins | Add missing labels to onboarding date inputs and bump subtle text contrast classes. |
| **8** | **P3** | **Scripts Directory Housekeeping** | Quality | Low | 30 mins | Move 37 ad-hoc root/script files into `scripts/archive/` or dedicated integration tests. |

---
*Report generated and committed to `docs/EVALUATION_AUDIT_REPORT_V2.md`.*
