from typing import Any
from pydantic import BaseModel, Field


class GuestRowSchema(BaseModel):
    name: str
    phone: str
    group_side: str | None = "general"
    diet: str | None = "veg"
    mobility_needs: bool | None = False
    kids_count: int | None = 0
    headcount: int | None = 1
    accommodation: bool | None = False
    language: str | None = "en"
    notes: str | None = None


class GuestImportRequest(BaseModel):
    guests: list[GuestRowSchema]


class GuestItemResponse(BaseModel):
    id: str
    name: str
    phone: str
    group_side: str | None = None
    diet: str | None = None
    mobility_needs: bool | None = None
    kids_count: int | None = None
    headcount: int | None = None
    rsvp_status: str | None = None
    accommodation: bool | None = None
    language: str | None = None
    notes: str | None = None
    needs_host_review: bool | None = None
    created_at: str


class FactSheetSchema(BaseModel):
    venue_address: str | None = None
    parking_info: str | None = None
    dress_code: str | None = None
    timing_notes: str | None = None
    map_link: str | None = None
    other_facts: dict[str, Any] | None = None


class FactSheetResponseSchema(BaseModel):
    event_id: str
    venue_address: str | None = None
    parking_info: str | None = None
    dress_code: str | None = None
    timing_notes: str | None = None
    map_link: str | None = None
    other_facts: dict[str, Any] = Field(default_factory=dict)


class DeleteGuestResponseSchema(BaseModel):
    status: str
    guest_id: str
