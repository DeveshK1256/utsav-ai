from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.services.invitation_wording_agent import WordingVariant


class InvitationGenerateRequest(BaseModel):
    theme_proposal_id: str | None = None
    layout_variant: str = Field(
        "classic_royal", description="classic_royal, modern_minimal, or floral_festive"
    )
    wording_text: str | None = None
    wording_variant_index: int | None = None


class InvitationCardSummary(BaseModel):
    id: str
    event_id: str
    layout_variant: str
    guest_id: str | None = None
    guest_name: str | None = None
    wording_preview: str
    generated_at: datetime
    png_download_url: str
    pdf_download_url: str


class FailedGuestSummary(BaseModel):
    guest_id: str
    name: str
    reason: str


class InvitationBatchResponse(BaseModel):
    event_id: str
    layout_variant: str
    total_generated: int
    total_failed: int
    cards: list[InvitationCardSummary]
    failed_guests: list[FailedGuestSummary]


class LayoutOption(BaseModel):
    id: str
    name: str
    description: str
    recommended_for: str


class InvitationStudioOptionsResponse(BaseModel):
    layout_options: list[LayoutOption]
    palette: list[str]
    theme_name: str | None = None
    theme_proposal_id: str | None = None
    event_name: str
    host_name: str | None = None
    date_str: str
    venue_str: str
    muhurat_time: str | None = None
    ceremonies: list[str] = []
    guest_count: int = 0
    wording_options: list[WordingVariant] = []
    provider_used: str = "stub"
    fallback_warning: str | None = None
    content_review_note: str = (
        "Ceremony details and ritual wordings are AI-assisted starting baselines; "
        "please verify with your family and elders before printing."
    )
