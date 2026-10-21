import uuid
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional

from backend.app.db.session import get_db
from backend.app.models.models import Event, User

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


@router.get("/{event_id}", response_model=EventResponseSchema)
def get_event(event_id: str, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


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
