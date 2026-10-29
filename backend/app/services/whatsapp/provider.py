import json
import logging
import os
import uuid
from abc import ABC, abstractmethod
from typing import Any

import httpx
from pydantic import BaseModel

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class WhatsAppSendResult(BaseModel):
    success: bool
    message_id: str
    status: str  # "sent", "failed", "queued"
    provider_used: str
    error: str | None = None


class WhatsAppProvider(ABC):
    """Abstract WhatsApp Cloud API provider interface."""

    @abstractmethod
    def send_template(
        self,
        to_phone: str,
        template_name: str,
        language: str = "en",
        parameters: list[str] | None = None,
    ) -> WhatsAppSendResult:
        pass

    @abstractmethod
    def send_freeform_text(self, to_phone: str, body: str) -> WhatsAppSendResult:
        pass

    @abstractmethod
    def send_interactive_buttons(
        self,
        to_phone: str,
        body: str,
        buttons: list[dict[str, str]],  # [{"id": "yes", "title": "Attending"}]
    ) -> WhatsAppSendResult:
        pass


class MockWhatsAppProvider(WhatsAppProvider):
    """
    Offline / Sandbox mock WhatsApp provider for deterministic unit testing
    and local development without incurring Meta API calls or requiring approved templates.
    """

    def __init__(self) -> None:
        self.sent_messages: list[dict[str, Any]] = []

    def clear(self) -> None:
        self.sent_messages.clear()

    def send_template(
        self,
        to_phone: str,
        template_name: str,
        language: str = "en",
        parameters: list[str] | None = None,
    ) -> WhatsAppSendResult:
        msg_id = f"wamid.mock_{uuid.uuid4().hex[:16]}"
        record = {
            "message_id": msg_id,
            "to_phone": to_phone,
            "type": "template",
            "template_name": template_name,
            "language": language,
            "parameters": parameters or [],
            "status": "sent",
            "provider_used": "mock",
        }
        self.sent_messages.append(record)
        return WhatsAppSendResult(
            success=True, message_id=msg_id, status="sent", provider_used="mock"
        )

    def send_freeform_text(self, to_phone: str, body: str) -> WhatsAppSendResult:
        msg_id = f"wamid.mock_{uuid.uuid4().hex[:16]}"
        record = {
            "message_id": msg_id,
            "to_phone": to_phone,
            "type": "freeform",
            "body": body,
            "status": "sent",
            "provider_used": "mock",
        }
        self.sent_messages.append(record)
        return WhatsAppSendResult(
            success=True, message_id=msg_id, status="sent", provider_used="mock"
        )

    def send_interactive_buttons(
        self, to_phone: str, body: str, buttons: list[dict[str, str]]
    ) -> WhatsAppSendResult:
        msg_id = f"wamid.mock_{uuid.uuid4().hex[:16]}"
        record = {
            "message_id": msg_id,
            "to_phone": to_phone,
            "type": "interactive_buttons",
            "body": body,
            "buttons": buttons,
            "status": "sent",
            "provider_used": "mock",
        }
        self.sent_messages.append(record)
        return WhatsAppSendResult(
            success=True, message_id=msg_id, status="sent", provider_used="mock"
        )


