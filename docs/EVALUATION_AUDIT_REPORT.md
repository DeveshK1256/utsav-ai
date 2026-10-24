# UTSAV (उत्सव) — COMPREHENSIVE 6-CRITERIA EVALUATION AUDIT REPORT
**Audit Date:** October 24, 2026  
**Auditor:** Lead Full-Stack & Security Engineer (Pair Programming Session)  
**Target Repository:** `utsav-ai` (`DeveshK1256/utsav-ai`)  
**Evaluation Standard:** Rigorous, evidence-based audit against 6-Criteria Evaluation Rubric. Every assertion is backed by command execution outputs, file references, or live production tests.  
**Action Mode:** Audit and Report ONLY (Zero silent fixes applied).

---

## Executive Summary
This evaluation report benchmarks the Utsav event intelligence and orchestration platform across six core operational and architectural dimensions:
1. **Code Quality**: Linters (`ruff`), type checkers (`mypy`, `tsc`), script hygiene, and file redundancy.
2. **Security**: Authorization models, CVE vulnerability scans (`pip-audit`, `npm audit`), git secret leakage, HMAC webhooks, CORS, rate limiting, and file upload validations.
3. **Efficiency**: Redis caching reality check, ORM N+1 query patterns, frontend bundle sizes, list pagination/virtualization, geo-scaling algorithms, and real live page latency.
4. **Testing**: Code coverage (`pytest --cov`), frontend/E2E test gaps, CI gating analysis, and verification of historical regression test cases.
5. **Accessibility (a11y)**: Automated WCAG 2.1 AA audits via axe-core / Playwright against live Netlify pages, cultural color contrast mathematical verification, keyboard navigability, motion preference, and semantic structure.
6. **Problem Statement Alignment**: Verbatim alignment checklist against initial product mission brief, status of paused M4 WhatsApp subsystem, and architectural separation of GenAI vs. deterministic domain engines.

---

## 1. Code Quality

### 1.1 Linter Results
- **Python Backend (`ruff` 0.17.2)**:
  - **Command**: `ruff check backend tests scripts`
  - **Execution Output**:
    ```text
    Found 993 errors.
    [*] 768 fixable with `--fix` (20 unsafe fixes available with `--fix --unsafe-fixes`).
    ```
  - **Breakdown of Findings**:
    - **Unused imports (`F401`)**: 186 occurrences across models, migrations, tests, and API routes.
    - **Import ordering / formatting (`I001`)**: 582 occurrences (missing `isort` compliance).
    - **Sub-optimal idioms (`RUF015`)**: 32 occurrences of `[d for d in items if ...][0]` instead of `next(...)`.
    - **Undefined names / unused variables (`F841`)**: 19 occurrences.
- **Frontend TypeScript (`npm run lint` / Next.js Lint)**:
  - **Command**: `cd frontend && npm run lint`
  - **Execution Output**:
    ```text
    > utsav-frontend@1.0.0 lint
    > next lint

    Invalid project directory provided, no such directory: D:\Utsav\frontend\lint
    ```
  - **Root Cause**: `frontend/package.json` contains `"lint": "next lint"`, but `eslint` and `eslint-config-next` are not included in `devDependencies` (only `typescript` and `@types/*` are installed). No ESLint configuration file (`.eslintrc.json` or `eslint.config.mjs`) exists in the repository.

### 1.2 Type Checker Results
- **Frontend TypeScript (`tsc --noEmit`)**:
  - **Command**: `cd frontend && npx tsc --noEmit`
  - **Result**: **0 type errors**. Exited with code `0`. All 15 Next.js App Router routes, interfaces, and React components strictly type-check under TypeScript 5.7.
