# Utsav AI Code Quality Audit

**Audit date:** 2026-10-29
**Repository:** `DeveshK1256/utsav-ai`
**Baseline commit:** `c6e7f09`
**Scope:** Initial read-only inspection followed by documented, incremental remediation batches.

## Executive summary

The repository has a useful existing quality foundation: Ruff, MyPy, Bandit, Radon, frontend ESLint/TypeScript/Vitest, Alembic migrations, security-header tests, and a substantial backend test suite. The measured baseline is not fully green, however:

| Gate | Observed baseline |
|---|---|
| Backend Ruff | Pass: `All checks passed!` |
| Backend MyPy | Pass: `Success: no issues found in 92 source files` |
| Bandit | Pass: no findings |
| Radon complexity (`C` and above) | Pass: no output |
| Initial backend tests (`-m "not live"`) | **181 passed, 1 skipped, 2 deselected, 2 failed** |
| Final backend tests with CI WhatsApp environment | **197 passed, 1 skipped, 3 deselected** |
| Final backend line coverage | **92.22%** |
| Final backend branch coverage | **85.04%**, above the documented 85% gate |
| Frontend ESLint | Pass |
| Frontend TypeScript | Pass |
| Frontend Vitest | Pass: 16/16 tests |
| Frontend production build/CSP post-processing | Pass, with Next.js workspace-root, middleware, and static-export warnings |
| npm dependency audit | Pass: no known vulnerabilities |
| Python dependency audit | Pass for published dependencies; local `utsav` package was not auditable because it is not on PyPI |
| CI baseline/ratchet files referenced by the request | **Absent**: `.github/ci_baseline.json` and `scripts/ci_ratchet.py` do not exist |

The highest-priority confirmed baseline risks were startup-time schema mutation outside Alembic, fail-open initialization error handling, WhatsApp enabled by default, a hardcoded webhook verification secret, a test-only authorization bypass in production code, and request-body limits that only inspected a client-controlled `Content-Length` header. The focused remediation batch below addresses these items; architectural refactoring remains follow-up work.

## Validation strategy

Changes will be made only after this baseline. Each focused batch will:

1. Add a regression test that reproduces the defect or protects the required invariant.
2. Use Alembic for schema changes; no destructive migration or production reset.
3. Run the smallest relevant backend/frontend checks, then the full CI-equivalent checks.
4. Report exact commands and observed results.
5. Keep live provider tests opt-in and deterministic tests offline with mocks.

## File-by-file audit coverage

Every tracked source, test, CI, dependency, deployment, script, migration, and documentation file was inventoried. The following files received direct code/configuration review or were included in baseline execution:

### Backend application

`backend/app/main.py`, `backend/app/core/config.py`, `backend/app/core/limiter.py`, `backend/app/core/security.py`, `backend/app/db/base.py`, `backend/app/db/session.py`, `backend/app/db/seed_benchmarks.py`, `backend/app/db/seed_traditions.py`, `backend/app/models/__init__.py`, `backend/app/models/models.py`

Routers: `backend/app/api/v1/discovery.py`, `events.py`, `guests.py`, `intake.py`, `invitations.py`, `quotes.py`, `replanning.py`, `rituals.py`, `vibe.py`, `webhooks.py`

Schemas: `backend/app/schemas/discovery.py`, `events.py`, `guests.py`, `intake.py`, `invitations.py`, `quotes.py`, `replanning.py`, `rituals.py`, `vibe.py`

Services and provider adapters: all files under `backend/app/services/`, including DAG scheduling, discovery, invitation rendering/export, LLM/Gemini providers, replanning, WhatsApp, tradition merge, budgeting, quoting, rituals, intake, vibe, and event composition.

Configuration/data assets: `backend/app/config/*.json` and `backend/app/assets/fonts/*.ttf`.

### Database and migrations

`backend/alembic.ini`, `backend/alembic/env.py`, and migrations `0001_initial_m0_schema.py` through `0008_f16_invitation_cards.py`.

### Frontend

All tracked files under `frontend/app/`, `frontend/components/`, `frontend/lib/`, `frontend/scripts/`, `frontend/tests/`, `frontend/public/`, plus `frontend/middleware.ts`, `next.config.js`, `tsconfig.json`, `eslint.config.mjs`, `vitest.config.mjs`, and both frontend manifests/lockfile.

### Tests and scripts

`tests/conftest.py`; all files under `tests/unit/`, `tests/schema/`, `tests/eval/`, `tests/live/`, `tests/e2e/`, and `tests/prompt-regression/`; all tracked files under `scripts/`, including audit, CI, coverage, seed, smoke, and deployment-verification scripts.

