import logging
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models.models import (
    Event,
    Guest,
    InvitationCard,
    SubEvent,
    ThemeProposal,
)
from backend.app.schemas.invitations import (
    FailedGuestSummary,
    InvitationCardSummary,
    InvitationGenerateRequest,
    LayoutOption,
)
from backend.app.services.invitation_renderer import InvitationCardRenderer
from backend.app.services.invitation_wording_agent import InvitationWordingAgent

logger = logging.getLogger(__name__)

STANDARD_LAYOUTS = [
    LayoutOption(
        id="classic_royal",
        name="Classic Royal (पारंपरिक राजेशाही)",
        description=(
            "Symmetrical royal framing with auspicious shubh-muhurat emblem "
            "and intricate gold accents."
        ),
        recommended_for="Traditional weddings, Vivah, and auspicious milestone ceremonies",
    ),
    LayoutOption(
        id="modern_minimal",
        name="Modern Contemporary (आधुनिक)",
        description=(
            "Clean vertical accent bar, airy typography, modern spacing, and minimalist geometry."
        ),
        recommended_for="Contemporary celebrations, cocktail parties, and modern receptions",
    ),
    LayoutOption(
        id="floral_festive",
        name="Floral Festive (उत्सव बहार)",
        description=(
            "Warm celebratory marigold motifs, centerpiece cartouche, "
            "and joyful decorative framing."
        ),
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
    meta = event.metadata_json
    if meta and isinstance(meta, dict) and meta.get("venue"):
        return str(meta.get("venue"))
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


def resolve_event_logistics(
    event: Event, db: Session
) -> tuple[str | None, str, str, str | None, list[str]]:
    """Helper to extract confirmed event details and avoid invented facts."""
    host_name = _resolve_host_name(event)
    date_str = (
        event.start_date.strftime("%A, %d %B %Y") if event.start_date else "Date to be confirmed"
    )
    venue_str = _resolve_venue_str(event)
    sub_events = (
        db.query(SubEvent).filter(SubEvent.event_id == event.id).order_by(SubEvent.start_time).all()
    )
    muhurat_time = _resolve_muhurat_time(event, sub_events)
    ceremonies = [s.name for s in sub_events if s.name]

    return host_name, date_str, venue_str, muhurat_time, ceremonies


def resolve_theme_and_palette(
    theme_proposal_id: str | None, db: Session
) -> tuple[str | None, list[str], str | None, str | None]:
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
    theme_name = theme.theme_name if theme else None
    return t_id, palette, brief, theme_name


def resolve_card_wording(
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


def render_guest_cards(
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
            logger.exception("Failed to render card for guest %s (%s): %s", g.id, g.name, err)
            failed_guests.append(FailedGuestSummary(guest_id=g.id, name=g.name, reason=str(err)))
    return created_cards, failed_guests


def render_generic_card(
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
        logger.exception("Failed to render generic card: %s", err)
        raise HTTPException(status_code=500, detail=f"Card composition failed: {err}") from err


def build_card_summaries(
    cards: list[InvitationCard], event_id: str
) -> list[InvitationCardSummary]:
    summaries = []
    base_url = f"/api/v1/events/{event_id}/invitations"
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
                png_download_url=f"{base_url}/{c.id}/download?format=png",
                pdf_download_url=f"{base_url}/{c.id}/download?format=pdf",
            )
        )
    return summaries
