from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ExtractedLineItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., description="Line item service or material name")
    qty: float = Field(default=1.0, gt=0, description="Quantity")
    unit: str = Field(
        default="units", description="Unit of measurement (plates, days, sqft, units)"
    )
    unit_price: float = Field(..., ge=0, description="Unit rate in INR")
    total: float = Field(..., ge=0, description="Line item total in INR")
    category_tag: str | None = Field(default=None, description="Granular category tag")
    notes: str | None = Field(default=None, description="Special conditions or specifications")


class QuoteExtractionPayloadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vendor_name: str = Field(..., description="Vendor business or contact name")
    category: str = Field(
        ..., description="Service category (caterer, venue, decorator, photographer, other)"
    )
    currency: str = Field(default="INR", description="Quote currency")
    subtotal: float = Field(..., ge=0, description="Pre-tax subtotal")
    tax_amount: float = Field(default=0.0, ge=0, description="Explicit tax amount")
    total_amount: float = Field(..., ge=0, description="Total payable amount quoted")
    line_items: list[ExtractedLineItemSchema] = Field(default_factory=list)
    terms_and_conditions: list[str] = Field(default_factory=list)
    validity_date: str | None = Field(default=None, description="Quote validity or expiration date")
    is_gst_included: bool = Field(
        default=False, description="Whether total explicitly includes GST"
    )
    confidence_score: float = Field(default=0.95, ge=0.0, le=1.0)

    def _check_essential_identity(self) -> float:
        v_clean = (self.vendor_name or "").strip().lower()
        invalid_names = {"unknown", "unassigned", "none", "n/a", "extraction failed"}
        return 0.10 if (v_clean and v_clean not in invalid_names) else 0.0

    def _check_item_arithmetic(self) -> float:
        if not self.line_items:
            return 0.0
        for it in self.line_items:
            qty = it.qty or 1.0
            price = it.unit_price or 0.0
            item_tot = it.total or 0.0
            if abs((qty * price) - item_tot) > 1.5:
                return 0.0
        return 0.10

    def _check_math_consistency(self) -> float:
        if not self.line_items:
            return 0.0
        items_sum = sum(it.total for it in self.line_items)
        sub_match = self.subtotal > 0 and abs(items_sum - self.subtotal) <= 2.0
        tot_match = self.total_amount > 0 and abs(items_sum - self.total_amount) <= 2.0
        tax_tot_match = (
            self.total_amount > 0 and abs((items_sum + self.tax_amount) - self.total_amount) <= 2.0
        )
        return 0.45 if (sub_match or tot_match or tax_tot_match) else 0.0

    def _check_tax_and_total_integrity(self) -> float:
        if self.total_amount <= 0:
            return 0.0
        if self.subtotal > 0:
            exact_match = abs((self.subtotal + self.tax_amount) - self.total_amount) <= 2.0
            gst_match = self.is_gst_included and abs(self.subtotal - self.total_amount) <= 2.0
            return 0.15 if (exact_match or gst_match) else 0.0
        return 0.15 if self.tax_amount == 0.0 else 0.0

    def compute_deterministic_confidence(self) -> float:
        """
        Deterministic factual and mathematical validation of extracted quote payloads in Python.
        Zero LLM self-reported assertions. Evaluates:
          1. Essential Identity (0.10): Non-empty, non-generic vendor name
          2. Financial Non-Zero (0.10): total_amount > 0
          3. Completeness (0.10): len(line_items) >= 1
          4. Per-Item Arithmetic (0.10): qty * unit_price == total for all line items
             (within 1.5 INR)
          5. Math Consistency (0.45): sum(line_items.total) matches subtotal or total
             (within 2.0 INR)
          6. Tax & Grand Total Integrity (0.15): subtotal + tax_amount == total or GST included
             (within 2.0 INR)
        Guarantees that any quote failing Macro-Math Consistency cannot exceed 0.55 (< 0.60 gate).
        """
        scores = [
            self._check_essential_identity(),
            0.10 if self.total_amount > 0 else 0.0,
            0.10 if (self.line_items and len(self.line_items) >= 1) else 0.0,
            self._check_item_arithmetic(),
            self._check_math_consistency(),
            self._check_tax_and_total_integrity(),
        ]
        return round(min(max(sum(scores), 0.0), 1.0), 2)


class HiddenCostAlertSchema(BaseModel):
    code: str
    name: str
    description: str
    typical_impact: str
    suggested_question: str
    status: str = Field(
        default="missing_from_quote",
        description="'missing_from_quote', 'explicitly_covered', or 'ambiguous'",
    )


class BenchmarkComparisonSchema(BaseModel):
    category: str
    city_tier: str
    sample_size: int
    median_unit_cost: float | None = None
    quote_unit_cost: float | None = None
    cost_status: str = Field(
        description="'above_median', 'near_median', 'below_median', or 'limited_data'"
    )
    percentage_diff_vs_median: float | None = None
    is_limited_data: bool = Field(default=False, description="True if sample size < 5")
    reasoning: dict[str, Any]


class QuoteDocumentResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    vendor_id: str | None = None
    vendor_name: str
    category: str
    file_name: str
    file_type: str
    extraction_status: Literal["completed", "flagged_review", "failed_needs_manual_entry"] = Field(
        ...,
        description=(
            "Extraction state: 'completed' (confidence >= 0.60), 'flagged_review' "
            "(confidence < 0.60, e.g. non-quote or low clarity document), "
            "or 'failed_needs_manual_entry' (corrupted file, unparseable schema, or hard error)"
        ),
    )
    total_quoted_amount: float | None = None
    tax_amount: float | None = None
    line_items: list[ExtractedLineItemSchema] = Field(default_factory=list)
    hidden_cost_alerts: list[HiddenCostAlertSchema] = Field(default_factory=list)
    benchmark_comparison: BenchmarkComparisonSchema | None = None
    uploaded_at: datetime


class QuoteComparisonRequestSchema(BaseModel):
    quote_ids: list[str] = Field(..., min_length=2, description="At least two quote IDs to compare")


class QuoteComparisonItemSchema(BaseModel):
    quote_id: str
    vendor_name: str
    raw_total: float
    effective_total_with_hidden_buffer: float
    normalized_cost_per_guest: float
    line_items: list[ExtractedLineItemSchema]
    hidden_cost_risk_count: int
    hidden_cost_risks: list[str]


class QuoteComparisonResponseSchema(BaseModel):
    event_id: str
    category: str
    guest_count: int
    compared_quotes: list[QuoteComparisonItemSchema]
    benchmark_median_unit_cost: float | None = None
    benchmark_sample_size: int = 0
    benchmark_is_limited_data: bool = False
    best_value_quote_id: str | None = None
    reasoning: dict[str, Any]


class NegotiationDraftRequestSchema(BaseModel):
    quote_id: str
    competing_quote_id: str | None = None
    target_discount_percentage: float = Field(default=10.0, ge=1.0, le=50.0)


class NegotiationMessageVariantSchema(BaseModel):
    english: str
    hindi: str


class NegotiationDraftResponseSchema(BaseModel):
    quote_id: str
    vendor_name: str
    target_discount_percentage: float
    leverage_points: list[str]
    draft_variants: dict[str, NegotiationMessageVariantSchema]  # 'polite', 'firm', 'bundle_ask'
    disclaimer: str = (
        "Draft messages are suggestions only. Utsav never sends messages autonomously."
    )
