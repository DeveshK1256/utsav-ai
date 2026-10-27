import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import mapped_column, relationship

from backend.app.db.base import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    phone_number = mapped_column(String(20), unique=True, nullable=False, index=True)
    email = mapped_column(String(255), nullable=True)
    full_name = mapped_column(String(150), nullable=False)
    role = mapped_column(String(50), default="host", nullable=False)
    preferred_language = mapped_column(String(10), default="en", nullable=False)
    created_at = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)

    events = relationship("Event", back_populates="owner", cascade="all, delete-orphan")


class Tradition(Base):
    __tablename__ = "traditions"

    code = mapped_column(String(50), primary_key=True)
    regional_name = mapped_column(String(150), nullable=False)
    description = mapped_column(Text, nullable=True)
    cultural_notes = mapped_column(Text, nullable=True)
    is_verified = mapped_column(Boolean, default=False, nullable=False)
    verification_source = mapped_column(String(255), nullable=True)

    ritual_items = relationship("RitualItem", back_populates="tradition", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="tradition", foreign_keys="Event.tradition_code")


class RitualItem(Base):
    __tablename__ = "ritual_items"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    tradition_code = mapped_column(String(50), ForeignKey("traditions.code"), nullable=False, index=True)
    ritual_name = mapped_column(String(100), nullable=True)
    category = mapped_column(String(50), default="puja_samagri", nullable=True)
    item_name = mapped_column(String(150), nullable=False)
    regional_name = mapped_column(String(150), nullable=True)
    standard_quantity = mapped_column(String(100), nullable=False)
    spiritual_purpose = mapped_column(Text, nullable=True)
    is_verified = mapped_column(Boolean, default=False, nullable=False)

    tradition = relationship("Tradition", back_populates="ritual_items")


class Event(Base):
    __tablename__ = "events"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    owner_id = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = mapped_column(String(255), nullable=False)
    event_type = mapped_column(String(50), nullable=False)  # wedding, puja, community_festival, etc.
    tradition_code = mapped_column(String(50), ForeignKey("traditions.code"), nullable=True)
    secondary_tradition_code = mapped_column(String(50), ForeignKey("traditions.code"), nullable=True)
    guest_count = mapped_column(Integer, nullable=False)
    total_budget = mapped_column(Numeric(14, 2), nullable=False)
    city = mapped_column(String(100), nullable=False)
    pincode = mapped_column(String(10), nullable=False)
    start_date = mapped_column(Date, nullable=False)
    end_date = mapped_column(Date, nullable=False)
    status = mapped_column(String(50), default="planning", nullable=False, index=True)
    owner_token = mapped_column(String(64), nullable=True, index=True)
    venue_capacity = mapped_column(Integer, nullable=True)  # Manually-entered placeholder per DEC-016
    metadata_json = mapped_column(JSON, default=dict, nullable=False)
    created_at = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    __table_args__ = (
        CheckConstraint("guest_count > 0", name="check_positive_guest_count"),
        CheckConstraint("total_budget >= 0", name="check_non_negative_budget"),
        Index("idx_events_dates", "start_date", "end_date"),
    )

    owner = relationship("User", back_populates="events")
    tradition = relationship("Tradition", foreign_keys=[tradition_code], back_populates="events")
    secondary_tradition = relationship("Tradition", foreign_keys=[secondary_tradition_code])
    sub_events = relationship("SubEvent", back_populates="event", cascade="all, delete-orphan", order_by="SubEvent.sort_order")
    budget_items = relationship("BudgetItem", back_populates="event", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="event", cascade="all, delete-orphan")
    event_logs = relationship("EventLog", back_populates="event", cascade="all, delete-orphan")
    vendors = relationship("Vendor", back_populates="event", cascade="all, delete-orphan")
    quote_documents = relationship("QuoteDocument", back_populates="event", cascade="all, delete-orphan")
    change_events = relationship("ChangeEvent", back_populates="event", cascade="all, delete-orphan")
    ai_suggestions = relationship("AISuggestion", back_populates="event", cascade="all, delete-orphan")
    style_profiles = relationship("StyleProfile", back_populates="event", cascade="all, delete-orphan")
    guests = relationship("Guest", back_populates="event", cascade="all, delete-orphan")
    message_logs = relationship("MessageLog", back_populates="event", cascade="all, delete-orphan")
    fact_sheet = relationship("EventFactSheet", back_populates="event", uselist=False, cascade="all, delete-orphan")
    invitation_cards = relationship("InvitationCard", back_populates="event", cascade="all, delete-orphan")


