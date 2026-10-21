from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from backend.app.db.session import get_db
from backend.app.schemas.intake import (
    IntakeRequestSchema,
    MasterPlanResponseSchema,
    BudgetCalculationRequestSchema,
    BudgetCalculationResponseSchema,
    BudgetItemCalculationSchema
)
from backend.app.services.intake_service import IntakeService
from backend.app.services.budget_engine import BudgetScalingEngine
from backend.app.models.models import Tradition

router = APIRouter(prefix="/intake", tags=["Intake"])


@router.post("/calculate-budget", response_model=BudgetCalculationResponseSchema)
def calculate_budget(payload: BudgetCalculationRequestSchema):
    """
    Computes deterministic city-tier scaled budget allocation.
    Single authoritative backend calculation engine called by frontend clients.
    """
    try:
        tier = BudgetScalingEngine.resolve_city_tier(payload.city)
        multiplier = float(BudgetScalingEngine.get_tier_multiplier(tier))
        scaled_envelope = round(payload.total_budget * multiplier, 2)
        allocations = BudgetScalingEngine.compute_budget_allocation(
            total_envelope=payload.total_budget,
            event_type=payload.event_type,
            city=payload.city,
            guest_count=payload.guest_count
        )
        return BudgetCalculationResponseSchema(
            city=payload.city,
            city_tier=tier,
            city_tier_multiplier=multiplier,
            total_budget=payload.total_budget,
            scaled_envelope=scaled_envelope,
            items=[
                BudgetItemCalculationSchema(
                    category=item["category"],
                    percentage=item["percentage"],
                    planned_amount=item["planned_amount"],
                    city_tier=item["city_tier"],
                    city_tier_multiplier=item["city_tier_multiplier"],
                    reasoning_spec=item["reasoning_spec"]
                )
                for item in allocations
            ]
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Budget calculation failed: {str(e)}")


@router.post("/generate", response_model=MasterPlanResponseSchema, status_code=status.HTTP_201_CREATED)
def generate_plan(payload: IntakeRequestSchema, db: Session = Depends(get_db)):
    """
    Submits conversational intake questionnaire and deterministically generates
    the multi-day master itinerary, itemized budget, and scheduled task dependencies.
    """
    try:
        return IntakeService.generate_master_plan(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Plan generation failed: {str(e)}")


@router.get("/traditions")
def list_traditions(db: Session = Depends(get_db)):
    """
    Lists available cultural traditions and ritual frameworks.
    """
    IntakeService.ensure_default_traditions(db)
    traditions = db.query(Tradition).all()
    return [
        {
            "code": t.code,
            "name": t.regional_name,
            "description": t.description
        }
        for t in traditions
    ]
