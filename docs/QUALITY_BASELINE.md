# Utsav Code Quality Baseline Audit (Phase 0)

**Date**: 2026-10-28  
**Target**: Raise external Code Quality rating from **86/100 to 95+** while maintaining Security (99), Efficiency (100), Testing (98), Accessibility (99), and Problem Statement Alignment (99).  
**Status**: Read-only measurement completed. No application code altered.

---

## 1. Executive Summary: Baseline Metrics Table

| Metric Category | Specific Indicator | Baseline Count | Target (Phase 1 & 2) |
| :--- | :--- | :--- | :--- |
| **Linter Compliance** | Expanded Ruff Violations (`--select E,F,W,I,UP,B,C4,PIE,SIM,RUF,BLE,S,ANN,C90,PL,ARG,T20,PTH,N,ERA,TRY,PERF`) | **801 errors** | **0 errors** |
| | Suppressed Ruff Rules in `pyproject.toml` | 6 rules (`E501`, `RUF001`, `E402`, `B904`, `RUF012`, `SIM116`) | **0 rules suppressed** (honest config) |
| **Type Integrity** | Mypy Strict Errors (`--disallow-untyped-defs`, `--disallow-incomplete-defs`, `--warn-return-any`, `--no-implicit-optional`, `--strict-equality`) | **72 errors** across 22 files | **0 errors** (100% typed endpoints & signatures) |
| | TypeScript `any` annotations | **40 usages** | **0 usages** (`strict` + `noUncheckedIndexedAccess`) |
| **Complexity & Maintainability** | Radon Maintainability Index < 20 (Grade B/C) | **1 file** (`replanning_service.py`: 15.74 B) | **0 files** (All Grade A >= 30) |
| | Functions with Cyclomatic Complexity > 10 (Grade C-F) | **32 functions/methods** (top: CC 44) | **0 functions with CC > 10** |
| | Backend Files > 400 Lines | **10 files** (max: 962 lines) | **0 files > 400 lines** (modularized) |
| | Backend Functions > 50 Lines | **64 functions** (max: 282 lines) | **0 functions > 50 lines** |
| | Frontend Components/Files > 400 Lines | **9 files** (max: 1199 lines) | Container / Presentational split |
| **Code Smells & Hygiene** | Blind `except Exception` (`BLE001`) | **41 occurrences** | **0 occurrences** (specific exception types) |
| | `raise` without `from err` (`B904`) | **17 occurrences** | **0 occurrences** (explicit chaining) |
| | Magic numbers in business logic (`PLR2004`) | **74 occurrences** | **0 occurrences** (centralized constants) |
| | Code duplication (`jscpd`) | **43 clones (1.82%, 613 lines)** | **< 0.5% duplication** |
| | Unused/Dead Code (`vulture`, `knip`) | 1 dead block (`guests.py:82`), 1 dead var, 2 unused frontend deps (`clsx`, `tailwind-merge`), 1 unused file (`theme-init.js`) | **0 dead code / 0 unused dependencies** |
| | Repo Root Clutter | 21 root files including SQLite DBs, JSON reports, binary `gitleaks.exe`, media | Clean root, structured `marketing/`, `docs/`, `scripts/` |

---

## 2. Detailed Tool Raw Outputs

### a. Ruff Expanded Rule Set Statistics
Command:
```bash
ruff check backend --select E,F,W,I,UP,B,C4,PIE,SIM,RUF,BLE,S,ANN,C90,PL,ARG,T20,PTH,N,ERA,TRY,PERF --ignore-noqa --statistics
```
Raw Statistics Output (801 Total Errors):
```text
324  E501     line-too-long
 74  PLR2004  magic-value-comparison
 57  ANN201   missing-return-type-undocumented-public-function
 40  BLE001   blind-except
 38  TRY003   raise-vanilla-args
 29  ARG001   unused-function-argument
 23  PLC0415  import-outside-top-level
 23  RUF012   mutable-class-default
 18  C901     complex-structure
 18  PLR0913  too-many-arguments
 18  PLR0917  too-many-positional-arguments
 17  B904     raise-without-from-inside-except
 14  PLR0912  too-many-branches
 12  PLR0915  too-many-statements
  9  ANN204   missing-return-type-special-method
  8  ARG002   unused-method-argument
  7  TRY400   error-instead-of-exception
  6  PTH118   os-path-join
  6  ARG003   unused-class-method-argument
  5  E402     module-import-not-at-top-of-file
  5  PTH120   os-path-dirname
  5  S310     suspicious-url-open-usage
  4  ANN401   any-type
  4  PTH123   builtin-open
  4  PERF401  manual-list-comprehension
  4  ANN001   missing-type-function-argument
  4  PTH110   os-path-exists
  4  T201     print
  3  RUF001   ambiguous-unicode-character-string
  3  PLR0911  too-many-return-statements
  3  TRY300   try-consider-else
  2  ERA001   commented-out-code
  2  ANN206   missing-return-type-class-method
  2  ANN202   missing-return-type-private-function
  2  N806     non-lowercase-variable-in-function
  1  S105     hardcoded-password-string
  1  SIM116   if-else-block-instead-of-dict-lookup
  1  PTH100   os-path-abspath
  1  TRY201   verbose-raise
Found 801 errors.
```

