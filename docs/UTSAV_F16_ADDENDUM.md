# Utsav Master Doc — F16 Addendum
### "Invitation Card Generator"

**How to use this file:** Drop-in addendum to `docs/UTSAV_MASTER_DOC.md`, matching the F15 addendum's conventions. Each block names its target section.

---

## Insert into Section 3 — Decisions & Assumptions Log

| ID | Category | Decision Taken | Rationale | Confidence | Revisit Trigger |
|---|---|---|---|---|---|
| **DEC-028** | **Card Rendering Approach** | Server-side composition (Pillow, same library already proven in F4's moodboard generator) over a second paid image-generation API | Keeps a consistent, already-tested dependency rather than adding a new generative cost/latency surface for something that is fundamentally a templated layout task, not open-ended image generation. | **High** | If hosts request true AI-illustrated card art (not just layout/typography), revisit with a generation provider, same pattern as F4's `DEC-022`. |
| **DEC-029** | **Personalization Scope** | Per-guest personalization is limited to name and RSVP-relevant fields (dietary note, table assignment if seating from F9 exists) — never fabricated personal details | Cards must never invent facts about a guest. Only fields the host or guest actually supplied are interpolated. | **Critical** | Never — same standard as all other no-invented-facts rules. |
| **DEC-030** | **Export Format** | Cards export as PNG (for WhatsApp/social sharing) and PDF (for printing), generated from one shared layout, not two separate designs | Avoids layout drift between the digital and print versions; matches the existing pattern of Claude Docs-style multi-format export used elsewhere in the stack. | **Medium** | If print-shop requirements (bleed, CMYK color profile) become necessary, add a dedicated print-export path. |

---

## Insert as Section 4.16 (after 4.15 F15, inside Section 4 — Functional Requirements)

### 4.16 F16: Invitation Card Generator
- **Overview:** Converts an accepted F4 theme (palette, style tags, invitation design brief text) plus confirmed event logistics (date/time — ideally muhurat-aware per F2 — venue name/address once selected) into an actual downloadable/shareable invitation card, personalized per guest where the guest list (F3, currently paused) exists.
- **User Story:** *As a host who's finalized my theme, my auspicious muhurat, and my venue, I want an actual invitation card generated — not just a text description of what one should look like — so I can send it to my guests without hiring a separate designer.*
- **User Flow:**
  1. User reaches this step only after a theme exists (F4) and a date/time is confirmed (F2's muhurat flow, or a manually chosen date if no muhurat applies for that event type).
  2. System pre-fills a card template using the theme's palette and style tags; user picks from 2-3 layout variants (not infinite customization — keep scope tight for v1).
  3. User confirms the text content: event name, host name(s), date/time, venue (once selected via F15-Lite or manually entered), and any tradition-specific wording pulled from F2's merged run-of-show (e.g. ceremony names).
  4. If a guest list exists (F3), the system generates one personalized card per guest (name interpolation only, per DEC-029); if no guest list exists yet, it generates one generic card the host can share manually.
  5. Preview renders before export — host can regenerate wording or swap layout, but cannot free-type arbitrary design changes in v1 (that's a future "full editor" scope, not this milestone).
  6. Export as PNG (digital share) or PDF (print), or both.
- **Edge Cases:** No venue selected yet (card renders with a placeholder "Venue to be confirmed" rather than blocking generation entirely); no muhurat/time confirmed yet (same placeholder pattern for time); very long venue names or guest names overflowing the template (truncate with ellipsis, never silently cut off important text like the date); non-Latin script names (Hindi/Marathi guest names) — font must support Devanagari rendering correctly, test this explicitly, don't assume the chosen font covers it.
- **Validation Rules:** Every field interpolated into a card must trace to a value the host actually confirmed (event record, theme record, guest record) — never a placeholder silently left in as if it were real content (no card should ship with literal `{host_name}` visible, that's a template bug, not acceptable output).
- **Empty States:** "Finish your theme and confirm your date to generate invitation cards."
- **Loading States:** "Composing your invitation..."
- **Error States:** If Pillow rendering fails for a specific guest's name (e.g. an unsupported character), generate the rest of the batch successfully and flag which ones failed with the specific reason, rather than failing the entire batch silently.
- **Acceptance Criteria:** Given a confirmed theme, date, and at least 3 test guests, the system generates 3 correctly personalized cards (distinct names, identical layout/palette/date/venue) as both PNG and PDF, with zero unfilled template placeholders visible in any output.

---

## Insert into Section 5.3 — Screen Inventory (new row)

| Screen Name | Route | Purpose | Primary Persona | Entry Points |
|---|---|---|---|---|
| **Invitation Card Studio** | `/dashboard/events/{id}/invitations` | Generate and export personalized invitation cards from the confirmed theme, date, and guest list | Host | Unified Event Workspace tab, Compose Celebration flow (Stage 4) |

---

## Insert into Section 8.4 — Specialized AI Agent Registry (new entry)

#### 12. Invitation Text Composer Agent (F16)
- **Trigger:** User reaches the card confirmation step with a theme, date, and (optionally) venue already set.
- **Inputs:** Theme's `invitation_design_brief` text (from F4), event basics, tradition-specific ceremony names (from F2's merged run-of-show, if applicable).
- **Output:** Short, warm invitation wording options (2-3 variants) for the host to pick from — strictly composed from the structured inputs already present, never inventing venue details, dates, or ceremony names not already confirmed in the data.
- **Guardrails:** Does not generate layout, images, or personalization logic — those are deterministic (Pillow + interpolation). This agent's only job is the wording options. If it fails, fall back to a plain, non-LLM template sentence (e.g. "You are cordially invited to celebrate [event_name] on [date] at [venue]") so card generation is never blocked by this agent.

---

## Insert into Section 10.2 — Field-Level Relational Database Schema (new table)

#### Table: `invitation_cards`
- `id` (UUID, Primary Key)
- `event_id` (UUID, FK -> `events(id)` ON DELETE CASCADE)
- `theme_proposal_id` (UUID, FK -> `theme_proposals(id)`, nullable — null if generated without an accepted theme)
- `layout_variant` (VARCHAR(50))
- `wording_text` (TEXT)
- `guest_id` (UUID, FK -> `guests(id)` ON DELETE CASCADE, nullable — null for the generic/non-personalized card)
- `rendered_png` (BYTEA, nullable)
- `rendered_pdf` (BYTEA, nullable)
- `generated_at` (TIMESTAMPTZ, Default `NOW()`)

---

## Insert into Section 11 — API Design (new subsection)

### 11.8 Invitation Cards (`/api/v1/events/{id}/invitations`)
- **POST `/generate`** — Body: `{theme_proposal_id, layout_variant, wording_variant_index}`. Generates either one generic card (no guest list) or one card per guest (if guests exist). Returns array of `invitation_cards` rows with download links.
- **GET `/{card_id}/download?format=png|pdf`** — Streams the rendered file.
- **Caching:** Rendered cards are cached (not regenerated on every request) since inputs are immutable once generated; regeneration only happens if the host explicitly requests a new variant.

---

## Insert into Section 12 — Component Inventory (append)

26. `<InvitationLayoutPicker />`: 2-3 card layout thumbnails driven by the active theme's palette.
27. `<InvitationWordingSelector />`: Shows the 2-3 LLM-composed wording variants (or the deterministic fallback) for the host to pick.
28. `<InvitationPreviewCard />`: Live preview of the rendered card before export, with regenerate/export controls.
29. `<GuestCardBatchStatus />`: Shows generation progress/failures when producing one card per guest, surfacing per-guest errors without blocking the batch.

---

## Insert into Section 17.2 — Milestones (new milestone, M10 — after M9 F15, but independently sequenced; can build in parallel with M9 since it doesn't depend on F15's output)

#### Milestone M10: F16 Invitation Card Generator
- **Scope:** `invitation_cards` schema, Pillow-based card renderer (layout + palette + text interpolation), wording composer agent with deterministic fallback, PNG/PDF export, per-guest batch generation wired to F3's guest list (resumes correctly once M4/F3 un-pauses).
- **Exit Gate:** 3-guest batch test produces 3 correctly personalized cards with zero unfilled placeholders, in both export formats; Devanagari name rendering explicitly tested and confirmed correct, not assumed.
