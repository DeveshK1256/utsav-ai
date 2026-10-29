import html
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.schemas.intake import (
    BudgetItemResponseSchema,
    SubEventResponseSchema,
    TaskResponseSchema,
)


class EventCreateSchema(BaseModel):
    name: str = Field(..., max_length=255)
    event_type: str = Field(..., max_length=50)
    guest_count: int = Field(..., gt=0)
    total_budget: float = Field(..., gt=0)
    city: str = Field(..., max_length=100)
    pincode: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    host_phone: str = Field(default="+919876543210")
    host_name: str = Field(default="Test Host")

    @field_validator("name")
    @classmethod
    def sanitize_event_name(cls, v: str) -> str:
        return html.escape(v.strip())


class EventResponseSchema(BaseModel):
    id: str
    owner_id: str
    name: str
    event_type: str
    guest_count: int
    total_budget: float
    city: str
    pincode: str | None = None
    status: str
    owner_token: str | None = None

    model_config = ConfigDict(from_attributes=True)


class EventDetailResponseSchema(EventResponseSchema):
    owner_name: str | None = None
    city_tier: str | None = None
    tradition_code: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    created_at: datetime | None = None
    elder_verification_disclaimer: str = (
        "Auspicious timings & ritual checklists are algorithmic estimates computed "
        "via astronomical ephemeris models. Please verify with your family Guruji or elders."
    )
    sub_events: list[SubEventResponseSchema] = []
    budget_breakdown: list[BudgetItemResponseSchema] = []
    tasks: list[TaskResponseSchema] = []
    metadata_json: dict[str, Any] | None = None


class ComposeUpdateSchema(BaseModel):
    step: str | None = Field(None, description="Current step: 'venue', 'timing', 'invitation'")
    vendor_profile_id: str | None = Field(
        None, description="UUID of real vendor_profile from discovery directory"
    )
    venue_name: str | None = None
    venue_locality: str | None = None
    venue_address: str | None = None
    venue_city: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    osm_id: str | None = None
    source_notes: str | None = None
    muhurat_time: str | None = None
    muhurat_date: date | None = None
    muhurat_notes: str | None = None
    sub_event_name: str | None = None
    skip_venue: bool | None = False
    skip_timing: bool | None = False
