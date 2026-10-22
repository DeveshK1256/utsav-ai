from datetime import datetime, date
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class ExtractedLineItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., description="Line item service or material name")
    qty: float = Field(default=1.0, gt=0, description="Quantity")
    unit: str = Field(default="units", description="Unit of measurement (plates, days, sqft, units)")
    unit_price: float = Field(..., ge=0, description="Unit rate in INR")
    total: float = Field(..., ge=0, description="Line item total in INR")
    category_tag: Optional[str] = Field(default=None, description="Granular category tag")
    notes: Optional[str] = Field(default=None, description="Special conditions or specifications")


class QuoteExtractionPayloadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vendor_name: str = Field(..., description="Vendor business or contact name")
    category: str = Field(..., description="Service category (caterer, venue, decorator, photographer, other)")
    currency: str = Field(default="INR", description="Quote currency")
    subtotal: float = Field(..., ge=0, description="Pre-tax subtotal")
    tax_amount: float = Field(default=0.0, ge=0, description="Explicit tax amount")
    total_amount: float = Field(..., ge=0, description="Total payable amount quoted")
    line_items: List[ExtractedLineItemSchema] = Field(default_factory=list)
    terms_and_conditions: List[str] = Field(default_factory=list)
    validity_date: Optional[str] = Field(default=None, description="Quote validity or expiration date")
    is_gst_included: bool = Field(default=False, description="Whether total explicitly includes GST")
    confidence_score: float = Field(default=0.95, ge=0.0, le=1.0)

    def compute_deterministic_confidence(self) -> float:
        """
        Deterministic factual and mathematical validation of extracted quote payloads in Python.
        Zero LLM self-reported assertions. Evaluates:
          1. Essential Identity (0.10): Non-empty, non-generic vendor name
          2. Financial Non-Zero (0.10): total_amount > 0
          3. Completeness (0.10): len(line_items) >= 1
          4. Per-Item Arithmetic (0.10): qty * unit_price == total for all line items (within 1.5 INR)
          5. Math Consistency (0.45): sum(line_items.total) matches subtotal or total (within 2.0 INR)
          6. Tax & Grand Total Integrity (0.15): subtotal + tax_amount == total or GST included (within 2.0 INR)
        Guarantees that any quote failing Macro-Math Consistency cannot exceed 0.55 (< 0.60 gate).
        """
        score = 0.0

        # 1. Essential Identity (0.10)
        v_clean = (self.vendor_name or "").strip().lower()
        if v_clean and v_clean not in {"unknown", "unassigned", "none", "n/a", "extraction failed"}:
            score += 0.10

        # 2. Financial Non-Zero (0.10)
        if self.total_amount > 0:
            score += 0.10

        # 3. Completeness (0.10)
        if self.line_items and len(self.line_items) >= 1:
            score += 0.10

        # 4. Per-Item Arithmetic (0.10)
        if self.line_items and len(self.line_items) >= 1:
            all_items_arithmetic_valid = True
            for it in self.line_items:
                qty = it.qty or 1.0
                price = it.unit_price or 0.0
                item_tot = it.total or 0.0
                if abs((qty * price) - item_tot) > 1.5:
                    all_items_arithmetic_valid = False
                    break
            if all_items_arithmetic_valid:
                score += 0.10

        # 5. Math Consistency: sum(line_items) vs Subtotal / Total (0.45)
        if self.line_items and len(self.line_items) >= 1:
            items_sum = sum(it.total for it in self.line_items)
            if self.subtotal > 0 and abs(items_sum - self.subtotal) <= 2.0:
                score += 0.45
            elif self.total_amount > 0 and abs(items_sum - self.total_amount) <= 2.0:
                score += 0.45
            elif self.total_amount > 0 and abs((items_sum + self.tax_amount) - self.total_amount) <= 2.0:
                score += 0.45

        # 6. Tax & Grand Total Integrity (0.15)
        if self.total_amount > 0:
            if self.subtotal > 0:
                if abs((self.subtotal + self.tax_amount) - self.total_amount) <= 2.0:
                    score += 0.15
                elif self.is_gst_included and abs(self.subtotal - self.total_amount) <= 2.0:
                    score += 0.15
            elif self.tax_amount == 0.0:
                score += 0.15

        return round(min(max(score, 0.0), 1.0), 2)


class HiddenCostAlertSchema(BaseModel):
    code: str
    name: str
    description: str
    typical_impact: str
    suggested_question: str
    status: str = Field(default="missing_from_quote", description="'missing_from_quote', 'explicitly_covered', or 'ambiguous'")


class BenchmarkComparisonSchema(BaseModel):
    category: str
    city_tier: str
    sample_size: int
    median_unit_cost: Optional[float] = None
    quote_unit_cost: Optional[float] = None
    cost_status: str = Field(description="'above_median', 'near_median', 'below_median', or 'limited_data'")
    percentage_diff_vs_median: Optional[float] = None
    is_limited_data: bool = Field(default=False, description="True if sample size < 5")
    reasoning: Dict[str, Any]


class QuoteDocumentResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    vendor_id: Optional[str] = None
    vendor_name: str
    category: str
    file_name: str
    file_type: str
    extraction_status: Literal["completed", "flagged_review", "failed_needs_manual_entry"] = Field(
        ...,
        description=(
            "Extraction state: 'completed' (confidence >= 0.60), 'flagged_review' (confidence < 0.60, e.g. non-quote "
            "or low clarity document), or 'failed_needs_manual_entry' (corrupted file, unparseable schema, or hard error)"
        )
    )
    total_quoted_amount: Optional[float] = None
    tax_amount: Optional[float] = None
    line_items: List[ExtractedLineItemSchema] = Field(default_factory=list)
    hidden_cost_alerts: List[HiddenCostAlertSchema] = Field(default_factory=list)
    benchmark_comparison: Optional[BenchmarkComparisonSchema] = None
    uploaded_at: datetime


class QuoteComparisonRequestSchema(BaseModel):
    quote_ids: List[str] = Field(..., min_length=2, description="At least two quote IDs to compare")


class QuoteComparisonItemSchema(BaseModel):
    quote_id: str
    vendor_name: str
    raw_total: float
    effective_total_with_hidden_buffer: float
    normalized_cost_per_guest: float
    line_items: List[ExtractedLineItemSchema]
    hidden_cost_risk_count: int
    hidden_cost_risks: List[str]


class QuoteComparisonResponseSchema(BaseModel):
    event_id: str
    category: str
    guest_count: int
    compared_quotes: List[QuoteComparisonItemSchema]
    benchmark_median_unit_cost: Optional[float] = None
    benchmark_sample_size: int = 0
    benchmark_is_limited_data: bool = False
    best_value_quote_id: Optional[str] = None
    reasoning: Dict[str, Any]


class NegotiationDraftRequestSchema(BaseModel):
    quote_id: str
    competing_quote_id: Optional[str] = None
    target_discount_percentage: float = Field(default=10.0, ge=1.0, le=50.0)


class NegotiationMessageVariantSchema(BaseModel):
    english: str
    hindi: str


class NegotiationDraftResponseSchema(BaseModel):
    quote_id: str
    vendor_name: str
    target_discount_percentage: float
    leverage_points: List[str]
    draft_variants: Dict[str, NegotiationMessageVariantSchema]  # 'polite', 'firm', 'bundle_ask'
    disclaimer: str = "Draft messages are suggestions only. Utsav never sends messages autonomously."