class SubEvent(Base):
    __tablename__ = "sub_events"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    event_id = mapped_column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    name = mapped_column(String(150), nullable=False)
    start_time = mapped_column(DateTime, nullable=False)
    end_time = mapped_column(DateTime, nullable=False)
    venue_name = mapped_column(String(255), nullable=False)
    venue_address = mapped_column(Text, nullable=True)
    is_outdoor = mapped_column(Boolean, default=False, nullable=False)
    is_muhurat_locked = mapped_column(Boolean, default=False, nullable=False)
    muhurat_notes = mapped_column(Text, nullable=True)
    sort_order = mapped_column(Integer, default=0, nullable=False)

    event = relationship("Event", back_populates="sub_events")
    tasks = relationship("Task", back_populates="sub_event")


class BudgetItem(Base):
    __tablename__ = "budget_items"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    event_id = mapped_column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    vendor_id = mapped_column(String(36), nullable=True)
    category = mapped_column(String(100), nullable=False)
    name = mapped_column(String(255), nullable=False)
    scaling_rule = mapped_column(String(50), default="per_guest", nullable=False)  # per_guest, fixed, tiered per DEC-018
    planned_amount = mapped_column(Numeric(14, 2), nullable=False)
    actual_amount = mapped_column(Numeric(14, 2), default=0.00, nullable=False)
    is_paid = mapped_column(Boolean, default=False, nullable=False)
    reasoning_spec = mapped_column(JSON, nullable=True)
    created_at = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    event = relationship("Event", back_populates="budget_items")


class Task(Base):
    __tablename__ = "tasks"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    event_id = mapped_column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    sub_event_id = mapped_column(String(36), ForeignKey("sub_events.id", ondelete="SET NULL"), nullable=True, index=True)
    title = mapped_column(String(255), nullable=False)
    description = mapped_column(Text, nullable=True)
    status = mapped_column(String(50), default="pending", nullable=False)
    scheduled_start = mapped_column(DateTime, nullable=True)
    scheduled_end = mapped_column(DateTime, nullable=True)
    duration_minutes = mapped_column(Integer, nullable=True)
    dependency_task_ids = mapped_column(JSON, default=list, nullable=False)
    assigned_role = mapped_column(String(100), nullable=True)
    created_at = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    event = relationship("Event", back_populates="tasks")
    sub_event = relationship("SubEvent", back_populates="tasks")


class EventLog(Base):
    __tablename__ = "event_log"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    event_id = mapped_column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = mapped_column(String(100), nullable=False)
    diff_payload = mapped_column(JSON, nullable=False)
    actor_id = mapped_column(String(36), nullable=True)
    logged_at = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    event = relationship("Event", back_populates="event_logs")


class Vendor(Base):
    __tablename__ = "vendors"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    event_id = mapped_column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    business_name = mapped_column(String(255), nullable=False)
    category = mapped_column(String(100), nullable=False)
    contact_person = mapped_column(String(150), nullable=True)
    contact_phone = mapped_column(String(20), nullable=True)
    agreed_quote = mapped_column(Numeric(14, 2), nullable=True)
    advance_paid = mapped_column(Numeric(14, 2), default=0.00, nullable=False)
    contract_terms = mapped_column(JSON, default=dict, nullable=False)
    hidden_cost_alerts = mapped_column(JSON, default=list, nullable=False)
    rating = mapped_column(Integer, nullable=True)
    created_at = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    event = relationship("Event", back_populates="vendors")
    quotes = relationship("QuoteDocument", back_populates="vendor")