### CI, deployment, and documentation

`.github/workflows/ci.yml`, `codeql.yml`, and `scorecard.yml`; `Dockerfile`, `render.yaml`, `netlify.toml`, `.env.example`, `.pre-commit-config.yaml`, `README.md`, `CONTRIBUTING.md`, and all tracked files under `docs/`.

## Confirmed defects and high-priority findings

### C1 — Application startup performs schema creation and ad hoc migrations

**Severity:** Critical
**Evidence:** `backend/app/main.py:110-221`, especially `120`, `124-166`, and `168-212`.

`_background_db_backfill()` calls `Base.metadata.create_all()` and executes raw `ALTER TABLE` statements during application startup. It also performs data updates and seed operations in the same startup path. This bypasses Alembic as the authoritative schema mechanism, creates concurrent initialization/race behavior through a daemon thread, and can leave an application serving traffic against a partially upgraded database.

**Reproduction:** `tests/conftest.py:12-20` also has to call `create_all`, issue an `ALTER TABLE`, and invoke the startup backfill to make tests work. The baseline emits a FastAPI `on_event` deprecation warning from `backend/app/main.py:231`.

**Required remediation:** Move schema changes into Alembic migrations, make startup validation/readiness explicit, and make seed operations independently idempotent and transactionally bounded. Initialization failures must be observable and must not be reported as a successful healthy state.

### C2 — WhatsApp feature flag defaults to enabled

**Severity:** High
**Evidence:** `backend/app/main.py:97-107`; `.env.example:25-32`.

When `ENABLE_M4_WHATSAPP` is absent, application code uses `"true"` and registers guest/webhook routes. The example environment says `"false"`, so a production deployment that omits the variable silently diverges from the documented safe default.

**Impact:** An optional external integration is enabled without an explicit operator decision, increasing attack surface and making missing provider configuration an operational failure rather than a fail-closed state.

### C3 — Hardcoded security-sensitive webhook verification default

**Severity:** High
**Evidence:** `backend/app/core/config.py:20`; fallback duplicated in `backend/app/api/v1/webhooks.py:27-29`; `.env.example:31`.

`WHATSAPP_WEBHOOK_VERIFY_TOKEN` has a hardcoded default value, and the router repeats the same fallback. A deployment that omits the secret has a predictable webhook verification token.

**Required remediation:** Require the secret when WhatsApp is enabled in production, reject an enabled cloud provider without required credentials, and keep local mock/test configuration explicit.

### C4 — Owner-token authorization has a test-environment bypass

**Severity:** Critical
**Evidence:** `backend/app/core/security.py:40-56` and `81-83`.

If `PYTEST_CURRENT_TEST` is present and an event lacks a token, authorization returns the event without requiring a token. Authorization behavior therefore depends on test-process environment state, and the security implementation contains a bypass that can be accidentally carried into a nonstandard production process.

**Required remediation:** Always generate/persist/recover tokens through the normal path and always require a matching header. Tests should create explicit tokens or inject a test database/session, not change authorization semantics.

### C5 — Request-body limit trusts `Content-Length`

**Severity:** High
**Evidence:** `backend/app/main.py:42-56`.

The middleware rejects only when the client supplies a numeric `Content-Length` above 10 MB. Chunked requests, missing headers, and malformed values proceed to the application, so the documented “strict limit” is not enforced for all request bodies.

**Required remediation:** Count bytes while receiving the body or enforce a bounded receive stream, preserving FastAPI request handling and returning 413 without buffering unbounded input.

### C6 — Initialization/provider failures are hidden as non-fatal

**Severity:** High
**Evidence:** `backend/app/main.py:224-228` and `100-107`.

Database backfill failures are logged as warnings while the server remains healthy, and optional router import failures are swallowed after logging. `/health` reports `"healthy"` without checking initialization readiness. This produces success-shaped responses while required persistence/provider setup may be unavailable.

**Required remediation:** Separate liveness from readiness, expose an initialization state, log structured failure context, and fail readiness when required startup work fails. Optional features should be explicitly disabled rather than silently skipped.

### C7 — Deterministic test suite depends on live/external OSM behavior

**Severity:** High
**Evidence:** Baseline command:

```text
PYTHONPATH=. DATABASE_URL=sqlite:///./baseline_test.db WHATSAPP_PROVIDER=mock ENABLE_M4_WHATSAPP=true TESTING=true .venv/bin/pytest tests -m "not live" --cov=backend/app --cov-branch --cov-report=json:/tmp/utsav-cov.json --cov-report=term
```

