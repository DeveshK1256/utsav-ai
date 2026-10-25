import sys
import os
sys.path.insert(0, os.path.abspath("."))

from backend.app.db.session import SessionLocal
from backend.app.models.models import VendorProfile, Event
from backend.app.services.discovery_service import VendorDiscoveryService, haversine_distance_km

def audit():
    db = SessionLocal()
    print("=" * 70)
    print("DATA-INTEGRITY AUDIT ON NATIONWIDE VENUE DISCOVERY")
    print("=" * 70)

    # 1. Inspect Curated Seeds in DB
    seeds = db.query(VendorProfile).filter(
        VendorProfile.source_notes.like("%pickyourtrail%") | VendorProfile.source_notes.like("%venuelook%")
    ).all()
    print(f"\n[1] Curated Seeds in Database: {len(seeds)} total")
    for s in seeds[:5]:
        print(f"    - {s.business_name} ({s.city}) @ ({s.latitude}, {s.longitude}) | ID={s.id}")

    # 2. Check Overlap in Jaipur (e.g., Rambagh Palace)
    jaipur_res = VendorDiscoveryService.search_vendors(
        db=db,
        lat=26.9124,
        lng=75.7873,
        city="Jaipur",
        radius_km=25.0
    )
    print(f"\n[2] Jaipur Discovery Total Returned: {jaipur_res.total_results}")
    rambagh_matches = [v for v in jaipur_res.results if "rambagh" in v.business_name.lower()]
    print(f"    Venues matching 'Rambagh' in Jaipur results: {len(rambagh_matches)}")
    for rm in rambagh_matches:
        print(f"     * Name: '{rm.business_name}' | Coords: ({rm.latitude}, {rm.longitude}) | Source: {rm.source_notes}")

    # Check Pune (e.g., Conrad, JW Marriott, etc.)
    pune_res = VendorDiscoveryService.search_vendors(
        db=db,
        lat=18.5204,
        lng=73.8567,
        city="Pune",
        radius_km=25.0
    )
    print(f"\n[3] Pune Discovery Total Returned: {pune_res.total_results}")
    marriott_matches = [v for v in pune_res.results if "marriott" in v.business_name.lower()]
    print(f"    Venues matching 'Marriott' in Pune results: {len(marriott_matches)}")
    for mm in marriott_matches:
        print(f"     * Name: '{mm.business_name}' | Coords: ({mm.latitude}, {mm.longitude}) | Source: {mm.source_notes}")

    # 3. Check OSM Venue Names for Bengaluru & Indore (Nameless/Garbage Check)
    bengaluru_res = VendorDiscoveryService.search_vendors(
        db=db,
        lat=12.9716,
        lng=77.5946,
        city="Bengaluru",
        radius_km=25.0
    )
    print(f"\n[4] Bengaluru Venue Names Check: {bengaluru_res.total_results} total")
    for b in bengaluru_res.results:
        print(f"     * ID: {b.id[:18]}... | Name: '{b.business_name}' | Locality: {b.locality} | Coords: ({b.latitude}, {b.longitude})")

    indore_res = VendorDiscoveryService.search_vendors(
        db=db,
        lat=22.7196,
        lng=75.8577,
        city="Indore",
        radius_km=25.0
    )
    print(f"\n[5] Indore Venue Names Check: {indore_res.total_results} total")
    for ind in indore_res.results:
        print(f"     * ID: {ind.id[:18]}... | Name: '{ind.business_name}' | Locality: {ind.locality} | Coords: ({ind.latitude}, {ind.longitude})")

    # 4. Check Cost Estimate on all items
    sample_items = jaipur_res.results[:3] + bengaluru_res.results[:3]
    print(f"\n[6] Cost Estimate Inspection (Jaipur seeds + Bengaluru OSM):")
    for si in sample_items:
        print(f"     * {si.business_name} -> is_estimate={si.cost_estimate.is_estimate}, limited_data={si.cost_estimate.limited_data}, display='{si.cost_estimate.estimated_cost_display}'")

    db.close()

if __name__ == "__main__":
    audit()
