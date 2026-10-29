from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from backend.app.models.models import Event, RitualItem, SubEvent, Tradition
from backend.app.services.panchang_service import default_panchang_provider
from backend.app.services.tradition_merge_service import TraditionMergeService


def get_city_coordinates(city: str) -> tuple[float, float, float]:
    city_coords = {
        "mumbai": (19.0760, 72.8777, 14.0),
        "delhi": (28.6139, 77.2090, 216.0),
        "new delhi": (28.6139, 77.2090, 216.0),
        "bengaluru": (12.9716, 77.5946, 920.0),
        "bangalore": (12.9716, 77.5946, 920.0),
    }
    return city_coords.get(city.lower(), (28.6139, 77.2090, 216.0))


def resolve_pandit_guide_samagri(
    event: Event, db: Session
) -> tuple[list[dict[str, Any]], list[Any], str]:
    if event.secondary_tradition_code and event.tradition_code:
        service = TraditionMergeService(db)
        merge_res = service.merge_traditions(event.tradition_code, event.secondary_tradition_code)
        tradition_summary = (
            f"{merge_res['primary_tradition']['name']} & {merge_res['secondary_tradition']['name']}"
        )
        return merge_res["samagri_items"], merge_res["family_alignment_points"], tradition_summary

    if event.tradition_code:
        tradition = db.query(Tradition).filter(Tradition.code == event.tradition_code).first()
        raw_items = (
            db.query(RitualItem).filter(RitualItem.tradition_code == event.tradition_code).all()
        )
        source_name = tradition.regional_name if tradition else "Traditional"
        items = [
            {
                "item_name": i.item_name,
                "regional_name": i.regional_name,
                "standard_quantity": i.standard_quantity,
                "category": i.category,
                "spiritual_purpose": i.spiritual_purpose,
                "ritual_name": i.ritual_name,
                "is_verified": i.is_verified,
                "source_tradition": source_name,
            }
            for i in raw_items
        ]
        tradition_summary = tradition.regional_name if tradition else "Custom / Standard"
        return items, [], tradition_summary

    return [], [], "Custom / Secular"


def calculate_muhurat_candidates(
    event_date: date, latitude: float, longitude: float, elevation_meters: float
) -> dict[str, Any]:
    p_data = default_panchang_provider.calculate_panchang(
        event_date=event_date,
        latitude=latitude,
        longitude=longitude,
        elevation_meters=elevation_meters,
    )

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
            "planetary_rationale": (
                f"Solar energy ascendant, {p_data['tithi']['name']} active, "
                "favorable nakshatra alignment."
            ),
            "is_recommended": True,
        },
        {
            "id": "muhurat-abhijit",
            "name": "Abhijit Muhurat (Midday Solar Zenith)",
            "window": (
                f"{p_data['abhijit_muhurat']['start'][:5]} - "
                f"{p_data['abhijit_muhurat']['end'][:5]}"
            ),
            "suitability": (
                "Auspicious (Universal Victory Muhurat)"
                if p_data["abhijit_muhurat"]["is_auspicious"]
                else "Caution on Wednesdays"
            ),
            "planetary_rationale": (
                "8th Muhurat of daytime, removes blemishes except when falling on Wednesdays."
            ),
            "is_recommended": p_data["abhijit_muhurat"]["is_auspicious"],
        },
        {
            "id": "muhurat-godhuli",
            "name": "Godhuli Bela (Twilight Sacred Window)",
            "window": f"{m3_start} - {m3_end}",
            "suitability": "Auspicious Evening Horizon",
            "planetary_rationale": (
                "Sacred twilight transition, revered across Vedic, Rajasthani, "
                "and Bengali traditions."
            ),
            "is_recommended": False,
        },
    ]

    return {
        "event_date": event_date.isoformat(),
        "sunrise": p_data["sunrise"],
        "sunset": p_data["sunset"],
        "rahu_kaal_prohibited_window": (
            f"{p_data['rahu_kaal']['start'][:5]} - "
            f"{p_data['rahu_kaal']['end'][:5]}"
        ),
        "tithi": p_data["tithi"],
        "nakshatra": p_data["nakshatra"],
        "candidates": candidates,
        "elevated_disclaimer": p_data["priest_disclaimer"],
    }


def build_pandit_guide_payload(event: Event, db: Session) -> dict[str, Any]:
    lat, lon, elev = get_city_coordinates(event.city)
    panchang = default_panchang_provider.calculate_panchang(
        event_date=event.start_date, latitude=lat, longitude=lon, elevation_meters=elev
    )

    sub_events = (
        db.query(SubEvent)
        .filter(SubEvent.event_id == event.id)
        .order_by(SubEvent.sort_order)
        .all()
    )
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

    samagri_items, alignment_points, tradition_summary = resolve_pandit_guide_samagri(event, db)

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
            "This ceremonial sequence and samagri list were AI-drafted as a starting point "
            f"based on general cultural knowledge of {tradition_summary} customs. "
            "It has NOT been reviewed by any priest, pandit, community elder, or religious "
            "authority and may contain errors, omissions, or regionally inappropriate details. "
            "Please review carefully with your family elders and officiant before finalizing."
        ),
        "disclaimer": panchang["priest_disclaimer"],
    }
