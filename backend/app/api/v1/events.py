import uuid
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from backend.app.db.session import get_db
from backend.app.models.models import Event, User
from backend.app.schemas.intake import (
    SubEventResponseSchema,
    BudgetItemResponseSchema,
    TaskResponseSchema
)
from backend.app.services.budget_engine import BudgetScalingEngine

router = APIRouter(prefix="/events", tags=["Events"])


class EventCreateSchema(BaseModel):
    name: str = Field(..., max_length=255)
    event_type: str = Field(..., max_length=50)
    guest_count: int = Field(..., gt=0)
    total_budget: float = Field(..., gt=0)
    city: str = Field(..., max_length=100)
    pincode: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    host_phone: str = Field(default="+919876543210")
    host_name: str = Field(default="Test Host")


class EventResponseSchema(BaseModel):
    id: str
    owner_id: str
    name: str
    event_type: str
    guest_count: int
    total_budget: float
    city: str
    pincode: Optional[str] = None
    status: str

    class Config:
        from_attributes = True


class EventDetailResponseSchema(EventResponseSchema):
    owner_name: Optional[str] = None
    city_tier: Optional[str] = None
    tradition_code: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    created_at: Optional[datetime] = None
    elder_verification_disclaimer: str = (
        "Auspicious timings & ritual checklists are algorithmic estimates computed via astronomical "
        "ephemeris models. Please verify with your family Guruji or elders."
    )
    sub_events: List[SubEventResponseSchema] = []
    budget_breakdown: List[BudgetItemResponseSchema] = []
    tasks: List[TaskResponseSchema] = []


@router.post("", response_model=EventResponseSchema, status_code=status.HTTP_201_CREATED)
def create_event(payload: EventCreateSchema, db: Session = Depends(get_db)):
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
        status="planning"
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/{event_id}", response_model=EventDetailResponseSchema)
def get_event(event_id: str, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

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
        tasks=tasks_list
    )


@router.delete("/{event_id}", status_code=status.HTTP_200_OK)
def delete_event(event_id: str, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
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
