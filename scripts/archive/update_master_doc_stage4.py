import re

file_path = "docs/UTSAV_MASTER_DOC.md"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update TOC
toc_target = "- [4.16 F16: Invitation Card Generator](#416-f16-invitation-card-generator)"
toc_replacement = "- [4.16 F16: Invitation Card Generator](#416-f16-invitation-card-generator)\n  - [4.17 F17: Compose Celebration Orchestration Flow](#417-f17-compose-celebration-orchestration-flow)"
assert toc_target in content, "TOC target not found"
content = content.replace(toc_target, toc_replacement, 1)

# 2. Update Decisions Log (fix DEC-031 newline and add DEC-032)
dec_pattern = re.compile(
    r"\|\s*\*\*DEC-031\*\*.*?Revisit at Milestone M9 when mature rating tiers, full Leaflet map, and PostGIS geocoding are implemented\.\s*\|",
    re.DOTALL
)
dec_match = dec_pattern.search(content)
assert dec_match, "DEC-031 match not found"

new_dec = (
    "| **DEC-031** | **F15-Lite Seed Strategy & Honesty Guardrail** | Curated real directory seed set (19 venues: 11 Jaipur, 8 Pune) with locality-centroid approximate coordinates; every entry starts unrated (`rating_tier: new_unrated`, `average_rating: null`) with `is_verified_profile: false` and cost estimates flagged as `limited_data: true`. | Unblocks Stage 4 Compose Celebration venue selection immediately without synthetic or unverified business claims. Preserves strict honesty until post-event ratings (F12) and quote benchmarks (F5) accumulate real data. | **Critical** | Revisit at Milestone M9 when mature rating tiers, full Leaflet map, and PostGIS geocoding are implemented. |\n"
    "| **DEC-032** | **Compose Celebration Progressive Confirmation & Zero Assumption Inheritance** | The guided celebration composer sequences Venue Selection -> Muhurat Timing -> Invitation Generation. Every step only consumes data explicitly confirmed by the host. A selected venue is stored strictly as a shortlist pick (`venue_status: \"shortlist_pick\"`), never falsely claimed as a confirmed booking. Panchang muhurat windows must be confirmed by the host to lock `sub_events.is_muhurat_locked = True`; skipped steps explicitly record skip flags in `events.metadata_json[\"compose_celebration\"]` and render clean placeholders in invitation outputs rather than blocking or fabricating details. Progress persists directly in the database (`events.metadata_json`), ensuring state survives browser refreshes and multi-device sessions without phantom drafts. | Preserves absolute truthfulness across multi-stage orchestration. Eliminates premature vendor commitment claims and fabricated religious timings. | **Critical / Absolute** | Fundamental invariant for host trust and workflow orchestration. |"
)
content = content[:dec_match.start()] + new_dec + content[dec_match.end():]

# 3. Add Section 4.17
sec4_target = "### 4.16 F16: Invitation Card Generator"
# find the end of Section 4.16 (before "## 5. Information Architecture")
ia_idx = content.find("## 5. Information Architecture")
assert ia_idx != -1, "Information Architecture section not found"

sec4_17 = """### 4.17 F17: Compose Celebration Orchestration Flow
- **Overview:** End-to-end guided orchestration flow that weaves together Stage 3 Venue Discovery (F15-Lite), Stage 1 Panchang Muhurat Timing (M5), and Stage 2 Invitation Card Studio (M10/F16) into a coherent, progressive multi-step wizard.
- **User Story:** *As an event host setting up a celebration, I want a step-by-step guided flow to discover and shortlist a venue, inspect and lock an auspicious muhurat, and immediately generate production-ready invitation cards without losing progress or seeing fabricated details.*
- **User Flow:**
  1. Host navigates to `/dashboard/events/{id}/compose` or clicks "✨ Compose Celebration" on the Event Workspace header.
  2. **Step A — Venue Selection:** Browser geolocation or fallback city selector queries nearby venues via F15-Lite. Host chooses a venue (persisted as `venue_status: "shortlist_pick"`) or explicitly clicks "I'll decide later".
  3. **Step B — Muhurat Timing:** System displays deterministic astronomical muhurat windows computed by M5's ephemeris engine with mandatory DEC-009 elder/priest consultation disclaimers. Host selects and confirms an auspicious window (locking `sub_events.is_muhurat_locked = True`) or clicks "Skip timing for now".
  4. **Step C — Invitation Generation:** Host seamlessly transitions to the Invitation Card Studio (`/dashboard/events/{id}/invitations`). Confirmed venue and locked muhurat are automatically consumed by M10; skipped steps display clean, honest placeholders ("Venue to be confirmed", "Time to be confirmed").
- **Edge Cases:** Host skips all steps; host picks venue but skips timing; host refreshes page mid-flow; host revisits previous steps to modify choices.
- **Validation Rules:** In accordance with DEC-032, no assumption inheritance is permitted across steps. Shortlisted venues must never be labeled as confirmed bookings. Skips must never invent default times or venues.
- **Acceptance Criteria:**
  - Automated unit test suite passes green across happy path, all-skips path, and partial paths.
  - State persisted to `events.metadata_json["compose_celebration"]` across all transitions.
  - Zero unverified claims or placeholder leaks in invitation generation outputs.

---

"""
content = content[:ia_idx] + sec4_17 + content[ia_idx:]

