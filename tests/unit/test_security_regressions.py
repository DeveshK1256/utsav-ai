import asyncio
import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from backend.app.core.config import Settings
from backend.app.core.security import _resolve_expected_token
from backend.app.main import MAX_REQUEST_BODY_BYTES, RequestSizeLimitMiddleware, app
from backend.app.models.models import Event, Guest, MessageLog, OptOut, User
from backend.app.services.whatsapp.webhook_service import WhatsAppWebhookService
from backend.app.services.whatsapp.provider import MockWhatsAppProvider
from backend.app.services.whatsapp.rsvp_parser import ParsedRSVP


def test_database_readiness_is_reported_after_startup():
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "healthy"
        assert client.get("/readyz").status_code == 200


def test_database_initialization_failure_is_not_reported_ready(monkeypatch):
    def fail_initialization():
        raise OperationalError("SELECT 1", {}, RuntimeError("database unavailable"))

    monkeypatch.setattr("backend.app.main._background_db_backfill", fail_initialization)
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "degraded"
        assert client.get("/readyz").status_code == 503


def test_webhook_failure_paths_remain_retryable(db):
    assert WhatsAppWebhookService._is_duplicate_inbound_message(db, None) is False
    opt_out_phone = f"+141555{uuid.uuid4().int % 10**6:06d}"
    db.add(OptOut(phone=opt_out_phone, reason="existing"))
    db.commit()
    assert WhatsAppWebhookService._handle_inbound_message_action(
        db, "STOP", None, opt_out_phone, None, None, None
    ) == (0, 0, 0)
    assert WhatsAppWebhookService._send_faq_response(
        db, "question", "+14155552671", None, None, MockWhatsAppProvider()
    ) == 0
    assert WhatsAppWebhookService._update_guest_rsvp(
        db,
        None,
        ParsedRSVP(
            rsvp_status="invalid",
            headcount=0,
            confidence=0.0,
            needs_host_review=False,
            parsing_method="test",
        ),
    ) == 0
    phone, guest, event, text, button = WhatsAppWebhookService._load_inbound_context(
        db, {"from": "not-a-phone", "type": "image"}
    )
    assert phone == "+not-a-phone"
    assert guest is None
    assert event is not None
    assert (text, button) == ("", None)


