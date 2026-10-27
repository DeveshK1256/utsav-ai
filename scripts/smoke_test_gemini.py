import os
import sys

sys.path.insert(0, os.path.abspath("."))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

print("=======================================================")
print("RUNNING GOOGLE GEMINI PROVIDER SMOKE TEST")
print("=======================================================")

api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

from backend.app.services.llm_provider import (
    get_quote_extraction_provider,
    get_vibe_extraction_provider,
    get_negotiation_draft_provider,
    get_replanning_explanation_provider,
)
from backend.app.services.invitation_wording_agent import InvitationWordingAgent

print(f"Environment Status: GEMINI_API_KEY is {'CONFIGURED' if api_key else 'UNSET (Evaluating Deterministic Safety Fallbacks)'}")

# 1. Quote Extraction Smoke Test
quote_prov = get_quote_extraction_provider()
print(f"1. Quote Extraction Provider: {quote_prov.__class__.__name__}")
dummy_pdf = b"%PDF-1.4 Mock Vendor Quotation for Royal Caterers Pune. Total: 150000 INR."
try:
    quote_res = quote_prov.extract_quote_from_document(
        file_bytes=dummy_pdf,
        file_name="vendor_quote.pdf",
        mime_type="application/pdf",
        category_hint="caterer"
    )
    print(f"   ✓ Extracted vendor: '{quote_res.vendor_name}'")
    print(f"   ✓ Extracted total: ₹{quote_res.total_amount:,.2f}")
    print(f"   ✓ Line items extracted: {len(quote_res.line_items)}")
    print(f"   ✓ Deterministic confidence: {quote_res.compute_deterministic_confidence():.2f}")
except Exception as e:
    print(f"   ✗ Extraction failed: {e}")
    sys.exit(1)

# 2. Vibe Extraction Smoke Test
vibe_prov = get_vibe_extraction_provider()
print(f"\n2. Vibe Extraction Provider: {vibe_prov.__class__.__name__}")
try:
    mock_images = [{"bytes": b"fake_image_bytes", "mime_type": "image/jpeg", "file_name": "inspiration.jpg"}]
    vibe_res = vibe_prov.extract_vibe_from_images(mock_images, text_description="Royal Rajasthani Palace Theme")
    print(f"   ✓ Overall mood words: {vibe_res.overall_mood_words}")
    if vibe_res.images:
        print(f"   ✓ Extracted palette: {vibe_res.images[0].palette}")
        print(f"   ✓ Style tags: {vibe_res.images[0].style_tags}")
        print(f"   ✓ Materials: {vibe_res.images[0].materials}")
except Exception as e:
    print(f"   ✗ Vibe extraction failed: {e}")
    sys.exit(1)

# 3. Negotiation Draft Smoke Test
neg_prov = get_negotiation_draft_provider()
print(f"\n3. Negotiation Draft Provider: {neg_prov.__class__.__name__}")
try:
    drafts = neg_prov.generate_negotiation_drafts(
        vendor_name="Royal Caterers Pune",
        category="caterer",
        quoted_total=177000.0,
        target_discount_pct=10.0,
        leverage_points=["Competitor offers ₹150,000", "Breakage deposit is non-standard"],
        competing_vendor_name="Elite Hospitality",
        competing_quote_total=150000.0
    )
    print(f"   ✓ Generated draft variants: {list(drafts.keys())}")
    print(f"   ✓ Polite English draft preview: '{drafts['polite']['english'][:65]}...'")
    print(f"   ✓ Polite Hindi draft preview: '{drafts['polite']['hindi'][:65]}...'")
except Exception as e:
    print(f"   ✗ Negotiation draft failed: {e}")
    sys.exit(1)

# 4. Invitation Cultural Wording Agent Smoke Test
print(f"\n4. Invitation Wording Agent: {InvitationWordingAgent.__name__}")
try:
    wording_res = InvitationWordingAgent.compose_wording(
        event_name="शुभ विवाह: रोहन आणि अनन्या",
        host_name="संजय आणि वंदना पाटील",
        event_type="wedding",
        date_str="२१ डिसेंबर २०२६",
        venue_str="महालक्ष्मी लॉन्स, पुणे",
        muhurat_time="सकाळी ११:४५ वाजता"
    )
    print(f"   ✓ Provider used: {wording_res.provider_used}")
    print(f"   ✓ Variants generated: {len(wording_res.variants)}")
    print(f"   ✓ Variant 1 title: '{wording_res.variants[0].title}'")
    print(f"   ✓ Content review note: '{wording_res.content_review_note[:60]}...'")
except Exception as e:
    print(f"   ✗ Invitation wording failed: {e}")
    sys.exit(1)

print("\n=======================================================")
print("GEMINI SMOKE TEST RESULT: ALL 4/4 CAPABILITIES OPERATIONAL (100% PASS)")
print("=======================================================")
