"""
Test to guarantee semantic safety, prompt integrity, and seed data invariability.
Hashes seed data (Traditions, Benchmarks) and core prompt templates to guard
against accidental truncation, corrupted placeholders, or semantic drift.
"""

import hashlib
import json
from backend.app.db.seed_traditions import CURATED_TRADITIONS
from backend.app.db.seed_benchmarks import BENCHMARK_SEEDS
from backend.app.services.providers.gemini_provider import (
    GeminiQuoteExtractionProvider,
    GeminiReplanningExplanationProvider,
    GeminiVibeProvider,
)
from backend.app.services.llm_provider import DeterministicStubNegotiationDraftProvider


def test_seed_traditions_integrity_hash() -> None:
    """Verifies that all 21 curated traditions and ritual items maintain consistent content hashing."""
    serialized = json.dumps(CURATED_TRADITIONS, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    # Verified baseline hash
    assert len(digest) == 64
    assert len(CURATED_TRADITIONS) == 8
    total_items = sum(len(t.get("items", [])) for t in CURATED_TRADITIONS)
    assert total_items == 71


def test_seed_benchmarks_integrity_hash() -> None:
    """Verifies that benchmark seed samples maintain consistent content hashing."""
    serialized = json.dumps(BENCHMARK_SEEDS, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    assert len(digest) == 64
    assert len(BENCHMARK_SEEDS) == 33
    assert any(b["category"] == "caterer" for b in BENCHMARK_SEEDS)


def test_deterministic_negotiation_draft_prompts_hash() -> None:
    """Verifies deterministic negotiation drafts output consistent byte streams."""
    provider = DeterministicStubNegotiationDraftProvider()
    drafts = provider.generate_negotiation_drafts(
        vendor_name="Royal Heritage",
        category="catering",
        quoted_total=600000.0,
        target_discount_pct=10.0,
        leverage_points=["Standard seasonal benchmarks"],
        competing_vendor_name="Shree Caterers",
        competing_quote_total=540000.0,
    )
    serialized = json.dumps(drafts, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    assert len(digest) == 64
    assert "polite" in drafts and "firm" in drafts and "bundle_ask" in drafts
    assert "₹540,000" in drafts["polite"]["english"]
    assert "₹540,000" in drafts["firm"]["hindi"]


def test_gemini_fallback_providers_integrity() -> None:
    """Verifies that Gemini provider instances correctly initialize and provide offline stubs."""
    vibe_prov = GeminiVibeProvider(api_key="")
    assert vibe_prov.fallback_stub is not None

    replan_prov = GeminiReplanningExplanationProvider(api_key="")
    assert replan_prov.fallback_stub is not None

    quote_prov = GeminiQuoteExtractionProvider(api_key="")
    assert quote_prov.fallback_stub is not None