---

### b. Mypy Strict Errors by File
Command:
```bash
mypy backend --disallow-untyped-defs --disallow-incomplete-defs --warn-return-any --no-implicit-optional --strict-equality
```
Summary: **72 errors across 22 files** (62 source files inspected)

| Source File | Strict Mypy Errors | Primary Reason |
| :--- | :--- | :--- |
| `backend/app/api/v1/guests.py` | 9 | Missing endpoint return annotations (`-> ResponseModel`) |
| `backend/app/api/v1/rituals.py` | 7 | Missing return type annotations on route handlers |
| `backend/app/api/v1/vibe.py` | 7 | Missing return type annotations on route handlers |
| `backend/app/api/v1/replanning.py` | 6 | Missing return type annotations on route handlers |
| `backend/app/main.py` | 5 | Unannotated middleware and exception handlers |
| `backend/app/api/v1/invitations.py` | 5 | Missing return type annotations on route handlers |
| `backend/app/api/v1/quotes.py` | 4 | Missing return type annotations on route handlers |
| `backend/app/api/v1/events.py` | 4 | Missing return type annotations on route handlers |
| `backend/alembic/env.py` | 3 | Missing return type annotation and config typing |
| `backend/app/api/v1/intake.py` | 3 | Missing return type annotations on route handlers |
| `backend/app/services/budget_engine.py` | 2 | Returning `Any` from typed dictionary functions |
| `backend/app/schemas/intake.py` | 2 | Unannotated validator function and parameters |
| `backend/app/services/whatsapp/provider.py` | 2 | Missing `-> None` return annotations |
| `backend/app/api/v1/discovery.py` | 2 | Missing return type annotations on route handlers |
| `backend/app/api/v1/webhooks.py` | 2 | Missing return type annotations on route handlers |
| `backend/app/db/session.py` | 1 | Generator missing yield/return type annotation |
| `scripts/seed_vendor_discovery.py` | 1 | Unannotated helper function |
| `backend/app/db/seed_traditions.py` | 1 | Unannotated seed function |
| `backend/app/db/seed_benchmarks.py` | 1 | Missing `-> None` annotation |
| `backend/app/services/llm_provider.py` | 1 | Returning `Any` from provider factory |
| `backend/app/services/providers/gemini_provider.py` | 1 | Returning `Any` from payload builder |
| `backend/app/services/intake_service.py` | 1 | Missing return type annotation |

---

### c. Complexity & Maintainability Analysis

#### Radon Maintainability Index (`radon mi -s backend/app`)
- **52 files with Grade A (High Maintainability)**: ranging from 30.34 to 100.00
- **1 file with Grade B (Moderate Maintainability)**:
  - `backend/app/services/replanning_service.py`: **15.74 (B)**

