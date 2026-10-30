import hmac
import secrets

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.models import Event


def generate_owner_token() -> str:
    """Generates a cryptographically secure 64-character hexadecimal token."""
    return secrets.token_hex(32)


def _extract_event_id(request: Request) -> str:
    event_id = (
        request.path_params.get("event_id")
        or request.path_params.get("id")
        or request.query_params.get("event_id")
    )
    if not event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing event_id in request"
        )
    return str(event_id)


def _extract_provided_token(
    x_event_owner_token: str | None, authorization: str | None
) -> str | None:
    if x_event_owner_token:
        return x_event_owner_token
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def _resolve_expected_token(event: Event, db: Session) -> str | None:
    expected = (event.metadata_json or {}).get("owner_token") or getattr(event, "owner_token", None)
    if expected:
        return str(expected)

    new_token = generate_owner_token()
    event.owner_token = new_token
    meta = dict(event.metadata_json or {})
    meta["owner_token"] = new_token
    event.metadata_json = meta
    db.add(event)
    db.commit()
    db.refresh(event)
    return new_token


def verify_event_owner_token(
    request: Request,
    x_event_owner_token: str | None = Header(None, alias="X-Event-Owner-Token"),
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> Event:
    """
    Guards mutating event operations (POST, PATCH, DELETE) and private reads (GET).
    Resolves event_id from path_params ('event_id' or 'id') or query params.
    Validates provided token against event.owner_token / event.metadata_json['owner_token'].
    Tokens must strictly be provided via HTTP headers (X-Event-Owner-Token or
    Authorization: Bearer).
    URL query parameter token transmission is permanently disabled to comply with CWE-598.
    Rejects with 403 Forbidden if invalid or missing.
    """
    event_id = _extract_event_id(request)
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Event with id '{event_id}' not found"
        )

    expected = _resolve_expected_token(event, db)
    provided = _extract_provided_token(x_event_owner_token, authorization)

    if not provided or not expected or not hmac.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Forbidden: Invalid or missing X-Event-Owner-Token. Unauthorized access attempt."
            ),
        )

    return event
