import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Numeric, Boolean, Date, DateTime,
    ForeignKey, Text, JSON, CheckConstraint, Index
)
from sqlalchemy.orm import relationship
from backend.app.db.base import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    phone_number = Column(String(20), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=True)
    full_name = Column(String(150), nullable=False)
    role = Column(String(50), default="host", nullable=False)
    preferred_language = Column(String(10), default="en", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    events = relationship("Event", back_populates="owner", cascade="all, delete-orphan")


class Tradition(Base):
    __tablename__ = "traditions"

    code = Column(String(50), primary_key=True)
    regional_name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    cultural_notes = Column(Text, nullable=True)

    ritual_items = relationship("RitualItem", back_populates="tradition", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="tradition")


class RitualItem(Base):
    __tablename__ = "ritual_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tradition_code = Column(String(50), ForeignKey("traditions.code"), nullable=False, index=True)
    item_name = Column(String(150), nullable=False)
    regional_name = Column(String(150), nullable=True)
    standard_quantity = Column(String(100), nullable=False)
    spiritual_purpose = Column(Text, nullable=True)

    tradition = relationship("Tradition", back_populates="ritual_items")


class Event(Base):
    __tablename__ = "events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    event_type = Column(String(50), nullable=False)  # wedding, puja, community_festival, etc.
    tradition_code = Column(String(50), ForeignKey("traditions.code"), nullable=True)
    guest_count = Column(Integer, nullable=False)
    total_budget = Column(Numeric(14, 2), nullable=False)
    city = Column(String(100), nullable=False)
    pincode = Column(String(10), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(50), default="planning", nullable=False, index=True)
    metadata_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        CheckConstraint("guest_count > 0", name="check_positive_guest_count"),
        CheckConstraint("total_budget >= 0", name="check_non_negative_budget"),
        Index("idx_events_dates", "start_date", "end_date"),
    )

    owner = relationship("User", back_populates="events")
    tradition = relationship("Tradition", back_populates="events")
    sub_events = relationship("SubEvent", back_populates="event", cascade="all, delete-orphan", order_by="SubEvent.sort_order")
    budget_items = relationship("BudgetItem", back_populates="event", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="event", cascade="all, delete-orphan")
    event_logs = relationship("EventLog", back_populates="event", cascade="all, delete-orphan")


class SubEvent(Base):
    __tablename__ = "sub_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    event_id = Column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    venue_name = Column(String(255), nullable=False)
    venue_address = Column(Text, nullable=True)
    is_outdoor = Column(Boolean, default=False, nullable=False)
    is_muhurat_locked = Column(Boolean, default=False, nullable=False)
    muhurat_notes = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)

    event = relationship("Event", back_populates="sub_events")
    tasks = relationship("Task", back_populates="sub_event")


class BudgetItem(Base):
    __tablename__ = "budget_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    event_id = Column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    vendor_id = Column(String(36), nullable=True)
    category = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    planned_amount = Column(Numeric(14, 2), nullable=False)
    actual_amount = Column(Numeric(14, 2), default=0.00, nullable=False)
    is_paid = Column(Boolean, default=False, nullable=False)
    reasoning_spec = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    event = relationship("Event", back_populates="budget_items")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    event_id = Column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    sub_event_id = Column(String(36), ForeignKey("sub_events.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="pending", nullable=False)
    scheduled_start = Column(DateTime, nullable=True)
    scheduled_end = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    dependency_task_ids = Column(JSON, default=list, nullable=False)
    assigned_role = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    event = relationship("Event", back_populates="tasks")
    sub_event = relationship("SubEvent", back_populates="tasks")


class EventLog(Base):
    __tablename__ = "event_log"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    event_id = Column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(String(100), nullable=False)
    diff_payload = Column(JSON, nullable=False)
    actor_id = Column(String(36), nullable=True)
    logged_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    event = relationship("Event", back_populates="event_logs")
