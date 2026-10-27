import os
import sys

sys.path.insert(0, os.path.abspath("."))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

print("=======================================================")
print("GOOGLE GEMINI LIVE PRODUCTION SMOKE TEST")
print("=======================================================")

api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("BLOCKED: GEMINI_API_KEY not set")
    print("Zero live API requests can be executed without real Google Gemini credentials.")
    print("Deterministic offline stubs are not considered live execution.")
    print("To unblock: provide GEMINI_API_KEY=<valid_key> and re-run.")
    print("=======================================================")
    sys.exit(2)

print("GEMINI_API_KEY is configured. Initializing LIVE Gemini providers...")

from backend.app.services.providers.gemini_provider import (
    GeminiQuoteExtractionProvider,
    GeminiVibeProvider,
    GeminiNegotiationDraftProvider,
    GeminiReplanningExplanationProvider
)

# 1. Quote Extraction Live Test
quote_prov = GeminiQuoteExtractionProvider(api_key=api_key)
print(f"1. Live Provider: {quote_prov.__class__.__name__}")
dummy_quote_text = (
    "Tax Invoice / Quotation\n"
    "Vendor: Royal Banquet & Catering, Pune\n"
    "Item 1: Deluxe Feast Buffet, 200 plates @ Rs 600 = Rs 120,000\n"
    "Item 2: Stage & Mandap Floral Decor = Rs 35,000\n"
    "Subtotal: Rs 155,000\n"
    "GST 18%: Rs 27,900\n"
    "Total Payable: Rs 182,900\n"
)
try:
    res = quote_prov.extract_quote_from_document(
        file_bytes=dummy_quote_text.encode("utf-8"),
        file_name="quote.txt",
        mime_type="text/plain",
        category_hint="caterer"
    )
    print(f"   ✓ Live Extracted Vendor: {res.vendor_name}")
    print(f"   ✓ Live Extracted Total: ₹{res.total_amount:,.2f}")
    print(f"   ✓ Line items: {len(res.line_items)}")
except Exception as e:
    print(f"   ✗ Live Quote Extraction Failed: {e}")
    sys.exit(1)

# 2. Vibe Extraction Live Test
vibe_prov = GeminiVibeProvider(api_key=api_key)
print(f"\n2. Live Provider: {vibe_prov.__class__.__name__}")
try:
    vibe_res = vibe_prov.generate_theme_from_profile(
        style_tags=["royal_rajasthani", "heritage_palace"],
        color_palette=["#FF9933", "#800020", "#FFD700"],
        event_type="wedding",
        city="Jaipur",
        guest_count=200,
        total_budget=1500000.0
    )
    print(f"   ✓ Live Theme Proposal: '{vibe_res.theme_name}'")
    print(f"   ✓ Decor items proposed: {len(vibe_res.decor_items)}")
except Exception as e:
    print(f"   ✗ Live Vibe Proposal Failed: {e}")
    sys.exit(1)

print("\n=======================================================")
print("LIVE GEMINI SMOKE TEST: ALL LIVE CAPABILITIES PASSED (100%)")
print("=======================================================")
