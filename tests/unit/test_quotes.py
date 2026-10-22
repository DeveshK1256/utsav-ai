import io
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.schemas.quotes import ExtractedLineItemSchema
from backend.app.services.hidden_cost_engine import HiddenCostDetector
from backend.app.services.quote_comparison_engine import QuoteComparisonEngine
from backend.app.services.llm_provider import (
    DeterministicStubQuoteExtractionProvider,
    DeterministicStubNegotiationDraftProvider
)

client = TestClient(app)


def test_hidden_cost_detector_flags_missing_and_covered():
    # Scenario A: Line items missing overtime and crockery breakage
    line_items = [
        ExtractedLineItemSchema(
            name="Rajasthani Royal Thali",
            qty=200,
            unit="plates",
            unit_price=1000.0,
            total=200000.0,
            category_tag="food"
        )
    ]
    alerts = HiddenCostDetector.analyze_quote("caterer", line_items, terms_and_conditions=[])
    alert_map = {a.code: a.status for a in alerts}

    assert alert_map.get("cat_overtime") == "missing_from_quote"
    assert alert_map.get("cat_crockery_breakage") == "missing_from_quote"
    assert alert_map.get("cat_service_staff") == "missing_from_quote"

    # Scenario B: Explicitly mentioning server staff and overtime in terms
    terms = ["Includes 15 uniformed banquet servers", "Extra overtime charged at ₹3,000/hr after midnight"]
    alerts_with_terms = HiddenCostDetector.analyze_quote("caterer", line_items, terms_and_conditions=terms)
    alert_map2 = {a.code: a.status for a in alerts_with_terms}

    assert alert_map2.get("cat_overtime") == "explicitly_covered"
    assert alert_map2.get("cat_service_staff") == "explicitly_covered"
    assert alert_map2.get("cat_crockery_breakage") == "missing_from_quote"


def test_benchmark_median_dec014_limited_data_threshold():
    # DEC-014 strict rule: sample size n < 5 must return limited_data
    small_samples = [1100.0, 1250.0, 1300.0, 1150.0]  # n = 4
    res = QuoteComparisonEngine.compute_median_benchmark(
        category="caterer",
        city_tier="Tier 1",
        benchmark_samples=small_samples,
        quote_unit_cost=1500.0
    )
    assert res.is_limited_data is True
    assert res.cost_status == "limited_data"
    assert res.sample_size == 4
    assert res.percentage_diff_vs_median is None


def test_benchmark_median_calculation_and_status():
    # n = 5 verified samples
    samples = [1000.0, 1100.0, 1200.0, 1300.0, 1400.0]  # median = 1200.0
    res_above = QuoteComparisonEngine.compute_median_benchmark(
        category="caterer",
        city_tier="Tier 1",
        benchmark_samples=samples,
        quote_unit_cost=1500.0  # +25% above median
    )
    assert res_above.is_limited_data is False
    assert res_above.median_unit_cost == 1200.0
    assert res_above.percentage_diff_vs_median == 25.0
    assert res_above.cost_status == "above_median"

    res_below = QuoteComparisonEngine.compute_median_benchmark(
        category="caterer",
        city_tier="Tier 1",
        benchmark_samples=samples,
        quote_unit_cost=960.0  # -20% below median
    )
    assert res_below.cost_status == "below_median"
    assert res_below.percentage_diff_vs_median == -20.0


def test_guest_count_normalization():
    # Caterer quote for 300 guests at ₹450,000 (₹1,500/head) normalized to 500 guests
    normalized = QuoteComparisonEngine.normalize_quote_to_guest_count(
        raw_total=450000.0,
        quoted_guest_count=300,
        target_guest_count=500,
        category="caterer"
    )
    assert normalized == 750000.0

    # Fixed-cost category (decorator) should remain unchanged
    normalized_dec = QuoteComparisonEngine.normalize_quote_to_guest_count(
        raw_total=350000.0,
        quoted_guest_count=300,
        target_guest_count=500,
        category="decorator"
    )
    assert normalized_dec == 350000.0


