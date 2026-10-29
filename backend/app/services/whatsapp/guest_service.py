import csv
import io
import logging
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.models.models import Event, Guest
from backend.app.services.whatsapp.phone_utils import validate_and_normalize_guest_phone

logger = logging.getLogger(__name__)


class GuestImportRow(BaseModel):
    name: str
    phone: str
    group_side: str = "general"
    diet: str = "veg"
    headcount: int = 1
    kids_count: int = 0
    mobility_needs: bool = False
    accommodation: bool = False
    language: str = "en"
    notes: str | None = None


class GuestImportError(BaseModel):
    row_number: int
    name: str
    phone_raw: str
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
    def _validate_guest_identity(
        cls, idx: int, name: str, phone_raw: str
    ) -> tuple[str | None, GuestImportError | None]:
        if not name:
            return None, GuestImportError(
                row_number=idx, name=name, phone_raw=phone_raw, reason="Guest name is required"
            )
        if not phone_raw:
            return None, GuestImportError(
                row_number=idx, name=name, phone_raw=phone_raw, reason="Phone number is required"
            )
        is_valid, norm_phone, err_msg = validate_and_normalize_guest_phone(phone_raw)
        if not is_valid or not norm_phone:
            return None, GuestImportError(
                row_number=idx,
                name=name,
                phone_raw=phone_raw,
                reason=err_msg or "Invalid phone number format",
            )
        return norm_phone, None

    @classmethod
    def _parse_kids(cls, row: dict[str, Any]) -> int:
        val = row.get("kids_count") or row.get("kids") or 0
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0

    @classmethod
    def _parse_headcount(cls, row: dict[str, Any], kids: int) -> int:
        val = row.get("headcount")
        if not val:
            return 1 + kids
        try:
            return max(1, int(str(val)))
        except (ValueError, TypeError):
            return 1 + kids

    @classmethod
    def _parse_diet(cls, row: dict[str, Any]) -> str:
        raw = str(row.get("diet") or row.get("dietary_preference") or "veg").strip().lower()
        return raw if raw in ("veg", "jain", "non_veg", "vegan") else "veg"

    @classmethod
    def _parse_guest_attributes(cls, row: dict[str, Any]) -> dict[str, Any]:
        group_side = str(row.get("group_side") or row.get("side") or "general").strip().lower()
        diet = cls._parse_diet(row)
        kids = cls._parse_kids(row)
        headcount = cls._parse_headcount(row, kids)

        mobility = bool(
            str(row.get("mobility_needs") or "").lower() in ("true", "1", "yes", "wheelchair")
        )
        accommodation = bool(str(row.get("accommodation") or "").lower() in ("true", "1", "yes"))
        language = str(row.get("language") or "en").strip().lower()[:10]
        notes = str(row.get("notes") or "").strip() or None

        return {
            "group_side": group_side,
            "diet": diet,
            "kids_count": kids,
            "headcount": headcount,
            "mobility_needs": mobility,
            "accommodation": accommodation,
            "language": language,
            "notes": notes,
        }

    @classmethod
    def _process_guest_row(
        cls,
        event_id: str,
        idx: int,
        row: dict[str, Any],
        existing_phones: set[str],
        seen_batch_phones: set[str],
    ) -> tuple[Guest | None, dict[str, Any] | None, GuestImportError | None, bool]:
        name = str(row.get("name") or row.get("full_name") or "").strip()
        phone_raw = str(row.get("phone") or row.get("phone_number") or "").strip()

        norm_phone, err = cls._validate_guest_identity(idx, name, phone_raw)
        if err or not norm_phone:
            return None, None, err, False

        if norm_phone in existing_phones or norm_phone in seen_batch_phones:
            return None, None, None, True

        seen_batch_phones.add(norm_phone)
        attrs = cls._parse_guest_attributes(row)

        guest = Guest(
            event_id=event_id,
            name=name,
            phone=norm_phone,
            rsvp_status="pending",
            **attrs,
        )
        succ = {
            "name": name,
            "phone": norm_phone,
            "group_side": attrs["group_side"],
            "diet": attrs["diet"],
            "headcount": attrs["headcount"],
        }
        return guest, succ, None, False

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
            err_msg = f"Event {event_id} not found"
            raise ValueError(err_msg)

        existing_phones = {
            g.phone for g in db.query(Guest.phone).filter(Guest.event_id == event_id).all()
        }

        successful = []
        errors: list[GuestImportError] = []
        skipped_duplicates = 0
        seen_batch_phones: set[str] = set()

        for idx, row in enumerate(rows, start=1):
            guest, succ, err, is_dup = cls._process_guest_row(
                event_id, idx, row, existing_phones, seen_batch_phones
            )
            if is_dup:
                skipped_duplicates += 1
            elif err:
                errors.append(err)
            elif guest and succ:
                db.add(guest)
                successful.append(succ)

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