#### Radon Cyclomatic Complexity (`radon cc -s -n C backend/app`)
High complexity functions (CC >= 11):
1. `backend/app/services/whatsapp/rsvp_parser.py:RSVPParser.parse_free_text` — **CC 44 (F)**
2. `backend/app/services/discovery_service.py:VendorDiscoveryService._fetch_and_persist_osm_venues` — **CC 43 (F)**
3. `backend/app/api/v1/quotes.py:upload_quote` — **CC 33 (E)**
4. `backend/app/services/replanning_service.py:ReplanningService.create_change_proposal` — **CC 33 (E)**
5. `backend/app/services/whatsapp/webhook_service.py:WhatsAppWebhookService.handle_inbound_payload` — **CC 33 (E)**
6. `backend/app/services/replanning_service.py:ReplanningService.accept_change` — **CC 32 (E)**
7. `backend/app/services/vibe_aggregation_engine.py:VibeAggregationEngine.aggregate_vibe_profiles` — **CC 31 (E)**
8. `backend/app/services/whatsapp/guest_service.py:GuestService.import_guest_rows` — **CC 31 (E)**
9. `backend/app/schemas/quotes.py:QuoteExtractionPayloadSchema.compute_deterministic_confidence` — **CC 30 (D)**
10. `backend/app/api/v1/events.py:update_event_compose_progress` — **CC 28 (D)**
11. `backend/app/services/tradition_merge_service.py:TraditionMergeService.merge_traditions` — **CC 28 (D)**
12. `backend/app/api/v1/invitations.py:_resolve_event_logistics` — **CC 27 (D)**
13. `backend/app/services/replanning_service.py:ReplanningService._check_infeasibility` — **CC 27 (D)**
14. `backend/app/services/invitation_renderer.py:InvitationCardRenderer._render_classic_royal` — **CC 25 (D)**
15. `backend/app/services/discovery_service.py:VendorDiscoveryService.search_vendors` — **CC 24 (D)**
16. `backend/app/services/whatsapp/faq_bot.py:FAQBotService.answer_question` — **CC 23 (D)**
17. `backend/app/services/whatsapp/phone_utils.py:normalize_e164_phone` — **CC 22 (D)**
18. `backend/app/services/invitation_renderer.py:InvitationCardRenderer._render_floral_festive` — **CC 21 (D)**
19. `backend/app/api/v1/quotes.py:generate_negotiation_draft` — **CC 21 (D)**
20. `backend/app/services/dag_scheduler.py:DAGScheduler.generate_ritual_samagri_tasks` — **CC 20 (C)**
21. `backend/app/api/v1/invitations.py:generate_invitation_cards` — **CC 19 (C)**
22. `backend/app/services/invitation_renderer.py:InvitationCardRenderer._render_modern_minimal` — **CC 19 (C)**
23. `backend/app/services/budget_rescaling_engine.py:BudgetRescalingEngine.rescale_for_budget_cut` — **CC 18 (C)**
24. `backend/app/services/budget_rescaling_engine.py:BudgetRescalingEngine.rescale_for_guest_count_change` — **CC 16 (C)**
25. `backend/app/services/discovery_service.py:are_venues_duplicates` — **CC 16 (C)**
26. `backend/app/services/invitation_renderer.py:InvitationCardRenderer.render_card` — **CC 16 (C)**
27. `backend/app/core/security.py:verify_event_owner_token` — **CC 15 (C)**
28. `backend/app/services/decor_cost_engine.py:DecorCostEngine.resolve_cost_range` — **CC 14 (C)**
29. `backend/app/services/providers/gemini_provider.py:GeminiNegotiationDraftProvider.generate_negotiation_drafts` — **CC 13 (C)**
30. `backend/app/services/providers/gemini_provider.py:GeminiReplanningExplanationProvider.generate_explanation_and_mitigations` — **CC 13 (C)**
31. `backend/app/services/providers/gemini_provider.py:GeminiVibeProvider.extract_vibe_from_images` — **CC 13 (C)**
32. `backend/app/api/v1/events.py:get_event` — **CC 12 (C)**

---

### d. Files > 400 Lines & Functions > 50 Lines

#### Backend Files > 400 Lines (10 files)
1. `backend/app/services/dag_scheduler.py` — **962 lines**
2. `backend/app/services/replanning_service.py` — **675 lines**
3. `backend/app/services/llm_provider.py` — **658 lines**
4. `backend/app/services/invitation_renderer.py` — **640 lines**
5. `backend/app/services/discovery_service.py` — **601 lines**
6. `backend/app/services/providers/gemini_provider.py` — **564 lines**
7. `backend/app/api/v1/quotes.py` — **539 lines**
8. `backend/app/services/tradition_merge_service.py` — **534 lines**
9. `backend/app/models/models.py` — **492 lines**
10. `backend/app/api/v1/invitations.py` — **402 lines**

#### Frontend Files > 400 Lines (9 application files)
1. `frontend/app/onboarding/page.tsx` — **1,199 lines**
2. `frontend/app/dashboard/events/[id]/EventDashboardClient.tsx` — **1,099 lines**
3. `frontend/app/dashboard/events/[id]/changes/[change_id]/ChangeProposalDiffClient.tsx` — **823 lines**
4. `frontend/components/ui/GuestCoordinationModule.tsx` — **817 lines**
5. `frontend/app/dashboard/events/[id]/vendors/quotes/ScopedQuotesDashboardClient.tsx` — **803 lines**
6. `frontend/components/ui/RitualIntelligenceHub.tsx` — **559 lines**
7. `frontend/app/dashboard/events/[id]/vibe/VibeToPlanClient.tsx` — **544 lines**
8. `frontend/components/ui/InvitationStudio.tsx` — **542 lines**
9. `frontend/components/ui/VenueDiscoveryList.tsx` — **461 lines**

#### Functions > 50 Lines
- **Backend**: **64 functions** exceeding 50 lines (top: 282 lines in `create_change_proposal`, 213 lines in `upload_quote`, 179 lines in `generate_merged_run_of_show`, 170 lines in `extract_quote_from_document`).
- **Frontend**: **24 components/functions** exceeding 50 lines (top: 1,008 lines in `EventDashboardClient`, 866 lines in `OnboardingPage`, 773 lines in `ChangeProposalDiffClient`, 767 lines in `GuestCoordinationModule`).

