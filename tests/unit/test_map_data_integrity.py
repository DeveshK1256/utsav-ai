import pytest
import uuid
import re
import random
from datetime import date, timedelta
from backend.app.services.discovery_service import (
    is_valid_venue_name,
    extract_distinctive_tokens,
    VendorDiscoveryService,
    haversine_distance_km
)
from backend.app.models.models import VendorProfile, Event, User
from backend.app.api.v1.events import update_event_compose_progress, ComposeUpdateSchema
from backend.app.db.session import SessionLocal


def test_filter_nameless_and_garbage_osm_results():
    """
    Check 2: Filter nameless/garbage OSM results.
    Confirms raw OSM identifiers ('node/...'), pure addresses/numbers ('14/2'),
    empty strings, and generic placeholders are excluded.
    """
    # Garbage / Invalid candidates that MUST be excluded
    invalid_cases = [
        "OSM node/8097211828",
        "node/10968771876",
        "way/274027021",
        "relation/99812",
        "osm node 12345",
        "14/2",
        "101",
        "---",
        "   ",
        None,
        "unnamed",
        "unknown",
        "venue",
        "hotel",
        "hall"
    ]
    for case in invalid_cases:
        assert not is_valid_venue_name(case), f"Expected '{case}' to be invalid, but passed filter"

    # Valid celebration venues that MUST be retained
    valid_cases = [
        "Akshay Dham Marriage Garden",
        "Waghela Ji Marriage Garden",
        "Jashn Banquet Hall",
        "The Banquet Hall",
        "Princess Academy Kalyana Mantapa",
        "Shri Ganga Marriage Garden",
        "Rambagh Palace"
    ]
    for case in valid_cases:
        assert is_valid_venue_name(case), f"Expected '{case}' to be valid, but was rejected by filter"


def test_deduplication_rambagh_palace_overlapping_test_case():
    """
    Check 1: Dedup check (Positive Match).
    Confirms that when Rambagh Palace exists in the curated seed list,
    any overlapping Overpass candidate (e.g. 'The Rambagh Palace, Jaipur' 20 meters away)
    is deduplicated down so a physical venue NEVER appears twice.
    Reports the before (2 candidates) vs after (1 candidate) deduplication count.
    """
    db = SessionLocal()
    
    # 1. Locate the permanent curated Rambagh Palace seed in the database
    seed = db.query(VendorProfile).filter(
        VendorProfile.business_name == "Rambagh Palace",
        VendorProfile.city == "Jaipur"
    ).first()
    assert seed is not None, "Permanent curated seed for Rambagh Palace not found in DB"
    
    # 2. Insert a temporary synthetic Overpass duplicate (20 meters away, with noise prefix/city)
    osm_id = str(uuid.uuid4())
    osm_node = VendorProfile(
        id=osm_id,
        business_name="The Rambagh Palace, Jaipur",
        category="venue",
        city="Jaipur",
        city_tier="tier_2",
        latitude=26.8972,
        longitude=75.8071,
        source_notes="OpenStreetMap (Real OSM Record: node/12345678)"
    )
    db.add(osm_node)
    db.commit()

    try:
        # Before deduplication: 2 distinct candidate rows exist in DB within 300m
        raw_candidates = db.query(VendorProfile).filter(
            VendorProfile.id.in_([seed.id, osm_id])
        ).all()
        before_count = len(raw_candidates)
        assert before_count == 2, f"Expected 2 raw candidates before deduplication, got {before_count}"

        # Run search centered on Rambagh Palace coordinates
        res = VendorDiscoveryService.search_vendors(
            db=db,
            lat=26.8970,
            lng=75.8070,
            city="Jaipur",
            radius_km=2.0
        )

        # Filter results matching Rambagh
        rambagh_results = [r for r in res.results if "rambagh" in r.business_name.lower()]
        after_count = len(rambagh_results)

        print(f"\n[DEDUP POSITIVE REPORT] Before deduplication: {before_count} candidates -> After deduplication: {after_count} venue")
        assert after_count == 1, f"Expected exactly 1 deduplicated venue, got {after_count}"
        
        # Verify the retained venue is the curated seed, not the uncurated OSM node
        retained = rambagh_results[0]
        assert retained.id == seed.id
        assert retained.business_name == "Rambagh Palace"
        assert "pickyourtrail" in retained.source_notes

    finally:
        db.query(VendorProfile).filter(VendorProfile.id == osm_id).delete(synchronize_session=False)
        db.commit()
        db.close()


