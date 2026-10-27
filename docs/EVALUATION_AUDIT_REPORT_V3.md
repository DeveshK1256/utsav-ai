# EVALUATION AUDIT REPORT V3: Comprehensive Third-Pass Numeric Scoring

**Audit Date:** 2026-10-27  
**Auditor:** Automated Agentic Pair / Quality & Security Auditor  
**Evaluation Standard:** Strict Evidence Discipline. No rounded-up numbers. A 10/10 requires zero found gaps after exhaustive attempts to break the system. All scores are backed by live production tests executed against deployed URLs on 2026-10-27:
- **Backend:** `https://utsav-ai-ycg2.onrender.com`
- **Frontend:** `https://utsav-ai.netlify.app`
- **CI / Build Pipeline:** [GitHub Actions Workflow Run 40385966974](https://github.com/DeveshK1256/utsav-ai/actions/runs/40385966974)

---

## Executive Scorecard Summary

| # | Rubric Criterion | Numeric Score (1–10) | One-Line Justification Grounded in Fresh Live Evidence |
|:---:|---|:---:|---|
| **1** | **Code Quality** | **7.2 / 10** | Clean domain modularity and zero frontend TypeScript build errors, but penalized by 932 Ruff lint issues, 279 MyPy type errors, and CI lint gates running in non-blocking `continue-on-error` mode. |
| **2** | **Security** | **8.8 / 10** | Live penetration tests verify 403 on unauth mutations/reads, forged origin CORS block, 404 on `/env-check`, fail-closed WhatsApp webhook, and live 20 req/min rate limit, but penalized by token acceptance in URL query strings (`?owner_token=`) and `localStorage` storage. |
| **3** | **Efficiency** | **7.5 / 10** | Server-internal execution is 1.90ms (instantaneous) and video is metadata-preloaded, but penalized by a severe ~43.2s cold start delay on Render free tier, 85ms–120ms network RTT to Singapore, and 6.5s–7.0s uncached public Overpass queries. |
| **4** | **Testing** | **7.6 / 10** | 84 of 84 automated backend tests pass with 80.0% coverage and all 6 bug regression safeguards active in a green CI gate, but strictly capped by 0.0% frontend component unit test coverage (no Jest/RTL or Vitest suite). |
| **5** | **Accessibility** | **8.6 / 10** | 0 automated axe-core violations on live Netlify across all 4 production routes, 4.5:1+ contrast, and synced WebVTT captions, but penalized because automated tools test ~35% of WCAG and manual screen-reader walkthrough of the multi-step compose wizard remains untested. |
| **6** | **Problem Statement Alignment** | **8.5 / 10** | Authentic, comprehensive Indian celebration planner with deterministic budgets, ephemeris panchang timings, and genuine Google `gemini-3-flash-preview` integration, but penalized by WhatsApp guest coordination being paused in production and absence of Google Cloud Run / Firebase infrastructure. |

### Overall Arithmetic Average: **8.0 / 10**
*(Computed strictly as: `(7.2 + 8.8 + 7.5 + 7.6 + 8.6 + 8.5) / 6 = 8.033 / 10`)*

---

## Detailed Criterion Evaluations

### Criterion 1: Code Quality — 7.2 / 10

#### 1. What was Actively Verified Today (2026-10-27)
- **Frontend TypeScript Build Gate:** Executed `npm --prefix frontend run build`. The production bundle compiles cleanly with **0 TypeScript errors** and **0 ESLint errors** in 18.1s.
- **Repository Cleanliness:** Audited `scripts/` and repository root. 32 ad-hoc test scripts were archived into `scripts/archive/`. No new temporary scratch scripts were accumulated.
- **Modular Domain Architecture:** Core services (`BudgetScalingEngine`, `DAGScheduler`, `PanchangService`, `InvitationCardRenderer`) remain cleanly decoupled from HTTP controller logic.

#### 2. Specific Remaining Gaps & Deficits
- **Linter Failures (Ruff):** Running `py -3 -m ruff check backend/` identifies **932 errors** (702 auto-fixable). Issues include unsorted imports (`I001`), unused imports (`F401` — e.g. unused `Tradition` and `VendorProfile` left inside `_background_db_backfill` in `backend/app/main.py:127`), legacy type annotations (`UP006`/`UP045`), and blind exception catches (`BLE001`).
- **Static Typing Failures (MyPy):** Running `py -3 -m mypy backend/app --explicit-package-bases --ignore-missing-imports` identifies **279 errors across 25 files**. The majority stem from SQLAlchemy 2.0 ORM column mappings where `Column[str]` is passed into helper functions typed for `str`.
- **CI Quality Gate Strategy:** In [`.github/workflows/ci.yml:44-50`](file:///d:/Utsav/.github/workflows/ci.yml#L44-L50), both the Ruff and MyPy steps specify `continue-on-error: true`. They operate in report-only mode and do not block pull requests from merging with linting or typing regressions.

#### 3. What Would Make this a True 10/10
1. Run `ruff check --fix backend/` and manually resolve the remaining ~230 non-autofixable linting errors.
2. Update SQLAlchemy model type annotations or introduce schema mapper helpers so `mypy` passes with 0 errors across all 53 backend source files.
3. Remove `continue-on-error: true` in `.github/workflows/ci.yml` so that static analysis becomes a hard blocking gate.

---

### Criterion 2: Security — 8.8 / 10

#### 1. What was Actively Verified Today (2026-10-27)
A fresh penetration test suite was executed directly against `https://utsav-ai-ycg2.onrender.com`:
- **Unauthenticated Mutation Block:** `DELETE https://utsav-ai-ycg2.onrender.com/api/v1/events/{id}` without a token was rejected with **HTTP 403 Forbidden** (`{'detail': 'Forbidden: Invalid or missing X-Event-Owner-Token. Unauthorized mutation attempt.'}`).
- **Unauthenticated Read Block:** `GET https://utsav-ai-ycg2.onrender.com/api/v1/events/{id}` without a token was rejected with **HTTP 403 Forbidden**.
- **Forged Token Read Block:** `GET ...` with `X-Event-Owner-Token: badtoken123` was rejected with **HTTP 403 Forbidden**.
- **Authenticated Read Success:** `GET ...` with valid owner token returned **HTTP 200 OK**.
- **CORS Forged Origin Block:** `GET /health` with `Origin: https://evil-hacker.com` returned `Access-Control-Allow-Origin: None`.
- **Information Disclosure Block:** `GET /env-check` returned **HTTP 404 Not Found**.
- **WhatsApp Webhook Fail-Closed:** `POST /api/v1/webhooks/whatsapp` without signature returned **HTTP 403**; with forged HMAC signature returned **HTTP 403**.
- **Live Rate Limiting:** A burst of 25 rapid requests to `https://utsav-ai-ycg2.onrender.com/api/v1/intake/generate` resulted in exactly **20 HTTP 201 Created** responses followed by **5 HTTP 429 Too Many Requests** responses (`{'error': 'Rate limit exceeded: 20 per 1 minute'}`).
- **Upload File Size Ceiling:** Enforced 5MB per-image limit in `vibe_service.py` with HTTP 400 rejection verified via regression suite.

#### 2. Specific Remaining Gaps & Deficits
- **Token Acceptance in Query Strings (CWE-598):** In [`backend/app/core/security.py:20`](file:///d:/Utsav/backend/app/core/security.py#L20), `verify_event_owner_token` accepts `owner_token: Optional[str] = Query(None)`. If a client passes `?owner_token=...` in a URL, the secret owner token is exposed to intermediary proxy logs, server access logs, and HTTP `Referer` headers.
- **Client Storage Mechanism:** The frontend stores the event owner token in browser `localStorage` (`utsav_event_owner_token_<eventId>`). While standard for lightweight single-page applications, `localStorage` is accessible to client-side scripts, making it vulnerable if an XSS flaw ever enters the frontend dependency tree.

#### 3. What Would Make this a True 10/10
1. Delete `owner_token: Optional[str] = Query(None)` from `security.py` so tokens can only be transmitted via headers (`X-Event-Owner-Token` or `Authorization: Bearer`).
2. Replace `localStorage` token storage with HttpOnly, Secure, SameSite session cookies issued by the backend upon event creation.

---

### Criterion 3: Efficiency — 7.5 / 10

#### 1. What was Actively Verified Today (2026-10-27)
- **Decoupled Background Startup:** Startup initialization and schema backfill run in a detached background daemon worker (`_background_db_backfill`), permanently eliminating startup hangs.
- **Server-Internal Route Latency:** Steady-state route execution on `/health` is **1.90 ms** mean (measured via `test_startup_performance.py`), verifying zero blocking I/O on the health check path.
- **Lazy Loading of Heavy Assets:**
  - Video asset (`1.53 MB`) in `WalkthroughVideoPlayer.tsx` specifies `preload="metadata"`, preventing video byte transmission on initial landing page load.
  - Leaflet map component in `VenueDiscoveryList.tsx` is dynamically imported (`dynamic(() => import(...), { ssr: false })`), ensuring map bundles are only evaluated client-side when needed.
- **Database Query Efficiency:** Single event view queries `Event` and its 3 child relationships in 4 deterministic SELECT queries without N+1 loops.

#### 2. Specific Remaining Gaps & Deficits
- **Render Free Tier Cold Start (~43.2s Delay):** When the backend is idle for >15 minutes, Render spins down the free container. The first request from a user incurs a **~43.2-second wait** while the container provisions. This is a severe, real user-facing friction point.
- **Cross-Region Geographic Network Transit:** Because the backend is hosted on Render's Singapore region (`ap-southeast-1`), client requests originating from India incur **85 ms – 120 ms** of latency even on established Keep-Alive sessions, and **115 ms – 250 ms** on fresh TLS handshakes.
- **Public Overpass API Latency (6.5s – 7.0s):** Live venue discovery queries (`/api/v1/discovery/vendors?city=Jaipur`) require **6.5s – 7.0s** to resolve because they query OpenStreetMap's public Overpass server synchronously without intermediate edge caching.

#### 3. What Would Make this a True 10/10
1. Deploy on an always-on infrastructure tier (or serverless platform with provisioned concurrency / Google Cloud Run `min-instances: 1`) to eliminate the 43s cold start.
2. Implement server-side caching (Redis or local SQLite TTL table) for Overpass geospatial bounding box queries, dropping repeated city venue searches from 7.0s down to <50ms.

---

### Criterion 4: Testing — 7.6 / 10

#### 1. What was Actively Verified Today (2026-10-27)
- **Comprehensive Backend Automated Suite:** Ran `pytest tests/unit/ tests/schema/ tests/eval/ --cov=backend/app`. All **84 tests passed in 88.20s** (100% pass rate).
- **Backend Test Coverage:** Real coverage across `backend/app/` is **80.0%** (3,751 statements executed out of 4,686 total).
- **Historical Bug Regression Safeguards Active:**
  1. *Venue scaling / tiered decor:* `test_tiered_decor_scaling_stepping_to_large_tier` (PASSED).
  2. *Decor base rate ceiling:* `test_decor_base_rate_sanity_ceiling_regression` (PASSED).
  3. *Deterministic confidence score:* `test_deterministic_rsvp_confidence_and_parsing` (PASSED).
  4. *Panchang elder citation requirement:* `test_ephem_panchang_provider_wednesday_abhijit_caution` (PASSED).
  5. *Venue dedup over-merge prevention:* `test_distinct_venues_not_overmerged_within_350m` (PASSED).
  6. *Startup hang decoupling:* `test_startup_and_health_check_instantaneous` (PASSED).
- **Automated CI Pipeline:** [GitHub Actions Workflow Run 40385966974](https://github.com/DeveshK1256/utsav-ai/actions/runs/40385966974) is **100% green** on `main`.

#### 2. Specific Remaining Gaps & Deficits
- **Frontend Component Unit Test Coverage is 0.0%:** There is no Jest, Vitest, or React Testing Library framework configured in `frontend/package.json`. While full-page flows are probed via end-to-end scripts, individual React components (`VenueDiscoveryList`, `ComposePageClient`, `BudgetBreakdown`, `GuestCoordinationModule`) have zero unit or isolated regression test coverage.
- **Gemini Provider Mocking:** `backend/app/services/providers/gemini_provider.py` achieves only **22% coverage** because external network calls to Google Gemini are bypassed or mocked in automated runs.

#### 3. What Would Make this a True 10/10
1. Configure Vitest and React Testing Library in `frontend/` and implement component tests for the onboarding form, step progression, and map filter state, reaching >75% frontend coverage.
2. Add simulated HTTP failure and timeout integration tests for `gemini_provider.py`.

---

### Criterion 5: Accessibility — 8.6 / 10

#### 1. What was Actively Verified Today (2026-10-27)
- **Live Axe-Core WCAG 2.1 AA Scan:** Executed headless browser audit against live Netlify deployment (`node scripts/verify_live_e2e_a11y.cjs`):
  - `https://utsav-ai.netlify.app/`: **0 Violations** (25 passes)
  - `https://utsav-ai.netlify.app/onboarding`: **0 Violations** (25 passes)
  - `https://utsav-ai.netlify.app/dashboard/events/default`: **0 Violations** (24 passes)
  - `https://utsav-ai.netlify.app/dashboard/events/default/compose`: **0 Violations** (24 passes)
- **Form Controls:** Every input on the multi-step onboarding wizard includes explicit `<label htmlFor="...">` bindings and descriptive `aria-label` tags.
- **Color Contrast:** All text, badges, and toggle buttons meet or exceed the WCAG 4.5:1 contrast requirement (dimming pulse opacity artifact resolved).
- **Live Video Captions:** `https://utsav-ai.netlify.app/media/utsav_demo_captions.vtt` was probed live and returned **HTTP 200 OK** (`Content-Type: text/vtt; charset=UTF-8`) with synchronized speech cues matching the walkthrough narration.
- **Keyboard Navigation Pins:** Leaflet markers in `LeafletVenueMap.tsx` are configured with programmatic `tabindex="0"`.

#### 2. Specific Remaining Gaps & Deficits
- **Automated Tool Blind Spots:** Axe-core only tests a subset (~30–40%) of WCAG requirements. Crucial user-experience criteria remain untested:
  - *Screen-Reader Voice Walkthrough:* No manual walkthrough with NVDA, JAWS, or VoiceOver has been performed to evaluate whether dynamic step changes in `/compose` are clearly announced.
  - *Dynamic State Announcements (`aria-live`):* When a user advances through the 3 steps of Compose Celebration or selects a venue pin, no `aria-live="polite"` region announces the selection or state update to assistive tech.
  - *Complex Map Focus Trap:* Keyboard tab navigation through interactive Leaflet map tiles lacks explicit boundary trapping, meaning keyboard users can get caught in panning controls.

#### 3. What Would Make this a True 10/10
1. Add `aria-live="polite"` status containers that announce step advancement and venue selection to screen readers.
2. Conduct and record a verified screen-reader user test using NVDA or VoiceOver across all 4 key routes.

---

### Criterion 6: Problem Statement Alignment — 8.5 / 10

#### 1. What was Actively Verified Today (2026-10-27)
- **Complete Cultural Celebration Capabilities:**
  - *Event Diversity:* Supports weddings, birthdays, and community festivals with tailored formulas and rituals.
  - *Deterministic Budget Scaling:* Budget engine accurately allocates tier multipliers and guest-count scaling.
  - *Muhurat Ephemeris Calculations:* Ephem-based astronomical calculations compute authentic auspicious timings and Rahu Kalam warnings with mandatory elder verification disclaimers.
  - *Devanagari Bilingual Invitations:* Generates print-ready PNG and bitwise-lossless PDF invitations supporting Hindi/Marathi typography.
  - *Nationwide OpenStreetMap Discovery:* Resolves physical venues across Indian cities with zero paid API billing risk.
- **Google AI Integration:** Configured and active on Google's bleeding-edge **`gemini-3-flash-preview`** model (verified directly in [`backend/app/services/providers/gemini_provider.py:31`](file:///d:/Utsav/backend/app/services/providers/gemini_provider.py#L31)).

#### 2. Specific Remaining Gaps & Deficits
- **WhatsApp Guest Coordination (F3) Paused in Production:** In production, `ENABLE_M4_WHATSAPP=false` is enforced pending external Meta Business verification. Because automated guest coordination, RSVP collection, and reminder scheduling are core to managing Indian celebrations, this feature being paused is a real, functional gap against the complete product promise.
- **Absence of Google Cloud Platform / Firebase Infrastructure:** The hackathon evaluation rubric explicitly highlights Google Cloud (Cloud Run, Firebase) adoption as a positive scoring factor. While Gemini usage is substantive, Utsav is deployed on Render (Singapore) and Netlify Edge, leaving the Google Cloud hosting/auth ecosystem criteria unfulfilled.

#### 3. What Would Make this a True 10/10
1. Complete Meta Business verification and enable live production WhatsApp two-way messaging (`ENABLE_M4_WHATSAPP=true`).
2. Deploy the containerized backend onto Google Cloud Run and integrate Firebase Authentication for host logins to satisfy the rubric's Google Cloud Platform adoption criteria.

---

## Final Scorecard & Arithmetic Summary

```
===================================================================
UTSAV AI — EVALUATION AUDIT V3 SCORECARD
===================================================================
1. Code Quality:                7.2 / 10
2. Security:                    8.8 / 10
3. Efficiency:                  7.5 / 10
4. Testing:                     7.6 / 10
5. Accessibility:               8.6 / 10
6. Problem Statement Alignment: 8.5 / 10
-------------------------------------------------------------------
OVERALL UNWEIGHTED AVERAGE:     8.03 / 10  (Report Score: 8.0 / 10)
===================================================================
```

*Report generated, verified against live production URLs on 2026-10-27, and committed in `docs/EVALUATION_AUDIT_REPORT_V3.md`.*
