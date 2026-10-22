import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Numeric, Boolean, Date, DateTime,
    ForeignKey, Text, JSON, CheckConstraint, Index, LargeBinary
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
    venue_capacity = Column(Integer, nullable=True)  # Manually-entered placeholder per DEC-016
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
    vendors = relationship("Vendor", back_populates="event", cascade="all, delete-orphan")
    quote_documents = relationship("QuoteDocument", back_populates="event", cascade="all, delete-orphan")
    change_events = relationship("ChangeEvent", back_populates="event", cascade="all, delete-orphan")
    ai_suggestions = relationship("AISuggestion", back_populates="event", cascade="all, delete-orphan")


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
    scaling_rule = Column(String(50), default="per_guest", nullable=False)  # per_guest, fixed, tiered per DEC-018
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


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    event_id = Column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    business_name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    contact_person = Column(String(150), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    agreed_quote = Column(Numeric(14, 2), nullable=True)
    advance_paid = Column(Numeric(14, 2), default=0.00, nullable=False)
    contract_terms = Column(JSON, default=dict, nullable=False)
    hidden_cost_alerts = Column(JSON, default=list, nullable=False)
    rating = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    event = relationship("Event", back_populates="vendors")
    quotes = relationship("QuoteDocument", back_populates="vendor")


class QuoteDocument(Base):
    __tablename__ = "quote_documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    event_id = Column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    vendor_id = Column(String(36), ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True, index=True)
    vendor_name = Column(String(200), nullable=False)
    category = Column(String(50), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(100), nullable=False)
    uploaded_file = Column(LargeBinary, nullable=False)  # Stored in DB bytea per DEC-017
    extraction_status = Column(String(50), default="pending", nullable=False, index=True)
    raw_extracted_json = Column(JSON, default=dict, nullable=False)
    total_quoted_amount = Column(Numeric(14, 2), nullable=True)
    tax_amount = Column(Numeric(14, 2), nullable=True)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    event = relationship("Event", back_populates="quote_documents")
    vendor = relationship("Vendor", back_populates="quotes")
    line_items = relationship("QuoteLineItem", back_populates="quote_document", cascade="all, delete-orphan")


class QuoteLineItem(Base):
    __tablename__ = "quote_line_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    quote_document_id = Column(String(36), ForeignKey("quote_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    qty = Column(Numeric(10, 2), default=1.0, nullable=False)
    unit = Column(String(50), default="units", nullable=False)
    unit_price = Column(Numeric(14, 2), nullable=False)
    total = Column(Numeric(14, 2), nullable=False)
    category_tag = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)

    quote_document = relationship("QuoteDocument", back_populates="line_items")


class VendorBenchmarkSample(Base):
    __tablename__ = "vendor_benchmark_samples"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    category = Column(String(50), nullable=False, index=True)
    city_tier = Column(String(20), nullable=False, index=True)
    normalized_unit_cost = Column(Numeric(14, 2), nullable=False)
    source_event_id = Column(String(36), ForeignKey("events.id", ondelete="SET NULL"), nullable=True)
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class ChangeEvent(Base):
    __tablename__ = "change_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    event_id = Column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    change_type = Column(String(50), nullable=False)  # guest_count_changed, vendor_cancelled, date_moved, budget_cut, venue_unavailable
    payload = Column(JSON, nullable=False)
    status = Column(String(50), default="pending", nullable=False, index=True)  # pending, queued, applied, rejected, blocked_infeasible
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    event = relationship("Event", back_populates="change_events")
    suggestions = relationship("AISuggestion", back_populates="change_event", cascade="all, delete-orphan")


class AISuggestion(Base):
    __tablename__ = "ai_suggestions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    event_id = Column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    change_event_id = Column(String(36), ForeignKey("change_events.id", ondelete="CASCADE"), nullable=True, index=True)
    agent_name = Column(String(100), nullable=False)
    proposal_payload = Column(JSON, nullable=False)
    reasoning = Column(JSON, nullable=True)
    status = Column(String(50), default="pending", nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    event = relationship("Event", back_populates="ai_suggestions")
    change_event = relationship("ChangeEvent", back_populates="suggestions")

