import logging
import time

from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models.models import Event, Guest, MessageLog, OptOut
from backend.app.services.whatsapp.phone_utils import normalize_e164_phone
from backend.app.services.whatsapp.provider import (
    WhatsAppProvider,
    WhatsAppSendResult,
    get_whatsapp_provider,
)

logger = logging.getLogger(__name__)


class OptOutBlockedError(Exception):
    """Raised when an outbound WhatsApp send is attempted to a phone number in opt_outs."""


class BatchSendResult(BaseModel):
    total_requested: int
    sent_count: int
    blocked_opt_out_count: int
    failed_count: int
    message_ids: list[str]
    errors: list[dict[str, str]]


class WhatsAppSendService:
    """
    Orchestrates outbound WhatsApp communications.
    Enforces non-negotiable send-layer opt-out checks before every transmission.
    """

    @classmethod
    def get_event_invitation_text(cls, event: Event, guest: Guest) -> str:
        """Adapts invitation tone based on celebration event_type (wedding/birthday/community)."""
        guest_name = guest.name
        event_name = event.name
        host_name = event.owner.full_name if event.owner else "The Host"
        date_str = event.start_date.strftime("%d %B %Y")
        city = event.city

        if event.event_type == "birthday":
            return (
                f"Hey {guest_name}! 🎂 You're invited to celebrate {event_name} with {host_name} "
                f"on {date_str} in {city}. Please RSVP to help us plan the party! "
                "Reply 'Yes', 'No', or 'Maybe'."
            )
        elif event.event_type in ("community_festival", "puja"):
            return (
                f"Namaste {guest_name}! 🙏 {host_name} warmly invites you and your family "
                f"to {event_name} on {date_str} in {city}. "
                "Please confirm your attendance for prasad/seating arrangements."
            )
        else:  # Wedding / general
            return (
                f"Namaste {guest_name}! 🌸 With the blessings of our elders, {host_name} "
                f"joyfully invites you to celebrate {event_name} on {date_str} in {city}. "
                "Please reply 'Yes' or 'No' to RSVP."
            )

    @classmethod
    def _enforce_opt_out(
        cls,
        db: Session,
        event_id: str,
        guest_id: str | None,
        norm_phone: str,
        message_type: str,
        message_body: str,
    ) -> None:
        opted_out = db.query(OptOut).filter(OptOut.phone == norm_phone).first()
        if not opted_out:
            return
        logger.warning(f"Blocked outbound WhatsApp send to opted-out phone: {norm_phone}")
        log_entry = MessageLog(
            guest_id=guest_id,
            event_id=event_id,
            phone_number=norm_phone,
            direction="outbound",
            message_type=message_type,
            content_snapshot=message_body,
            whatsapp_message_id=None,
            delivery_status="failed",
            failure_reason=f"recipient_opted_out at {opted_out.opted_out_at.isoformat()}",
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        raise OptOutBlockedError(
            f"Phone {norm_phone} has opted out (STOP) and cannot be contacted."
        )

    @classmethod
    def _dispatch_provider_message(
        cls,
        active_provider: WhatsAppProvider,
        norm_phone: str,
        template_name: str | None,
        guest: Guest | None,
        event: Event,
        message_body: str,
    ) -> WhatsAppSendResult:
        if template_name:
            return active_provider.send_template(
                to_phone=norm_phone,
                template_name=template_name,
                language=guest.language if guest else "en",
                parameters=[guest.name if guest else "Guest", event.name],
            )
        buttons = [
            {"id": "yes", "title": "Attending"},
            {"id": "no", "title": "Decline"},
            {"id": "maybe", "title": "Maybe"},
        ]
        return active_provider.send_interactive_buttons(
            to_phone=norm_phone, body=message_body, buttons=buttons
        )

    @classmethod
    def send_single_message(
        cls,
        db: Session,
        event: Event,
        guest: Guest | None,
        to_phone: str,
        message_body: str,
        message_type: str = "freeform",
        template_name: str | None = None,
        provider: WhatsAppProvider | None = None,
    ) -> MessageLog:
        """
        Sends an individual message.
        MANDATORY SEND-LAYER CHECK: If to_phone exists in opt_outs, the send is HARD-BLOCKED.
        """
        norm_phone = normalize_e164_phone(to_phone)
        active_provider = provider or get_whatsapp_provider()

        # 1. Non-negotiable Opt-Out Guard
        guest_id = guest.id if guest else None
        cls._enforce_opt_out(db, event.id, guest_id, norm_phone, message_type, message_body)

        # 2. Transmit via Provider
        res = cls._dispatch_provider_message(
            active_provider, norm_phone, template_name, guest, event, message_body
        )

        # 3. Log Audit Trail
        log_entry = MessageLog(
            guest_id=guest_id,
            event_id=event.id,
            phone_number=norm_phone,
            direction="outbound",
            message_type=message_type,
            content_snapshot=message_body,
            whatsapp_message_id=res.message_id if res.success else None,
            delivery_status=res.status if res.success else "failed",
            failure_reason=res.error if not res.success else None,
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

    @classmethod
    def send_batch_invitations(
        cls,
        db: Session,
        event_id: str,
        guest_ids: list[str] | None = None,
        provider: WhatsAppProvider | None = None,
        rate_limit_delay_secs: float = 0.05,
    ) -> BatchSendResult:
        """
        Sends invitations in batch to guests of an event.
        Checks opt_outs before every single send and respects rate limits.
        """
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise ValueError(f"Event {event_id} not found")

        query = db.query(Guest).filter(Guest.event_id == event_id)
        if guest_ids:
            query = query.filter(Guest.id.in_(guest_ids))
        guests = query.all()

        total = len(guests)
        sent = 0
        blocked = 0
        failed = 0
        msg_ids = []
        errors = []

        for guest in guests:
            msg_text = cls.get_event_invitation_text(event, guest)
            try:
                log = cls.send_single_message(
                    db=db,
                    event=event,
                    guest=guest,
                    to_phone=guest.phone,
                    message_body=msg_text,
                    message_type="interactive_button",
                    provider=provider,
                )
                if log.delivery_status in ("sent", "delivered", "read", "queued"):
                    sent += 1
                    if log.whatsapp_message_id:
                        msg_ids.append(log.whatsapp_message_id)
                else:
                    failed += 1
                    errors.append(
                        {"phone": guest.phone, "error": log.failure_reason or "Send failed"}
                    )
            except OptOutBlockedError as e:
                blocked += 1
                errors.append({"phone": guest.phone, "error": str(e)})
            except (SQLAlchemyError, ValueError, RuntimeError, TypeError, KeyError) as e:
                failed += 1
                errors.append({"phone": guest.phone, "error": str(e)})

            # Rate limit pacing
            if rate_limit_delay_secs > 0:
                time.sleep(rate_limit_delay_secs)

        return BatchSendResult(
            total_requested=total,
            sent_count=sent,
            blocked_opt_out_count=blocked,
            failed_count=failed,
            message_ids=msg_ids,
            errors=errors,
        )