Observed failures:

* `tests/unit/test_compose_celebration.py::test_compose_celebration_with_discovered_osm_venue`: expected a Bengaluru OSM venue but received zero results.
* `tests/unit/test_discovery.py::test_discovery_osm_venues_overpass_mock`: patched `urllib.request.urlopen`, but no `VendorProfile` was persisted.

The first test is network/environment dependent despite being outside the `live` marker. The second indicates the production adapter and test double are not aligned, or the adapter suppresses the mocked failure path.

**Required remediation:** Inject the discovery client, make offline fixtures the default for unit tests, and isolate real OSM integration tests behind an explicit opt-in marker.

## Other confirmed risks and maintainability findings

* `backend/app/main.py:231` uses deprecated FastAPI `on_event`; migrate to lifespan while preserving startup semantics.
* `backend/app/main.py:164-166` suppresses SQLite migration errors, which can hide incompatible schemas.
* `backend/app/api/v1/events.py:50-53` fabricates pincode and event dates when omitted. This conflicts with preserving truthful event defaults and should be replaced with explicit schema validation or a documented domain default.
* The same owner token is stored in both `events.owner_token` and `metadata_json` (`backend/app/api/v1/events.py:43-56`), creating dual sources of truth. Recovery must define precedence and repair behavior.
* `backend/app/api/v1/webhooks.py:27-29` duplicates configuration fallback logic.
* CI uses `npm ci || npm install` (`.github/workflows/ci.yml`), which can silently disregard lockfile reproducibility after a failed locked install.
* Frontend build warns about multiple lockfiles/workspace-root inference and deprecated middleware convention. These are non-blocking but should be resolved deliberately.
* `google.generativeai` emits a deprecation warning during tests; provider migration should be planned separately from deterministic business-rule changes.

## Probable risks requiring focused follow-up

1. Concurrent startup threads/processes can race on seed inserts and data backfills even when individual seed functions appear idempotent.
2. Storing uploaded quote bytes in the primary database (`QuoteDocument.uploaded_file`) can create unbounded row growth and expensive transactions; verify deployment limits before changing the contract.
3. Broad CORS methods/headers (`backend/app/main.py:78-85`) should be narrowed to the actual frontend contract.
4. The current health response identifies a database type but does not perform a database readiness query.
5. Provider exception paths and transaction boundaries in `llm_provider.py`, `replanning/service.py`, `invitation/renderer.py`, and discovery services need targeted failure-path tests before refactoring.

## Stylistic and incremental improvement suggestions

* Add explicit public return types to service interfaces not covered by current MyPy configuration.
* Prefer typed settings for feature flags and provider mode rather than repeated `os.getenv` parsing.
* Replace duplicated response-construction logic with small typed helpers where it improves cohesion.
* Use structured logging fields for event IDs, provider names, and migration/seed phases.
* Add a documented dependency lock/update policy for Python; the frontend already has a lockfile.

## Prioritized remediation checklist

### P0 — correctness/security

- [ ] Remove startup `create_all`, raw DDL, and data backfills from application startup; add/verify Alembic migrations.
- [ ] Remove the `PYTEST_CURRENT_TEST` owner-token bypass; test authorization with explicit persisted tokens.
- [ ] Enforce request-body size for missing/untrusted `Content-Length` using bounded receive handling.
- [ ] Make WhatsApp disabled by default and fail closed when production cloud credentials/secrets are missing.
- [ ] Remove hardcoded webhook verification fallback and add regression tests for missing/invalid secrets.
- [ ] Make readiness reflect migration/seed/provider initialization failures.

### P1 — deterministic quality

- [ ] Inject/mock OSM discovery in unit tests and mark live network checks explicitly.
- [ ] Add owner-token generation, persistence, recovery, header-only authorization, and concurrency regression tests.
- [ ] Add startup/seed idempotency and concurrent initialization tests.
- [ ] Add boundary tests for request size, malformed headers, invalid payloads, and response contracts.

### P2 — engineering standards

- [ ] Replace deprecated startup event API with lifespan.
- [ ] Remove `npm ci || npm install`; make lockfile installation failure explicit.
- [ ] Add or restore `.github/ci_baseline.json` and `scripts/ci_ratchet.py` only after their intended threshold semantics are specified.
- [ ] Resolve frontend workspace-root/middleware warnings without changing deployment behavior.
- [ ] Plan migration from deprecated Gemini SDK.