class MetaCloudWhatsAppProvider(WhatsAppProvider):
    """
    Live Meta WhatsApp Business Cloud API provider.
    Communicates with graph.facebook.com/v21.0 using bearer authentication.
    """

    def __init__(self, phone_number_id: str, api_token: str) -> None:
        self.phone_number_id = phone_number_id
        self.api_token = api_token
        self.base_url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json"}

    def send_template(
        self,
        to_phone: str,
        template_name: str,
        language: str = "en",
        parameters: list[str] | None = None,
    ) -> WhatsAppSendResult:
        clean_to = to_phone.lstrip("+")
        components = []
        if parameters:
            components.append(
                {"type": "body", "parameters": [{"type": "text", "text": p} for p in parameters]}
            )

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
                "components": components,
            },
        }

        try:
            res = httpx.post(self.base_url, json=payload, headers=self._headers(), timeout=10.0)
            data = res.json()
            if res.status_code == 200 and "messages" in data and len(data["messages"]) > 0:
                msg_id = data["messages"][0]["id"]
                return WhatsAppSendResult(
                    success=True, message_id=msg_id, status="sent", provider_used="meta_cloud_api"
                )
            err_msg = data.get("error", {}).get("message", res.text)
            return WhatsAppSendResult(
                success=False,
                message_id="",
                status="failed",
                provider_used="meta_cloud_api",
                error=err_msg,
            )
        except (
            httpx.HTTPError,
            RuntimeError,
            OSError,
            json.JSONDecodeError,
            KeyError,
            IndexError,
            ValueError,
            TypeError,
        ) as e:
            return WhatsAppSendResult(
                success=False,
                message_id="",
                status="failed",
                provider_used="meta_cloud_api",
                error=str(e),
            )

    def send_freeform_text(self, to_phone: str, body: str) -> WhatsAppSendResult:
        clean_to = to_phone.lstrip("+")
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_to,
            "type": "text",
            "text": {"preview_url": False, "body": body},
        }
        try:
            res = httpx.post(self.base_url, json=payload, headers=self._headers(), timeout=10.0)
            data = res.json()
            if res.status_code == 200 and "messages" in data and len(data["messages"]) > 0:
                return WhatsAppSendResult(
                    success=True,
                    message_id=data["messages"][0]["id"],
                    status="sent",
                    provider_used="meta_cloud_api",
                )
            err_msg = data.get("error", {}).get("message", res.text)
            return WhatsAppSendResult(
                success=False,
                message_id="",
                status="failed",
                provider_used="meta_cloud_api",
                error=err_msg,
            )
        except (
            httpx.HTTPError,
            RuntimeError,
            OSError,
            json.JSONDecodeError,
            KeyError,
            IndexError,
            ValueError,
            TypeError,
        ) as e:
            return WhatsAppSendResult(
                success=False,
                message_id="",
                status="failed",
                provider_used="meta_cloud_api",
                error=str(e),
            )

    def send_interactive_buttons(
        self, to_phone: str, body: str, buttons: list[dict[str, str]]
    ) -> WhatsAppSendResult:
        clean_to = to_phone.lstrip("+")
        formatted_buttons = []
        for b in buttons[:3]:  # WhatsApp interactive supports max 3 quick-reply buttons
            formatted_buttons.append(
                {
                    "type": "reply",
                    "reply": {
                        "id": b["id"],
                        "title": b["title"][:20],  # Max 20 chars per button title
                    },
                }
            )

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body},
                "action": {"buttons": formatted_buttons},
            },
        }
        try:
            res = httpx.post(self.base_url, json=payload, headers=self._headers(), timeout=10.0)
            data = res.json()
            if res.status_code == 200 and "messages" in data and len(data["messages"]) > 0:
                return WhatsAppSendResult(
                    success=True,
                    message_id=data["messages"][0]["id"],
                    status="sent",
                    provider_used="meta_cloud_api",
                )
            err_msg = data.get("error", {}).get("message", res.text)
            return WhatsAppSendResult(
                success=False,
                message_id="",
                status="failed",
                provider_used="meta_cloud_api",
                error=err_msg,
            )
        except (
            httpx.HTTPError,
            RuntimeError,
            OSError,
            json.JSONDecodeError,
            KeyError,
            IndexError,
            ValueError,
            TypeError,
        ) as e:
            return WhatsAppSendResult(
                success=False,
                message_id="",
                status="failed",
                provider_used="meta_cloud_api",
                error=str(e),
            )


# Global default mock provider instance for tests/local
_default_mock_provider = MockWhatsAppProvider()


def get_whatsapp_provider() -> WhatsAppProvider:
    """
    Factory resolving active WhatsApp provider.
    Defaults to MockWhatsAppProvider if WHATSAPP_PROVIDER == 'mock'
    or credentials are not configured.
    """
    provider_type = os.getenv(
        "WHATSAPP_PROVIDER", getattr(settings, "WHATSAPP_PROVIDER", "mock")
    ).lower()
    api_token = os.getenv("WHATSAPP_API_TOKEN", getattr(settings, "WHATSAPP_API_TOKEN", None))
    phone_number_id = os.getenv(
        "WHATSAPP_PHONE_NUMBER_ID", getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", None)
    )

    if provider_type == "cloud_api" and api_token and phone_number_id:
        return MetaCloudWhatsAppProvider(phone_number_id=phone_number_id, api_token=api_token)

    return _default_mock_provider