class QuoteDocument(Base):
    __tablename__ = "quote_documents"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    event_id = mapped_column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    vendor_id = mapped_column(String(36), ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True, index=True)
    vendor_name = mapped_column(String(200), nullable=False)
    category = mapped_column(String(50), nullable=False, index=True)
    file_name = mapped_column(String(255), nullable=False)
    file_type = mapped_column(String(100), nullable=False)
    uploaded_file = mapped_column(LargeBinary, nullable=False)  # Stored in DB bytea per DEC-017
    extraction_status = mapped_column(String(50), default="pending", nullable=False, index=True)
    raw_extracted_json = mapped_column(JSON, default=dict, nullable=False)
    total_quoted_amount = mapped_column(Numeric(14, 2), nullable=True)
    tax_amount = mapped_column(Numeric(14, 2), nullable=True)
    uploaded_at = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    event = relationship("Event", back_populates="quote_documents")
    vendor = relationship("Vendor", back_populates="quotes")
    line_items = relationship("QuoteLineItem", back_populates="quote_document", cascade="all, delete-orphan")


class QuoteLineItem(Base):
    __tablename__ = "quote_line_items"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    quote_document_id = mapped_column(String(36), ForeignKey("quote_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    name = mapped_column(String(255), nullable=False)
    qty = mapped_column(Numeric(10, 2), default=1.0, nullable=False)
    unit = mapped_column(String(50), default="units", nullable=False)
    unit_price = mapped_column(Numeric(14, 2), nullable=False)
    total = mapped_column(Numeric(14, 2), nullable=False)
    category_tag = mapped_column(String(50), nullable=True)
    notes = mapped_column(Text, nullable=True)

    quote_document = relationship("QuoteDocument", back_populates="line_items")


class VendorBenchmarkSample(Base):
    __tablename__ = "vendor_benchmark_samples"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    category = mapped_column(String(50), nullable=False, index=True)
    city_tier = mapped_column(String(20), nullable=False, index=True)
    normalized_unit_cost = mapped_column(Numeric(14, 2), nullable=False)
    source_event_id = mapped_column(String(36), ForeignKey("events.id", ondelete="SET NULL"), nullable=True)
    notes = mapped_column(String(255), nullable=True)
    created_at = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class ChangeEvent(Base):
    __tablename__ = "change_events"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    event_id = mapped_column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    change_type = mapped_column(String(50), nullable=False)  # guest_count_changed, vendor_cancelled, date_moved, budget_cut, venue_unavailable
    payload = mapped_column(JSON, nullable=False)
    status = mapped_column(String(50), default="pending", nullable=False, index=True)  # pending, queued, applied, rejected, blocked_infeasible
    created_at = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    event = relationship("Event", back_populates="change_events")
    suggestions = relationship("AISuggestion", back_populates="change_event", cascade="all, delete-orphan")


class AISuggestion(Base):
    __tablename__ = "ai_suggestions"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    event_id = mapped_column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    change_event_id = mapped_column(String(36), ForeignKey("change_events.id", ondelete="CASCADE"), nullable=True, index=True)
    agent_name = mapped_column(String(100), nullable=False)
    proposal_payload = mapped_column(JSON, nullable=False)
    reasoning = mapped_column(JSON, nullable=True)
    status = mapped_column(String(50), default="pending", nullable=False, index=True)
    created_at = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    event = relationship("Event", back_populates="ai_suggestions")
    change_event = relationship("ChangeEvent", back_populates="suggestions")


class StyleProfile(Base):
    __tablename__ = "style_profiles"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    event_id = mapped_column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    uploaded_image_refs = mapped_column(JSON, default=list, nullable=False)
    extracted_palette = mapped_column(JSON, default=list, nullable=False)  # Array of hex colors
    style_tags = mapped_column(JSON, default=list, nullable=False)
    mood_words = mapped_column(JSON, default=list, nullable=False)
    text_description = mapped_column(Text, nullable=True)
    created_at = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    event = relationship("Event", back_populates="style_profiles")
    uploaded_images = relationship("UploadedImage", back_populates="style_profile", cascade="all, delete-orphan")
    theme_proposals = relationship("ThemeProposal", back_populates="style_profile", cascade="all, delete-orphan")


class UploadedImage(Base):
    __tablename__ = "uploaded_images"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    style_profile_id = mapped_column(String(36), ForeignKey("style_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    image_data = mapped_column(LargeBinary, nullable=False)  # Stored directly as bytea per DEC-017
    content_type = mapped_column(String(100), nullable=False)
    uploaded_at = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    style_profile = relationship("StyleProfile", back_populates="uploaded_images")


class ThemeProposal(Base):
    __tablename__ = "theme_proposals"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    style_profile_id = mapped_column(String(36), ForeignKey("style_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    theme_name = mapped_column(String(255), nullable=False)
    palette = mapped_column(JSON, default=list, nullable=False)
    menu_direction = mapped_column(Text, nullable=True)
    playlist_genres = mapped_column(JSON, default=list, nullable=False)
    dress_code_suggestion = mapped_column(Text, nullable=True)
    invitation_design_brief = mapped_column(Text, nullable=True)
    status = mapped_column(String(50), default="proposed", nullable=False, index=True)  # proposed, accepted, rejected
    provider_used = mapped_column(String(100), default="gemini-3-flash-preview", nullable=True)
    fallback_warning = mapped_column(Text, nullable=True)
    created_at = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    style_profile = relationship("StyleProfile", back_populates="theme_proposals")
    decor_items = relationship("DecorItem", back_populates="theme_proposal", cascade="all, delete-orphan")


class DecorItem(Base):
    __tablename__ = "decor_items"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    theme_proposal_id = mapped_column(String(36), ForeignKey("theme_proposals.id", ondelete="CASCADE"), nullable=False, index=True)
    category = mapped_column(String(100), nullable=False)  # stage_backdrop, table_centerpiece, entrance_arch, lighting, photobooth, seating_lounges
    name = mapped_column(String(255), nullable=False)
    quantity_formula = mapped_column(Text, nullable=False)
    computed_quantity = mapped_column(Integer, default=1, nullable=False)
    cost_tier = mapped_column(String(50), default="medium", nullable=False)  # low, medium, high
    cost_range_low = mapped_column(Numeric(14, 2), nullable=False)
    cost_range_high = mapped_column(Numeric(14, 2), nullable=False)
    sourcing_type = mapped_column(String(50), default="rent", nullable=False)  # rent, diy, buy
    budget_item_id = mapped_column(String(36), ForeignKey("budget_items.id", ondelete="SET NULL"), nullable=True, index=True)
    task_id = mapped_column(String(36), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    status = mapped_column(String(50), default="proposed", nullable=False, index=True)  # proposed, accepted, rejected
    reasoning = mapped_column(JSON, default=dict, nullable=False)
    created_at = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    theme_proposal = relationship("ThemeProposal", back_populates="decor_items")
    budget_item = relationship("BudgetItem")
    task = relationship("Task")


class Guest(Base):
    __tablename__ = "guests"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    event_id = mapped_column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    name = mapped_column(String(150), nullable=False)
    phone = mapped_column(String(30), nullable=False, index=True)
    group_side = mapped_column(String(50), nullable=True)  # bride, groom, family, friends, society, general
    diet = mapped_column(String(50), default="veg", nullable=True)  # veg, jain, non_veg, vegan
    mobility_needs = mapped_column(Boolean, default=False, nullable=False)
    kids_count = mapped_column(Integer, default=0, nullable=False)
    headcount = mapped_column(Integer, default=1, nullable=False)
    rsvp_status = mapped_column(String(30), default="pending", nullable=False, index=True)  # pending, attending, declined, maybe
    accommodation = mapped_column(Boolean, default=False, nullable=False)
    language = mapped_column(String(10), default="en", nullable=False)
    notes = mapped_column(Text, nullable=True)
    needs_host_review = mapped_column(Boolean, default=False, nullable=False)
    created_at = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)

    __table_args__ = (
        Index("idx_guests_event_phone", "event_id", "phone", unique=True),
    )

    event = relationship("Event", back_populates="guests")
    messages = relationship("MessageLog", back_populates="guest", cascade="all, delete-orphan")


class MessageTemplate(Base):
    __tablename__ = "message_templates"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    template_name = mapped_column(String(100), unique=True, nullable=False, index=True)
    category = mapped_column(String(50), nullable=False)  # invitation, reminder, faq_response, update
    language = mapped_column(String(10), default="en", nullable=False)
    body_text = mapped_column(Text, nullable=False)
    meta_template_id = mapped_column(String(100), nullable=True)
    approval_status = mapped_column(String(50), default="approved", nullable=False)  # pending, approved, rejected
    created_at = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class MessageLog(Base):
    __tablename__ = "message_log"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    guest_id = mapped_column(String(36), ForeignKey("guests.id", ondelete="SET NULL"), nullable=True, index=True)
    event_id = mapped_column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    phone_number = mapped_column(String(30), nullable=False, index=True)
    direction = mapped_column(String(20), nullable=False)  # outbound, inbound
    message_type = mapped_column(String(30), nullable=False)  # template, freeform, quick_reply
    content_snapshot = mapped_column(Text, nullable=False)
    whatsapp_message_id = mapped_column(String(100), nullable=True, index=True)
    delivery_status = mapped_column(String(30), default="queued", nullable=False, index=True)  # queued, sent, delivered, read, failed
    failure_reason = mapped_column(Text, nullable=True)
    created_at = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False, index=True)

    guest = relationship("Guest", back_populates="messages")
    event = relationship("Event", back_populates="message_logs")


class EventFactSheet(Base):
    __tablename__ = "event_fact_sheets"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    event_id = mapped_column(String(36), ForeignKey("events.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    venue_address = mapped_column(Text, nullable=True)
    parking_info = mapped_column(Text, nullable=True)
    dress_code = mapped_column(Text, nullable=True)
    timing_notes = mapped_column(Text, nullable=True)
    map_link = mapped_column(String(500), nullable=True)
    other_facts = mapped_column(JSON, default=dict, nullable=False)
    created_at = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)

    event = relationship("Event", back_populates="fact_sheet")


class OptOut(Base):
    __tablename__ = "opt_outs"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    phone = mapped_column(String(30), unique=True, nullable=False, index=True)
    reason = mapped_column(String(100), default="STOP", nullable=False)
    opted_out_at = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class InvitationCard(Base):
    __tablename__ = "invitation_cards"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    event_id = mapped_column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    theme_proposal_id = mapped_column(String(36), ForeignKey("theme_proposals.id", ondelete="SET NULL"), nullable=True, index=True)
    layout_variant = mapped_column(String(50), nullable=False, default="classic_royal")
    wording_text = mapped_column(Text, nullable=False)
    guest_id = mapped_column(String(36), ForeignKey("guests.id", ondelete="CASCADE"), nullable=True, index=True)
    rendered_png = mapped_column(LargeBinary, nullable=True)
    rendered_pdf = mapped_column(LargeBinary, nullable=True)
    generated_at = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    event = relationship("Event", back_populates="invitation_cards")
    theme_proposal = relationship("ThemeProposal")
    guest = relationship("Guest")


class VendorProfile(Base):
    """
    Global vendor/venue directory profile (F15).
    Distinct from the per-event `Vendor` contract table.
    """
    __tablename__ = "vendor_profiles"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    business_name = mapped_column(String(200), nullable=False)
    category = mapped_column(String(50), nullable=False, index=True)  # venue, caterer, decorator, etc.
    latitude = mapped_column(Numeric(9, 6), nullable=True)
    longitude = mapped_column(Numeric(9, 6), nullable=True)
    service_area_radius_km = mapped_column(Integer, nullable=True)
    city = mapped_column(String(100), nullable=False, index=True)
    locality = mapped_column(String(150), nullable=True)
    city_tier = mapped_column(String(20), nullable=True)
    contact_phone = mapped_column(String(20), nullable=True)
    average_rating = mapped_column(Numeric(2, 1), default=None, nullable=True)  # NULL when unrated (DEC-013)
    rating_count = mapped_column(Integer, default=0, nullable=False)
    is_verified_profile = mapped_column(Boolean, default=False, nullable=False)
    coordinate_precision = mapped_column(String(50), default="locality_approximate", nullable=False)
    source_notes = mapped_column(Text, nullable=True)
    metadata_json = mapped_column(JSON, default=dict, nullable=False)
    created_at = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)





