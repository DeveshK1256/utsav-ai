import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.limiter import limiter
from backend.app.core.security import verify_event_owner_token
from backend.app.db.session import get_db
from backend.app.models.models import (
    Event,
    Guest,
    InvitationCard,
    SubEvent,
    ThemeProposal,
)
from backend.app.schemas.invitations import (
    FailedGuestSummary,
    InvitationBatchResponse,
    InvitationCardSummary,
    InvitationGenerateRequest,
    InvitationStudioOptionsResponse,
    LayoutOption,
)
from backend.app.services.invitation_renderer import InvitationCardRenderer
from backend.app.services.invitation_wording_agent import InvitationWordingAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events/{event_id}/invitations", tags=["Invitation Cards (F16)"])

STANDARD_LAYOUTS = [
    LayoutOption(
        id="classic_royal",
        name="Classic Royal (पारंपरिक राजेशाही)",
        description="Symmetrical royal framing with auspicious shubh-muhurat emblem and intricate gold accents.",
        recommended_for="Traditional weddings, Vivah, and auspicious milestone ceremonies",
    ),
    LayoutOption(
        id="modern_minimal",
        name="Modern Contemporary (आधुनिक)",
        description="Clean vertical accent bar, airy typography, modern spacing, and minimalist geometry.",
        recommended_for="Contemporary celebrations, cocktail parties, and modern receptions",
    ),
    LayoutOption(
        id="floral_festive",
        name="Floral Festive (उत्सव बहार)",
        description="Warm celebratory marigold motifs, centerpiece cartouche, and joyful decorative framing.",
        recommended_for="Sangeet, Mehendi, Diwali Sneh Milan, and Community Festivals",
    ),
]

DEFAULT_PALETTE = ["#B45309", "#991B1B", "#FEF3C7", "#1E3A8A", "#D97706"]


