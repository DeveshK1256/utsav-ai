from datetime import date

from pydantic import BaseModel, Field


class PanchangResponseSchema(BaseModel):
    date: str
    location: dict
    sunrise: str
    sunset: str
    daylight_duration_seconds: int
    daylight_formatted: str
    rahu_kaal: dict
    abhijit_muhurat: dict
    tithi: dict
    nakshatra: dict
    ayanamsha: dict
    priest_disclaimer: str


class MergeTraditionsRequest(BaseModel):
    primary_tradition_code: str = Field(
        ..., description="Primary cultural code, e.g. maharashtrian_vedic"
    )
    secondary_tradition_code: str = Field(
        ..., description="Secondary cultural code, e.g. punjabi_traditional"
    )
    start_date: date | None = None
    event_id: str | None = None
    notes: str | None = None
