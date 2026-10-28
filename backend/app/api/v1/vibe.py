
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from backend.app.core.limiter import limiter
from backend.app.core.security import verify_event_owner_token
from backend.app.db.session import get_db
from backend.app.models.models import DecorItem, Event, StyleProfile, ThemeProposal
from backend.app.schemas.vibe import (
    AggregatedStyleProfileSchema,
    DecorItemProposalSchema,
    ThemeProposalResponseSchema,
)
from backend.app.services.vibe_service import VibeService

router = APIRouter(tags=["Vibe-to-Plan (Theme & Decor)"])


def format_profile_response(profile: StyleProfile) -> AggregatedStyleProfileSchema:
    return AggregatedStyleProfileSchema(
        profile_id=profile.id,
        event_id=profile.event_id,
        extracted_palette=profile.extracted_palette or [],
        style_tags=profile.style_tags or [],
        mood_words=profile.mood_words or [],
        text_description=profile.text_description,
        uploaded_image_count=len(profile.uploaded_image_refs or []),
        created_at=profile.created_at
    )


def format_theme_response(theme: ThemeProposal) -> ThemeProposalResponseSchema:
    items = []
    for d in (theme.decor_items or []):
        items.append(
            DecorItemProposalSchema(
                id=d.id,
                category=d.category,
                name=d.name,
                quantity_formula=d.quantity_formula,
                computed_quantity=d.computed_quantity,
                cost_tier=d.cost_tier,
                cost_range_low=float(d.cost_range_low),
                cost_range_high=float(d.cost_range_high),
                sourcing_type=d.sourcing_type,
                status=d.status,
                budget_item_id=d.budget_item_id,
                task_id=d.task_id,
                reasoning=d.reasoning or {}
            )
        )

    return ThemeProposalResponseSchema(
        theme_id=theme.id,
        style_profile_id=theme.style_profile_id,
        theme_name=theme.theme_name,
        palette=theme.palette or [],
        menu_direction=theme.menu_direction,
        playlist_genres=theme.playlist_genres or [],
        dress_code_suggestion=theme.dress_code_suggestion,
        invitation_design_brief=theme.invitation_design_brief,
        status=theme.status,
        decor_items=items,
        provider_used=getattr(theme, "provider_used", "gemini-3-flash-preview") or "gemini-3-flash-preview",
        fallback_warning=getattr(theme, "fallback_warning", None),
        created_at=theme.created_at
    )


def format_decor_item_response(d: DecorItem) -> DecorItemProposalSchema:
    return DecorItemProposalSchema(
        id=d.id,
        category=d.category,
        name=d.name,
        quantity_formula=d.quantity_formula,
        computed_quantity=d.computed_quantity,
        cost_tier=d.cost_tier,
        cost_range_low=float(d.cost_range_low),
        cost_range_high=float(d.cost_range_high),
        sourcing_type=d.sourcing_type,
        status=d.status,
        budget_item_id=d.budget_item_id,
        task_id=d.task_id,
        reasoning=d.reasoning or {}
    )


@router.post("/events/{event_id}/vibe/upload", response_model=AggregatedStyleProfileSchema, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
def upload_vibe_and_extract(
    request: Request,
    event_id: str,
    files: list[UploadFile] = File([]),
    text_description: str | None = Form(None),
    event: Event = Depends(verify_event_owner_token),
    db: Session = Depends(get_db)
) -> AggregatedStyleProfileSchema:
    """
    Uploads up to 10 inspiration images + text description.
    Batches images into a single multimodal Gemini call (DEC-023) or deterministic stub.
    Aggregates palettes, style tags, and mood words into a StyleProfile.
    """
    profile = VibeService.upload_vibe_and_extract(
        db=db,
        event_id=event_id,
        files=files,
        text_description=text_description
    )
    return format_profile_response(profile)


@router.post("/events/{event_id}/vibe/{profile_id}/generate-theme", response_model=ThemeProposalResponseSchema, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
def generate_theme(
    request: Request,
    event_id: str,
    profile_id: str,
    event: Event = Depends(verify_event_owner_token),
    db: Session = Depends(get_db)
) -> ThemeProposalResponseSchema:
    """
    Generates a concrete theme proposal with >=10 decor items with formulas, menu direction,
    playlist genres, dress codes, and invitation briefs.
    Decor item costs and quantities are calculated with Zero LLM Math using DecorCostEngine.
    """
    theme = VibeService.generate_theme(
        db=db,
        event_id=event_id,
        profile_id=profile_id
    )
    return format_theme_response(theme)


@router.get("/events/{event_id}/vibe/{profile_id}/moodboard")
def get_moodboard(
    event_id: str,
    profile_id: str,
    db: Session = Depends(get_db)
) -> Response:
    """
    Returns code-side generated Pillow mood board collage JPEG (DEC-022).
    """
    jpeg_bytes = VibeService.get_moodboard(db=db, profile_id=profile_id)
    return Response(content=jpeg_bytes, media_type="image/jpeg")


@router.post("/events/{event_id}/vibe/decor-items/{item_id}/accept", response_model=DecorItemProposalSchema)
def accept_decor_item(
    event_id: str,
    item_id: str,
    event: Event = Depends(verify_event_owner_token),
    db: Session = Depends(get_db)
) -> DecorItemProposalSchema:
    """
    Accepts an individual decor item, automatically creating a corresponding BudgetItem and Task.
    """
    item = VibeService.accept_decor_item(db=db, item_id=item_id)
    return format_decor_item_response(item)


@router.post("/events/{event_id}/vibe/decor-items/{item_id}/reject", response_model=DecorItemProposalSchema)
def reject_decor_item(
    event_id: str,
    item_id: str,
    event: Event = Depends(verify_event_owner_token),
    db: Session = Depends(get_db)
) -> DecorItemProposalSchema:
    """
    Rejects an individual decor item.
    """
    item = VibeService.reject_decor_item(db=db, item_id=item_id)
    return format_decor_item_response(item)


@router.get("/events/{event_id}/vibe/profiles", response_model=list[AggregatedStyleProfileSchema])
def list_style_profiles(
    event_id: str,
    db: Session = Depends(get_db)
) -> list[AggregatedStyleProfileSchema]:
    """
    Lists all style profiles created for an event.
    """
    profiles = db.query(StyleProfile).filter(StyleProfile.event_id == event_id).order_by(StyleProfile.created_at.desc()).all()
    return [format_profile_response(p) for p in profiles]


@router.get("/events/{event_id}/vibe/{profile_id}/themes", response_model=list[ThemeProposalResponseSchema])
def list_themes_for_profile(
    event_id: str,
    profile_id: str,
    db: Session = Depends(get_db)
) -> list[ThemeProposalResponseSchema]:
    """
    Lists theme proposals generated for a given style profile.
    """
    themes = db.query(ThemeProposal).filter(ThemeProposal.style_profile_id == profile_id).order_by(ThemeProposal.created_at.desc()).all()
    return [format_theme_response(t) for t in themes]
