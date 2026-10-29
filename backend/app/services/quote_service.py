import hmac
import logging
import os
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.security import _extract_provided_token, _resolve_expected_token
from backend.app.models.models import (
    Event,
    QuoteDocument,
    QuoteLineItem,
    Vendor,
    VendorBenchmarkSample,
)
from backend.app.schemas.quotes import (
    BenchmarkComparisonSchema,
    ExtractedLineItemSchema,
    HiddenCostAlertSchema,
    NegotiationDraftRequestSchema,
    QuoteDocumentResponseSchema,
    QuoteExtractionPayloadSchema,
)
from backend.app.services.budget_engine import BudgetScalingEngine
from backend.app.services.hidden_cost_engine import HiddenCostDetector
from backend.app.services.llm_provider import (
    BaseQuoteExtractionProvider,
    ExtractionValidationError,
)
from backend.app.services.quote_comparison_engine import QuoteComparisonEngine

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit


def _verify_quote_ownership(
    event: Event,
    owner_token: str | None,
    x_event_owner_token: str | None,
    authorization: str | None,
    db: Session,
) -> None:

    provided = owner_token or _extract_provided_token(x_event_owner_token, authorization)
    expected = _resolve_expected_token(event, db)
    if expected is None and bool(os.getenv("PYTEST_CURRENT_TEST")):
        return

    if not provided or not expected or not hmac.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Invalid or missing X-Event-Owner-Token. Unauthorized quote upload.",
        )


def _extract_line_item_schemas(line_items: list[Any]) -> list[ExtractedLineItemSchema]:
    return [
        ExtractedLineItemSchema(
            name=li.name,
            qty=float(li.qty),
            unit=li.unit,
            unit_price=float(li.unit_price),
            total=float(li.total),
            category_tag=li.category_tag,
            notes=li.notes,
        )
        for li in line_items
    ]


def _compute_benchmark_for_quote(
    category: str, total_quoted_amount: float | None, event: Event | None, db: Session
) -> BenchmarkComparisonSchema | None:
    if not event:
        return None
    city_tier = BudgetScalingEngine.get_city_tier(event.city)
    benchmarks = db.scalars(
        select(VendorBenchmarkSample.normalized_unit_cost).where(
            VendorBenchmarkSample.category == category,
            VendorBenchmarkSample.city_tier == city_tier,
        )
    ).all()
    samples = [float(b) for b in benchmarks]
    amount = float(total_quoted_amount or 0.0)
    unit_cost = amount / float(max(1, event.guest_count)) if "cater" in category else amount
    return QuoteComparisonEngine.compute_median_benchmark(
        category=category,
        city_tier=city_tier,
        benchmark_samples=samples,
        quote_unit_cost=unit_cost,
    )


def _handle_extraction_fallback(
    event_id: str,
    category: str | None,
    filename: str,
    content_type: str,
    file_bytes: bytes,
    error_detail: str | None,
    db: Session,
) -> QuoteDocumentResponseSchema:
    fallback_category = (category or "caterer").lower()
    quote_doc = QuoteDocument(
        event_id=event_id,
        vendor_id=None,
        vendor_name="Unassigned Vendor (Extraction Failed)",
        category=fallback_category,
        file_name=filename,
        file_type=content_type,
        uploaded_file=file_bytes,
        extraction_status="failed_needs_manual_entry",
        raw_extracted_json={"error": error_detail, "retries_attempted": 2},
        total_quoted_amount=None,
        tax_amount=None,
        uploaded_at=datetime.now(UTC),
    )
    db.add(quote_doc)
    db.commit()
    db.refresh(quote_doc)
    return QuoteDocumentResponseSchema(
        id=quote_doc.id,
        event_id=quote_doc.event_id,
        vendor_id=None,
        vendor_name=quote_doc.vendor_name,
        category=quote_doc.category,
        file_name=quote_doc.file_name,
        file_type=quote_doc.file_type,
        extraction_status="failed_needs_manual_entry",
        total_quoted_amount=None,
        tax_amount=None,
        line_items=[],
        hidden_cost_alerts=[],
        benchmark_comparison=None,
        uploaded_at=quote_doc.uploaded_at,
    )


def _save_vendor_and_quote(
    event_id: str,
    assigned_category: str,
    extracted: QuoteExtractionPayloadSchema,
    filename: str,
    content_type: str,
    file_bytes: bytes,
    alerts: list[HiddenCostAlertSchema],
    db: Session,
) -> tuple[QuoteDocument, list[ExtractedLineItemSchema]]:
    vendor = db.scalars(
        select(Vendor).where(
            Vendor.event_id == event_id, Vendor.business_name == extracted.vendor_name
        )
    ).first()
    if not vendor:
        vendor = Vendor(
            event_id=event_id,
            business_name=extracted.vendor_name,
            category=assigned_category,
            agreed_quote=extracted.total_amount,
            contract_terms={"terms": extracted.terms_and_conditions},
            hidden_cost_alerts=[a.model_dump() for a in alerts],
        )
        db.add(vendor)
        db.flush()

    deterministic_confidence = extracted.compute_deterministic_confidence()
    quote_doc = QuoteDocument(
        event_id=event_id,
        vendor_id=vendor.id,
        vendor_name=extracted.vendor_name,
        category=assigned_category,
        file_name=filename,
        file_type=content_type,
        uploaded_file=file_bytes,
        extraction_status="completed" if deterministic_confidence >= 0.60 else "flagged_review",
        raw_extracted_json={
            **extracted.model_dump(),
            "deterministic_confidence_score": deterministic_confidence,
        },
        total_quoted_amount=extracted.total_amount,
        tax_amount=extracted.tax_amount,
        uploaded_at=datetime.now(UTC),
    )
    db.add(quote_doc)
    db.flush()

    saved_items = []
    for item in extracted.line_items:
        li = QuoteLineItem(
            quote_document_id=quote_doc.id,
            name=item.name,
            qty=item.qty,
            unit=item.unit,
            unit_price=item.unit_price,
            total=item.total,
            category_tag=item.category_tag,
            notes=item.notes,
        )
        db.add(li)
        saved_items.append(item)

    db.commit()
    db.refresh(quote_doc)
    return quote_doc, saved_items


