from datetime import datetime, date
from typing import List, Optional, Dict, Any
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
    extraction_status: str
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
