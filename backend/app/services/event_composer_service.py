from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.models.models import Event, SubEvent, VendorProfile
from backend.app.schemas.events import ComposeUpdateSchema


def build_dynamic_osm_vendor(payload: ComposeUpdateSchema, event: Event) -> VendorProfile:
    source = (
        payload.source_notes
        or f"OpenStreetMap Selected (OSM Record: {payload.osm_id or 'user_selection'})"
    )
    addr_meta = {"address": payload.venue_address} if payload.venue_address else {}
    precision = "exact_osm_node" if payload.latitude else "locality_approximate"
    tier = getattr(event, "city_tier", None) or "tier_2"
    city = (payload.venue_city or event.city or "Nearby")[:100]
    loc = payload.venue_locality[:150] if payload.venue_locality else None
    return VendorProfile(
        id=payload.vendor_profile_id,
        business_name=payload.venue_name.strip()[:200] if payload.venue_name else "Venue",
        category="venue",
        latitude=payload.latitude,
        longitude=payload.longitude,
        city=city,
        locality=loc,
        city_tier=tier,
        is_verified_profile=False,
        average_rating=None,
        rating_count=0,
        coordinate_precision=precision,
        source_notes=source,
        metadata_json=addr_meta,
    )


def resolve_or_create_vendor_profile(
    payload: ComposeUpdateSchema, event: Event, db: Session
) -> VendorProfile:
    vendor = db.query(VendorProfile).filter(VendorProfile.id == payload.vendor_profile_id).first()
    if vendor:
        return vendor

    if not payload.venue_name:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Vendor profile with ID '{payload.vendor_profile_id}' "
                "not found in discovery directory"
            ),
        )

    new_vendor = build_dynamic_osm_vendor(payload, event)
    db.add(new_vendor)
    db.commit()
    db.refresh(new_vendor)
    return new_vendor


def update_event_fact_sheet_venue(
    event: Event, payload: ComposeUpdateSchema, vendor: VendorProfile
) -> None:
    if not event.fact_sheet:
        return
    if payload.venue_address:
        event.fact_sheet.venue_address = payload.venue_address
    elif vendor.locality:
        event.fact_sheet.venue_address = f"{vendor.business_name}, {vendor.locality}, {vendor.city}"


def handle_compose_venue_selection(
    payload: ComposeUpdateSchema,
    event: Event,
    compose_state: dict[str, Any],
    meta: dict[str, Any],
    db: Session,
) -> None:
    if payload.skip_venue:
        compose_state["venue_skipped"] = True
        for k in (
            "vendor_profile_id",
            "venue_name",
            "venue_locality",
            "venue_city",
            "venue_status",
        ):
            compose_state.pop(k, None)
        meta.pop("venue", None)
        return

    if not payload.vendor_profile_id:
        if payload.step == "venue":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Step A venue selection requires a valid vendor_profile_id "
                    "from the discovery directory (or skip_venue: true)"
                ),
            )
        return

    vendor = resolve_or_create_vendor_profile(payload, event, db)
    venue_display = (
        f"{vendor.business_name}, {vendor.locality}" if vendor.locality else vendor.business_name
    )
    meta["venue"] = venue_display
    compose_state["vendor_profile_id"] = vendor.id
    compose_state["venue_name"] = vendor.business_name
    compose_state["venue_locality"] = vendor.locality
    compose_state["venue_city"] = vendor.city
    compose_state["venue_status"] = "shortlist_pick"
    compose_state["venue_skipped"] = False

    update_event_fact_sheet_venue(event, payload, vendor)


def handle_compose_timing_selection(
    payload: ComposeUpdateSchema,
    event: Event,
    compose_state: dict[str, Any],
    meta: dict[str, Any],
    db: Session,
) -> None:
    if payload.skip_timing:
        compose_state["timing_skipped"] = True
        meta.pop("muhurat_time", None)
        compose_state["muhurat_locked"] = False
        return

    if not payload.muhurat_time:
        return

    meta["muhurat_time"] = payload.muhurat_time
    compose_state["muhurat_time"] = payload.muhurat_time
    compose_state["muhurat_locked"] = True
    compose_state["timing_skipped"] = False

    target_sub = None
    if payload.sub_event_name:
        target_sub = (
            db.query(SubEvent)
            .filter(
                SubEvent.event_id == event.id, SubEvent.name.ilike(f"%{payload.sub_event_name}%")
            )
            .first()
        )
    if not target_sub:
        target_sub = (
            db.query(SubEvent)
            .filter(SubEvent.event_id == event.id)
            .order_by(SubEvent.start_time)
            .first()
        )

    if target_sub:
        target_sub.is_muhurat_locked = True
        if payload.muhurat_notes:
            target_sub.muhurat_notes = payload.muhurat_notes
        db.add(target_sub)
