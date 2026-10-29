"""
Ritual & Cultural Intelligence API Endpoints (M5 - F2).
Exposes astronomical panchang calculations (DEC-027), curated tradition samagri,
cross-tradition fusion merging, and priest/guruji export formats.
"""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.security import verify_event_owner_token
from backend.app.db.session import get_db
from backend.app.models.models import Event, RitualItem, Tradition
from backend.app.schemas.rituals import MergeTraditionsRequest, PanchangResponseSchema
from backend.app.services.panchang_service import default_panchang_provider
from backend.app.services.ritual_guide_service import (
    build_pandit_guide_payload,
    calculate_muhurat_candidates,
)
from backend.app.services.tradition_merge_service import TraditionMergeService

router = APIRouter(prefix="/rituals", tags=["Ritual & Cultural Intelligence"])


@router.get("/panchang", response_model=PanchangResponseSchema)
def get_panchang_for_date(
    event_date: date = Query(..., description="Calendar date YYYY-MM-DD"),
    latitude: float = Query(28.6139, description="Venue latitude (-90 to 90)"),
    longitude: float = Query(77.2090, description="Venue longitude (-180 to 180)"),
    elevation_meters: float = Query(216.0, description="Venue elevation above sea level in meters"),
) -> PanchangResponseSchema:
    """
    Computes rigorous astronomical panchang parameters for a given date and venue coordinates.
    DEC-027: Deterministic ephemeris math using Chitrapaksha (Lahiri) Ayanamsha.
    """
    if not (-90.0 <= latitude <= 90.0) or not (-180.0 <= longitude <= 180.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Latitude must be in [-90, 90] and longitude in [-180, 180]",
        )

    res = default_panchang_provider.calculate_panchang(
        event_date=event_date,
        latitude=latitude,
        longitude=longitude,
        elevation_meters=elevation_meters,
    )
    return PanchangResponseSchema.model_validate(res)


@router.get("/traditions")
def list_curated_traditions(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """Lists all available cultural traditions with verification status and sources."""
    traditions = db.query(Tradition).all()
    return [
        {
            "code": t.code,
            "regional_name": t.regional_name,
            "description": t.description,
            "cultural_notes": t.cultural_notes,
            "is_verified": t.is_verified,
            "verification_source": t.verification_source,
            "item_count": len(t.ritual_items),
        }
        for t in traditions
    ]


@router.get("/traditions/{code}/samagri")
def get_tradition_samagri(code: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Retrieves full itemized samagri checklist for a given cultural tradition."""
    tradition = db.query(Tradition).filter(Tradition.code == code).first()
    if not tradition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Tradition '{code}' not found"
        )

    items = db.query(RitualItem).filter(RitualItem.tradition_code == code).all()
    return {
        "tradition": {
            "code": tradition.code,
            "regional_name": tradition.regional_name,
            "description": tradition.description,
            "is_verified": tradition.is_verified,
            "verification_source": tradition.verification_source,
        },
        "content_accuracy_disclaimer": (
            "This samagri list was AI-drafted as a starting point based on general "
            f"knowledge of {tradition.regional_name} customs. "
            "It has not been reviewed by a priest or community elder and may contain "
            "errors, omissions, or regionally inappropriate details. "
            "Please review carefully with your family and officiant before finalizing."
        ),
        "total_items": len(items),
        "items": [
            {
                "id": i.id,
                "item_name": i.item_name,
                "regional_name": i.regional_name,
                "standard_quantity": i.standard_quantity,
                "category": i.category,
                "ritual_name": i.ritual_name,
                "spiritual_purpose": i.spiritual_purpose,
                "is_verified": i.is_verified,
            }
            for i in items
        ],
    }


@router.post("/merge-traditions")
def merge_dual_traditions(
    payload: MergeTraditionsRequest, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    Reconciles two distinct cultural traditions into an integrated schedule and samagri list.
    Tags source traditions, combines shared sacred items, detects conflicts, and creates
    elder alignment points.
    """
    service = TraditionMergeService(db)
    event_name = None
    event_start = payload.start_date
    if payload.event_id:
        event = db.query(Event).filter(Event.id == payload.event_id).first()
        if event:
            event_name = event.name
            event_start = event.start_date
            event.secondary_tradition_code = payload.secondary_tradition_code
            db.commit()

    try:
        merged = service.merge_traditions(
            primary_code=payload.primary_tradition_code,
            secondary_code=payload.secondary_tradition_code,
            start_date=event_start,
            event_name=event_name,
            notes=payload.notes,
        )
        return merged
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/events/{event_id}/generate-tasks")
def generate_ritual_tasks_for_event(
    event_id: str, event: Event = Depends(verify_event_owner_token), db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    Generates structured preparation and procurement tasks for ritual samagri,
    inserting them into the event's DAG task graph.
    """
    import uuid

    from backend.app.models.models import Task
    from backend.app.services.dag_scheduler import DAGScheduler

    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    tasks_payload = DAGScheduler.generate_ritual_samagri_tasks(
        start_date_val=event.start_date,
        tradition_code=event.tradition_code or "maharashtrian_vedic",
        secondary_tradition_code=event.secondary_tradition_code,
        db=db,
    )

    created_tasks = []
    for t_data in tasks_payload:
        task_obj = Task(
            id=f"task-ritual-{uuid.uuid4().hex[:12]}",
            event_id=event.id,
            title=t_data["title"],
            description=t_data["description"],
            status="pending",
            scheduled_start=t_data["scheduled_start"],
            scheduled_end=t_data["scheduled_end"],
            duration_minutes=t_data["duration_minutes"],
            dependency_task_ids=t_data["dependency_task_ids"],
            assigned_role=t_data["assigned_role"],
        )
        db.add(task_obj)
        created_tasks.append(
            {
                "id": task_obj.id,
                "title": task_obj.title,
                "scheduled_start": task_obj.scheduled_start.isoformat(),
                "assigned_role": task_obj.assigned_role,
            }
        )

    db.commit()
    return {
        "status": "success",
        "event_id": event.id,
        "tasks_created_count": len(created_tasks),
        "tasks": created_tasks,
    }


@router.get("/muhurat-candidates")
def get_muhurat_candidates(
    event_date: date = Query(..., description="Date YYYY-MM-DD"),
    latitude: float = Query(28.6139, description="Venue latitude"),
    longitude: float = Query(77.2090, description="Venue longitude"),
    elevation_meters: float = Query(216.0, description="Elevation in meters"),
) -> dict[str, Any]:
    """
    Calculates 3 auspicious candidate muhurat windows (Morning Brahma/Pratah,
    Midday Abhijit, Evening Godhuli/Twilight) alongside inauspicious Rahu Kaal
    prohibitions and mandatory priest verification disclaimer.
    """
    return calculate_muhurat_candidates(
        event_date=event_date,
        latitude=latitude,
        longitude=longitude,
        elevation_meters=elevation_meters,
    )


@router.get("/events/{event_id}/pandit-guide")
def generate_pandit_guide(event_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Generates a print-ready, priest-tailored ceremonial guide for an event.
    Includes date, local panchang & muhurat calculations, ritual sequence, and itemized samagri.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    return build_pandit_guide_payload(event, db)