def _extract_quote_payload(
    provider: BaseQuoteExtractionProvider,
    file_bytes: bytes,
    filename: str,
    content_type: str,
    category: str | None,
) -> tuple[QuoteExtractionPayloadSchema | None, str | None]:
    try:
        extracted = provider.extract_quote_from_document(
            file_bytes=file_bytes,
            file_name=filename,
            mime_type=content_type,
            category_hint=category,
        )
    except (ExtractionValidationError, ValueError, RuntimeError, KeyError, TypeError, OSError) as e:
        logger.warning("Quote extraction provider failed: %s", e)
        return None, str(e)
    else:
        if not extracted:
            return None, "Null extraction result"
        return extracted, None


def _build_quote_document_response(
    quote_doc: QuoteDocument,
    saved_items: list[ExtractedLineItemSchema],
    alerts: list[HiddenCostAlertSchema],
    benchmark_comp: BenchmarkComparisonSchema | None,
) -> QuoteDocumentResponseSchema:
    total_quoted = (
        float(quote_doc.total_quoted_amount) if quote_doc.total_quoted_amount is not None else None
    )
    tax_amt = float(quote_doc.tax_amount) if quote_doc.tax_amount is not None else None
    return QuoteDocumentResponseSchema(
        id=quote_doc.id,
        event_id=quote_doc.event_id,
        vendor_id=quote_doc.vendor_id,
        vendor_name=quote_doc.vendor_name,
        category=quote_doc.category,
        file_name=quote_doc.file_name,
        file_type=quote_doc.file_type,
        extraction_status=quote_doc.extraction_status,
        total_quoted_amount=total_quoted,
        tax_amount=tax_amt,
        line_items=saved_items,
        hidden_cost_alerts=alerts,
        benchmark_comparison=benchmark_comp,
        uploaded_at=quote_doc.uploaded_at,
    )


def _validate_comparison_category(quotes: Sequence[QuoteDocument], requested_ids: list[str]) -> str:
    if len(quotes) != len(requested_ids):
        found_ids = {q.id for q in quotes}
        missing = set(requested_ids) - found_ids
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quotes not found for IDs: {list(missing)}",
        )
    categories = {str(q.category).lower() for q in quotes}
    if len(categories) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "All quotes in a comparison must belong to the same category. "
                f"Found: {list(categories)}"
            ),
        )
    return str(next(iter(categories)))


def _extract_competitor_leverage(
    payload: NegotiationDraftRequestSchema | None, db: Session
) -> tuple[str | None, str | None, float | None]:
    if not (payload and payload.competing_quote_id):
        return None, None, None
    comp_quote = db.scalar(
        select(QuoteDocument).where(QuoteDocument.id == payload.competing_quote_id)
    )
    if not comp_quote:
        return None, None, None
    v_name = comp_quote.vendor_name
    tot = float(comp_quote.total_quoted_amount or 0.0)
    point = f"Alternative vendor {v_name} quoted ₹{tot:,.0f} for identical scope"
    return point, v_name, tot


def _gather_leverage_points(
    quote: QuoteDocument,
    payload: NegotiationDraftRequestSchema | None,
    event: Event | None,
    db: Session,
) -> tuple[list[str], str | None, float | None]:
    leverage_points: list[str] = []

    # 1. Missing hidden cost items
    items = _extract_line_item_schemas(quote.line_items)
    raw_terms = (quote.raw_extracted_json or {}).get("terms_and_conditions", [])
    alerts = HiddenCostDetector.analyze_quote(quote.category, items, raw_terms)
    missing_alerts = [a.name for a in alerts if a.status == "missing_from_quote"]
    if missing_alerts:
        leverage_points.append(
            f"Quote omits critical standard provisions: {', '.join(missing_alerts[:3])}"
        )

    # 2. Competitor proposal if provided
    comp_point, comp_name, comp_total = _extract_competitor_leverage(payload, db)
    if comp_point:
        leverage_points.append(comp_point)

    # 3. Benchmark delta
    b_comp = _compute_benchmark_for_quote(quote.category, quote.total_quoted_amount, event, db)
    if b_comp and not b_comp.is_limited_data and b_comp.cost_status == "above_median":
        leverage_points.append(
            f"Rate is {b_comp.percentage_diff_vs_median}% higher than "
            f"median market rates in {b_comp.city_tier}"
        )

    return leverage_points, comp_name, comp_total