def test_negotiation_draft_generation():
    provider = DeterministicStubNegotiationDraftProvider()
    drafts = provider.generate_negotiation_drafts(
        vendor_name="Shree Ganesh Caterers",
        category="caterer",
        quoted_total=500000.0,
        target_discount_pct=10.0,
        leverage_points=["Missing diesel generator provision", "Rate is 15% above Tier 1 median"],
        competing_vendor_name="Annapurna Caterers",
        competing_quote_total=420000.0
    )
    assert "polite" in drafts
    assert "firm" in drafts
    assert "bundle_ask" in drafts

    for variant_name in ["polite", "firm", "bundle_ask"]:
        assert "english" in drafts[variant_name]
        assert "hindi" in drafts[variant_name]
        assert len(drafts[variant_name]["english"]) > 50
        assert len(drafts[variant_name]["hindi"]) > 50


def test_quotes_api_endpoints_flow():
    # 1. First create an event to attach quotes to
    event_payload = {
        "name": "M1 Test Grand Sangeet",
        "event_type": "sangeet",
        "guest_count": 350,
        "total_budget": 3000000.0,
        "city": "Jaipur",
        "pincode": "302001",
        "host_phone": "+919876543210",
        "host_name": "Test Host"
    }
    event_res = client.post("/api/v1/events", json=event_payload)
    assert event_res.status_code == 201
    event_id = event_res.json()["id"]

    # 2. Upload Quote 1 (Catering)
    fake_pdf = io.BytesIO(b"%PDF-1.4 Fake Quote Data For Testing")
    upload_res1 = client.post(
        "/api/v1/quotes/upload",
        data={"event_id": event_id, "category": "caterer"},
        files={"file": ("caterer_quote_1.pdf", fake_pdf, "application/pdf")}
    )
    assert upload_res1.status_code == 201
    quote1_data = upload_res1.json()
    quote1_id = quote1_data["id"]
    assert quote1_data["category"] == "caterer"
    assert len(quote1_data["line_items"]) > 0
    assert len(quote1_data["hidden_cost_alerts"]) > 0

    # 3. Upload Quote 2 (Catering - Competitor)
    fake_pdf2 = io.BytesIO(b"%PDF-1.4 Fake Second Quote Data")
    upload_res2 = client.post(
        "/api/v1/quotes/upload",
        data={"event_id": event_id, "category": "caterer"},
        files={"file": ("caterer_quote_2.pdf", fake_pdf2, "application/pdf")}
    )
    assert upload_res2.status_code == 201
    quote2_data = upload_res2.json()
    quote2_id = quote2_data["id"]

    # 4. List quotes for event
    list_res = client.get(f"/api/v1/quotes/event/{event_id}")
    assert list_res.status_code == 200
    quotes_list = list_res.json()
    assert len(quotes_list) >= 2

    # 5. Side-by-side compare quotes
    compare_res = client.post(
        "/api/v1/quotes/compare",
        json={"quote_ids": [quote1_id, quote2_id]}
    )
    assert compare_res.status_code == 200
    compare_data = compare_res.json()
    assert compare_data["category"] == "caterer"
    assert len(compare_data["compared_quotes"]) == 2

    # 6. Mismatched category compare should return 400
    fake_dec_pdf = io.BytesIO(b"%PDF-1.4 Decorator Quote")
    upload_dec = client.post(
        "/api/v1/quotes/upload",
        data={"event_id": event_id, "category": "decorator"},
        files={"file": ("decorator_quote.pdf", fake_dec_pdf, "application/pdf")}
    )
    assert upload_dec.status_code == 201
    dec_quote_id = upload_dec.json()["id"]

    mismatched_compare = client.post(
        "/api/v1/quotes/compare",
        json={"quote_ids": [quote1_id, dec_quote_id]}
    )
    assert mismatched_compare.status_code == 400
    assert "same category" in mismatched_compare.json()["detail"]

    # 7. Generate negotiation draft
    negotiate_res = client.post(
        f"/api/v1/quotes/{quote1_id}/negotiate-draft",
        json={"quote_id": quote1_id, "target_discount_percentage": 12.0, "competing_quote_id": quote2_id}
    )
    assert negotiate_res.status_code == 200
    draft_data = negotiate_res.json()
    assert "draft_variants" in draft_data
    assert "polite" in draft_data["draft_variants"]
    assert "firm" in draft_data["draft_variants"]
    assert "bundle_ask" in draft_data["draft_variants"]
    assert "never sends messages autonomously" in draft_data["disclaimer"]

    # Cleanup event (cascades to quotes and line items)
    client.delete(f"/api/v1/events/{event_id}")


