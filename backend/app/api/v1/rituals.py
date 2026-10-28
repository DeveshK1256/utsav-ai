from typing import Any

"""
Ritual & Cultural Intelligence API Endpoints (M5 - F2).
Exposes astronomical panchang calculations (DEC-027), curated tradition samagri,
cross-tradition fusion merging, and priest/guruji export formats.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.core.security import verify_event_owner_token
from backend.app.db.session import get_db
from backend.app.models.models import Event, RitualItem, SubEvent, Tradition
from backend.app.services.panchang_service import default_panchang_provider
from backend.app.services.tradition_merge_service import TraditionMergeService

router = APIRouter(prefix="/rituals", tags=["Ritual & Cultural Intelligence"])


# Pydantic Schemas
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
    primary_tradition_code: str = Field(..., description="Primary cultural code, e.g. maharashtrian_vedic")
    secondary_tradition_code: str = Field(..., description="Secondary cultural code, e.g. punjabi_traditional")
    start_date: date | None = None
    event_id: str | None = None
    notes: str | None = None


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
            detail="Latitude must be in [-90, 90] and longitude in [-180, 180]"
        )

    res = default_panchang_provider.calculate_panchang(
        event_date=event_date,
        latitude=latitude,
        longitude=longitude,
        elevation_meters=elevation_meters
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tradition '{code}' not found")

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
            f"This samagri list was AI-drafted as a starting point based on general knowledge of {tradition.regional_name} customs. "
            "It has not been reviewed by a priest or community elder and may contain errors, omissions, or regionally inappropriate details. "
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
        ]
    }


@router.post("/merge-traditions")
def merge_dual_traditions(payload: MergeTraditionsRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Reconciles two distinct cultural traditions into an integrated schedule and samagri list.
    Tags source traditions, combines shared sacred items, detects conflicts, and creates elder alignment points.
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
            notes=payload.notes
        )
        return merged
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/events/{event_id}/generate-tasks")
def generate_ritual_tasks_for_event(
    event_id: str,
    event: Event = Depends(verify_event_owner_token),
    db: Session = Depends(get_db)
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
        db=db
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
            assigned_role=t_data["assigned_role"]
        )
        db.add(task_obj)
        created_tasks.append({
            "id": task_obj.id,
            "title": task_obj.title,
            "scheduled_start": task_obj.scheduled_start.isoformat(),
            "assigned_role": task_obj.assigned_role,
        })

    db.commit()
    return {
        "status": "success",
        "event_id": event.id,
        "tasks_created_count": len(created_tasks),
        "tasks": created_tasks
    }


@router.get("/muhurat-candidates")
def get_muhurat_candidates(
    event_date: date = Query(..., description="Date YYYY-MM-DD"),
    latitude: float = Query(28.6139, description="Venue latitude"),
    longitude: float = Query(77.2090, description="Venue longitude"),
    elevation_meters: float = Query(216.0, description="Elevation in meters")
) -> dict[str, Any]:
    """
    Calculates 3 auspicious candidate muhurat windows (Morning Brahma/Pratah, Midday Abhijit, Evening Godhuli/Twilight)
    alongside inauspicious Rahu Kaal prohibitions and mandatory priest verification disclaimer.
    """
    p_data = default_panchang_provider.calculate_panchang(
        event_date=event_date,
        latitude=latitude,
        longitude=longitude,
        elevation_meters=elevation_meters
    )

    from datetime import datetime, timedelta
    sunrise_dt = datetime.strptime(p_data["sunrise"], "%H:%M:%S")

    # Morning auspicious window: 1.5h to 3.5h post-sunrise
    m1_start = (sunrise_dt + timedelta(hours=1, minutes=30)).strftime("%H:%M")
    m1_end = (sunrise_dt + timedelta(hours=3, minutes=30)).strftime("%H:%M")

    # Twilight Godhuli window: 24 min before to 24 min after sunset
    sunset_dt = datetime.strptime(p_data["sunset"], "%H:%M:%S")
    m3_start = (sunset_dt - timedelta(minutes=24)).strftime("%H:%M")
    m3_end = (sunset_dt + timedelta(minutes=24)).strftime("%H:%M")

    candidates = [
        {
            "id": "muhurat-morning",
            "name": "Pratah Kaal / Morning Vivah Muhurat",
            "window": f"{m1_start} - {m1_end}",
            "suitability": "Highly Auspicious",
            "planetary_rationale": f"Solar energy ascendant, {p_data['tithi']['name']} active, favorable nakshatra alignment.",
            "is_recommended": True,
        },
        {
            "id": "muhurat-abhijit",
            "name": "Abhijit Muhurat (Midday Solar Zenith)",
            "window": f"{p_data['abhijit_muhurat']['start'][:5]} - {p_data['abhijit_muhurat']['end'][:5]}",
            "suitability": "Auspicious (Universal Victory Muhurat)" if p_data["abhijit_muhurat"]["is_auspicious"] else "Caution on Wednesdays",
            "planetary_rationale": "8th Muhurat of daytime, removes blemishes except when falling on Wednesdays.",
            "is_recommended": p_data["abhijit_muhurat"]["is_auspicious"],
        },
        {
            "id": "muhurat-godhuli",
            "name": "Godhuli Bela (Twilight Sacred Window)",
            "window": f"{m3_start} - {m3_end}",
            "suitability": "Auspicious Evening Horizon",
            "planetary_rationale": "Sacred twilight transition, revered across Vedic, Rajasthani, and Bengali traditions.",
            "is_recommended": False,
        }
    ]

    return {
        "event_date": event_date.isoformat(),
        "sunrise": p_data["sunrise"],
        "sunset": p_data["sunset"],
        "rahu_kaal_prohibited_window": f"{p_data['rahu_kaal']['start'][:5]} - {p_data['rahu_kaal']['end'][:5]}",
        "tithi": p_data["tithi"],
        "nakshatra": p_data["nakshatra"],
        "candidates": candidates,
        "elevated_disclaimer": p_data["priest_disclaimer"]
    }


@router.get("/events/{event_id}/pandit-guide")
def generate_pandit_guide(event_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Generates a print-ready, priest-tailored ceremonial guide for an event.
    Includes date, local panchang & muhurat calculations, ritual sequence, and itemized samagri.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    # City coordinates approximation (Delhi default if unknown)
    city_coords = {
        "mumbai": (19.0760, 72.8777, 14.0),
        "delhi": (28.6139, 77.2090, 216.0),
        "new delhi": (28.6139, 77.2090, 216.0),
        "bengaluru": (12.9716, 77.5946, 920.0),
        "bangalore": (12.9716, 77.5946, 920.0),
    }
    lat, lon, elev = city_coords.get(event.city.lower(), (28.6139, 77.2090, 216.0))

    # Calculate astronomical panchang for event start date
    panchang = default_panchang_provider.calculate_panchang(
        event_date=event.start_date,
        latitude=lat,
        longitude=lon,
        elevation_meters=elev
    )

    # Sub-events / Itinerary
    sub_events = db.query(SubEvent).filter(SubEvent.event_id == event_id).order_by(SubEvent.sort_order).all()
    itinerary_summary = [
        {
            "name": se.name,
            "start_time": se.start_time.isoformat() if se.start_time else None,
            "end_time": se.end_time.isoformat() if se.end_time else None,
            "location_name": se.venue_name,
            "is_outdoor": se.is_outdoor,
        }
        for se in sub_events
    ]

    # Samagri: check if dual tradition or single tradition
    if event.secondary_tradition_code and event.tradition_code:
        service = TraditionMergeService(db)
        merge_res = service.merge_traditions(event.tradition_code, event.secondary_tradition_code)
        samagri_items = merge_res["samagri_items"]
        alignment_points = merge_res["family_alignment_points"]
        tradition_summary = f"{merge_res['primary_tradition']['name']} & {merge_res['secondary_tradition']['name']}"
    elif event.tradition_code:
        tradition = db.query(Tradition).filter(Tradition.code == event.tradition_code).first()
        raw_items = db.query(RitualItem).filter(RitualItem.tradition_code == event.tradition_code).all()
        samagri_items = [
            {
                "item_name": i.item_name,
                "regional_name": i.regional_name,
                "standard_quantity": i.standard_quantity,
                "category": i.category,
                "spiritual_purpose": i.spiritual_purpose,
                "ritual_name": i.ritual_name,
                "is_verified": i.is_verified,
                "source_tradition": tradition.regional_name if tradition else "Traditional",
            }
            for i in raw_items
        ]
        alignment_points = []
        tradition_summary = tradition.regional_name if tradition else "Custom / Standard"
    else:
        samagri_items = []
        alignment_points = []
        tradition_summary = "Custom / Secular"

    return {
        "event_id": event.id,
        "event_name": event.name,
        "city": event.city,
        "event_date": event.start_date.isoformat(),
        "tradition": tradition_summary,
        "panchang_and_muhurat": panchang,
        "itinerary_sequence": itinerary_summary,
        "samagri_checklist": samagri_items,
        "family_alignment_points": alignment_points,
        "priest_notes": (
            "This document is prepared for the officiating Panditji / Guruji / Vadhyar. "
            "Please review all samagri quantities against local family kul-parampara."
        ),
        "content_accuracy_disclaimer": (
            f"This ceremonial sequence and samagri list were AI-drafted as a starting point based on general cultural knowledge of {tradition_summary} customs. "
            "It has NOT been reviewed by any priest, pandit, community elder, or religious authority and may contain errors, omissions, or regionally inappropriate details. "
            "Please review carefully with your family elders and officiant before finalizing."
        ),
        "disclaimer": panchang["priest_disclaimer"],
    }
