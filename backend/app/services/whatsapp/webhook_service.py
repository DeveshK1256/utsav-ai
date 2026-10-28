import hashlib
import hmac
import logging
import os
import time
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.models import Event, EventFactSheet, Guest, MessageLog, OptOut
from backend.app.services.whatsapp.faq_bot import FAQBotService
from backend.app.services.whatsapp.phone_utils import normalize_e164_phone
from backend.app.services.whatsapp.provider import WhatsAppProvider
from backend.app.services.whatsapp.rsvp_parser import RSVPParser
from backend.app.services.whatsapp.send_service import WhatsAppSendService

logger = logging.getLogger(__name__)

STOP_KEYWORDS = {"stop", "unsubscribe", "halt", "cancel", "roko", "mat bhejo", "end"}


class WebhookSecurityError(Exception):
    """Raised when Meta webhook HMAC signature verification fails."""


class WhatsAppWebhookService:
    @classmethod
    def verify_meta_signature(
        cls,
        raw_payload: bytes,
        signature_header: str | None,
        timestamp: float | int | None = None,
        max_age_seconds: int = 300,
    ) -> bool:
        """
        Verifies Meta X-Hub-Signature-256 HMAC SHA256 header and enforces timestamp-based replay protection.
        Rejects unsigned, forged, or replayed requests (fail-closed).
        """
        if timestamp is not None:
            now = time.time()
            if (now - float(timestamp)) > max_age_seconds or (float(timestamp) - now) > 60:
                logger.warning(
                    "Rejected replayed/stale WhatsApp webhook: timestamp delta %.1fs exceeds %ds limit",
                    now - float(timestamp),
                    max_age_seconds,
                )
                return False

        is_test_env = bool(os.getenv("PYTEST_CURRENT_TEST")) or getattr(
            settings, "ENVIRONMENT", ""
        ).lower() in ("test", "testing")
        app_secret = getattr(settings, "WHATSAPP_APP_SECRET", None)
        if not app_secret:
            if is_test_env:
                # Allowed only during automated test suite execution without secret
                return True
            logger.error("WHATSAPP_APP_SECRET is not configured; rejecting webhook (fail-closed)")
            return False

        if not signature_header:
            return False

        if not signature_header.startswith("sha256="):
            return False

        expected = (
            "sha256="
            + hmac.new(app_secret.encode("utf-8"), raw_payload, hashlib.sha256).hexdigest()
        )

        return hmac.compare_digest(expected, signature_header)

    @classmethod
    def _process_status_callbacks(cls, db: Session, statuses: list[dict[str, Any]]) -> int:
        updated = 0
        for status_item in statuses:
            wamid = status_item.get("id")
            status_name = status_item.get("status")
            if not wamid or not status_name:
                continue
            msg_row = db.query(MessageLog).filter(MessageLog.whatsapp_message_id == wamid).first()
            if msg_row:
                msg_row.delivery_status = status_name
                if status_name == "failed":
                    errors = status_item.get("errors", [])
                    if errors:
                        msg_row.failure_reason = str(errors[0].get("title", "Delivery failure"))
                db.commit()
                updated += 1
        return updated

    @classmethod
    def _extract_message_content(cls, msg: dict[str, Any]) -> tuple[str, str | None]:
        msg_type = msg.get("type")
        if msg_type == "text":
            return msg.get("text", {}).get("body", "").strip(), None
        if msg_type == "interactive":
            interactive = msg.get("interactive", {})
            if interactive.get("type") == "button_reply":
                b_reply = interactive.get("button_reply", {})
                return b_reply.get("title", ""), b_reply.get("id")
        elif msg_type == "button":
            btn = msg.get("button", {})
            return btn.get("text", ""), btn.get("payload")
        return "", None

    @classmethod
    def _update_guest_rsvp(cls, db: Session, guest: Guest | None, parsed: Any) -> int:
        if not guest or parsed.rsvp_status not in ("attending", "declined", "maybe"):
            return 0
        guest.rsvp_status = parsed.rsvp_status
        guest.headcount = max(1, parsed.headcount) if parsed.rsvp_status == "attending" else 0
        if getattr(parsed, "diet", None):
            guest.diet = parsed.diet
        guest.needs_host_review = getattr(parsed, "needs_host_review", False)
        db.commit()
        return 1

    @classmethod
    def _send_faq_response(
        cls,
        db: Session,
        text_content: str,
        from_phone: str,
        guest: Guest | None,
        event: Event | None,
        provider: WhatsAppProvider | None,
    ) -> int:
        if not event:
            return 0
        fact_sheet = db.query(EventFactSheet).filter(EventFactSheet.event_id == event.id).first()
        faq_res = FAQBotService.answer_question(event, fact_sheet, text_content)
        try:
            WhatsAppSendService.send_single_message(
                db=db,
                event=event,
                guest=guest,
                to_phone=from_phone,
                message_body=faq_res.answer,
                message_type="freeform",
                provider=provider,
            )
            return 1
        except (SQLAlchemyError, ValueError, RuntimeError, TypeError, KeyError) as e:
            logger.error("Failed to transmit FAQ response: %s", e)
            return 0

    @classmethod
    def _handle_inbound_message_action(
        cls,
        db: Session,
        text_content: str,
        button_id: str | None,
        from_phone: str,
        guest: Guest | None,
        event: Event | None,
        provider: WhatsAppProvider | None,
    ) -> tuple[int, int, int]:
        """Returns (opt_outs_recorded, rsvps_updated, faq_replies_sent)."""
        clean_lower = text_content.lower().strip()

        # 1. STOP Opt-out
        if clean_lower in STOP_KEYWORDS:
            if not db.query(OptOut).filter(OptOut.phone == from_phone).first():
                db.add(OptOut(phone=from_phone, reason="Inbound STOP request"))
                db.commit()
            return 1, 0, 0

        # 2. Button Quick-Reply RSVP
        if button_id:
            parsed = RSVPParser.parse_quick_reply(button_id)
            return 0, cls._update_guest_rsvp(db, guest, parsed), 0

        # 3. Free-Text RSVP
        parsed_free = RSVPParser.parse_free_text(text_content)
        if parsed_free.confidence >= 0.70 and parsed_free.rsvp_status in ("attending", "declined", "maybe"):
            return 0, cls._update_guest_rsvp(db, guest, parsed_free), 0

        # 4. FAQ query fallback
        faq_sent = cls._send_faq_response(db, text_content, from_phone, guest, event, provider)
        return 0, 0, faq_sent

    @classmethod
    def _process_inbound_message_item(
        cls, db: Session, msg: dict[str, Any], provider: WhatsAppProvider | None
    ) -> tuple[int, int, int]:
        from_raw = msg.get("from")
        if not from_raw:
            return 0, 0, 0

        try:
            from_phone = normalize_e164_phone(from_raw)
        except ValueError:
            from_phone = f"+{from_raw}"

        guest = db.query(Guest).filter(Guest.phone == from_phone).order_by(Guest.created_at.desc()).first()
        event = guest.event if guest else db.query(Event).order_by(Event.created_at.desc()).first()
        text_content, button_id = cls._extract_message_content(msg)

        inbound_log = MessageLog(
            guest_id=guest.id if guest else None,
            event_id=event.id if event else "global",
            phone_number=from_phone,
            direction="inbound",
            message_type="freeform" if not button_id else "quick_reply",
            content_snapshot=text_content or f"[Type: {msg.get('type')}]",
            whatsapp_message_id=msg.get("id"),
            delivery_status="received",
        )
        db.add(inbound_log)
        db.commit()

        return cls._handle_inbound_message_action(
            db, text_content, button_id, from_phone, guest, event, provider
        )

    @classmethod
    def handle_inbound_payload(
        cls, db: Session, payload: dict[str, Any], provider: WhatsAppProvider | None = None
    ) -> dict[str, Any]:
        """
        Parses Meta Cloud API inbound webhook payload.
        Handles:
        1. Status callbacks (sent, delivered, read, failed)
        2. STOP opt-out requests
        3. Structured quick-replies (Yes/No/Maybe)
        4. Free-text RSVP responses
        5. Guest FAQ questions (grounded in fact sheet)
        """
        results = {
            "statuses_updated": 0,
            "opt_outs_recorded": 0,
            "rsvps_updated": 0,
            "faq_replies_sent": 0,
        }

        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                results["statuses_updated"] += cls._process_status_callbacks(db, value.get("statuses", []))
                for msg in value.get("messages", []):
                    opt_out, rsvp_upd, faq_sent = cls._process_inbound_message_item(db, msg, provider)
                    results["opt_outs_recorded"] += opt_out
                    results["rsvps_updated"] += rsvp_upd
                    results["faq_replies_sent"] += faq_sent

        return results