# 4. Add Screen Inventory row to Section 5.3
screen_target = "| **Invitation Card Studio** | `/dashboard/events/{id}/invitations` | Generate and export personalized invitation cards from the confirmed theme, date, and guest list | Host | Unified Event Workspace tab, Compose Celebration flow (Stage 4) |"
screen_replacement = (
    "| **Invitation Card Studio** | `/dashboard/events/{id}/invitations` | Generate and export personalized invitation cards from the confirmed theme, date, and guest list | Host | Unified Event Workspace tab, Compose Celebration flow (Stage 4) |\n"
    "| **Compose Celebration Orchestrator** | `/dashboard/events/{id}/compose` | Step-by-step progressive confirmation wizard (Venue -> Muhurat -> Invitation) | Host | Event Workspace CTA, Onboarding success |"
)
assert screen_target in content, "Screen Inventory target not found"
content = content.replace(screen_target, screen_replacement, 1)

# 5. Add Section 11.9
sec11_target = "### 11.8 Invitation Cards (`/api/v1/events/{id}/invitations`)"
sec12_idx = content.find("## 12. Component Inventory")
assert sec12_idx != -1, "Component Inventory section not found"

sec11_9 = """### 11.9 Compose Celebration Orchestration (`/api/v1/events/{id}/compose`)
- **POST `/compose`** — Body: `ComposeUpdateSchema` (`step`, `venue_name`, `venue_locality`, `venue_skipped`, `muhurat_time`, `muhurat_locked`, `timing_skipped`).
  - Progressively updates celebration setup state in `events.metadata_json["compose_celebration"]`.
  - When venue is selected, stores venue details with `venue_status: "shortlist_pick"` (DEC-032).
  - When muhurat is confirmed, updates `metadata_json["muhurat_time"]` and locks primary sub-event `is_muhurat_locked = True`.
  - When steps are skipped, clears unconfirmed attributes to ensure clean downstream placeholders.

---

"""
content = content[:sec12_idx] + sec11_9 + content[sec12_idx:]

# 6. Add Component Inventory entry
comp_target = "5. `<EventTimelineCard />`: Interactive timeline card rendering sub-event duration, venue, and muhurat lock status."
comp_replacement = (
    "5. `<EventTimelineCard />`: Interactive timeline card rendering sub-event duration, venue, and muhurat lock status.\n"
    "6. `<ComposeCelebrationStepper />`: Guided 3-step wizard coordinating venue discovery, panchang muhurat selection, and invitation card generation."
)
assert comp_target in content, "Component Inventory target not found"
content = content.replace(comp_target, comp_replacement, 1)

# 7. Add Section 17.2 Stage 4 subsection
milestone_target = "### 17.3 Definition of Done (DoD) per Milestone"
milestone_idx = content.find(milestone_target)
assert milestone_idx != -1, "DoD target not found"

stage4_sec = """#### Stage 4: Compose Celebration Orchestration Flow [COMPLETE — SEQUENCED WORKFLOW, STEPPER & LIVE DB WIRED]
- **Scope:** Coherent end-to-end orchestration flow sequencing Stage 3 (F15-Lite Venue Selection) -> Stage 1 (M5 Panchang Muhurat Timing) -> Stage 2 (M10 Invitation Card Studio).
- **Core Orchestration Guarantees (DEC-032):**
  - **Progressive Confirmation:** Zero assumption inheritance. Steps only use data explicitly confirmed by the host.
  - **Honest Venue Status:** Selected venue is stored as a shortlist pick (`venue_status: "shortlist_pick"`), never falsely claimed as a confirmed booking.
  - **Explicit Muhurat Confirmation:** Astronomical muhurat candidates computed deterministically; locked to `sub_events.is_muhurat_locked = True` only on explicit host confirmation; skips leave time unconfirmed.
  - **Honest Invitation Rendering:** Invitations consume confirmed venue & muhurat seamlessly; when skipped, render clean placeholders ("Venue to be confirmed", "Time to be confirmed") with zero hallucination.
  - **State Persistence:** Multi-step wizard state persisted to PostgreSQL `events.metadata_json["compose_celebration"]` supporting browser refresh and multi-device resumption.
  - **Route & UI:** Dedicated guided stepper route `/dashboard/events/{id}/compose` and quick action tile in `EventDashboardClient.tsx`.
- **Test Coverage:** Automated unit test suite (`tests/unit/test_compose_celebration.py`) validating (1) Happy path (venue + muhurat confirmed -> M10 renders with lossless PDF), (2) All-skips path (zero fabricated values), and (3) Partial path (venue confirmed, timing skipped).

"""
content = content[:milestone_idx] + stage4_sec + content[milestone_idx:]

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Successfully updated docs/UTSAV_MASTER_DOC.md with Stage 4 specifications!")