def test_distinct_venues_not_overmerged_within_350m():
    """
    Check 1b: Anti-Overmerging Protection (Negative Match).
    Confirms that genuinely different venues within 350m sharing common words
    (e.g., 'Bharti Banquet & Lawn' vs 'Bharti Vihar Community Hall', or
    'Shree Ganesh Banquet Hall' vs 'Shree Krishna Banquet Hall')
    are NOT erroneously collapsed into one. Both must be preserved as separate pins.
    """
    from backend.app.services.discovery_service import are_venues_duplicates
    
    # 1. Pure unit tests with are_venues_duplicates
    # Case A: Two different "X Banquet Hall" businesses sharing the honorific prefix 'Shree'
    assert not are_venues_duplicates(
        "Shree Ganesh Banquet Hall", 18.5200, 73.8560,
        "Shree Krishna Banquet Hall", 18.5210, 73.8570
    ), "Two distinct halls sharing 'Shree' were incorrectly flagged as duplicates"

    # Case B: Two venues with generic modifier 'Royal' vs 'Grand'
    assert not are_venues_duplicates(
        "Royal Banquet Hall", 18.5200, 73.8560,
        "Grand Banquet Hall", 18.5210, 73.8570
    ), "'Royal Banquet' and 'Grand Banquet' were incorrectly flagged as duplicates"

    # Case C: Bharti Banquet & Lawn vs nearby Bharti Vihar Community Hall
    assert not are_venues_duplicates(
        "Bharti Banquet & Lawn", 18.4610, 73.8510,
        "Bharti Vihar Community Hall", 18.4622, 73.8522
    ), "'Bharti Banquet & Lawn' and 'Bharti Vihar Community Hall' were incorrectly flagged as duplicates"

    # 2. Database End-to-End Search Test in Pune near Bharti Banquet
    db = SessionLocal()
    venue_a_id = str(uuid.uuid4())
    venue_b_id = str(uuid.uuid4())

    # Venue A: Seeded/curated Bharti Banquet & Lawn
    venue_a = VendorProfile(
        id=venue_a_id,
        business_name="Bharti Banquet & Lawn",
        category="venue",
        city="Pune",
        city_tier="tier_2",
        latitude=18.4610,
        longitude=73.8510,
        source_notes="venuelook.com Pune locality listings; locality centroid approximation."
    )

    # Venue B: Distinct nearby community trust hall 180 meters away
    venue_b = VendorProfile(
        id=venue_b_id,
        business_name="Bharti Vihar Community Hall",
        category="community_centre",
        city="Pune",
        city_tier="tier_2",
        latitude=18.4622,
        longitude=73.8522,
        source_notes="OpenStreetMap (Real OSM Record: node/777888999)"
    )

    db.add(venue_a)
    db.add(venue_b)
    db.commit()

    try:
        # Distance between A and B is ~180 meters
        dist_between = haversine_distance_km(18.4610, 73.8510, 18.4622, 73.8522)
        assert dist_between <= 0.35, f"Expected proximity <= 350m, got {dist_between} km"

        res = VendorDiscoveryService.search_vendors(
            db=db,
            lat=18.4610,
            lng=73.8510,
            city="Pune",
            radius_km=1.0
        )

        # Retrieve both venues
        bharti_results = [r for r in res.results if "bharti" in r.business_name.lower()]
        returned_names = {r.business_name for r in bharti_results}

        print(f"\n[ANTI-OVERMERGE REPORT] Input candidates: 2 distinct venues -> Output: {len(bharti_results)} venues preserved: {returned_names}")
        assert len(bharti_results) >= 2, f"Expected at least 2 distinct venues, got {len(bharti_results)}"
        assert "Bharti Banquet & Lawn" in returned_names
        assert "Bharti Vihar Community Hall" in returned_names

    finally:
        db.query(VendorProfile).filter(VendorProfile.id.in_([venue_a_id, venue_b_id])).delete(synchronize_session=False)
        db.commit()
        db.close()


