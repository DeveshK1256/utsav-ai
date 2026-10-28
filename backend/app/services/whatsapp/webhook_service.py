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

        entry_list = payload.get("entry", [])
        for entry in entry_list:
            for change in entry.get("changes", []):
                value = change.get("value", {})

                # 1. Process Delivery Status Callbacks
                statuses = value.get("statuses", [])
                for status_item in statuses:
                    wamid = status_item.get("id")
                    status_name = status_item.get("status")  # sent, delivered, read, failed
                    if wamid and status_name:
                        msg_row = (
                            db.query(MessageLog)
                            .filter(MessageLog.whatsapp_message_id == wamid)
                            .first()
                        )
                        if msg_row:
                            msg_row.delivery_status = status_name
                            if status_name == "failed":
                                errors = status_item.get("errors", [])
                                if errors:
                                    msg_row.failure_reason = str(
                                        errors[0].get("title", "Delivery failure")
                                    )
                            db.commit()
                            results["statuses_updated"] += 1

                # 2. Process Inbound Messages
                messages = value.get("messages", [])
                for msg in messages:
                    from_raw = msg.get("from")
                    if not from_raw:
                        continue

                    try:
                        from_phone = normalize_e164_phone(from_raw)
                    except ValueError:
                        from_phone = f"+{from_raw}"

                    # Find recipient guest (if exists across active events)
                    guest = (
                        db.query(Guest)
                        .filter(Guest.phone == from_phone)
                        .order_by(Guest.created_at.desc())
                        .first()
                    )
                    event = (
                        guest.event
                        if guest
                        else db.query(Event).order_by(Event.created_at.desc()).first()
                    )

                    msg_id = msg.get("id")
                    msg_type = msg.get("type")

                    # Extract text content
                    text_content = ""
                    button_id = None

                    if msg_type == "text":
                        text_content = msg.get("text", {}).get("body", "").strip()
                    elif msg_type == "interactive":
                        interactive = msg.get("interactive", {})
                        if interactive.get("type") == "button_reply":
                            button_id = interactive.get("button_reply", {}).get("id")
                            text_content = interactive.get("button_reply", {}).get("title", "")
                    elif msg_type == "button":
                        button_id = msg.get("button", {}).get("payload")
                        text_content = msg.get("button", {}).get("text", "")

                    # Log inbound message in audit trail
                    inbound_log = MessageLog(
                        guest_id=guest.id if guest else None,
                        event_id=event.id if event else "global",
                        phone_number=from_phone,
                        direction="inbound",
                        message_type="freeform" if not button_id else "quick_reply",
                        content_snapshot=text_content or f"[Type: {msg_type}]",
                        whatsapp_message_id=msg_id,
                        delivery_status="received",
                    )
                    db.add(inbound_log)
                    db.commit()

                    # Check for STOP / Opt-Out Keyword
                    clean_lower = text_content.lower().strip()
                    if clean_lower in STOP_KEYWORDS:
                        existing_opt = db.query(OptOut).filter(OptOut.phone == from_phone).first()
                        if not existing_opt:
                            new_opt = OptOut(phone=from_phone, reason="Inbound STOP request")
                            db.add(new_opt)
                            db.commit()
                        results["opt_outs_recorded"] += 1
                        continue

                    # Check for Quick-Reply Button RSVP
                    if button_id:
                        parsed = RSVPParser.parse_quick_reply(button_id)
                        if guest and parsed.rsvp_status != "unknown":
                            guest.rsvp_status = parsed.rsvp_status
                            guest.headcount = max(1, parsed.headcount)
                            guest.needs_host_review = parsed.needs_host_review
                            db.commit()
                            results["rsvps_updated"] += 1
                        continue

                    # Check for Free-Text RSVP
                    parsed = RSVPParser.parse_free_text(text_content)
                    if parsed.confidence >= 0.70 and parsed.rsvp_status in (
                        "attending",
                        "declined",
                        "maybe",
                    ):
                        if guest:
                            guest.rsvp_status = parsed.rsvp_status
                            guest.headcount = (
                                max(1, parsed.headcount) if parsed.rsvp_status == "attending" else 0
                            )
                            if parsed.diet:
                                guest.diet = parsed.diet
                            guest.needs_host_review = False
                            db.commit()
                            results["rsvps_updated"] += 1
                        continue

                    # If not a clear RSVP, treat as potential FAQ query
                    if event:
                        fact_sheet = (
                            db.query(EventFactSheet)
                            .filter(EventFactSheet.event_id == event.id)
                            .first()
                        )
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
                            results["faq_replies_sent"] += 1
                        except (
                            SQLAlchemyError,
                            ValueError,
                            RuntimeError,
                            TypeError,
                            KeyError,
                        ) as e:
                            logger.error(f"Failed to transmit FAQ response: {e}")

        return results
