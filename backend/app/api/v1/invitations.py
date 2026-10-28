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


def _resolve_host_name(event: Event) -> str | None:
    if event.metadata_json and isinstance(event.metadata_json, dict):
        host = event.metadata_json.get("host_name")
        if host:
            return str(host)
    if event.owner and event.owner.full_name:
        return str(event.owner.full_name)
    return None


def _resolve_venue_str(event: Event) -> str:
    if event.fact_sheet and event.fact_sheet.venue_address:
        return str(event.fact_sheet.venue_address)
    if event.metadata_json and isinstance(event.metadata_json, dict) and event.metadata_json.get("venue"):
        return str(event.metadata_json.get("venue"))
    if event.city:
        return f"{event.city} (Venue to be confirmed)"
    return "Venue to be confirmed"


def _format_sub_event_window(locked: SubEvent) -> str | None:
    start_fmt = locked.start_time.strftime("%I:%M %p").lstrip("0") if locked.start_time else None
    end_fmt = locked.end_time.strftime("%I:%M %p").lstrip("0") if locked.end_time else None
    if start_fmt and end_fmt:
        tr = f"{start_fmt} - {end_fmt}"
    elif start_fmt:
        tr = start_fmt
    else:
        return None
    note = locked.muhurat_notes or locked.name
    return f"{tr} ({note})"


def _resolve_muhurat_time(event: Event, sub_events: list[SubEvent]) -> str | None:
    if event.metadata_json and isinstance(event.metadata_json, dict):
        m_time = event.metadata_json.get("muhurat_time")
        if m_time:
            return str(m_time)
    locked = next((s for s in sub_events if s.is_muhurat_locked), None)
    return _format_sub_event_window(locked) if locked else None


def _resolve_event_logistics(
    event: Event, db: Session
) -> tuple[str | None, str, str, str | None, list[str]]:
    """Helper to extract confirmed event details and avoid invented facts."""
    host_name = _resolve_host_name(event)
    date_str = event.start_date.strftime("%A, %d %B %Y") if event.start_date else "Date to be confirmed"
    venue_str = _resolve_venue_str(event)
    sub_events = db.query(SubEvent).filter(SubEvent.event_id == event.id).order_by(SubEvent.start_time).all()
    muhurat_time = _resolve_muhurat_time(event, sub_events)
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


def _resolve_theme_and_palette(
    theme_proposal_id: str | None, db: Session
) -> tuple[str | None, list[str], str | None]:
    theme = None
    if theme_proposal_id:
        theme = db.query(ThemeProposal).filter(ThemeProposal.id == theme_proposal_id).first()
    if not theme:
        theme = (
            db.query(ThemeProposal)
            .join(ThemeProposal.style_profile)
            .filter(ThemeProposal.status == "accepted")
            .first()
        )
    palette = theme.palette if theme and theme.palette else DEFAULT_PALETTE
    t_id = theme.id if theme else None
    brief = theme.invitation_design_brief if theme else None
    return t_id, palette, brief


def _resolve_card_wording(
    payload: InvitationGenerateRequest,
    event: Event,
    host_name: str | None,
    date_str: str,
    venue_str: str,
    muhurat_time: str | None,
    ceremonies: list[str],
    design_brief: str | None,
) -> str:
    if payload.wording_text:
        return payload.wording_text
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
        return wording_res.variants[idx].body_text
    return wording_res.variants[0].body_text


def _render_guest_cards(
    guests: list[Guest],
    event: Event,
    theme_proposal_id: str | None,
    layout_variant: str,
    wording_text: str,
    host_name: str | None,
    date_str: str,
    venue_str: str,
    muhurat_time: str | None,
    ceremonies: list[str],
    palette: list[str],
    db: Session,
) -> tuple[list[InvitationCard], list[FailedGuestSummary]]:
    created_cards: list[InvitationCard] = []
    failed_guests: list[FailedGuestSummary] = []
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
            failed_guests.append(FailedGuestSummary(guest_id=g.id, name=g.name, reason=str(err)))
    return created_cards, failed_guests


def _render_generic_card(
    event: Event,
    theme_proposal_id: str | None,
    layout_variant: str,
    wording_text: str,
    host_name: str | None,
    date_str: str,
    venue_str: str,
    muhurat_time: str | None,
    ceremonies: list[str],
    palette: list[str],
    db: Session,
) -> InvitationCard:
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
        return card
    except (ValueError, RuntimeError, OSError, KeyError, SQLAlchemyError) as err:
        logger.error("Failed to render generic card: %s", err)
        raise HTTPException(status_code=500, detail=f"Card composition failed: {err}") from err


def _build_card_summaries(cards: list[InvitationCard], event_id: str) -> list[InvitationCardSummary]:
    summaries = []
    for c in cards:
        g_name = c.guest.name if c.guest else None
        preview = (c.wording_text[:120] + "...") if len(c.wording_text) > 120 else c.wording_text
        summaries.append(
            InvitationCardSummary(
                id=c.id,
                event_id=c.event_id,
                layout_variant=c.layout_variant,
                guest_id=c.guest_id,
                guest_name=g_name,
                wording_preview=preview,
                generated_at=c.generated_at,
                png_download_url=f"/api/v1/events/{event_id}/invitations/{c.id}/download?format=png",
                pdf_download_url=f"/api/v1/events/{event_id}/invitations/{c.id}/download?format=pdf",
            )
        )
    return summaries


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
    t_id, palette, brief = _resolve_theme_and_palette(payload.theme_proposal_id, db)
    wording_text = _resolve_card_wording(
        payload, event, host_name, date_str, venue_str, muhurat_time, ceremonies, brief
    )
    layout_variant = payload.layout_variant or "classic_royal"

    guests = db.query(Guest).filter(Guest.event_id == event_id).all()
    if guests:
        created_cards, failed_guests = _render_guest_cards(
            guests, event, t_id, layout_variant, wording_text, host_name,
            date_str, venue_str, muhurat_time, ceremonies, palette, db
        )
    else:
        card = _render_generic_card(
            event, t_id, layout_variant, wording_text, host_name,
            date_str, venue_str, muhurat_time, ceremonies, palette, db
        )
        created_cards = [card]
        failed_guests = []

    db.commit()
    for c in created_cards:
        db.refresh(c)

    card_summaries = _build_card_summaries(created_cards, event.id)

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
