import csv
import io
import logging
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.models.models import Event, Guest
from backend.app.services.whatsapp.phone_utils import validate_and_normalize_guest_phone

logger = logging.getLogger(__name__)


class GuestImportError(BaseModel):
    row_number: int
    name: str | None = None
    phone_raw: str | None = None
    reason: str


class GuestImportResponse(BaseModel):
    total_processed: int
    successful_count: int
    skipped_duplicates_count: int
    invalid_rows_count: int
    imported_guests: list[dict[str, Any]]
    errors: list[GuestImportError]


class RSVPSummary(BaseModel):
    total_guests: int
    attending_count: int
    declined_count: int
    maybe_count: int
    pending_count: int
    total_confirmed_headcount: int
    diet_breakdown: dict[str, int]
    mobility_needs_count: int
    kids_count: int
    accommodation_needed_count: int


class GuestService:
    @classmethod
    def import_guest_rows(
        cls, db: Session, event_id: str, rows: list[dict[str, Any]]
    ) -> GuestImportResponse:
        """
        Validates, normalizes, and ingests guest rows.
        - Deduplicates within batch and against existing event guests.
        - Rejects unparseable phone numbers with explicit error reporting.
        """
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise ValueError(f"Event {event_id} not found")

        # Pre-fetch existing guest phones for this event to dedupe
        existing_phones = {
            g.phone for g in db.query(Guest.phone).filter(Guest.event_id == event_id).all()
        }

        successful = []
        errors: list[GuestImportError] = []
        skipped_duplicates = 0
        seen_batch_phones = set()

        for idx, row in enumerate(rows, start=1):
            name = str(row.get("name") or row.get("full_name") or "").strip()
            phone_raw = str(row.get("phone") or row.get("phone_number") or "").strip()

            if not name:
                errors.append(
                    GuestImportError(
                        row_number=idx,
                        name=name,
                        phone_raw=phone_raw,
                        reason="Guest name is required",
                    )
                )
                continue

            if not phone_raw:
                errors.append(
                    GuestImportError(
                        row_number=idx,
                        name=name,
                        phone_raw=phone_raw,
                        reason="Phone number is required",
                    )
                )
                continue

            # Validate & normalize phone to E.164
            is_valid, norm_phone, err_msg = validate_and_normalize_guest_phone(phone_raw)
            if not is_valid or not norm_phone:
                errors.append(
                    GuestImportError(
                        row_number=idx,
                        name=name,
                        phone_raw=phone_raw,
                        reason=err_msg or "Invalid phone number format",
                    )
                )
                continue

            # Deduplication Check
            if norm_phone in existing_phones or norm_phone in seen_batch_phones:
                skipped_duplicates += 1
                continue

            seen_batch_phones.add(norm_phone)

            # Parse optional fields
            group_side = str(row.get("group_side") or row.get("side") or "general").strip().lower()
            diet = str(row.get("diet") or row.get("dietary_preference") or "veg").strip().lower()
            if diet not in ("veg", "jain", "non_veg", "vegan"):
                diet = "veg"

            kids = 0
            try:
                kids = int(row.get("kids_count") or row.get("kids") or 0)
            except (ValueError, TypeError):
                kids = 0

            headcount = 1 + kids
            try:
                if row.get("headcount"):
                    headcount = max(1, int(str(row.get("headcount") or 1)))
            except (ValueError, TypeError):
                pass

            mobility = bool(
                str(row.get("mobility_needs") or "").lower() in ("true", "1", "yes", "wheelchair")
            )
            accommodation = bool(
                str(row.get("accommodation") or "").lower() in ("true", "1", "yes")
            )
            language = str(row.get("language") or "en").strip().lower()[:10]
            notes = str(row.get("notes") or "").strip() or None

            guest = Guest(
                event_id=event_id,
                name=name,
                phone=norm_phone,
                group_side=group_side,
                diet=diet,
                mobility_needs=mobility,
                kids_count=kids,
                headcount=headcount,
                rsvp_status="pending",
                accommodation=accommodation,
                language=language,
                notes=notes,
            )
            db.add(guest)
            successful.append(
                {
                    "name": name,
                    "phone": norm_phone,
                    "group_side": group_side,
                    "diet": diet,
                    "headcount": headcount,
                }
            )

        db.commit()

        return GuestImportResponse(
            total_processed=len(rows),
            successful_count=len(successful),
            skipped_duplicates_count=skipped_duplicates,
            invalid_rows_count=len(errors),
            imported_guests=successful,
            errors=errors,
        )

    @classmethod
    def parse_csv_file(cls, csv_text: str) -> list[dict[str, Any]]:
        """Parses CSV text into a list of row dicts."""
        reader = csv.DictReader(io.StringIO(csv_text.strip()))
        rows = []
        for row in reader:
            clean_row = {k.strip().lower(): v.strip() for k, v in row.items() if k}
            rows.append(clean_row)
        return rows

    @classmethod
    def get_rsvp_summary(cls, db: Session, event_id: str) -> RSVPSummary:
        """Computes deterministic RSVP metrics across confirmed guests."""
        guests = db.query(Guest).filter(Guest.event_id == event_id).all()

        total = len(guests)
        attending = 0
        declined = 0
        maybe = 0
        pending = 0
        confirmed_headcount = 0
        diet_counts = {"veg": 0, "jain": 0, "non_veg": 0, "vegan": 0}
        mobility_count = 0
        total_kids = 0
        accommodation_count = 0

        for g in guests:
            status = (g.rsvp_status or "pending").lower()
            if status == "attending":
                attending += 1
                confirmed_headcount += max(1, g.headcount)
                total_kids += g.kids_count
                d = (g.diet or "veg").lower()
                diet_counts[d] = diet_counts.get(d, 0) + max(1, g.headcount)
            elif status == "declined":
                declined += 1
            elif status == "maybe":
                maybe += 1
            else:
                pending += 1

            if g.mobility_needs:
                mobility_count += 1
            if g.accommodation:
                accommodation_count += 1

        return RSVPSummary(
            total_guests=total,
            attending_count=attending,
            declined_count=declined,
            maybe_count=maybe,
            pending_count=pending,
            total_confirmed_headcount=confirmed_headcount,
            diet_breakdown=diet_counts,
            mobility_needs_count=mobility_count,
            kids_count=total_kids,
            accommodation_needed_count=accommodation_count,
        )

    @classmethod
    def delete_guest_privacy_purge(cls, db: Session, event_id: str, guest_id: str) -> bool:
        """Purges guest data on request per privacy and data-deletion policies."""
        guest = db.query(Guest).filter(Guest.id == guest_id, Guest.event_id == event_id).first()
        if not guest:
            return False

        db.delete(guest)
        db.commit()
        return True
