from pydantic import BaseModel, Field


class CeremonyItemSchema(BaseModel):
    name: str = Field(..., description="Ceremony name")
    origin_tradition: str = Field(..., description="Origin cultural lineage or 'Shared / Combined'")
    day_offset: int = Field(0, description="Day offset (0, 1, 2) from event start")
    start_time: str = Field(..., description="Time string HH:MM")
    duration_hours: float = Field(..., description="Duration in hours")
    venue_type: str = Field(..., description="Recommended venue setting")
    is_outdoor: bool = Field(False, description="Whether event is outdoor")
    is_muhurat_locked: bool = Field(
        False, description="Whether ceremony requires auspicious timing"
    )
    cultural_significance: str = Field(..., description="Cultural meaning and purpose")
    family_guidance: str | None = Field(None, description="Actionable elder alignment note")


CEREMONY_CONTENT_ACCURACY_DISCLAIMER = (
    "This sequence was AI-drafted as a starting point based on general knowledge of "
    "customs. It has not been reviewed by a priest or community elder and may contain "
    "errors, omissions, or regionally inappropriate details. Please review carefully with "
    "your family and officiant before finalizing."
)


class FamilyAlignmentPointSchema(BaseModel):
    issue: str
    description: str
    recommendation: str


class MergedRunOfShowSchema(BaseModel):
    fusion_title: str
    primary_tradition: str
    secondary_tradition: str
    ceremonies: list[CeremonyItemSchema]
    family_alignment_points: list[FamilyAlignmentPointSchema]
    content_accuracy_disclaimer: str = Field(default=CEREMONY_CONTENT_ACCURACY_DISCLAIMER)
    timing_disclaimer: str = Field(
        default=(
            "Panchang calculations are astronomical estimates based on Drik Ganita and "
            "Ephemeris models. Muhurat dates and ritual sequences must always be confirmed "
            "with your family's trusted priest, pandit, or religious officiant."
        )
    )
    disclaimer: str = Field(default=CEREMONY_CONTENT_ACCURACY_DISCLAIMER)
