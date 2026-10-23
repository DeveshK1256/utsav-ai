from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from backend.app.services.invitation_wording_agent import WordingVariant


class InvitationGenerateRequest(BaseModel):
    theme_proposal_id: Optional[str] = None
    layout_variant: str = Field("classic_royal", description="classic_royal, modern_minimal, or floral_festive")
    wording_text: Optional[str] = None
    wording_variant_index: Optional[int] = None


class InvitationCardSummary(BaseModel):
    id: str
    event_id: str
    layout_variant: str
    guest_id: Optional[str] = None
    guest_name: Optional[str] = None
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
    cards: List[InvitationCardSummary]
    failed_guests: List[FailedGuestSummary]


class LayoutOption(BaseModel):
    id: str
    name: str
    description: str
    recommended_for: str


class InvitationStudioOptionsResponse(BaseModel):
    layout_options: List[LayoutOption]
    palette: List[str]
    theme_name: Optional[str] = None
    theme_proposal_id: Optional[str] = None
    event_name: str
    host_name: Optional[str] = None
    date_str: str
    venue_str: str
    muhurat_time: Optional[str] = None
    ceremonies: List[str] = []
    guest_count: int = 0
    wording_options: List[WordingVariant] = []
    provider_used: str = "stub"
    fallback_warning: Optional[str] = None
    content_review_note: str = (
        "Ceremony details and ritual wordings are AI-assisted starting baselines; "
        "please verify with your family and elders before printing."
    )