## Exact baseline commands and observed results

```text
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
cd frontend && npm ci
.venv/bin/ruff check backend
# All checks passed!
.venv/bin/mypy backend --explicit-package-bases
# Success: no issues found in 92 source files
.venv/bin/bandit -r backend/app -q
# no findings
.venv/bin/python -m radon cc -s -n C backend/app
# no output
frontend: npm run lint
# exit 0
frontend: npm test -- --run
# 4 files, 16 tests passed
frontend: npx tsc --project tsconfig.json --noEmit
# exit 0
frontend: npm run build
# exit 0; warnings recorded above
.venv/bin/pip-audit
# No known vulnerabilities; local utsav package not found on PyPI
```

The backend test command and full output are recorded above. It reached the configured 90% line-coverage requirement but failed because of the two OSM tests; its measured branch coverage was 83.36%, below the CI workflow’s 85% assertion.

## Final report status

## Remediation completed in this pass

The following changes were implemented with regression coverage:

* Added Alembic revision `0009_owner_tokens_and_vendor_profiles.py` for the owner-token column and vendor profile table; removed application-startup schema creation, raw DDL, and backfill mutation.
* Replaced the owner-token test bypass with secure generation, persistence, recovery, and explicit header authorization. Existing metadata tokens remain preferred for compatibility.
* Disabled WhatsApp by default, removed the predictable webhook fallback, and rejected unsafe production/mock or incomplete cloud configuration.
* Added streamed ASGI request-body accounting so limits apply when `Content-Length` is absent or untrusted.
* Made reference-data initialization synchronous in the FastAPI lifespan so failures are visible instead of hidden in a daemon thread.
* Made OSM cache retries deterministic and marked the live network test separately.
* Added `tests/unit/test_security_regressions.py` covering token recovery, configuration fail-closed behavior, streamed request limits, and middleware scope handling.

Final validation commands and observed results:

```text
PYTHONPATH=/root/utsav-ai ENABLE_M4_WHATSAPP=true WHATSAPP_WEBHOOK_VERIFY_TOKEN=ci-test-token WHATSAPP_PROVIDER=mock \
  .venv/bin/python -m pytest -m "not live" --cov=backend/app --cov-branch --cov-fail-under=90
# 197 passed, 1 skipped, 3 deselected; line coverage 92.22%, branch coverage 85.04%

.venv/bin/ruff check backend tests/unit/test_security_regressions.py
# All checks passed
.venv/bin/mypy backend --explicit-package-bases
# Success: no issues found in 93 source files
git diff --check
# no output
```

Remaining risks and incomplete checks:

* The requested incremental refactors for scheduler, LLM, replanning, invitation rendering, discovery, and models are not complete.
* `.github/ci_baseline.json` and `scripts/ci_ratchet.py` remain absent; no baseline ratchet behavior is claimed.
* The health endpoint is still liveness-oriented and does not expose a separate initialization readiness state.
* Frontend checks, Bandit, Radon, dependency audits, and Alembic clean-upgrade were run previously in this session and passed; the existing Next.js and provider deprecation warnings remain.

## Second audit measurements

The requested analyzer measurements were rerun after the remediation batch:

```text
.venv/bin/ruff check backend
# All checks passed
.venv/bin/mypy backend --explicit-package-bases
# Success: no issues found in 94 source files
.venv/bin/python -m radon cc -s -n C backend/app
# no output; no function exceeded cyclomatic complexity 10
```

Additional repository measurements:

The reproducible machine-readable and Markdown inventories are generated with:

```text
python scripts/quality_report.py
```

The resulting `reports/quality_metrics.json` and `reports/quality_metrics.md` are generated
in CI from the checked-out commit and uploaded as the `quality-metrics` artifact; generated
snapshots are intentionally not committed so their SHA cannot become stale. Cross-language duplication is measured
separately with `npx --yes jscpd@4.0.5 ... --threshold 2.0`; this is a ratchet ceiling,
not a claim that the requested `<0.5%` target has been met.

