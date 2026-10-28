from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SingleImageVibeSchema(BaseModel):
    palette: list[str] = Field(
        default_factory=list,
        description="Extracted dominant hex color codes, e.g. ['#FF9933', '#800020']",
    )
    style_tags: list[str] = Field(
        default_factory=list,
        description="Style descriptors, e.g. ['royal_rajasthani', 'rustic_floral']",
    )
    materials: list[str] = Field(
        default_factory=list,
        description="Physical decor materials, e.g. ['brass', 'raw_silk', 'marigold']",
    )
    lighting_mood: str | None = Field(
        default="warm_ambient", description="Lighting atmosphere descriptor"
    )
    flower_types: list[str] = Field(
        default_factory=list,
        description="Identified flowers, e.g. ['marigold', 'rajnigandha', 'rose']",
    )


class VibeExtractionPayloadSchema(BaseModel):
    images: list[SingleImageVibeSchema] = Field(default_factory=list)
    overall_mood_words: list[str] = Field(
        default_factory=list, description="High-level mood keywords across the collage"
    )


class AggregatedStyleProfileSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    profile_id: str
    event_id: str
    extracted_palette: list[str] = Field(default_factory=list)
    style_tags: list[str] = Field(default_factory=list)
    mood_words: list[str] = Field(default_factory=list)
    text_description: str | None = None
    uploaded_image_count: int = 0
    created_at: datetime


class DecorItemProposalSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str | None = None
    category: str
    name: str
    quantity_formula: str
    computed_quantity: int = 1
    cost_tier: Literal["low", "medium", "high"] = "medium"
    cost_range_low: float = 0.0
    cost_range_high: float = 0.0
    sourcing_type: Literal["rent", "diy", "buy"] = "rent"
    status: str = "proposed"
    budget_item_id: str | None = None
    task_id: str | None = None
    reasoning: dict[str, Any] = Field(default_factory=dict)


class ThemeGenerationPayloadSchema(BaseModel):
    theme_name: str
    palette: list[str] = Field(default_factory=list)
    menu_direction: str
    playlist_genres: list[str] = Field(default_factory=list)
    dress_code_suggestion: str
    invitation_design_brief: str
    decor_items: list[DecorItemProposalSchema] = Field(default_factory=list)


class ThemeProposalResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    theme_id: str
    style_profile_id: str
    theme_name: str
    palette: list[str] = Field(default_factory=list)
    menu_direction: str | None = None
    playlist_genres: list[str] = Field(default_factory=list)
    dress_code_suggestion: str | None = None
    invitation_design_brief: str | None = None
    status: str
    decor_items: list[DecorItemProposalSchema] = Field(default_factory=list)
    provider_used: str = "gemini-3-flash-preview"
    fallback_warning: str | None = None
    created_at: datetime