def _resolve_event_logistics(
    event: Event, db: Session
) -> tuple[str | None, str, str, str | None, list[str]]:
    """Helper to extract confirmed event details and avoid invented facts."""
    # 1. Host Name
    host_name = None
    if event.metadata_json and isinstance(event.metadata_json, dict):
        host_name = event.metadata_json.get("host_name")
    if not host_name and event.owner:
        host_name = event.owner.full_name

    # 2. Date String
    date_str = (
        event.start_date.strftime("%A, %d %B %Y") if event.start_date else "Date to be confirmed"
    )

    # 3. Venue String
    venue_str = "Venue to be confirmed"
    if event.fact_sheet and event.fact_sheet.venue_address:
        venue_str = event.fact_sheet.venue_address
    elif (
        event.metadata_json
        and isinstance(event.metadata_json, dict)
        and event.metadata_json.get("venue")
    ):
        venue_str = str(event.metadata_json.get("venue"))
    elif event.city:
        venue_str = f"{event.city} (Venue to be confirmed)"

    # 4. Muhurat Time:
    # Priority A: Confirmed manual/event-level muhurat time from metadata_json
    # Priority B: Sub-event with is_muhurat_locked == True (M5 auspicious locked time)
    # Priority C: None (card renders without muhurat badge / with confirmed timing only, never fabricating unconfirmed panchang)
    muhurat_time = None
    if event.metadata_json and isinstance(event.metadata_json, dict):
        muhurat_time = event.metadata_json.get("muhurat_time")

    # Fetch sub_events for both muhurat resolution and ceremony listing
    sub_events = (
        db.query(SubEvent).filter(SubEvent.event_id == event.id).order_by(SubEvent.start_time).all()
    )

    if not muhurat_time:
        locked_sub_event = next((s for s in sub_events if s.is_muhurat_locked), None)
        if locked_sub_event:
            # Format locked window: e.g. "10:30 AM - 12:00 PM (Vivah Muhurat)" or time range
            start_fmt = (
                locked_sub_event.start_time.strftime("%I:%M %p").lstrip("0")
                if locked_sub_event.start_time
                else None
            )
            end_fmt = (
                locked_sub_event.end_time.strftime("%I:%M %p").lstrip("0")
                if locked_sub_event.end_time
                else None
            )
            if start_fmt and end_fmt:
                time_range = f"{start_fmt} - {end_fmt}"
            elif start_fmt:
                time_range = start_fmt
            else:
                time_range = None

            if time_range:
                if locked_sub_event.muhurat_notes:
                    muhurat_time = f"{time_range} ({locked_sub_event.muhurat_notes})"
                else:
                    muhurat_time = f"{time_range} ({locked_sub_event.name})"

    # 5. Ceremonies from sub_events
    ceremonies = [s.name for s in sub_events if s.name]

    return host_name, date_str, venue_str, muhurat_time, ceremonies


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

    host_name, date_str, venue_str, muhurat_time, ceremonies = _resolve_event_logistics(event, db)

    # Resolve Theme & Palette
    theme = None
    if theme_proposal_id:
        theme = db.query(ThemeProposal).filter(ThemeProposal.id == theme_proposal_id).first()
    if not theme:
        # Check if there is an accepted theme proposal for this event
        theme = (
            db.query(ThemeProposal)
            .join(ThemeProposal.style_profile)
            .filter(ThemeProposal.status == "accepted")
            .first()
        )

    palette = theme.palette if theme and theme.palette else DEFAULT_PALETTE
    theme_name = theme.theme_name if theme else None
    resolved_theme_id = theme.id if theme else None
    design_brief = theme.invitation_design_brief if theme else None

    # Guest count
    guest_count = db.query(Guest).filter(Guest.event_id == event_id).count()

    # Generate Wording Variants
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
    host_name, date_str, venue_str, muhurat_time, ceremonies = _resolve_event_logistics(event, db)

    # Resolve Theme
    theme = None
    if payload.theme_proposal_id:
        theme = (
            db.query(ThemeProposal).filter(ThemeProposal.id == payload.theme_proposal_id).first()
        )
    if not theme:
        theme = (
            db.query(ThemeProposal)
            .join(ThemeProposal.style_profile)
            .filter(ThemeProposal.status == "accepted")
            .first()
        )

    palette = theme.palette if theme and theme.palette else DEFAULT_PALETTE
    theme_proposal_id = theme.id if theme else None
    design_brief = theme.invitation_design_brief if theme else None

    # Resolve Wording Text
    wording_text = payload.wording_text
    if not wording_text:
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
        idx = payload.wording_variant_index or 0
        if 0 <= idx < len(wording_res.variants):
            wording_text = wording_res.variants[idx].body_text
        else:
            wording_text = wording_res.variants[0].body_text

    layout_variant = payload.layout_variant or "classic_royal"

    # Fetch Guests
    guests = db.query(Guest).filter(Guest.event_id == event_id).all()

    created_cards: list[InvitationCard] = []
    failed_guests: list[FailedGuestSummary] = []

    if guests:
        # Batch generation: One card per guest
        for g in guests:
            try:
                png_bytes, pdf_bytes = InvitationCardRenderer.render_card(
                    event_name=event.name,
                    host_name=host_name,
                    date_str=date_str,
                    venue_str=venue_str,
                    wording_text=wording_text,
                    muhurat_time=muhurat_time,
                    ceremony_names=ceremonies,
                    guest_name=g.name,
                    guest_diet=g.diet,
                    palette=palette,
                    layout_variant=layout_variant,
                )

                card = InvitationCard(
                    event_id=event.id,
                    theme_proposal_id=theme_proposal_id,
                    layout_variant=layout_variant,
                    wording_text=wording_text,
                    guest_id=g.id,
                    rendered_png=png_bytes,
                    rendered_pdf=pdf_bytes,
                    generated_at=datetime.now(UTC),
                )
                db.add(card)
                created_cards.append(card)
            except (ValueError, RuntimeError, OSError, KeyError) as err:
                logger.error("Failed to render card for guest %s (%s): %s", g.id, g.name, err)
                failed_guests.append(
                    FailedGuestSummary(guest_id=g.id, name=g.name, reason=str(err))
                )
    else:
        # Single generic card
        try:
            png_bytes, pdf_bytes = InvitationCardRenderer.render_card(
                event_name=event.name,
                host_name=host_name,
                date_str=date_str,
                venue_str=venue_str,
                wording_text=wording_text,
                muhurat_time=muhurat_time,
                ceremony_names=ceremonies,
                guest_name=None,
                guest_diet=None,
                palette=palette,
                layout_variant=layout_variant,
            )

            card = InvitationCard(
                event_id=event.id,
                theme_proposal_id=theme_proposal_id,
                layout_variant=layout_variant,
                wording_text=wording_text,
                guest_id=None,
                rendered_png=png_bytes,
                rendered_pdf=pdf_bytes,
                generated_at=datetime.now(UTC),
            )
            db.add(card)
            created_cards.append(card)
        except (ValueError, RuntimeError, OSError, KeyError, SQLAlchemyError) as err:
            logger.error("Failed to render generic card: %s", err)
            raise HTTPException(status_code=500, detail=f"Card composition failed: {err}") from err

    db.commit()
    for c in created_cards:
        db.refresh(c)

    # Format summaries
    card_summaries: list[InvitationCardSummary] = []
    for c in created_cards:
        g_name = None
        if c.guest:
            g_name = c.guest.name
        card_summaries.append(
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
                png_download_url=f"/api/v1/events/{event.id}/invitations/{c.id}/download?format=png",
                pdf_download_url=f"/api/v1/events/{event.id}/invitations/{c.id}/download?format=pdf",
            )
        )

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
                png_download_url=f"/api/v1/events/{event_id}/invitations/{c.id}/download?format=png",
                pdf_download_url=f"/api/v1/events/{event_id}/invitations/{c.id}/download?format=pdf",
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
    else:  # PNG default
        if not card.rendered_png:
            raise HTTPException(status_code=404, detail="PNG format not available for this card")
        filename = f"utsav_invitation_{card.guest_id or 'generic'}.png"
        return Response(
            content=card.rendered_png,
            media_type="image/png",
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )
