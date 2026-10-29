import logging

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.limiter import limiter
from backend.app.db.session import get_db
from backend.app.models.models import (
    Event,
    QuoteDocument,
    VendorBenchmarkSample,
)
from backend.app.schemas.quotes import (
    NegotiationDraftRequestSchema,
    NegotiationDraftResponseSchema,
    NegotiationMessageVariantSchema,
    QuoteComparisonRequestSchema,
    QuoteComparisonResponseSchema,
    QuoteDocumentResponseSchema,
)
from backend.app.services.budget_engine import BudgetScalingEngine
from backend.app.services.hidden_cost_engine import HiddenCostDetector
from backend.app.services.llm_provider import (
    get_negotiation_draft_provider,
    get_quote_extraction_provider,
)
from backend.app.services.quote_comparison_engine import QuoteComparisonEngine
from backend.app.services.quote_service import (
    MAX_FILE_SIZE_BYTES,
    _build_quote_document_response,
    _compute_benchmark_for_quote,
    _extract_line_item_schemas,
    _extract_quote_payload,
    _gather_leverage_points,
    _handle_extraction_fallback,
    _save_vendor_and_quote,
    _validate_comparison_category,
    _verify_quote_ownership,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quotes", tags=["quotes"])


@router.post(
    "/upload", response_model=QuoteDocumentResponseSchema, status_code=status.HTTP_201_CREATED
)
@limiter.limit("20/minute")
async def upload_quote(
    request: Request,
    event_id: str = Form(..., description="ID of the event this quote belongs to"),
    category: str | None = Form(None, description="Optional vendor category override"),
    file: UploadFile = File(..., description="Quote file (PDF or image)"),
    owner_token: str | None = Form(None),
    x_event_owner_token: str | None = Header(None, alias="X-Event-Owner-Token"),
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> QuoteDocumentResponseSchema:
    """
    Accepts multipart upload of a vendor quote document.
    Stores the raw file in DB bytea (DEC-017), extracts structured line items via LLM
    provider, runs deterministic hidden-cost detection, saves quote + line items,
    and returns enriched analysis.
    """
    _ = (request,)
    event = db.scalar(select(Event).where(Event.id == event_id))
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Event with id '{event_id}' not found."
        )

    _verify_quote_ownership(event, owner_token, x_event_owner_token, authorization, db)

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Uploaded file exceeds maximum limit of 10 MB ({len(file_bytes)} bytes).",
        )

    provider = get_quote_extraction_provider()
    content_type = file.content_type or "application/octet-stream"
    filename = file.filename or "quote.pdf"

    extracted, err_msg = _extract_quote_payload(
        provider, file_bytes, filename, content_type, category
    )
    if not extracted:
        return _handle_extraction_fallback(
            event_id,
            category,
            filename,
            content_type,
            file_bytes,
            err_msg or "Extraction failed",
            db,
        )

    assigned_category = (category or extracted.category or "caterer").lower()
    alerts = HiddenCostDetector.analyze_quote(
        category=assigned_category,
        line_items=extracted.line_items,
        terms_and_conditions=extracted.terms_and_conditions,
    )

    quote_doc, saved_items = _save_vendor_and_quote(
        event_id, assigned_category, extracted, filename, content_type, file_bytes, alerts, db
    )
    benchmark_comp = _compute_benchmark_for_quote(
        assigned_category, quote_doc.total_quoted_amount, event, db
    )

    return _build_quote_document_response(quote_doc, saved_items, alerts, benchmark_comp)


@router.get("/event/{event_id}", response_model=list[QuoteDocumentResponseSchema])
def list_event_quotes(
    event_id: str, db: Session = Depends(get_db)
) -> list[QuoteDocumentResponseSchema]:
    """
    List all uploaded quotes for an event with parsed line items and analysis.
    """
    event = db.scalar(select(Event).where(Event.id == event_id))
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Event with id '{event_id}' not found."
        )

    quotes = db.scalars(
        select(QuoteDocument)
        .where(QuoteDocument.event_id == event_id)
        .order_by(QuoteDocument.uploaded_at.desc())
    ).all()

    results = []
    for q in quotes:
        items = _extract_line_item_schemas(q.line_items)
        raw_terms = (q.raw_extracted_json or {}).get("terms_and_conditions", [])
        alerts = HiddenCostDetector.analyze_quote(
            category=q.category, line_items=items, terms_and_conditions=raw_terms
        )
        b_comp = _compute_benchmark_for_quote(q.category, q.total_quoted_amount, event, db)

        results.append(
            QuoteDocumentResponseSchema(
                id=q.id,
                event_id=q.event_id,
                vendor_id=q.vendor_id,
                vendor_name=q.vendor_name,
                category=q.category,
                file_name=q.file_name,
                file_type=q.file_type,
                extraction_status=q.extraction_status,
                total_quoted_amount=float(q.total_quoted_amount)
                if q.total_quoted_amount is not None
                else None,
                tax_amount=float(q.tax_amount) if q.tax_amount is not None else None,
                line_items=items,
                hidden_cost_alerts=alerts,
                benchmark_comparison=b_comp,
                uploaded_at=q.uploaded_at,
            )
        )

    return results


@router.post("/compare", response_model=QuoteComparisonResponseSchema)
def compare_quotes(
    payload: QuoteComparisonRequestSchema, db: Session = Depends(get_db)
) -> QuoteComparisonResponseSchema:
    """
    Compares two or more quotes side-by-side.
    Validates all quotes share the exact same category.
    Normalizes per-guest variable costs, includes risk buffers for missing hidden-cost items,
    and returns deterministic comparative metrics.
    """
    if len(payload.quote_ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least two quote IDs are required for comparison.",
        )

    quotes = db.scalars(select(QuoteDocument).where(QuoteDocument.id.in_(payload.quote_ids))).all()
    assigned_category = _validate_comparison_category(quotes, payload.quote_ids)

    first_event_id = quotes[0].event_id
    event = db.scalar(select(Event).where(Event.id == first_event_id))
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Associated event not found."
        )

    city_tier = BudgetScalingEngine.get_city_tier(event.city)
    benchmarks = db.scalars(
        select(VendorBenchmarkSample.normalized_unit_cost).where(
            VendorBenchmarkSample.category == assigned_category,
            VendorBenchmarkSample.city_tier == city_tier,
        )
    ).all()
    samples = [float(b) for b in benchmarks]

    quotes_data = []
    for q in quotes:
        items = _extract_line_item_schemas(q.line_items)
        raw_terms = (q.raw_extracted_json or {}).get("terms_and_conditions", [])
        alerts = HiddenCostDetector.analyze_quote(
            category=q.category, line_items=items, terms_and_conditions=raw_terms
        )
        quotes_data.append(
            {
                "id": q.id,
                "vendor_name": q.vendor_name,
                "total_amount": float(q.total_quoted_amount or 0.0),
                "quoted_guest_count": event.guest_count,
                "line_items": items,
                "hidden_cost_alerts": alerts,
            }
        )

    return QuoteComparisonEngine.compare_quotes(
        event_id=event.id,
        category=assigned_category,
        target_guest_count=event.guest_count,
        quotes_data=quotes_data,
        benchmark_samples=samples,
    )


@router.post("/{quote_id}/negotiate-draft", response_model=NegotiationDraftResponseSchema)
def generate_negotiation_draft(
    quote_id: str,
    payload: NegotiationDraftRequestSchema | None = None,
    db: Session = Depends(get_db),
) -> NegotiationDraftResponseSchema:
    """
    Generates polite, firm, and bundle-ask negotiation draft letters in English and Hindi.
    Draws leverage points directly from detected hidden costs and benchmark discrepancies.
    Copy/edit only — no autonomous message sending.
    """
    quote = db.scalar(select(QuoteDocument).where(QuoteDocument.id == quote_id))
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"QuoteDocument with id '{quote_id}' not found.",
        )

    event = db.scalar(select(Event).where(Event.id == quote.event_id))
    discount_pct = payload.target_discount_percentage if payload else 10.0

    leverage_points, comp_name, comp_total = _gather_leverage_points(quote, payload, event, db)

    provider = get_negotiation_draft_provider()
    drafts_dict = provider.generate_negotiation_drafts(
        vendor_name=quote.vendor_name,
        category=quote.category,
        quoted_total=float(quote.total_quoted_amount or 0.0),
        target_discount_pct=discount_pct,
        leverage_points=leverage_points,
        competing_vendor_name=comp_name,
        competing_quote_total=comp_total,
    )

    formatted_variants = {
        key: NegotiationMessageVariantSchema(
            english=variant.get("english", ""), hindi=variant.get("hindi", "")
        )
        for key, variant in drafts_dict.items()
    }

    return NegotiationDraftResponseSchema(
        quote_id=quote.id,
        vendor_name=quote.vendor_name,
        target_discount_percentage=discount_pct,
        leverage_points=leverage_points,
        draft_variants=formatted_variants,
        disclaimer="Draft messages are suggestions only. Utsav never sends messages autonomously.",
    )
