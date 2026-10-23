import re
import sys

def main():
    with open("docs/UTSAV_MASTER_DOC.md", "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Update TOC
    toc_f15 = "- [4.15 F15: Vendor & Venue Discovery Map](#415-f15-vendor--venue-discovery-map)"
    toc_f16 = "- [4.15 F15: Vendor & Venue Discovery Map](#415-f15-vendor--venue-discovery-map)\n  - [4.16 F16: Invitation Card Generator](#416-f16-invitation-card-generator)"
    assert toc_f15 in content, "TOC F15 not found"
    content = content.replace(toc_f15, toc_f16, 1)

    toc_agents_old = "- [8.4 Specialized AI Agent Registry (11 Discrete Autonomous Workers)](#84-specialized-ai-agent-registry-11-discrete-autonomous-workers)"
    toc_agents_new = "- [8.4 Specialized AI Agent Registry (12 Discrete Autonomous Workers)](#84-specialized-ai-agent-registry-12-discrete-autonomous-workers)"
    assert toc_agents_old in content, "TOC Agents not found"
    content = content.replace(toc_agents_old, toc_agents_new, 1)

    toc_m9_old = "- [17.2 Milestones M0 through M9 with Strict Exit Gates](#172-milestones-m0-through-m9-with-strict-exit-gates)"
    toc_m10_new = "- [17.2 Milestones M0 through M10 with Strict Exit Gates](#172-milestones-m0-through-m10-with-strict-exit-gates)"
    assert toc_m9_old in content, "TOC Milestones not found"
    content = content.replace(toc_m9_old, toc_m10_new, 1)

    # 2. Section 3: Decisions Log
    dec_block = """| **DEC-028** | **Card Rendering Approach** | Server-side composition (Pillow, same library already proven in F4's moodboard generator) over a second paid image-generation API | Keeps a consistent, already-tested dependency rather than adding a new generative cost/latency surface for something that is fundamentally a templated layout task, not open-ended image generation. | **High** | If hosts request true AI-illustrated card art (not just layout/typography), revisit with a generation provider, same pattern as F4's `DEC-022`. |
| **DEC-029** | **Personalization Scope** | Per-guest personalization is limited to name and RSVP-relevant fields (dietary note, table assignment if seating from F9 exists) — never fabricated personal details | Cards must never invent facts about a guest. Only fields the host or guest actually supplied are interpolated. | **Critical** | Never — same standard as all other no-invented-facts rules. |
| **DEC-030** | **Export Format** | Cards export as PNG (for WhatsApp/social sharing) and PDF (for printing), generated from one shared layout, not two separate designs | Avoids layout drift between the digital and print versions; matches the existing pattern of Claude Docs-style multi-format export used elsewhere in the stack. | **Medium** | If print-shop requirements (bleed, CMYK color profile) become necessary, add a dedicated print-export path. |
"""
    # Insert after DEC-027 row
    dec_027_pattern = r"(\| \*\*DEC-027\*\* \|.*?\n)"
    m = re.search(dec_027_pattern, content)
    assert m, "DEC-027 not found"
    content = content[:m.end()] + dec_block + content[m.end():]

    # 3. Section 4.16: Functional Spec
    f16_section = """### 4.16 F16: Invitation Card Generator
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

"""
    f15_end_marker = "\n## 5. Information Architecture"
    assert f15_end_marker in content, "Section 5 marker not found"
    content = content.replace(f15_end_marker, "\n" + f16_section + f15_end_marker, 1)

    # 4. Section 5.3: Screen Inventory row
    f16_screen_row = "| **Invitation Card Studio** | `/dashboard/events/{id}/invitations` | Generate and export personalized invitation cards from the confirmed theme, date, and guest list | Host | Unified Event Workspace tab, Compose Celebration flow (Stage 4) |\n"
    disc_map_row = "| **Vendor & Venue Discovery Map** | `/dashboard/vendors/discover` (and public `/discover` pre-signup) | Geolocated map of nearby venues/vendors ranked by rating with normalized cost estimates | Host, Prospective Host | Marketing site CTA, Vendors subnav |\n"
    assert disc_map_row in content, "Discovery Map row not found in screen inventory"
    content = content.replace(disc_map_row, disc_map_row + f16_screen_row, 1)

    # 5. Section 8.4: Specialized AI Agent Registry (12 Discrete Autonomous Workers)
    sec84_old = "## 8.4 Specialized AI Agent Registry (11 Discrete Autonomous Workers)"
    sec84_new = "## 8.4 Specialized AI Agent Registry (12 Discrete Autonomous Workers)"
    assert sec84_old in content, "Section 8.4 header not found"
    content = content.replace(sec84_old, sec84_new, 1)

    agent_12_block = """#### 12. Invitation Text Composer Agent (F16)
- **Trigger:** User reaches the card confirmation step with a theme, date, and (optionally) venue already set.
- **Inputs:** Theme's `invitation_design_brief` text (from F4), event basics, tradition-specific ceremony names (from F2's merged run-of-show, if applicable).
- **Output:** Short, warm invitation wording options (2-3 variants) for the host to pick from — strictly composed from the structured inputs already present, never inventing venue details, dates, or ceremony names not already confirmed in the data.
- **Guardrails:** Does not generate layout, images, or personalization logic — those are deterministic (Pillow + interpolation). This agent's only job is the wording options. If it fails, fall back to a plain, non-LLM template sentence (e.g. "You are cordially invited to celebrate [event_name] on [date] at [venue]") so card generation is never blocked by this agent.

"""
    sec85_marker = "### 8.5 Infrastructure, Environments & CI/CD Pipelines"
    assert sec85_marker in content, "Section 8.5 marker not found"
    content = content.replace(sec85_marker, agent_12_block + sec85_marker, 1)

    # 6. Section 10.2: invitation_cards table
    table_block = """#### Table: `invitation_cards`
- `id` (UUID, Primary Key)
- `event_id` (UUID, FK -> `events(id)` ON DELETE CASCADE)
- `theme_proposal_id` (UUID, FK -> `theme_proposals(id)`, nullable — null if generated without an accepted theme)
- `layout_variant` (VARCHAR(50))
- `wording_text` (TEXT)
- `guest_id` (UUID, FK -> `guests(id)` ON DELETE CASCADE, nullable — null for the generic/non-personalized card)
- `rendered_png` (BYTEA, nullable)
- `rendered_pdf` (BYTEA, nullable)
- `generated_at` (TIMESTAMPTZ, Default `NOW()`)

"""
    sec103_marker = "## 10.3 Formal JSON Schemas for Agent Payloads"
    assert sec103_marker in content, "Section 10.3 marker not found"
    content = content.replace(sec103_marker, table_block + "---\n\n" + sec103_marker, 1)

    # 7. Section 11: 11.8 Invitation Cards
    api_118_block = """### 11.8 Invitation Cards (`/api/v1/events/{id}/invitations`)
- **POST `/generate`** — Body: `{theme_proposal_id, layout_variant, wording_variant_index}`. Generates either one generic card (no guest list) or one card per guest (if guests exist). Returns array of `invitation_cards` rows with download links.
- **GET `/{card_id}/download?format=png|pdf`** — Streams the rendered file.
- **Caching:** Rendered cards are cached (not regenerated on every request) since inputs are immutable once generated; regeneration only happens if the host explicitly requests a new variant.

"""
    sec12_marker = "## 12. Component Inventory"
    assert sec12_marker in content, "Section 12 marker not found"
    content = content.replace(sec12_marker, api_118_block + "---\n\n" + sec12_marker, 1)

    # 8. Section 12: Components 26-29
    comp_block = """26. `<InvitationLayoutPicker />`: 2-3 card layout thumbnails driven by the active theme's palette.
27. `<InvitationWordingSelector />`: Shows the 2-3 LLM-composed wording variants (or the deterministic fallback) for the host to pick.
28. `<InvitationPreviewCard />`: Live preview of the rendered card before export, with regenerate/export controls.
29. `<GuestCardBatchStatus />`: Shows generation progress/failures when producing one card per guest, surfacing per-guest errors without blocking the batch.
"""
    comp_target = "25. `<LocationPermissionPrompt />`: Geolocation consent UI with a mandatory manual city/pincode entry path shown alongside, never gated behind permission grant.\n"
    assert comp_target in content, "Component 25 not found"
    content = content.replace(comp_target, comp_target + comp_block, 1)

    # 9. Section 17.2: Milestones M0 through M10
    sec172_old = "### 17.2 Milestones M0 through M9 with Strict Exit Gates"
    sec172_new = "### 17.2 Milestones M0 through M10 with Strict Exit Gates"
    assert sec172_old in content, "Section 17.2 header not found"
    content = content.replace(sec172_old, sec172_new, 1)

    m10_block = """#### Milestone M10: F16 Invitation Card Generator
- **Scope:** `invitation_cards` schema, Pillow-based card renderer (layout + palette + text interpolation), wording composer agent with deterministic fallback, PNG/PDF export, per-guest batch generation wired to F3's guest list (resumes correctly once M4/F3 un-pauses).
- **Exit Gate:** 3-guest batch test produces 3 correctly personalized cards with zero unfilled placeholders, in both export formats; Devanagari name rendering explicitly tested and confirmed correct, not assumed.
"""
    sec173_marker = "### 17.3 Definition of Done (DoD) per Milestone"
    assert sec173_marker in content, "Section 17.3 marker not found"
    content = content.replace(sec173_marker, m10_block + "\n" + sec173_marker, 1)

    with open("docs/UTSAV_MASTER_DOC.md", "w", encoding="utf-8") as f:
        f.write(content)

    print("Successfully merged UTSAV_F16_ADDENDUM into docs/UTSAV_MASTER_DOC.md")

if __name__ == "__main__":
    main()
