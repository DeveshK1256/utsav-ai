from datetime import datetime, date
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class ChangeRequestSchema(BaseModel):
    change_type: Literal[
        "guest_count_changed",
        "vendor_cancelled",
        "date_moved",
        "budget_cut",
        "venue_unavailable"
    ]
    payload: Dict[str, Any] = Field(
        ...,
        description="Raw change parameters, e.g. {'from_guest_count': 150, 'to_guest_count': 220}"
    )


class BudgetItemDiffSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    budget_item_id: str
    category: str
    name: str
    scaling_rule: str
    old_amount: float
    new_amount: float
    difference: float
    formula: str


class TaskDiffSchema(BaseModel):
    added_tasks: List[Dict[str, Any]] = Field(default_factory=list)
    moved_tasks: List[Dict[str, Any]] = Field(default_factory=list)
    cancelled_tasks: List[str] = Field(default_factory=list)


class ChangeProposalResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    change_id: str
    event_id: str
    change_type: str
    status: str  # pending, queued, applied, rejected, blocked_infeasible
    summary: str
    budget_diff: List[BudgetItemDiffSchema] = Field(default_factory=list)
    budget_total_old: float = 0.0
    budget_total_new: float = 0.0
    budget_total_delta: float = 0.0
    task_diff: TaskDiffSchema = Field(default_factory=TaskDiffSchema)
    vendor_re_quote_categories: List[str] = Field(default_factory=list)
    capacity_warning: Optional[str] = None
    infeasibility_reason: Optional[str] = None
    explanation: Optional[str] = None
    mitigation_suggestions: List[str] = Field(default_factory=list)
    provider_used: str = Field(default="deterministic_stub", description="Actual provider that generated the explanation ('gemini', 'stub', 'stub_fallback_quota_exhausted', 'stub_fallback_error')")
    fallback_warning: Optional[str] = Field(default=None, description="Prominent alert when an LLM provider fails or is rate-limited and falls back to deterministic stub")
    created_at: datetime


class PatchChangeProposalSchema(BaseModel):
    budget_overrides: Optional[Dict[str, float]] = Field(
        default=None,
        description="Map of budget_item_id to overridden new_amount"
    )
