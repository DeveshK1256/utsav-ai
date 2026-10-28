from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ChangeRequestSchema(BaseModel):
    change_type: Literal[
        "guest_count_changed", "vendor_cancelled", "date_moved", "budget_cut", "venue_unavailable"
    ]
    payload: dict[str, Any] = Field(
        ...,
        description="Raw change parameters, e.g. {'from_guest_count': 150, 'to_guest_count': 220}",
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
    added_tasks: list[dict[str, Any]] = Field(default_factory=list)
    moved_tasks: list[dict[str, Any]] = Field(default_factory=list)
    cancelled_tasks: list[str] = Field(default_factory=list)


class ChangeProposalResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    change_id: str
    event_id: str
    change_type: str
    status: str  # pending, queued, applied, rejected, blocked_infeasible
    summary: str
    budget_diff: list[BudgetItemDiffSchema] = Field(default_factory=list)
    budget_total_old: float = 0.0
    budget_total_new: float = 0.0
    budget_total_delta: float = 0.0
    task_diff: TaskDiffSchema = Field(default_factory=TaskDiffSchema)
    vendor_re_quote_categories: list[str] = Field(default_factory=list)
    capacity_warning: str | None = None
    infeasibility_reason: str | None = None
    explanation: str | None = None
    mitigation_suggestions: list[str] = Field(default_factory=list)
    provider_used: str = Field(
        default="deterministic_stub",
        description="Actual provider that generated the explanation ('gemini', 'stub', 'stub_fallback_quota_exhausted', 'stub_fallback_error')",
    )
    fallback_warning: str | None = Field(
        default=None,
        description="Prominent alert when an LLM provider fails or is rate-limited and falls back to deterministic stub",
    )
    created_at: datetime


class PatchChangeProposalSchema(BaseModel):
    budget_overrides: dict[str, float] | None = Field(
        default=None, description="Map of budget_item_id to overridden new_amount"
    )
