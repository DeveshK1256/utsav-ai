from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from backend.app.db.session import get_db
from backend.app.schemas.intake import IntakeRequestSchema, MasterPlanResponseSchema
from backend.app.services.intake_service import IntakeService
from backend.app.models.models import Tradition

router = APIRouter(prefix="/intake", tags=["Intake"])


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