---

### e. Code Duplication, Dead Code, and Dependencies

#### Code Duplication (`jscpd`)
- **Total Duplicate Clones**: 43 clones detected
- **Duplication Rate**: 1.82% overall (613 lines duplicated across 33,666 lines total)
  - Python: 30 clones (389 lines, 2.96% of Python code)
  - TSX: 11 clones (167 lines, 1.59% of TSX code)
  - JSON: 2 clones (57 lines, 0.62% of JSON config)

#### Dead Code & Unreachable Logic (`vulture`)
- `backend/app/api/v1/guests.py:82`: **Unreachable code after `return` (100% confidence)**
- `backend/app/services/whatsapp/faq_bot.py:43`: Unused variable `use_llm` (100% confidence)

#### Frontend Dependency Audit (`knip`)
- **Unused dependencies in `frontend/package.json`**:
  - `clsx`
  - `tailwind-merge`
- **Unused files**:
  - `frontend/public/theme-init.js`
- **Unused & Duplicate exports**:
  - Unused export: `default` in `components/ui/VenueDiscoveryList.tsx`
  - Unused type: `CostEstimate` in `components/ui/VenueDiscoveryList.tsx`
  - Duplicate export: `VenueDiscoveryList | default`

---

### f. Code Smells & Quantitative Markers

| Marker | Count | Scope |
| :--- | :--- | :--- |
| `except Exception` (Blind Exception) | **41** | Backend routers & services |
| `# nosec` (Security Suppression) | **4** | Backend (`os.urandom`, hash operations) |
| `# noqa` (Linter Suppression) | **0** | Clean |
| `type: ignore` (Mypy Suppression) | **0** | Clean |
| `any` in TypeScript | **40** | Frontend client components |
| `TODO` / `FIXME` | **0** | Clean |
| `print(...)` in Python | **4** | Backend utility scripts/services |
| `console.log(...)` in TS/JS | **1** | Frontend client script |
| Magic Numbers (`PLR2004`) | **74** | HTTP status codes, budget weights, confidence thresholds |

---

### g. Repository Root Hygiene Inventory

| Root Item | Type | Current Purpose | Proposed Action in Phase 3 |
| :--- | :--- | :--- | :--- |
| `.git/`, `.github/` | Dir | Version control and GitHub Actions CI workflow | Retain, enhance CI with single workflow |
| `backend/` | Dir | FastAPI backend application and migrations | Retain, convert to standard Python package |
| `frontend/` | Dir | Next.js 15 frontend application | Retain, enforce strict TS & modularize |
| `tests/` | Dir | Pytest test suite (backend unit/integration/e2e) | Retain, restructure coverage-driven files |
| `docs/` | Dir | Project architecture and quality documentation | Retain |
| `scripts/` | Dir | Seeding, migration, and development utilities | Retain, relocate audit scripts to `scripts/audit/` |
| `AUDIT_LOG.md` | File | Historical milestone verification audit log | Move to `docs/AUDIT_LOG.md` |
| `brag-output/` | Dir | Social demo videos, incognito walkthroughs, reels | Move to `marketing/demo-assets/` |
| `social/` | Dir | Preview stills, marketing copy, reel scripts | Move to `marketing/social/` |
| `video_pipeline/` | Dir | Playwright video generators and neural TTS scripts | Move to `tools/video_pipeline/` |
| `landing/` | Dir | Static landing page mockup | Move to `marketing/landing-archive/` |
| `tools/` | Dir | Video/media utility wrappers | Retain under `tools/` |
| `doc_parts/` | Dir | Temporary fragments from doc compilation | Archive / Remove |
| `build_master_doc.py`| File | Doc compilation script | Move to `scripts/docs/` |
| `gitleaks.exe` | File | 15MB local binary executable | Remove from root, place in `.gitignore` |
| `utsav_dev.db` | File | 36MB local SQLite development database | Remove from root, place in `.gitignore` |
| `ci_test.db` | File | 1.1MB test database artifact | Remove from root, add to `.gitignore` |
| `cov.json` | File | Coverage JSON report dump | Move / ignore |
| `lh-*.json` | Files | 3 Lighthouse JSON reports (1.7MB total) | Move to `docs/lighthouse/` |
| `test_incognito_deployed.png` | File | Screenshot artifact | Move to `docs/assets/` |
| `uv.lock` | File | Minimal uv lockfile | Align with single dependency source |
| `LICENSE` | File | Missing Open-Source license | Add MIT License file |
