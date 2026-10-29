import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from backend.app.core.limiter import limiter
from backend.app.core.security import verify_event_owner_token
from backend.app.db.session import get_db
from backend.app.models.models import Event, Guest, InvitationCard
from backend.app.schemas.invitations import (
    InvitationBatchResponse,
    InvitationCardSummary,
    InvitationGenerateRequest,
    InvitationStudioOptionsResponse,
)
from backend.app.services.invitation.studio_service import (
    STANDARD_LAYOUTS,
    build_card_summaries,
    render_generic_card,
    render_guest_cards,
    resolve_card_wording,
    resolve_event_logistics,
    resolve_theme_and_palette,
)
from backend.app.services.invitation_wording_agent import InvitationWordingAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events/{event_id}/invitations", tags=["Invitation Cards (F16)"])


@router.get("/options", response_model=InvitationStudioOptionsResponse)
def get_invitation_studio_options(
    event_id: str, theme_proposal_id: str | None = Query(None), db: Session = Depends(get_db)
) -> InvitationStudioOptionsResponse:
    """
    Returns layout options, theme palette, event logistics, and AI/stub wording variants
    ready for user preview and selection in the Invitation Card Studio.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    host_name, date_str, venue_str, muhurat_time, ceremonies = resolve_event_logistics(event, db)
    resolved_theme_id, palette, design_brief, theme_name = resolve_theme_and_palette(
        theme_proposal_id, db
    )

    guest_count = db.query(Guest).filter(Guest.event_id == event_id).count()

    wording_res = InvitationWordingAgent.compose_wording(
        event_name=event.name,
        host_name=host_name,
        event_type=event.event_type,
        date_str=date_str,
        venue_str=venue_str,
        muhurat_time=muhurat_time,
        ceremony_names=ceremonies,
        design_brief=design_brief,
    )

    return InvitationStudioOptionsResponse(
        layout_options=STANDARD_LAYOUTS,
        palette=palette,
        theme_name=theme_name,
        theme_proposal_id=resolved_theme_id,
        event_name=event.name,
        host_name=host_name,
        date_str=date_str,
        venue_str=venue_str,
        muhurat_time=muhurat_time,
        ceremonies=ceremonies[:4],
        guest_count=guest_count,
        wording_options=wording_res.variants,
        provider_used=wording_res.provider_used,
        fallback_warning=wording_res.fallback_warning,
        content_review_note=wording_res.content_review_note,
    )


@router.post(
    "/generate", response_model=InvitationBatchResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit("20/minute")
def generate_invitation_cards(
    request: Request,
    event_id: str,
    payload: InvitationGenerateRequest,
    event: Event = Depends(verify_event_owner_token),
    db: Session = Depends(get_db),
) -> InvitationBatchResponse:
    """
    Generates personalized invitation cards for all guests (or one generic card if no guests).
    Uses server-side Pillow rendering (DEC-028), per-guest personalization (DEC-029),
    and exports both PNG and PDF from single composition pipeline (DEC-030).
    Per-guest errors are isolated and returned in failed_guests without failing the entire batch.
    """
    _ = (request,)
    host_name, date_str, venue_str, muhurat_time, ceremonies = resolve_event_logistics(event, db)
    t_id, palette, brief, _ = resolve_theme_and_palette(payload.theme_proposal_id, db)
    wording_text = resolve_card_wording(
        payload, event, host_name, date_str, venue_str, muhurat_time, ceremonies, brief
    )
    layout_variant = payload.layout_variant or "classic_royal"

    guests = db.query(Guest).filter(Guest.event_id == event_id).all()
    if guests:
        created_cards, failed_guests = render_guest_cards(
            guests,
            event,
            t_id,
            layout_variant,
            wording_text,
            host_name,
            date_str,
            venue_str,
            muhurat_time,
            ceremonies,
            palette,
            db,
        )
    else:
        card = render_generic_card(
            event,
            t_id,
            layout_variant,
            wording_text,
            host_name,
            date_str,
            venue_str,
            muhurat_time,
            ceremonies,
            palette,
            db,
        )
        created_cards = [card]
        failed_guests = []

    db.commit()
    for c in created_cards:
        db.refresh(c)

    card_summaries = build_card_summaries(created_cards, event.id)

    return InvitationBatchResponse(
        event_id=event.id,
        layout_variant=layout_variant,
        total_generated=len(card_summaries),
        total_failed=len(failed_guests),
        cards=card_summaries,
        failed_guests=failed_guests,
    )


@router.get("", response_model=list[InvitationCardSummary])
def list_invitation_cards(
    event_id: str, db: Session = Depends(get_db)
) -> list[InvitationCardSummary]:
    """Lists all previously generated invitation cards for this event."""
    cards = (
        db.query(InvitationCard)
        .filter(InvitationCard.event_id == event_id)
        .order_by(InvitationCard.generated_at.desc())
        .all()
    )

    summaries = []
    for c in cards:
        g_name = c.guest.name if c.guest else None
        summaries.append(
            InvitationCardSummary(
                id=c.id,
                event_id=c.event_id,
                layout_variant=c.layout_variant,
                guest_id=c.guest_id,
                guest_name=g_name,
                wording_preview=(c.wording_text[:120] + "...")
                if len(c.wording_text) > 120
                else c.wording_text,
                generated_at=c.generated_at,
                png_download_url=(
                    f"/api/v1/events/{event_id}/invitations/{c.id}/download?format=png"
                ),
                pdf_download_url=(
                    f"/api/v1/events/{event_id}/invitations/{c.id}/download?format=pdf"
                ),
            )
        )
    return summaries


@router.get("/{card_id}/download")
def download_invitation_card(
    event_id: str,
    card_id: str,
    format: str = Query("png", description="png or pdf"),
    db: Session = Depends(get_db),
) -> Response:
    """
    Streams the binary rendered card file in requested format (PNG or PDF).
    """
    card = (
        db.query(InvitationCard)
        .filter(InvitationCard.id == card_id, InvitationCard.event_id == event_id)
        .first()
    )
    if not card:
        raise HTTPException(status_code=404, detail="Invitation card not found")

    clean_format = format.lower().strip()
    if clean_format == "pdf":
        if not card.rendered_pdf:
            raise HTTPException(status_code=404, detail="PDF format not available for this card")
        filename = f"utsav_invitation_{card.guest_id or 'generic'}.pdf"
        return Response(
            content=card.rendered_pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )
    # PNG default
    if not card.rendered_png:
        raise HTTPException(status_code=404, detail="PNG format not available for this card")
    filename = f"utsav_invitation_{card.guest_id or 'generic'}.png"
    return Response(
        content=card.rendered_png,
        media_type="image/png",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