def test_extraction_validation_failure_fallback(monkeypatch):
    """
    Asserts requirement:
    (a) Exactly 2 retries occur (3 attempts total).
    (b) quote_documents.extraction_status ends as 'failed_needs_manual_entry'.
    (c) No partial/garbage line items get written to quote_line_items.
    """
    from backend.app.services.llm_provider import BaseQuoteExtractionProvider, ExtractionValidationError
    from backend.app.db.session import SessionLocal
    from backend.app.models.models import QuoteDocument, QuoteLineItem
    from sqlalchemy import select

    call_history = []

    class FailingSchemaMockProvider(BaseQuoteExtractionProvider):
        def extract_quote_from_document(self, file_bytes, file_name, mime_type, category_hint=None):
            # Simulate initial attempt + exactly 2 retries = 3 attempts total
            for attempt_num in range(1, 4):
                call_history.append(f"attempt_{attempt_num}")
                # All 3 attempts fail schema validation due to malformed LLM response
            raise ExtractionValidationError("Schema validation failed: malformed JSON returned by provider after 2 retries")

    mock_provider = FailingSchemaMockProvider()
    monkeypatch.setattr("backend.app.api.v1.quotes.get_quote_extraction_provider", lambda: mock_provider)

    # 1. Create an event
    ev_res = client.post("/api/v1/events", json={
        "name": "Fallback Test Event",
        "event_type": "wedding",
        "guest_count": 250,
        "total_budget": 2000000.0,
        "city": "Mumbai",
        "pincode": "400001",
        "host_phone": "+919876543210",
        "host_name": "Fallback Host"
    })
    assert ev_res.status_code == 201
    event_id = ev_res.json()["id"]

    try:
        # 2. Upload file that triggers provider failure
        corrupt_doc = io.BytesIO(b"Malformed contract data")
        res = client.post(
            "/api/v1/quotes/upload",
            data={"event_id": event_id, "category": "caterer"},
            files={"file": ("corrupt_quote.pdf", corrupt_doc, "application/pdf")}
        )
        assert res.status_code == 201
        data = res.json()
        quote_id = data["id"]

        # Assert (a): Exactly 2 retries occurred (3 attempts total: attempt 1 initial + 2 retries)
        assert len(call_history) == 3
        assert call_history == ["attempt_1", "attempt_2", "attempt_3"]

        # Assert (b): Returned extraction_status ends as 'failed_needs_manual_entry'
        assert data["extraction_status"] == "failed_needs_manual_entry"
        assert data["total_quoted_amount"] is None
        assert data["line_items"] == []

        # Assert (c): Verify database state directly
        db = SessionLocal()
        try:
            db_quote = db.scalar(select(QuoteDocument).where(QuoteDocument.id == quote_id))
            assert db_quote is not None
            assert db_quote.extraction_status == "failed_needs_manual_entry"
            assert db_quote.total_quoted_amount is None
            assert db_quote.raw_extracted_json["retries_attempted"] == 2

            # Assert no partial/garbage line items get written to quote_line_items
            db_line_items = db.scalars(select(QuoteLineItem).where(QuoteLineItem.quote_document_id == quote_id)).all()
            assert len(db_line_items) == 0
        finally:
            db.close()

    finally:
        # Cleanup
        client.delete(f"/api/v1/events/{event_id}")


