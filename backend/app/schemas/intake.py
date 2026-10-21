from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class BudgetCalculationRequestSchema(BaseModel):
    total_budget: float = Field(..., gt=0, description="Target Budget Envelope in INR")
    event_type: str = Field(default="wedding", description="Celebration Type")
    city: str = Field(default="Pune", description="City for cost tier calibration")
    guest_count: int = Field(default=350, gt=0, description="Estimated Headcount")


class BudgetItemCalculationSchema(BaseModel):
    category: str
    percentage: float
    planned_amount: float
    city_tier: str
    city_tier_multiplier: float
    reasoning_spec: Dict[str, Any]


class BudgetCalculationResponseSchema(BaseModel):
    city: str
    city_tier: str
    city_tier_multiplier: float
    total_budget: float
    scaled_envelope: float
    items: List[BudgetItemCalculationSchema]


class IntakeRequestSchema(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Celebration Name")
    host_name: str = Field(..., min_length=2, max_length=150, description="Primary Host / Couple Name")
    phone_number: str = Field(..., description="Indian E.164 Phone Number")
    event_type: str = Field(default="wedding", description="Celebration Type (wedding, puja, community_festival, etc.)")
    tradition_code: str = Field(default="maharashtrian_vedic", description="Cultural Tradition Code")
    guest_count: int = Field(..., gt=0, description="Estimated Total Guest Count")
    total_budget: float = Field(..., ge=0, description="Total Target Budget Envelope in INR")
    city: str = Field(..., min_length=2, description="Target Celebration City")
    pincode: str = Field(..., min_length=4, max_length=10, description="Area Pincode")
    start_date: date = Field(..., description="Celebration Start Date")
    end_date: date = Field(..., description="Celebration End Date")

    @field_validator("end_date")
    @classmethod
    def validate_dates(cls, end_date_val: date, info):
        start_date_val = info.data.get("start_date")
        if start_date_val and end_date_val < start_date_val:
            raise ValueError("end_date cannot be earlier than start_date")
        return end_date_val


class SubEventResponseSchema(BaseModel):
    id: str
    name: str
    start_time: datetime
    end_time: datetime
    venue_name: str
    is_outdoor: bool
    is_muhurat_locked: bool
    muhurat_notes: Optional[str] = None
    sort_order: int


class BudgetItemResponseSchema(BaseModel):
    id: str
    category: str
    name: str
    planned_amount: float
    actual_amount: float
    percentage: float
    reasoning_spec: Optional[Dict[str, Any]] = None


class TaskResponseSchema(BaseModel):
    id: str
    title: str
    status: str
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    assigned_role: Optional[str] = None


class MasterPlanResponseSchema(BaseModel):
    event_id: str
    name: str
    owner_name: str
    status: str
    city_tier: str
    total_budget: float
    guest_count: int
    tradition_code: str
    elder_verification_disclaimer: str = (
        "Auspicious timings & ritual checklists are algorithmic estimates computed via astronomical "
        "ephemeris models. Please verify with your family Guruji or elders."
    )
    sub_events: List[SubEventResponseSchema]
    budget_breakdown: List[BudgetItemResponseSchema]
    tasks: List[TaskResponseSchema]
    created_at: datetime
