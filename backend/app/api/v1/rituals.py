"""
Ritual & Cultural Intelligence API Endpoints (M5 - F2).
Exposes astronomical panchang calculations (DEC-027), curated tradition samagri,
cross-tradition fusion merging, and priest/guruji export formats.
"""

from datetime import date
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.models import Tradition, RitualItem, Event, SubEvent
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
    primary_tradition_code: str = Field(..., description="Primary cultural code, e.g. south_indian_iyer")
    secondary_tradition_code: str = Field(..., description="Secondary cultural code, e.g. punjabi_sikh")
    event_id: Optional[str] = None


@router.get("/panchang", response_model=PanchangResponseSchema)
def get_panchang_for_date(
    event_date: date = Query(..., description="Calendar date YYYY-MM-DD"),
    latitude: float = Query(28.6139, description="Venue latitude (-90 to 90)"),
    longitude: float = Query(77.2090, description="Venue longitude (-180 to 180)"),
    elevation_meters: float = Query(216.0, description="Venue elevation above sea level in meters"),
):
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
    return res


@router.get("/traditions")
def list_curated_traditions(db: Session = Depends(get_db)):
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
def get_tradition_samagri(code: str, db: Session = Depends(get_db)):
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
def merge_dual_traditions(payload: MergeTraditionsRequest, db: Session = Depends(get_db)):
    """
    Reconciles two distinct cultural traditions into an integrated schedule and samagri list.
    Tags source traditions, combines shared sacred items, detects conflicts, and creates elder alignment points.
    """
    service = TraditionMergeService(db)
    event_name = None
    if payload.event_id:
        event = db.query(Event).filter(Event.id == payload.event_id).first()
        if event:
            event_name = event.name
            # If requested, attach secondary tradition to event record
            event.secondary_tradition_code = payload.secondary_tradition_code
            db.commit()

    try:
        merged = service.merge_traditions(
            primary_code=payload.primary_tradition_code,
            secondary_code=payload.secondary_tradition_code,
            event_name=event_name
        )
        return merged
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/events/{event_id}/pandit-guide")
def generate_pandit_guide(event_id: str, db: Session = Depends(get_db)):
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
            "location_name": se.location_name,
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
        "disclaimer": panchang["priest_disclaimer"],
    }
