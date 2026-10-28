import html
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from backend.app.core.security import generate_owner_token, verify_event_owner_token
from backend.app.db.session import get_db
from backend.app.models.models import Event, User, VendorProfile
from backend.app.schemas.intake import (
    BudgetItemResponseSchema,
    SubEventResponseSchema,
    TaskResponseSchema,
)
from backend.app.services.budget_engine import BudgetScalingEngine

router = APIRouter(prefix="/events", tags=["Events"])


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
        "Auspicious timings & ritual checklists are algorithmic estimates computed via astronomical "
        "ephemeris models. Please verify with your family Guruji or elders."
    )
    sub_events: list[SubEventResponseSchema] = []
    budget_breakdown: list[BudgetItemResponseSchema] = []
    tasks: list[TaskResponseSchema] = []
    metadata_json: dict[str, Any] | None = None


class ComposeUpdateSchema(BaseModel):
    step: str | None = Field(None, description="Current step: 'venue', 'timing', 'invitation'")
    vendor_profile_id: str | None = Field(None, description="UUID of real vendor_profile from discovery directory")
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


@router.post("", response_model=EventResponseSchema, status_code=status.HTTP_201_CREATED)
def create_event(payload: EventCreateSchema, db: Session = Depends(get_db)) -> EventResponseSchema:
    # Find or create user
    user = db.query(User).filter(User.phone_number == payload.host_phone).first()
    if not user:
        user = User(
            phone_number=payload.host_phone,
            full_name=payload.host_name,
            role="host",
            preferred_language="en"
        )
        db.add(user)
        db.flush()

    owner_token = generate_owner_token()
    event = Event(
        owner_id=user.id,
        name=payload.name,
        event_type=payload.event_type,
        guest_count=payload.guest_count,
        total_budget=payload.total_budget,
        city=payload.city,
        pincode=payload.pincode or "400001",
        start_date=payload.start_date or date.today(),
        end_date=payload.end_date or date.today(),
        status="planning",
        owner_token=owner_token,
        metadata_json={"owner_token": owner_token, "host_name": payload.host_name}
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return EventResponseSchema.model_validate(event)


@router.get("/{event_id}", response_model=EventDetailResponseSchema)
def get_event(
    event_id: str,
    event: Event = Depends(verify_event_owner_token),
    db: Session = Depends(get_db)
) -> EventDetailResponseSchema:
    returned_token = event.owner_token or (event.metadata_json or {}).get("owner_token")
    tier = BudgetScalingEngine.resolve_city_tier(event.city)
    owner_name = (
        event.owner.full_name
        if event.owner
        else (event.metadata_json.get("host_name") if event.metadata_json else "Host")
    )

    sub_events_list = [
        SubEventResponseSchema(
            id=se.id,
            name=se.name,
            start_time=se.start_time,
            end_time=se.end_time,
            venue_name=se.venue_name,
            is_outdoor=se.is_outdoor,
            is_muhurat_locked=se.is_muhurat_locked,
            muhurat_notes=se.muhurat_notes,
            sort_order=se.sort_order
        )
        for se in event.sub_events
    ]

    budget_list = []
    tot_budget = float(event.total_budget) if event.total_budget else 1.0
    for b in event.budget_items:
        pct = round((float(b.planned_amount) / tot_budget) * 100, 1) if tot_budget > 0 else 0.0
        budget_list.append(
            BudgetItemResponseSchema(
                id=b.id,
                category=b.category,
                name=b.name,
                planned_amount=float(b.planned_amount),
                actual_amount=float(b.actual_amount or 0.0),
                percentage=pct,
                reasoning_spec=b.reasoning_spec
            )
        )

    tasks_list = [
        TaskResponseSchema(
            id=t.id,
            title=t.title,
            status=t.status,
            scheduled_start=t.scheduled_start,
            scheduled_end=t.scheduled_end,
            duration_minutes=t.duration_minutes,
            assigned_role=t.assigned_role
        )
        for t in event.tasks
    ]

    return EventDetailResponseSchema(
        id=event.id,
        owner_id=event.owner_id,
        name=event.name,
        event_type=event.event_type,
        guest_count=event.guest_count,
        total_budget=float(event.total_budget),
        city=event.city,
        pincode=event.pincode,
        status=event.status,
        owner_name=owner_name,
        city_tier=tier,
        tradition_code=event.tradition_code,
        start_date=event.start_date,
        end_date=event.end_date,
        created_at=event.created_at,
        sub_events=sub_events_list,
        budget_breakdown=budget_list,
        tasks=tasks_list,
        owner_token=returned_token,
        metadata_json=event.metadata_json or {}
    )


@router.post("/{event_id}/compose", response_model=EventDetailResponseSchema)
def update_event_compose_progress(
    event_id: str,
    payload: ComposeUpdateSchema,
    event: Event = Depends(verify_event_owner_token),
    db: Session = Depends(get_db)
) -> EventDetailResponseSchema:
    """
    Orchestration progress persistence for the Compose Celebration flow.
    - Saves current step and shortlist venue picks to metadata_json.
    - If muhurat_time is selected, locks it to the primary sub_event (is_muhurat_locked=True)
      and writes to event.metadata_json['muhurat_time'].
    - Explicit skip actions record skip flags without fabricating or carrying stale data.
    """
    meta = dict(event.metadata_json or {})
    compose_state = dict(meta.get("compose_celebration", {}))

    if payload.step:
        compose_state["current_step"] = payload.step

    # Step A: Venue handling
    if payload.skip_venue:
        compose_state["venue_skipped"] = True
        compose_state.pop("vendor_profile_id", None)
        compose_state.pop("venue_name", None)
        compose_state.pop("venue_locality", None)
        compose_state.pop("venue_city", None)
        compose_state.pop("venue_status", None)
        meta.pop("venue", None)
    elif payload.vendor_profile_id:
        vendor = db.query(VendorProfile).filter(VendorProfile.id == payload.vendor_profile_id).first()
        if not vendor:
            # If not yet in DB (e.g. dynamically selected from OpenStreetMap search or client cache),
            # dynamically INSERT a permanent row into vendor_profiles NOW so it has a real database identity
            # for future quotes (F5) and reviews (F12) to attach via foreign key.
            if payload.venue_name:
                vendor = VendorProfile(
                    id=payload.vendor_profile_id,
                    business_name=payload.venue_name.strip()[:200],
                    category="venue",
                    latitude=payload.latitude,
                    longitude=payload.longitude,
                    city=(payload.venue_city or event.city or "Nearby")[:100],
                    locality=payload.venue_locality[:150] if payload.venue_locality else None,
                    city_tier=getattr(event, "city_tier", None) or "tier_2",
                    is_verified_profile=False,
                    average_rating=None,  # Honest unrated
                    rating_count=0,
                    coordinate_precision="exact_osm_node" if payload.latitude else "locality_approximate",
                    source_notes=payload.source_notes or f"OpenStreetMap Selected (OSM Record: {payload.osm_id or 'user_selection'})",
                    metadata_json={"address": payload.venue_address} if payload.venue_address else {}
                )
                db.add(vendor)
                db.commit()
                db.refresh(vendor)
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Vendor profile with ID '{payload.vendor_profile_id}' not found in discovery directory"
                )
        venue_display = f"{vendor.business_name}, {vendor.locality}" if vendor.locality else vendor.business_name
        meta["venue"] = venue_display
        compose_state["vendor_profile_id"] = vendor.id
        compose_state["venue_name"] = vendor.business_name
        compose_state["venue_locality"] = vendor.locality
        compose_state["venue_city"] = vendor.city
        compose_state["venue_status"] = "shortlist_pick"  # Honest note: shortlist pick, not confirmed booking
        compose_state["venue_skipped"] = False

        if event.fact_sheet and payload.venue_address:
            event.fact_sheet.venue_address = payload.venue_address
        elif event.fact_sheet and vendor.locality:
            event.fact_sheet.venue_address = f"{vendor.business_name}, {vendor.locality}, {vendor.city}"
    elif payload.step == "venue" and not payload.skip_venue:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Step A venue selection requires a valid vendor_profile_id from the discovery directory (or skip_venue: true)"
        )

    # Step B: Timing & Muhurat handling
    if payload.skip_timing:
        compose_state["timing_skipped"] = True
        # If timing was explicitly skipped, remove any event-level muhurat_time override
        # so M10 cleanly falls back to 'Time to be confirmed' / placeholder
        meta.pop("muhurat_time", None)
        compose_state["muhurat_locked"] = False
    elif payload.muhurat_time:
        meta["muhurat_time"] = payload.muhurat_time
        compose_state["muhurat_time"] = payload.muhurat_time
        compose_state["muhurat_locked"] = True
        compose_state["timing_skipped"] = False

        # If we have sub_events, lock the primary / first ceremony
        from backend.app.models.models import SubEvent
        target_sub = None
        if payload.sub_event_name:
            target_sub = db.query(SubEvent).filter(
                SubEvent.event_id == event.id,
                SubEvent.name.ilike(f"%{payload.sub_event_name}%")
            ).first()
        if not target_sub:
            target_sub = db.query(SubEvent).filter(SubEvent.event_id == event.id).order_by(SubEvent.start_time).first()

        if target_sub:
            target_sub.is_muhurat_locked = True
            if payload.muhurat_notes:
                target_sub.muhurat_notes = payload.muhurat_notes
            db.add(target_sub)

    meta["compose_celebration"] = compose_state
    event.metadata_json = meta
    db.add(event)
    db.commit()
    db.refresh(event)

    return get_event(
        event_id=event.id,
        event=event,
        db=db
    )


@router.delete("/{event_id}", status_code=status.HTTP_200_OK)
def delete_event(
    event_id: str,
    event: Event = Depends(verify_event_owner_token),
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    owner_id = event.owner_id
    db.delete(event)
    db.commit()
    # Clean up test user if no other events
    remaining = db.query(Event).filter(Event.owner_id == owner_id).count()
    if remaining == 0:
        test_user = db.query(User).filter(User.id == owner_id).first()
        if test_user:
            db.delete(test_user)
            db.commit()
    return {"deleted": True, "event_id": event_id}
