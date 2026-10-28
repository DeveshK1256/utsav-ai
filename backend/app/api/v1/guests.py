import logging

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from backend.app.core.security import verify_event_owner_token
from backend.app.db.session import get_db
from backend.app.models.models import Event, EventFactSheet, Guest
from backend.app.schemas.guests import (
    DeleteGuestResponseSchema,
    FactSheetResponseSchema,
    FactSheetSchema,
    GuestImportRequest,
    GuestItemResponse,
)
from backend.app.services.whatsapp.guest_service import (
    GuestImportResponse,
    GuestService,
    RSVPSummary,
)
from backend.app.services.whatsapp.reminder_scheduler import (
    ReminderScheduler,
    ScheduledReminderPlan,
)
from backend.app.services.whatsapp.send_service import (
    BatchSendResult,
    WhatsAppSendService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["Guests & Coordination"])


@router.post("/{event_id}/guests/import", response_model=GuestImportResponse)
def import_guests(
    event_id: str,
    payload: GuestImportRequest | None = None,
    event: Event = Depends(verify_event_owner_token),
    db: Session = Depends(get_db)
) -> GuestImportResponse:
    """
    Imports, validates, and normalizes guest rows for an event.
    Deduplicates by phone and rejects unparseable phone numbers with explicit feedback.
    """
    rows = [g.model_dump() for g in payload.guests] if payload and payload.guests else []
    return GuestService.import_guest_rows(db, event_id, rows)


@router.post("/{event_id}/guests/import-csv", response_model=GuestImportResponse)
async def import_guests_csv(
    event_id: str,
    file: UploadFile = File(...),
    event: Event = Depends(verify_event_owner_token),
    db: Session = Depends(get_db)
) -> GuestImportResponse:
    """
    Imports guests via CSV file upload.
    """
    contents = await file.read()
    text = contents.decode("utf-8-sig", errors="ignore")
    rows = GuestService.parse_csv_file(text)
    return GuestService.import_guest_rows(db, event_id, rows)


@router.get("/{event_id}/guests", response_model=list[GuestItemResponse])
def list_guests(
    event_id: str,
    status: str | None = Query(None),
    db: Session = Depends(get_db)
) -> list[GuestItemResponse]:
    """Lists all guests for an event with optional RSVP status filter."""
    query = db.query(Guest).filter(Guest.event_id == event_id)
    if status:
        query = query.filter(Guest.rsvp_status == status)
    guests = query.order_by(Guest.name.asc()).all()

    return [
        GuestItemResponse(
            id=g.id,
            name=g.name,
            phone=g.phone,
            group_side=g.group_side,
            diet=g.diet,
            mobility_needs=g.mobility_needs,
            kids_count=g.kids_count,
            headcount=g.headcount,
            rsvp_status=g.rsvp_status,
            accommodation=g.accommodation,
            language=g.language,
            notes=g.notes,
            needs_host_review=g.needs_host_review,
            created_at=g.created_at.isoformat()
        )
        for g in guests
    ]


@router.get("/{event_id}/guests/rsvp-summary", response_model=RSVPSummary)
def get_rsvp_summary(
    event_id: str,
    db: Session = Depends(get_db)
) -> RSVPSummary:
    """Deterministic live RSVP metrics for the event dashboard."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return GuestService.get_rsvp_summary(db, event_id)


@router.post("/{event_id}/guests/send-invitations", response_model=BatchSendResult)
def send_invitations(
    event_id: str,
    guest_ids: list[str] | None = None,
    event: Event = Depends(verify_event_owner_token),
    db: Session = Depends(get_db)
) -> BatchSendResult:
    """
    Batch-sends WhatsApp invitations to guests.
    Enforces opt_out verification before every send.
    """
    return WhatsAppSendService.send_batch_invitations(db, event_id, guest_ids)


@router.delete("/{event_id}/guests/{guest_id}", response_model=DeleteGuestResponseSchema)
def delete_guest(
    event_id: str,
    guest_id: str,
    event: Event = Depends(verify_event_owner_token),
    db: Session = Depends(get_db)
) -> DeleteGuestResponseSchema:
    """Purges guest data on request per privacy and data-deletion policies."""
    success = GuestService.delete_guest_privacy_purge(db, event_id, guest_id)
    if not success:
        raise HTTPException(status_code=404, detail="Guest not found")
    return DeleteGuestResponseSchema(status="purged", guest_id=guest_id)


@router.get("/{event_id}/fact-sheet", response_model=FactSheetResponseSchema)
def get_fact_sheet(
    event_id: str,
    db: Session = Depends(get_db)
) -> FactSheetResponseSchema:
    """Retrieves the verified event fact sheet (only source for guest FAQ bot)."""
    fs = db.query(EventFactSheet).filter(EventFactSheet.event_id == event_id).first()
    if not fs:
        return FactSheetResponseSchema(
            event_id=event_id,
            venue_address=None,
            parking_info=None,
            dress_code=None,
            timing_notes=None,
            map_link=None,
            other_facts={}
        )
    return FactSheetResponseSchema(
        event_id=fs.event_id,
        venue_address=fs.venue_address,
        parking_info=fs.parking_info,
        dress_code=fs.dress_code,
        timing_notes=fs.timing_notes,
        map_link=fs.map_link,
        other_facts=fs.other_facts or {}
    )


@router.post("/{event_id}/fact-sheet", response_model=FactSheetResponseSchema)
def update_fact_sheet(
    event_id: str,
    payload: FactSheetSchema,
    event: Event = Depends(verify_event_owner_token),
    db: Session = Depends(get_db)
) -> FactSheetResponseSchema:
    """Creates or updates the verified event fact sheet."""
    fs = db.query(EventFactSheet).filter(EventFactSheet.event_id == event_id).first()
    if not fs:
        fs = EventFactSheet(
            event_id=event_id,
            venue_address=payload.venue_address,
            parking_info=payload.parking_info,
            dress_code=payload.dress_code,
            timing_notes=payload.timing_notes,
            map_link=payload.map_link,
            other_facts=payload.other_facts or {}
        )
        db.add(fs)
    else:
        if payload.venue_address is not None:
            fs.venue_address = payload.venue_address
        if payload.parking_info is not None:
            fs.parking_info = payload.parking_info
        if payload.dress_code is not None:
            fs.dress_code = payload.dress_code
        if payload.timing_notes is not None:
            fs.timing_notes = payload.timing_notes
        if payload.map_link is not None:
            fs.map_link = payload.map_link
        if payload.other_facts is not None:
            fs.other_facts = payload.other_facts

    db.commit()
    return FactSheetResponseSchema(
        event_id=event_id,
        venue_address=fs.venue_address,
        parking_info=fs.parking_info,
        dress_code=fs.dress_code,
        timing_notes=fs.timing_notes,
        map_link=fs.map_link,
        other_facts=fs.other_facts or {}
    )


@router.get("/{event_id}/reminders", response_model=list[ScheduledReminderPlan])
def get_reminder_schedule(
    event_id: str,
    db: Session = Depends(get_db)
) -> list[ScheduledReminderPlan]:
    """Returns deterministic scheduled reminders for all sub-events in an event."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return ReminderScheduler.generate_event_reminder_plans(event, event.sub_events)
