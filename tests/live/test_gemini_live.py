"""
Live Gemini Production Integration Test Suite.
Requires valid GEMINI_API_KEY. Marked with @pytest.mark.live.
Enforces non-stub execution: provider class must be Gemini*Provider, not DeterministicStub*.
"""

import os
import pytest


@pytest.mark.live
def test_gemini_live_quote_extraction():
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        pytest.skip("BLOCKED: GEMINI_API_KEY not set. Cannot run @pytest.mark.live test without real credentials.")

    from backend.app.services.providers.gemini_provider import GeminiQuoteExtractionProvider

    provider = GeminiQuoteExtractionProvider(api_key=api_key)
    assert "Gemini" in provider.__class__.__name__
    assert "Stub" not in provider.__class__.__name__

    sample_doc = (
        "Quotation\n"
        "Vendor: Royal Palace Banquets, Jaipur\n"
        "Dinner Buffet: 150 plates @ Rs 800 = Rs 120,000\n"
        "Mandap Decor = Rs 40,000\n"
        "GST: Rs 28,800\n"
        "Total: Rs 188,800\n"
    )

    res = provider.extract_quote_from_document(
        file_bytes=sample_doc.encode("utf-8"),
        file_name="quote.txt",
        mime_type="text/plain",
        category_hint="caterer"
    )

    assert res.total_amount > 0
    assert len(res.line_items) > 0


@pytest.mark.live
def test_gemini_live_vibe_proposal():
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        pytest.skip("BLOCKED: GEMINI_API_KEY not set. Cannot run @pytest.mark.live test without real credentials.")

    from backend.app.services.providers.gemini_provider import GeminiVibeProvider

    provider = GeminiVibeProvider(api_key=api_key)
    assert "Gemini" in provider.__class__.__name__
    assert "Stub" not in provider.__class__.__name__

    res = provider.generate_theme_from_profile(
        style_tags=["royal_rajasthani", "heritage"],
        color_palette=["#800020", "#D4AF37", "#E2725B"],
        event_type="wedding",
        city="Jaipur",
        guest_count=200,
        total_budget=1500000.0
    )

    assert res.theme_name
    assert len(res.decor_items) > 0
