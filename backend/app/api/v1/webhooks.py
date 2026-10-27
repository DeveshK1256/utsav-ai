import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.db.session import get_db
from backend.app.services.whatsapp.webhook_service import WhatsAppWebhookService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["WhatsApp Webhooks"])


@router.get("/whatsapp")
def verify_whatsapp_webhook(
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(None, alias="hub.challenge")
):
    """
    Meta WhatsApp Cloud API Webhook Challenge Verification.
    Responds with hub.challenge if hub.verify_token matches configured secret.
    """
    configured_token = getattr(settings, "WHATSAPP_WEBHOOK_VERIFY_TOKEN", "utsav_webhook_verify_token_secure")
    if hub_mode == "subscribe" and hub_verify_token == configured_token:
        logger.info("Meta WhatsApp webhook challenge successfully verified.")
        return Response(content=hub_challenge or "", media_type="text/plain")

    logger.warning("Meta WhatsApp webhook challenge verification failed (token mismatch).")
    raise HTTPException(status_code=403, detail="Verification token mismatch")


@router.post("/whatsapp")
async def receive_whatsapp_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
    db: Session = Depends(get_db)
):
    """
    Receives real-time inbound events from Meta WhatsApp Cloud API:
    - Message delivery receipts (sent, delivered, read, failed)
    - Inbound guest RSVPs (buttons and free-text)
    - Guest FAQ inquiries
    - STOP opt-out requests
    Rejects unsigned or forged requests when WHATSAPP_APP_SECRET is set.
    """
    raw_body = await request.body()

    # Meta HMAC Signature Verification (Public Endpoint Guardrail)
    is_valid = WhatsAppWebhookService.verify_meta_signature(raw_body, x_hub_signature_256)
    if not is_valid:
        logger.error("Rejected unauthorized WhatsApp webhook request: invalid HMAC signature")
        raise HTTPException(status_code=403, detail="Invalid HMAC signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    results = WhatsAppWebhookService.handle_inbound_payload(db, payload)
    return {"status": "processed", "results": results}
