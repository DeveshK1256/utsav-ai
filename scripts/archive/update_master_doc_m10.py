def main():
    with open("docs/UTSAV_MASTER_DOC.md", "r", encoding="utf-8") as f:
        content = f.read()

    target = """#### Milestone M10: F16 Invitation Card Generator
- **Scope:** `invitation_cards` schema, Pillow-based card renderer (layout + palette + text interpolation), wording composer agent with deterministic fallback, PNG/PDF export, per-guest batch generation wired to F3's guest list (resumes correctly once M4/F3 un-pauses).
- **Exit Gate:** 3-guest batch test produces 3 correctly personalized cards with zero unfilled placeholders, in both export formats; Devanagari name rendering explicitly tested and confirmed correct, not assumed."""

    replacement = """#### Milestone M10: F16 Invitation Card Generator [COMPLETE — SERVER-SIDE PILLOW COMPOSITION, DEVANAGARI VERIFIED & LIVE DB PROVEN]
- **Scope:** `invitation_cards` schema, Pillow-based card renderer (`classic_royal`, `modern_minimal`, `floral_festive` layouts + theme palette + text interpolation), wording composer agent with deterministic fallback, dual PNG and PDF export, per-guest batch generation wired to F3's guest list (resumes correctly once M4/F3 un-pauses), and frontend Invitation Card Studio integrated into the unified Event Dashboard workspace.
- **Implementation & Live Verification Status:**
  - **Live Deployed API:** `https://utsav-ai-ycg2.onrender.com`
  - **Live Production Database:** Render Managed PostgreSQL (`utsav_db_nrue` in Singapore) with migration `0008_f16_invitation_cards.py` applied and indexed (`ix_invitation_cards_event_id`, `ix_invitation_cards_theme_proposal_id`, `ix_invitation_cards_guest_id`).
  - **Server-Side Pillow Composition Engine (DEC-028):** Deterministic layout composition without expensive generative image APIs. Generates 1200 × 1800 px high-resolution cards with theme palette binding, shubh muhurat badges, and guest personalization.
  - **Devanagari Font & Script Verification:** Official Google Noto Sans Devanagari (Regular and Bold) bundled directly into `backend/app/assets/fonts/` guaranteeing identical rendering across Windows, Ubuntu CI, and Render Linux containers. Full conjunct/ligature rendering confirmed for Hindi/Marathi/Sanskrit (`श्री Ganesh`, `विवाह`, `काळे व परिवार`).
  - **Zero-Invented-Facts & No-Placeholder Guarantee (DEC-029):** All card fields interpolate strictly confirmed database values. Truncation with ellipsis prevents overflow; zero unfilled template tags (`{host_name}`, `{venue}`, etc.) leak to cards.
  - **Dual-Format Single Pipeline Export (DEC-030):** Produces both PNG (digital share) and PDF (300 DPI print) from a single shared composition, preventing design drift. Validated binary magic headers (`\\x89PNG\\r\\n\\x1a\\n` and `%PDF`).
  - **Wording Composer Agent (Agent #12):** Composes 3 culturally warm wording variants (`traditional`, `contemporary`, `formal`) strictly from confirmed structured logistics, with deterministic fallback when offline or without Gemini API key.
  - **Partial Failure Isolation:** Batch guest generation isolates per-guest errors (e.g. malformed characters) without aborting the batch; failures are tracked and surfaced with specific reasons in `failed_guests`.
  - **Live Acceptance Criteria Pass:** Verified on live Render backend with real Singapore PostgreSQL:
    - 3 test guests seeded (`Vikram Malhotra`, `Dr. Aditi Sen`, `श्री रमेश काळे व परिवार`).
    - Batch generation returned `total_generated: 3`, `total_failed: 0`.
    - Downloaded and visually verified Devanagari card (`m10_rendered_invitation_devanagari.png`) displaying complete layout, borders, auspicious emblem, shubh muhurat, and personalized guest invitation.
  - **Frontend Workspace:** Built `<InvitationStudio />` with `<InvitationLayoutPicker />`, `<InvitationWordingSelector />`, `<InvitationPreviewCard />`, and `<GuestCardBatchStatus />`, integrated as a tab in `EventDashboardClient.tsx` and routed at `/dashboard/events/{id}/invitations`.
  - **Automated Regression Suite:** 63/63 tests passing green across M0-M3, M5, M10, schema regressions, and golden event evals."""

    assert target in content, "Target M10 block not found in docs/UTSAV_MASTER_DOC.md"
    new_content = content.replace(target, replacement, 1)

    with open("docs/UTSAV_MASTER_DOC.md", "w", encoding="utf-8") as f:
        f.write(new_content)

    print("Master doc Milestone M10 successfully updated with live evidence!")

if __name__ == "__main__":
    main()