def test_selection_time_permanent_vendor_persistence():
    """
    Check 3: Persistence check.
    When a user selects an OSM-discovered venue not previously in vendor_profiles,
    POST /events/{id}/compose dynamically INSERTS a real, permanent row into vendor_profiles
    so it has a genuine database identity for future quotes (F5) and reviews (F12).
    """
    db = SessionLocal()
    try:
        phone = f"+9194{random.randint(10000000, 99999999)}"
        user = User(phone_number=phone, full_name="Persistence Host", role="host")
        db.add(user)
        db.commit()
        db.refresh(user)

        event = Event(
            owner_id=user.id,
            name="Persistence Verification Wedding",
            event_type="wedding",
            guest_count=200,
            total_budget=1500000.0,
            city="Bengaluru",
            pincode="560001",
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=31),
            owner_token="test_owner_token_123",
            metadata_json={}
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        # Synthetic OSM node UUID not in vendor_profiles
        test_osm_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, "osm_node_test_selection_persist_9999"))
        
        # Confirm it does NOT exist before selection
        existing = db.query(VendorProfile).filter(VendorProfile.id == test_osm_uuid).first()
        if existing:
            db.delete(existing)
            db.commit()

        # Selection call via update_event_compose_progress
        payload = ComposeUpdateSchema(
            step="venue",
            vendor_profile_id=test_osm_uuid,
            venue_name="Sambhram Kalyana Mantapa",
            venue_locality="Malleswaram",
            venue_city="Bengaluru",
            latitude=13.0034,
            longitude=77.5689,
            osm_id="node/9999999",
            source_notes="OpenStreetMap (Real OSM Record: node/9999999)"
        )

        updated_event = update_event_compose_progress(
            event_id=event.id,
            payload=payload,
            event=event,
            db=db
        )

        # Verify permanent row now exists in vendor_profiles table!
        persisted = db.query(VendorProfile).filter(VendorProfile.id == test_osm_uuid).first()
        assert persisted is not None, "Vendor profile was NOT persisted to database at selection time!"
        assert persisted.id == test_osm_uuid
        assert persisted.business_name == "Sambhram Kalyana Mantapa"
        assert persisted.city == "Bengaluru"
        assert persisted.locality == "Malleswaram"
        assert float(persisted.latitude) == 13.0034
        assert float(persisted.longitude) == 77.5689
        assert persisted.is_verified_profile is False
        assert persisted.average_rating is None
        assert persisted.rating_count == 0
        assert persisted.coordinate_precision == "exact_osm_node"
        assert "OpenStreetMap" in persisted.source_notes

        # Verify compose_state references the persisted profile ID
        meta = updated_event.metadata_json or {}
        compose_state = meta.get("compose_celebration", {})
        assert compose_state.get("vendor_profile_id") == test_osm_uuid
        assert compose_state.get("venue_name") == "Sambhram Kalyana Mantapa"
        assert compose_state.get("venue_status") == "shortlist_pick"

        # Cleanup
        db.delete(persisted)
        db.delete(event)
        db.delete(user)
        db.commit()
    finally:
        db.close()


def test_cost_honesty_discipline():
    """
    Check 4: Cost honesty check.
    Confirms discovery items return is_estimate=True and limited_data=True
    with estimated_cost_display='Limited data' for both seed and OSM venues.
    """
    # Seed mock
    seed_profile = VendorProfile(
        id=str(uuid.uuid4()),
        business_name="Curated Palace Jaipur",
        category="palace",
        city="Jaipur",
        city_tier="tier_2",
        latitude=26.9124,
        longitude=75.7873,
        is_verified_profile=True,
        source_notes="pickyourtrail.com curated seed"
    )
    seed_item = VendorDiscoveryService._profile_to_item(seed_profile, distance_km=1.2)
    assert seed_item.cost_estimate.is_estimate is True
    assert seed_item.cost_estimate.limited_data is True
    assert seed_item.cost_estimate.estimated_cost_display == "Limited data"

    # OSM mock
    osm_profile = VendorProfile(
        id=str(uuid.uuid4()),
        business_name="Bengaluru Kalyana Mantapa",
        category="venue",
        city="Bengaluru",
        city_tier="tier_1",
        latitude=12.9716,
        longitude=77.5946,
        is_verified_profile=False,
        source_notes="OpenStreetMap (Real OSM Record: node/12345)"
    )
    osm_item = VendorDiscoveryService._profile_to_item(osm_profile, distance_km=3.5)
    assert osm_item.cost_estimate.is_estimate is True
    assert osm_item.cost_estimate.limited_data is True
    assert osm_item.cost_estimate.estimated_cost_display == "Limited data"