| Measurement | Command/result |
|---|---|
| Python source files inspected | AST script: 95 |
| Functions over 50 lines | `scripts/quality_report.py`: 50; largest is `llm_provider.py:86` at 170 lines |
| Files over 400 lines | AST/script inventory: 5 (`seed_traditions.py`, `llm_provider.py`, `models.py`, `gemini_provider.py`, `dag/templates.py`) |
| Broad `except Exception` handlers | AST script: 0 |
| TypeScript `any` type tokens | `rg` over `frontend/app`, `frontend/components`, and `frontend/lib`: 0; remaining textual “any” matches are prose/HTML metadata |
| Duplication | `jscpd@4.0.5`, excluding `node_modules`/`.next`: 1.65% overall (485/29,377 lines; 37 clone groups), above the requested `<0.5%` target |
| Frontend tests | Vitest: 16 passed |
| Frontend build | `npm run build`: passed, with existing workspace-root, middleware, and static-export warnings |

No independent analyzer capable of producing a trustworthy composite “95+/100” score is configured in this repository. A composite score is therefore not claimed. The measured gates are reported directly, including the unmet duplication and function-size targets.

## Additional reliability/security remediation

* Added migration `0010_unique_inbound_whatsapp_message_ids.py`, creating a partial unique index for provider message IDs.
* Webhook inbound processing now checks the provider message ID before applying RSVP/STOP/FAQ side effects, making repeated deliveries idempotent in addition to the database uniqueness guarantee.
* Deterministic replanning responses now identify themselves with an explicit `fallback_warning`.
* Added regression tests for duplicate webhook delivery, malformed webhook entries, and private GET authorization.
* Private GET routes for guests, fact sheets, reminders, invitations, vibe assets, replanning proposals, pandit guides, and quote operations now require the event owner token.
* Quote comparisons and competitor leverage are constrained to the authenticated event, preventing cross-event data access.

Complexity status: Radon reports no function above cyclomatic complexity 10, including the prioritized modules. The separate readability threshold remains unmet for 50 functions over 50 physical lines; the largest prioritized functions are `replanning/service.py:create_change_proposal` (131 lines), `quotes.py:compare_quotes` (68 lines), `quotes.py:upload_quote` (65 lines), and `discovery/service.py:search_vendors` (61 lines). These are follow-up refactor targets because splitting them safely requires preserving provider and transaction boundaries.

### Updated remediation checklist

- [x] Remove startup schema mutation and use Alembic.
- [x] Remove the owner-token test bypass and add authorization regression tests.
- [x] Enforce streamed request-body limits.
- [x] Make WhatsApp configuration fail closed.
- [x] Remove hardcoded webhook verification fallback.
- [x] Make reference-data initialization synchronous.
- [x] Add deterministic discovery and security regression coverage.
- [x] Add separate database readiness reporting and fail readiness on initialization/probe errors.
- [x] Centralize Meta WhatsApp transport, response validation, timeout, and error mapping.
- [ ] Complete the larger service/model dependency-injection refactors.
- [ ] Add or restore the documented CI baseline/ratchet artifacts.

## Fourth audit validation

The local remediation was audited against remote `main` at `c6e7f097e89b9236618cfc0d076d9182b3ad8029`.
The fourth-pass changes add `/readyz`, make `/health` report degraded until database initialization
and a readiness query succeed, and centralize Meta provider HTTP response validation and failure
handling in one transport helper. The exact validated commit must be recorded here after publication.

Current local measurements after these changes:

| Measurement | Result |
|---|---|
| Backend tests | 199 passed, 1 skipped, 3 deselected |
| Backend line coverage | 92.28% |
| Backend branch coverage | Above the enforced 85% threshold |
| Ruff / MyPy | Passed; 94 source files type-checked |
| Bandit / Radon | Passed; no complexity output at threshold C |
| Lizard | Backend gate passes at CCN 10; report records 8 frontend functions above CCN 10 for follow-up |
| pip-audit | No known vulnerabilities; editable local package skipped |
| Readiness regressions | 2 passed: healthy/ready and initialization failure/degraded |
| WhatsApp/security regressions | 32 passed |

## Fifth audit decisions

The checked-in Advanced CodeQL workflow was removed because GitHub repository default setup is
enabled and GitHub rejects uploads from both configurations. The repository therefore uses one
active configuration: GitHub default CodeQL setup for Python, JavaScript/TypeScript, and Actions.
If Advanced setup is required later, an administrator must first disable default setup in
**Settings → Security → Code security and analysis → Code scanning → CodeQL analysis**, then
restore an Advanced workflow with equivalent language coverage.

Webhook HMAC verification no longer consults pytest or test-environment variables. Missing,
malformed, stale, future, or invalid signatures fail closed. Inbound RSVP/STOP database changes
and receipt logging now share one transaction; concurrent duplicate IDs roll back safely. FAQ
outbound delivery remains at-least-once because the provider call is external and is not claimed
as exactly-once delivery.