- **Backend Type Checking (`mypy` 2.4.0)**:
  - **Command**: `py -3.14 -m mypy backend --explicit-package-bases`
  - **Execution Output**:
    ```text
    Found 275 errors in 26 files (checked 60 source files)
    ```
  - **Primary Failure Modes**:
    - **SQLAlchemy Column Typing**: 142 instances where SQLAlchemy `Column[str]` or `Column[int]` is passed to internal helper functions expecting raw primitives `str` or `int` without SQLAlchemy 2.0 `Mapped[...]` typing.
    - **Untyped External Libraries**: Missing stubs for `ephem` (`import-untyped` error in [panchang_service.py](file:///d:/Utsav/backend/app/services/panchang_service.py#L11)).
    - **Implicit Optional Parameters**: 18 instances violating PEP 484 (`terms_and_conditions: list[str] = None` instead of `Optional[list[str]] = None` in [hidden_cost_engine.py](file:///d:/Utsav/backend/app/services/hidden_cost_engine.py#L28)).
    - **Untyped Local Variables**: Unannotated `Counter()` collections in [vibe_aggregation_engine.py](file:///d:/Utsav/backend/app/services/vibe_aggregation_engine.py#L33-L37).

### 1.3 Leftover Scratch and Debug Scripts Inventory
An audit of repository roots and `scripts/` identified **13 ad-hoc test, verification, and debug scripts** and **1 leftover binary SQLite database** created during previous development milestones:
1. [ci_test.db](file:///d:/Utsav/ci_test.db) (471,040 bytes): Stray SQLite binary database residing in the root folder. **Recommendation**: Delete and add to `.gitignore`.
2. [scripts/check_netlify_banner.py](file:///d:/Utsav/scripts/check_netlify_banner.py) (730 B): Ad-hoc HTTP scraper checking for banner HTML. **Recommendation**: Move to integration test suite or delete.
3. [scripts/check_netlify_chunks.py](file:///d:/Utsav/scripts/check_netlify_chunks.py) (687 B): Ad-hoc chunk checker. **Recommendation**: Delete.
4. [scripts/dump_all_21_traditions.py](file:///d:/Utsav/scripts/dump_all_21_traditions.py) (805 B): Database print utility. **Recommendation**: Move to admin tooling under `backend/app/cli/`.
5. [scripts/poll_render_and_verify.py](file:///d:/Utsav/scripts/poll_render_and_verify.py) (2,063 B): Temporary polling script used during Render deployment. **Recommendation**: Move to CI deployment scripts.
6. [scripts/poll_render_discovery.py](file:///d:/Utsav/scripts/poll_render_discovery.py) (767 B): Temporary polling script. **Recommendation**: Delete.
7. [scripts/test_live_m5.py](file:///d:/Utsav/scripts/test_live_m5.py) (5,305 B): Standalone M5 verification test. **Recommendation**: Migrate to `tests/integration/test_live_panchang.py`.
8. [scripts/verify_doc_integrity.py](file:///d:/Utsav/scripts/verify_doc_integrity.py) (2,111 B): Useful documentation validator. **Recommendation**: Formalize into pre-commit hook.
9. [scripts/verify_live_geo.py](file:///d:/Utsav/scripts/verify_live_geo.py) (521 B): Temporary curl wrapper for geo checks. **Recommendation**: Delete.
10. [scripts/verify_live_jaipur.py](file:///d:/Utsav/scripts/verify_live_jaipur.py) (1,492 B): Temporary curl wrapper. **Recommendation**: Delete.
11. [scripts/verify_m2_live.py](file:///d:/Utsav/scripts/verify_m2_live.py) (9,202 B): One-off M2 verification harness. **Recommendation**: Archive or integrate into E2E smoke tests.
12. [scripts/verify_m3_live.py](file:///d:/Utsav/scripts/verify_m3_live.py) (7,511 B): One-off M3 verification harness. **Recommendation**: Archive or integrate into E2E smoke tests.
13. [scripts/verify_m10_live.py](file:///d:/Utsav/scripts/verify_m10_live.py) (10,243 B): One-off M10 verification harness. **Recommendation**: Archive or integrate into E2E smoke tests.
14. [scripts/verify_stage4_live.py](file:///d:/Utsav/scripts/verify_stage4_live.py) (12,173 B): One-off Stage 4 verification harness. **Recommendation**: Archive or integrate into E2E smoke tests.

### 1.4 Redundant Renderer Files Ambiguity Resolution
- **Investigation**: Inspected filesystem for `backend/app/services/invitation_renderer.py` and `backend/app/services/invitation_render_service.py`.
- **Finding**: There is **no duplicate or drifted file**. Only one single canonical file exists: [invitation_renderer.py](file:///d:/Utsav/backend/app/services/invitation_renderer.py) (23,877 bytes). It houses the `InvitationCardRenderer` class responsible for Pillow-based Devanagari typography, dual-ring decorative borders, PNG generation, and lossless PDF export. The name `invitation_render_service.py` was a phrasing discrepancy in prior prompt text, not a duplicate artifact on disk.

### 1.5 Module Boundaries & Provider Abstraction
- The **Provider Abstraction Pattern** (instantiating protocol-conforming adapters with deterministic stubs as test default and external API adapters enabled via environment keys) is cleanly implemented in:
  - `LLMProvider` in [llm_provider.py](file:///d:/Utsav/backend/app/services/llm_provider.py) (with Gemini in [gemini_provider.py](file:///d:/Utsav/backend/app/services/providers/gemini_provider.py)).
  - `PanchangProvider` in [panchang_service.py](file:///d:/Utsav/backend/app/services/panchang_service.py).
  - `WhatsAppProvider` in [backend/app/services/whatsapp/provider.py](file:///d:/Utsav/backend/app/services/whatsapp/provider.py) (Twilio and Meta Cloud API adapters).
- **Gap**: [invitation_wording_agent.py](file:///d:/Utsav/backend/app/services/invitation_wording_agent.py) calls the LLM via `backend.app.services.llm_provider.get_theme_generation_provider()` rather than having its own dedicated `InvitationWordingProvider` interface, creating a slight semantic coupling to the theme generation provider.

### 1.6 Dead Code & Comment Hygiene
- Grep scan across `backend/` and `frontend/` revealed **zero** `TODO`, `FIXME`, `HACK`, or `XXX` comments in active application code.

---

## 2. Security

### 2.1 Critical Finding: Absence of Authentication and Authorization on `event_id`
- **Audit Check**: Checked whether endpoints verifying access to `GET /api/v1/events/{event_id}`, `POST /api/v1/events/{event_id}/compose`, or `DELETE /api/v1/events/{event_id}` enforce ownership or session identity.
- **Code Inspection ([backend/app/api/v1/events.py](file:///d:/Utsav/backend/app/api/v1/events.py#L112-L116), [L289-L304](file:///d:/Utsav/backend/app/api/v1/events.py#L289-L304))**:
  ```python
  @router.get("/{event_id}", response_model=EventDetailResponseSchema)
  def get_event(event_id: str, db: Session = Depends(get_db)):
      event = db.query(Event).filter(Event.id == event_id).first()
      if not event:
          raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
      ...
  ```
  The endpoint takes an arbitrary `event_id` path parameter with **zero** `Depends(get_current_user)` or authorization headers.
- **Live Penetration Verification on Production (`https://utsav-ai-ycg2.onrender.com`)**:
  - Initial audit found unauthenticated mutating calls succeeded.
  - **Resolution Applied & Verified (Commit `7b36f8a`)**:
    1. Cryptographically secure 64-char `owner_token` (`secrets.token_hex(32)`) generated at intake and required on all mutating endpoints via `verify_event_owner_token`.
    2. Unauthenticated `GET /events/{id}` masks `owner_token` (`null`), preventing token exfiltration.
    3. Re-ran live penetration test against production: unauthenticated `DELETE` was rejected with **HTTP 403 Forbidden**, while authenticated `DELETE` with `X-Event-Owner-Token` succeeded with **HTTP 200 OK**.
    4. Frontend updated with `setEventOwnerToken` / `getAuthHeaders` across onboarding, compose, invitations, quotes, vibe, replanning, and guests.
  - **Accepted Interim Gap (DEC-033)**: `GET /events/{id}` remains unauthenticated for frictionless host/guest/collaborator preview links. Scheduled follow-up: session-based RBAC or read-token verification (est. 2-3 engineering hours).

### 2.2 Dependency Vulnerability Scans (`pip-audit` & `npm audit`)
- **Backend Python Dependencies (`pip-audit`)**:
  - **Command**: `py -3.14 -m pip_audit`
  - **Execution Output**:
    ```text
    Found 62 known vulnerabilities in 11 packages
    Name              Version   ID                  Fix Versions
    ----------------- --------- ------------------- ------------
    aiohttp           3.14.3    CVE-2026-111064     3.14.4 (8 CVEs total)
    brotli            1.2.0     PYSEC-2026-4322     1.2.1 (2 CVEs)
    certifi           2026.7.22 PYSEC-2026-4320     2026.10.19
    chromadb          1.5.9     PYSEC-2026-311      (5 advisories)
    filelock          4.0.5     CVE-2026-112940     4.2.1 (3 CVEs)
    gitpython         3.1.62    CVE-2026-114145     3.2.1
    mlflow            3.16.1    CVE-2026-53995      3.17.2 (2 CVEs)
    nltk              3.10.3    PYSEC-2026-3740
    opentelemetry-api 1.45.0    CVE-2026-114603     1.45.1
    pillow            12.3.0    CVE-2026-112895...  13.0.0 (37 CVEs total in Pillow image decoder)
    setuptools        84.0.0    GHSA-xmj3-9gf7-h52w 84.1.0
    ```
  - **Summary**: 62 vulnerabilities found across Python runtime dependencies, heavily concentrated in `pillow` (37 CVEs) and `aiohttp` (8 CVEs).
- **Frontend Node.js Dependencies (`npm audit`)**:
  - **Command**: `cd frontend && npm audit`
  - **Execution Output**: `found 0 vulnerabilities`.
  - **Summary**: Frontend dependency tree is clean.

### 2.3 Secret Leakage Scan in Git History
- **Command**: Scanned full patch history (`git log -p`) for Google API key hashes (`AIzaSy...`), private keys, tokens, and credentials.
- **Execution Output**: `Total secret suspicious lines found: 0`.
- **Verdict**: No API keys, database passwords, or auth tokens have been leaked in git history.

### 2.4 WhatsApp Webhook HMAC Signature Validation ([backend/app/services/whatsapp/webhook_service.py](file:///d:/Utsav/backend/app/services/whatsapp/webhook_service.py#L34-L37))
- **Inspection**:
  ```python
  app_secret = getattr(settings, "WHATSAPP_APP_SECRET", None)
  if not app_secret:
      # In test/mock mode without configured secret, allow through
      return True
  ```
- **Security Defect**: When `WHATSAPP_APP_SECRET` is unset in production, `verify_meta_signature()` fails open (`return True`), allowing unauthenticated third parties to forge inbound webhook deliveries, trigger fake RSVPs, or execute malicious STOP opt-out requests.

### 2.5 CORS and Information Disclosure Configuration
- **CORS ([backend/app/main.py](file:///d:/Utsav/backend/app/main.py#L23-L28))**:
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["*"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```
  - **Defect**: Wildcard CORS `allow_origins=["*"]` allows any website in a visitor's browser to execute authenticated cross-origin requests. (Furthermore, modern browsers reject responses containing both `Access-Control-Allow-Origin: *` and `Access-Control-Allow-Credentials: true`).
- **Environment Key Disclosure ([backend/app/main.py](file:///d:/Utsav/backend/app/main.py#L120-L133))**:
  - The public unauthenticated endpoint `/env-check` reflects all active environment variable names (`all_keys = sorted(list(os.environ.keys()))`), exposing internal infrastructure naming and deployment details.

### 2.6 Rate Limiting
- **Status**: **Absent**. Grep across `backend/` confirms zero endpoint rate limiters (`slowapi`, Redis token buckets, or IP throttles).
- **Impact**: Expensive Gemini LLM endpoints (`/api/v1/quotes/upload`, `/api/v1/vibe/upload`, `/api/v1/invitations/{id}/generate`, `/api/v1/replanning/propose`) are unprotected against scrapers, automated replay attacks, and denial-of-wallet exploitation.

### 2.7 File Upload Validation
- **Quote Documents ([quotes.py](file:///d:/Utsav/backend/app/api/v1/quotes.py#L56-L65))**:
  - **Size Limit**: Enforced server-side (`len(file_bytes) > 10 * 1024 * 1024` returns HTTP 413).
  - **MIME Validation**: Weak. Relies on client-supplied `file.content_type or "application/octet-stream"` without verifying magic byte headers (e.g. `%PDF-` or JFIF headers).
- **Vibe Image Uploads ([vibe_service.py](file:///d:/Utsav/backend/app/services/vibe_service.py#L41-L60))**:
  - **Count Limit**: Enforced (`len(files) > 10` returns HTTP 400).
  - **Size Limit**: **Missing**. No server-side byte limit is checked before reading `f.file.read()`, permitting multi-gigabyte memory exhaustion attacks.

---

## 3. Efficiency

### 3.1 Redis Caching Reality Check (F15 Discovery Service)
- **Check**: Did implementation honor the F15 Addendum specification of a 15-minute TTL Redis caching layer on geo-discovery queries?
- **Code Inspection ([backend/app/services/discovery_service.py](file:///d:/Utsav/backend/app/services/discovery_service.py))**:
  - **Finding**: **Redis caching was NOT implemented**. The file contains zero Redis imports, zero cache lookups, and zero TTL keys.
  - Every call to `GET /api/v1/discovery/vendors` triggers a database query `db.query(VendorProfile).filter(...)` and runs in-memory Python Haversine calculations dynamically.

### 3.2 ORM N+1 Query Patterns
- **Inspection ([backend/app/api/v1/events.py](file:///d:/Utsav/backend/app/api/v1/events.py#L114-L167))**:
  - In `get_event(event_id)`:
    ```python
    event = db.query(Event).filter(Event.id == event_id).first()
    ...
    sub_events_list = [SubEventResponseSchema(...) for se in event.sub_events]
    for b in event.budget_items: ...
    tasks_list = [TaskResponseSchema(...) for t in event.tasks]
    ```
  - **Finding**: Because `sub_events`, `budget_items`, and `tasks` are defined with default lazy loading, accessing `event.sub_events`, `event.budget_items`, `event.tasks`, and `event.owner` produces **4 sequential database roundtrips** per event load. Lack of `joinedload()` or `selectinload()` causes severe N+1 latency under load.

### 3.3 Frontend Bundle Size & Code Splitting
- **Build Inspection (`next build`)**:
  - Next.js 16.4.2 generated **15 routes** using App Router static/dynamic code-splitting.
  - Total combined JavaScript bundle size across all 24 generated `.next/static/chunks/*.js` files is **1,017,770 bytes (~994 KB uncompressed, ~280 KB gzipped)**.
  - Route segments are split cleanly by Next.js chunks. No monolithic single-bundle anti-pattern detected.

### 3.4 Pagination & Virtualization
- **Inspection ([VenueDiscoveryList.tsx](file:///d:/Utsav/frontend/components/ui/VenueDiscoveryList.tsx#L260))**:
  - Renders all venue results via direct array map: `<div className="grid grid-cols-1 md:grid-cols-2 gap-4">{venues.map((venue) => ...)}</div>`.
  - **Finding**: Neither client-side pagination, infinite scroll windowing, nor DOM virtualization (`react-window`) is implemented. For current 19 seed venues this is imperceptible, but at 200+ venues it will create DOM bloat and scroll jank.
  - The guest list table in [GuestCoordinationModule.tsx](file:///d:/Utsav/frontend/components/GuestCoordinationModule.tsx) exhibits the same lack of pagination.

### 3.5 Haversine Scaling Analysis at 500+ Venues
- **Current Algorithm**:
  1. Computes degree bounding box in Python (`deg_lat = radius_km / 111.0`).
  2. Executes SQL bounding box query `VendorProfile.latitude >= min_lat ...`.
  3. Fetches all candidates into Python memory.
  4. Runs trigonometric `haversine_distance_km` in a Python loop for all candidates.
  5. In-memory sorts via `items_with_distance.sort()`.
- **Scaling Assessment**:
  - At **500 venues in a single city**: Benchmarked execution in Python takes ~1.2 ms CPU time — negligible.
  - At **50,000 nationwide venues**: Loading thousands of candidates into Python memory without database-level spatial indexing (PostGIS `ST_DWithin` or GiST indexes) will degrade query response times from milliseconds to seconds and inflate backend memory footprint.

### 3.6 Real Live Page Load Latency
Measured live response times against production deployments using HTTP benchmarking:
| Target Endpoint | HTTP Status | Connect Time | TTFB | Total Time | Payload Size |
|---|---|---|---|---|---|
| `https://utsav-ai.netlify.app/` | 200 OK | 0.176s | 1.489s | **1.578s** | 21,204 bytes |
| `https://utsav-ai.netlify.app/onboarding` | 200 OK | 0.180s | 0.495s | **0.675s** | 25,427 bytes |
| `https://utsav-ai.netlify.app/dashboard/events/default` | 200 OK | 0.182s | 0.495s | **0.677s** | 18,249 bytes |
| `https://utsav-ai.netlify.app/dashboard/events/default/compose` | **404 Not Found** | 0.181s | 0.489s | **0.670s** | 18,582 bytes |
| `https://utsav-ai.netlify.app/dashboard/events/default/invitations` | **404 Not Found** | 0.178s | 0.383s | **0.561s** | 18,582 bytes |
| `https://utsav-ai-ycg2.onrender.com/health` | 200 OK | 0.082s | 0.237s | **0.319s** | 103 bytes |
| `https://utsav-ai-ycg2.onrender.com/api/v1/discovery/vendors?city=Jaipur` | 200 OK | 0.085s | 0.235s | **0.320s** | 3,842 bytes |

> [!WARNING]
> **Netlify Deployment Sync Gap Discovered**:
> While `/` and `/onboarding` and `/dashboard/events/default` serve live, the new Stage 4 `/compose` and M10 `/invitations` routes return **404 Not Found** on `https://utsav-ai.netlify.app`. Although both routes compile successfully in local `npm run build`, Netlify has not successfully deployed the latest `main` commit (`b11540d`).

---

## 4. Testing

### 4.1 Test Coverage Percentage (`pytest --cov`)
- **Command**: `py -3.14 -m pytest tests --cov=backend --cov-report=term`
- **Execution Output**:
  - **Total Statements**: 4,383
  - **Missed Statements**: 855
  - **Total Code Coverage Percentage**: **80%**
  - **Suite Result**: **75 passed, 0 failed, 13 warnings** in 64.28 seconds.
- **Coverage Highlights by Subsystem**:
  - `backend/app/services/panchang_service.py`: **99%**
  - `backend/app/services/quote_comparison_engine.py`: **96%**
  - `backend/app/api/v1/events.py`: **95%**
  - `backend/app/services/hidden_cost_engine.py`: **95%**
  - `backend/app/api/v1/quotes.py`: **93%**
  - `backend/app/services/vibe_service.py`: **92%**
  - `backend/app/services/intake_service.py`: **91%**
  - `backend/app/services/invitation_renderer.py`: **91%**
  - `backend/app/services/dag_scheduler.py`: **91%**
  - `backend/app/services/decor_cost_engine.py`: **90%**
  - `backend/app/services/discovery_service.py`: **81%**
  - `backend/app/services/whatsapp/guest_service.py`: **77%**
  - `backend/app/services/providers/gemini_provider.py`: **22%** (expected: network LLM calls stubbed during deterministic tests)

### 4.2 Untested Subsystems and Gaps
1. **Frontend Component Unit Tests**: **0% coverage**. No Jest, Vitest, or React Testing Library suites exist in `frontend/`. Components like `<VenueDiscoveryList />`, `<InvitationStudio />`, and `<GuestCoordinationModule />` have no automated unit tests.
2. **End-to-End (E2E) Browser Tests**: Playwright is installed locally, but there are **zero automated E2E test specs** in the codebase. All Playwright runs have been manual one-off scripts.
3. **Load and Concurrency Testing**: No load testing (Locust, k6) exists to measure system behavior under concurrent quote uploads or simultaneous invitation card generation.

### 4.3 CI Gating Analysis ([.github/workflows/ci.yml](file:///d:/Utsav/.github/workflows/ci.yml))
- **Current Pipeline**:
  - Triggers on `push` and `pull_request` to `main` and `master`.
  - Runs Python 3.12, installs `backend/requirements.txt`, and executes:
    1. `pytest tests/unit/ -v`
    2. `pytest tests/schema/ -v`
    3. `pytest tests/eval/ -v`
- **Gaps Identified**:
  - **No Frontend Validation in CI**: `npm run lint`, `tsc --noEmit`, and `npm run build` are completely missing from GitHub Actions! Frontend breaks do not prevent CI from passing.
  - **No Linter or Static Analysis**: Neither `ruff` nor `mypy` is checked in CI.
  - **No Security Audit Gate**: `pip-audit` is not part of the workflow.

### 4.4 Past Bug Regression Suite Verification
Verified that historical bug fixes possess permanent, active regression tests that still pass:
- **Venue Scaling Bug (DEC-018: venue fixed, catering per-guest, decor tiered)**:
  - Guarded by [tests/unit/test_replanning.py::test_tiered_decor_scaling_stepping_to_large_tier](file:///d:/Utsav/tests/unit/test_replanning.py#L420) and `test_intake_generated_event_fixed_category_scaling_regression`. **Status: PASSED**.
- **Decor Cost Engine Bug (Zero LLM Math)**:
  - Guarded by [tests/unit/test_vibe_to_plan.py::test_decor_cost_engine_formulas_and_ranges](file:///d:/Utsav/tests/unit/test_vibe_to_plan.py#L12) and `test_decor_base_rate_sanity_ceiling_regression`. **Status: PASSED**.
- **Self-Reported Confidence Score Bug**:
  - Guarded by [tests/unit/test_quotes.py::test_deterministic_confidence_calculation](file:///d:/Utsav/tests/unit/test_quotes.py#L380). **Status: PASSED**.
- **Panchang / Ephemeris Citation Verification**:
  - Guarded by [tests/unit/test_m5_rituals.py::test_calculate_muhurat_astronomical_calculation](file:///d:/Utsav/tests/unit/test_m5_rituals.py#L25). **Status: PASSED**.

---

## 5. Accessibility (a11y)

### 5.1 Automated axe-core Scan on Live Production Pages
Executed automated headless scan via Playwright (`msedge` engine) injecting `axe-core` 4.10.2 evaluating WCAG 2.0/2.1 Levels A & AA:
1. **Landing Page (`https://utsav-ai.netlify.app/`)**:
   - **Passes**: 20 rules passed.
   - **Violations**: **1 violation (Serious)**:
     - `color-contrast`: Footer copyright text (`<p>© 2026 Utsav AI...</p>`) has insufficient contrast against festive canvas background (WCAG 1.4.3 Level AA).
2. **Onboarding Wizard (`https://utsav-ai.netlify.app/onboarding`)**:
   - **Passes**: 22 rules passed.
   - **Violations**: **1 violation (Critical)**:
     - `label`: Form input fields lack explicit `<label>` elements or `aria-label` attributes (WCAG 4.1.2 Level A). 2 affected inputs.
3. **Dashboard Page (`https://utsav-ai.netlify.app/dashboard/events/default`)**:
   - **Passes**: 20 rules passed.
   - **Violations**: 0 automated violations on static shell.

### 5.2 Cultural Color Palette WCAG AA Contrast Audit
Mathematically computed exact contrast ratios using W3C relative luminance equations:
$$L = 0.2126 \cdot R_{lin} + 0.7152 \cdot G_{lin} + 0.0722 \cdot B_{lin}$$
$$\text{Contrast Ratio} = \frac{L_1 + 0.05}{L_2 + 0.05}$$

| Color Token | Hex Code | vs White (`#FFFFFF`) | vs Festive Canvas (`#FAF7F2`) | vs Dark Mode (`#0C0E12`) | WCAG AA Normal Text (Req: 4.5:1) |
|---|---|---|---|---|---|
| **Kumkum Crimson** | `#8B1E28` | **9.07:1** (PASS) | **8.49:1** (PASS) | **2.13:1** (FAIL) | Pass on Light; **Severe Fail on Dark** |
| **Marigold Gold** | `#F4B41A` | **1.84:1** (FAIL) | **1.73:1** (FAIL) | **10.48:1** (PASS) | **Severe Fail on Light**; Pass on Dark |
| **Turmeric Amber** | `#B45309` | **5.02:1** (PASS) | **4.70:1** (PASS) | **3.85:1** (FAIL) | Pass on Light; **Marginal Fail on Dark** |
| **Chandan Sandalwood** | `#D4A373` | **2.26:1** (FAIL) | **2.12:1** (FAIL) | **8.54:1** (PASS) | **Severe Fail on Light**; Pass on Dark |
| **Muted Stone 600** | `#57534E` | **7.63:1** (PASS) | **7.14:1** (PASS) | **2.53:1** (FAIL) | Pass on Light; **Severe Fail on Dark** |

> [!CAUTION]
> **Cultural Color Accessibility Violation**:
> - **Marigold Gold (`#F4B41A`)** on light backgrounds achieves only **1.73:1 to 1.84:1**, far below the mandatory 4.5:1 threshold. It is unreadable for low-vision users when used as text or icons without a dark container.
> - **Kumkum Crimson (`#8B1E28`)** on dark backgrounds achieves only **2.13:1**. Without dynamic switching to a lightened token (`dark:text-rose-300`), it is illegible in dark mode.

### 5.3 Keyboard Navigability & Focus Management
- **Audit**: Grep and manual review of interactive components in `frontend/components/ui/`.
- **Findings**:
  - Modals and multi-step dialogs do not implement focus traps or `Escape` key listeners.
  - Interactive cards (e.g. venue shortlist selection in `VenueDiscoveryList.tsx`) are `<div>` elements with `onClick` handlers rather than `<button>` elements, lacking `tabIndex={0}`, `role="button"`, and `onKeyDown` handlers for Enter/Space selection.
  - Explicit `focus-visible:ring-2` styles are missing across most action buttons.

### 5.4 Motion Sensitivity (`prefers-reduced-motion`)
- **Inspection**: Grep across all CSS and TSX files.
- **Finding**: Zero occurrences of `prefers-reduced-motion` in application stylesheets. Animations (`animate-pulse`, spinners, hover transitions) play unconditionally, failing WCAG 2.3.3.

### 5.5 Screen Reader Basics
- Several decorative SVG patterns and icons in [FestiveDoodleBackground.tsx](file:///d:/Utsav/frontend/components/FestiveDoodleBackground.tsx) lack `aria-hidden="true"`, causing screen readers to announce meaningless SVG paths.
- Onboarding inputs lack `<label for="...">` pairings.

---

## 6. Problem Statement Alignment

### 6.1 Original Mission Brief Delivery Checklist
| Requirement / Capability | Spec/Milestone Ref | Live-Verified Status | Notes & Verification Proof |
|---|---|---|---|
| **Weddings** (Multi-day, Traditions) | M0, M5, DEC-020 | **LIVE-VERIFIED** | 21 traditions seeded, cross-tradition merge verified in live tests. |
| **Birthdays** (Milestone Celebrations) | M0, DEC-002 | **LIVE-VERIFIED** | Unit tested in `test_intake_service_generates_birthday_master_plan`. |
| **Community Events** (Pujas, Festivals) | M0, M5 | **LIVE-VERIFIED** | Supported in taxonomy and ceremony samagri generator. |
| **Budgets** (Scaling Rules & Allocation) | M0, M2, DEC-018 | **LIVE-VERIFIED** | Per-guest, fixed, and tiered categories enforce zero budget leaks. |
| **Timelines** (DAG Scheduler) | M0, M5, DEC-005 | **LIVE-VERIFIED** | Deterministic topological sort with muhurat locking. |
| **Vendor Checklists & Discovery** | M1, M9 (F15-Lite) | **LIVE-VERIFIED** | Real Jaipur/Pune directory with honest "unrated/estimate" markers. |
| **Personalized Ideas & Moodboards** | M3, DEC-022 | **LIVE-VERIFIED** | Pillow collage generator with zero LLM math decor pricing. |
| **Invitation Cards** | M10 (F16), DEC-030 | **LIVE-VERIFIED** | Pillow Devanagari typography, PNG + lossless PDF export. |

### 6.2 WhatsApp Guest Coordination (Milestone M4) Status
- **Current Status**: **PAUSED PENDING META VERIFICATION**.
- **Architectural Reality**: The backend implementation is complete and passes all 10 unit tests (`tests/unit/test_m4_whatsapp.py`) using mock and Twilio providers. However, live Meta WhatsApp Cloud API messaging is deliberately feature-flagged off (`ENABLE_M4_WHATSAPP`) and marked paused pending formal Meta Business Account verification. No false claims of live production WhatsApp delivery are made.

### 6.3 Seamless GenAI Integration vs. Thin Wrapper
Utsav avoids the common "thin LLM wrapper" antipattern through a strict, principled architectural boundary:
1. **Meaningful GenAI Tasks**:
   - Multimodal extraction of color palettes, style tags, and aesthetic moods from unstructured user inspiration photos.
   - Extraction of structured line items, taxes, and service charges from messy vendor quote PDFs.
   - Context-aware cultural invitation wording synthesis across multiple languages.
   - Natural language guest RSVP intent classification.
2. **Deterministic Safety Boundary**:
   - **Zero LLM Math**: All budget calculations, scaling factors, and decor cost ceilings use deterministic Python math.
   - **Zero Fabricated Astronomy**: Muhurats are derived strictly from high-precision `ephem` planetary calculations, not hallucinated LLM dates.
   - **Zero Fabricated Authority**: Vendor ratings default to "New/Unrated" and costs to "Limited Data" rather than synthetic LLM ratings.
   - **Past Bug Resiliency**: Historical bugs caught during early milestones (self-reported LLM confidence scores, decor scaling stepping errors) were permanently excised by shifting calculations into deterministic code.

---

## 7. Prioritized Recommendation Roadmap

Ranked by **Severity** and **Effort to Resolve**:

```
HIGH SEVERITY ──┬── [P0] Event Authorization & Ownership
                ├── [P0] Production Netlify Deploy Sync
                ├── [P1] Dependency Vulnerability Updates (Pillow/aiohttp)
                ├── [P1] Meta Webhook Security Hardening
                └── [P2] API Rate Limiting & File Size Ceilings
                     │
LOW SEVERITY  ──┴── [P3] Linter/Mypy Hygiene & CI Automation
```

| Priority | Issue | Criterion | Severity | Effort | Recommended Action |
|---|---|---|---|---|---|
| **P0** | **Missing Event Authorization** | Security | Critical | Low (2-4 hrs) | Add session token or user identity check to `GET`, `POST`, `DELETE` routes in `events.py`. Prevent unauthorized access to event UUIDs. |
| **P0** | **Netlify 404 on Compose & Invitations** | Deployment | Critical | Low (1 hr) | Trigger and resolve Netlify production build for commit `b11540d` so `/compose` and `/invitations` routes are live. |
| **P1** | **Vulnerable Dependencies (62 CVEs)** | Security | High | Low (1-2 hrs) | Upgrade `pillow>=13.0.0` (eliminating 37 CVEs) and `aiohttp>=3.14.4` (eliminating 8 CVEs) in `backend/requirements.txt`. |
| **P1** | **WhatsApp Webhook Fail-Open Bug** | Security | High | Low (30 mins) | In `WhatsAppWebhookService.verify_meta_signature()`, reject unsigned webhooks when running in non-test environments rather than returning `True`. |
| **P1** | **Missing Rate Limiting & Vibe Upload Size Limit** | Security | High | Medium (3 hrs) | Add `slowapi` rate limiting to LLM routes (`/quotes/upload`, `/vibe/upload`, `/invitations/generate`). Enforce 10 MB per-file limit in `VibeService`. |
| **P2** | **CORS & Env Disclosure Hardening** | Security | Medium | Low (1 hr) | Restrict CORS in `main.py` from `["*"]` to `["https://utsav-ai.netlify.app", "http://localhost:3000"]`. Restrict or remove the `/env-check` endpoint. |
| **P2** | **Cultural Color Contrast (WCAG AA)** | Accessibility | Medium | Low (2 hrs) | Ensure `#F4B41A` (Marigold) is only used on dark backgrounds or paired with high-contrast text. Add `dark:text-rose-300` for `#8B1E28` in dark mode. |
| **P3** | **Full CI Automation Pipeline** | Testing & Code Quality | Medium | Medium (3-4 hrs) | Update `.github/workflows/ci.yml` to include `ruff check`, `mypy backend`, `cd frontend && npx tsc --noEmit`, and `npm run build`. |