def test_owner_token_is_persisted_and_required_for_recovery(db):
    user = User(
        phone_number=f"+9198{uuid.uuid4().hex[:8]}",
        full_name="Recovery Host",
        role="host",
    )
    db.add(user)
    db.flush()
    event = Event(
        owner_id=user.id,
        name="Recovery Event",
        event_type="wedding",
        guest_count=10,
        total_budget=100000,
        city="Pune",
        pincode="411001",
        start_date=date.today() + timedelta(days=10),
        end_date=date.today() + timedelta(days=11),
        metadata_json={},
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    client = TestClient(app)
    assert client.get(f"/api/v1/events/{event.id}").status_code == 403

    db.refresh(event)
    assert event.owner_token is not None
    assert (
        client.get(
            f"/api/v1/events/{event.id}",
            headers={"X-Event-Owner-Token": event.owner_token},
        ).status_code
        == 200
    )


def test_enabled_production_whatsapp_requires_explicit_secrets():
    with pytest.raises(ValueError, match="WHATSAPP_PROVIDER=mock"):
        Settings(
            ENVIRONMENT="production",
            ENABLE_M4_WHATSAPP=True,
            WHATSAPP_PROVIDER="mock",
        )


def test_disabled_whatsapp_skips_secret_validation():
    settings = Settings(
        ENABLE_M4_WHATSAPP=False,
        WHATSAPP_PROVIDER="cloud_api",
        WHATSAPP_WEBHOOK_VERIFY_TOKEN="",
    )
    assert settings.ENABLE_M4_WHATSAPP is False


def test_enabled_whatsapp_requires_webhook_secret():
    with pytest.raises(ValueError, match="WHATSAPP_WEBHOOK_VERIFY_TOKEN"):
        Settings(
            ENABLE_M4_WHATSAPP=True,
            WHATSAPP_PROVIDER="mock",
            WHATSAPP_WEBHOOK_VERIFY_TOKEN="",
        )


def test_cloud_whatsapp_requires_api_credentials():
    with pytest.raises(ValueError, match="WHATSAPP_API_TOKEN"):
        Settings(
            ENABLE_M4_WHATSAPP=True,
            WHATSAPP_PROVIDER="cloud_api",
            WHATSAPP_WEBHOOK_VERIFY_TOKEN="configured" + "-token",
        )


def test_streamed_request_body_limit_is_enforced():
    oversized_body = b"x" * (MAX_REQUEST_BODY_BYTES + 1)
    sent_messages = []
    received = False

    async def receive():
        nonlocal received
        if received:
            return {"type": "http.disconnect"}
        received = True
        return {"type": "http.request", "body": oversized_body, "more_body": False}

    async def send(message):
        sent_messages.append(message)

    asyncio.run(
        app(
            {
                "type": "http",
                "method": "POST",
                "path": "/api/v1/events",
                "raw_path": b"/api/v1/events",
                "query_string": b"",
                "headers": [(b"transfer-encoding", b"chunked")],
                "scheme": "http",
                "server": ("testserver", 80),
                "client": ("testclient", 123),
                "root_path": "",
                "http_version": "1.1",
            },
            receive,
            send,
        )
    )

    assert sent_messages[0]["status"] == 413


def test_owner_token_recovery_generates_and_persists_missing_token(db):
    user = User(
        phone_number=f"+9198{uuid.uuid4().hex[:8]}",
        full_name="Token Recovery Host",
        role="host",
    )
    db.add(user)
    db.flush()
    event = Event(
        owner_id=user.id,
        name="Token Recovery Event",
        event_type="wedding",
        guest_count=1,
        total_budget=1,
        city="Pune",
        pincode="411001",
        start_date=date.today(),
        end_date=date.today(),
        metadata_json={},
    )
    token = _resolve_expected_token(event, db)
    assert token is not None
    assert event.metadata_json["owner_token"] == token


def test_request_size_middleware_passes_non_http_scopes():
    sent = []

    async def downstream(scope, receive, send):
        sent.append(scope["type"])

    async def receive():
        return {"type": "lifespan.startup"}

    async def send(message):
        sent.append(message)

    asyncio.run(
        RequestSizeLimitMiddleware(downstream, MAX_REQUEST_BODY_BYTES)(
            {"type": "lifespan"}, receive, send
        )
    )
    assert sent == ["lifespan"]


def test_request_size_middleware_accepts_small_body_and_invalid_length():
    middleware = RequestSizeLimitMiddleware(lambda *_args: None, MAX_REQUEST_BODY_BYTES)
    assert middleware._content_length_exceeds_limit(b"not-a-number") is False
    received, sent_wrapper, rejected = middleware._wrap_io(
        lambda: asyncio.sleep(0, result={"type": "http.request", "body": b"ok"}),
        lambda _message: asyncio.sleep(0),
    )
    message = asyncio.run(received())
    asyncio.run(sent_wrapper({"type": "http.response.start", "status": 200}))
    assert message["body"] == b"ok"
    assert rejected() is False


def test_private_event_reads_require_owner_token(db):
    user = User(
        phone_number=f"+9198{uuid.uuid4().hex[:8]}",
        full_name="Private Read Host",
        role="host",
    )
    db.add(user)
    db.flush()
    event = Event(
        owner_id=user.id,
        name="Private Read Event",
        event_type="wedding",
        guest_count=1,
        total_budget=1,
        city="Pune",
        pincode="411001",
        start_date=date.today(),
        end_date=date.today(),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    client = TestClient(app)

    guest_url = f"/api/v1/events/{event.id}/guests"
    quote_url = f"/api/v1/quotes/event/{event.id}"
    assert client.get(guest_url).status_code == 403
    assert client.get(quote_url).status_code == 403
    headers = {"X-Event-Owner-Token": event.owner_token}
    assert client.get(guest_url, headers=headers).status_code == 200
    assert client.get(quote_url, headers=headers).status_code == 200


def test_duplicate_whatsapp_message_id_is_processed_once(db):
    user = User(
        phone_number=f"+9198{uuid.uuid4().hex[:8]}",
        full_name="Webhook Host",
        role="host",
    )
    db.add(user)
    db.flush()
    event = Event(
        owner_id=user.id,
        name="Webhook Event",
        event_type="wedding",
        guest_count=1,
        total_budget=1,
        city="Pune",
        pincode="411001",
        start_date=date.today(),
        end_date=date.today(),
    )
    db.add(event)
    db.flush()
    guest_phone = f"+919876{uuid.uuid4().int % 10**6:06d}"
    guest = Guest(event_id=event.id, name="Webhook Guest", phone=guest_phone)
    db.add(guest)
    db.commit()
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": f"wamid-regression-{uuid.uuid4().hex}",
                                    "from": guest_phone.removeprefix("+"),
                                    "type": "text",
                                    "text": {"body": "STOP"},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }

    first = WhatsAppWebhookService.handle_inbound_payload(db, payload)
    second = WhatsAppWebhookService.handle_inbound_payload(db, payload)
    message_id = payload["entry"][0]["changes"][0]["value"]["messages"][0]["id"]
    assert first["opt_outs_recorded"] == 1
    assert second == {
        "statuses_updated": 0,
        "opt_outs_recorded": 0,
        "rsvps_updated": 0,
        "faq_replies_sent": 0,
    }
    assert (
        db.query(MessageLog)
        .filter(MessageLog.whatsapp_message_id == message_id)
        .count()
        == 1
    )


def test_webhook_ignores_malformed_status_and_message_entries(db, monkeypatch):
    results = WhatsAppWebhookService.handle_inbound_payload(
        db,
        {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "statuses": [{"id": "missing-status-name"}],
                                "messages": [{"id": "missing-sender", "type": "text"}],
                            }
                        }
                    ]
                }
            ]
        },
    )
    assert results == {
        "statuses_updated": 0,
        "opt_outs_recorded": 0,
        "rsvps_updated": 0,
        "faq_replies_sent": 0,
    }
    assert WhatsAppWebhookService._extract_message_content(
        {"type": "button", "button": {"text": "Yes", "payload": "rsvp_yes"}}
    ) == ("Yes", "rsvp_yes")
    assert WhatsAppWebhookService._extract_message_content({"type": "image"}) == ("", None)
    _, _, faq_sent = WhatsAppWebhookService._process_inbound_message_item(
        db,
        {"from": f"+141555{uuid.uuid4().int % 10**6:06d}", "type": "image"},
        MockWhatsAppProvider(),
    )
    assert faq_sent == 1

    original_commit = db.commit
    commit_calls = 0

    def commit_then_report_duplicate():
        nonlocal commit_calls
        commit_calls += 1
        original_commit()
        if commit_calls == 1:
            from sqlalchemy.exc import IntegrityError

            raise IntegrityError("duplicate", {}, Exception("unique index"))

    monkeypatch.setattr(db, "commit", commit_then_report_duplicate)
    duplicate_result = WhatsAppWebhookService._process_inbound_message_item(
        db,
        {"from": "+14155552671", "id": f"race-{uuid.uuid4().hex}", "type": "image"},
        MockWhatsAppProvider(),
    )
    assert duplicate_result == (0, 0, 0)