def test_deterministic_confidence_calculation():
    """
    Asserts zero LLM self-reported math:
    - Consistent mathematical quote yields score >= 0.60 (completed).
    - Recipe/zeroed document yields score < 0.60 (flagged_review).
    - Arithmetically inconsistent quote drops confidence score.
    """
    from backend.app.schemas.quotes import QuoteExtractionPayloadSchema, ExtractedLineItemSchema

    # 1. Valid, consistent quote
    valid_payload = QuoteExtractionPayloadSchema(
        vendor_name="Royal Rajputana Banquets",
        category="caterer",
        subtotal=576000.0,
        tax_amount=28800.0,
        total_amount=604800.0,
        line_items=[
            ExtractedLineItemSchema(name="Maharaja Thali", qty=300.0, unit="plate", unit_price=1450.0, total=435000.0),
            ExtractedLineItemSchema(name="Chaat Counter", qty=300.0, unit="plate", unit_price=320.0, total=96000.0),
            ExtractedLineItemSchema(name="Butler Service", qty=1.0, unit="package", unit_price=45000.0, total=45000.0)
        ]
    )
    score_valid = valid_payload.compute_deterministic_confidence()
    assert score_valid == 1.0
    assert score_valid >= 0.60

    # 2. Non-quote recipe payload (zeroed financials, unknown vendor, no items)
    recipe_payload = QuoteExtractionPayloadSchema(
        vendor_name="Unknown",
        category="caterer",
        subtotal=0.0,
        tax_amount=0.0,
        total_amount=0.0,
        line_items=[]
    )
    score_recipe = recipe_payload.compute_deterministic_confidence()
    assert score_recipe == 0.0
    assert score_recipe < 0.60

    # 3. Mismatched arithmetic (line items sum to 100k, but subtotal is 500k and tax doesn't balance)
    mismatched_payload = QuoteExtractionPayloadSchema(
        vendor_name="Unreliable Vendor",
        category="caterer",
        subtotal=500000.0,
        tax_amount=10000.0,
        total_amount=900000.0,
        line_items=[
            ExtractedLineItemSchema(name="Item 1", qty=10.0, unit="units", unit_price=10000.0, total=100000.0)
        ]
    )
    score_mismatched = mismatched_payload.compute_deterministic_confidence()
    # Has identity (+0.10), total > 0 (+0.10), len(items) >= 1 (+0.10), item math (+0.10), but macro-math fails and tax fails
    assert score_mismatched == 0.40
    assert score_mismatched < 0.60

    # 4. Stress Test: Plausible-looking quote with subtle line-item discrepancy (sum 275k vs stated subtotal 300k)
    discrepant_payload = QuoteExtractionPayloadSchema(
        vendor_name="Raj Tent & Catering",
        category="caterer",
        subtotal=300000.0,
        tax_amount=54000.0,
        total_amount=354000.0,
        line_items=[
            ExtractedLineItemSchema(name="Silver Buffet", qty=1.0, unit="package", unit_price=150000.0, total=150000.0),
            ExtractedLineItemSchema(name="Beverage Bar", qty=1.0, unit="package", unit_price=75000.0, total=75000.0),
            ExtractedLineItemSchema(name="Service Staff", qty=1.0, unit="package", unit_price=50000.0, total=50000.0)
        ]
    )
    score_discrepant = discrepant_payload.compute_deterministic_confidence()
    # Check 1: identity (+0.10)
    # Check 2: non-zero total (+0.10)
    # Check 3: completeness (+0.10)
    # Check 4: item arithmetic (+0.10)
    # Check 5: macro-math fails (275,000 != 300,000 subtotal) -> 0.00
    # Check 6: tax integrity (300,000 + 54,000 == 354,000) -> +0.15
    # Total score = 0.55 < 0.60 -> correctly routed to flagged_review
    assert score_discrepant == 0.55
    assert score_discrepant < 0.60

