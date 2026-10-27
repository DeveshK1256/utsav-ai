"""
Seed script for F15-Lite Vendor & Venue Discovery.
Populates vendor_profiles with 19 real venues across Jaipur (11) and Pune (8).

Sources:
- pickyourtrail.com Jaipur wedding venues list
- venuelook.com Sanganer & Pune locality listings
- sarovarhotels.com Golden Tulip Kukas page
- odoo.com Hadapsar venue page

Honesty Annotations:
1. Coordinates are locality-centroid approximations, not verified geocoded street addresses.
2. `is_verified_profile` is set to False for every entry.
3. `coordinate_precision` is set to 'locality_approximate'.
4. `average_rating` is NULL and `rating_count` is 0 (DEC-013 cold start).
"""

import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from backend.app.db.session import engine, SessionLocal
from backend.app.models.models import VendorProfile, Base

SEED_VENUES = [
    # Jaipur (11 venues)
    {
        "business_name": "Fairmont Jaipur",
        "category": "venue",
        "city": "Jaipur",
        "locality": "Kukas",
        "city_tier": "tier_2",
        "latitude": 27.050,
        "longitude": 75.880,
        "source_notes": "Sourced from pickyourtrail.com Jaipur wedding venues list; locality centroid approximation."
    },
    {
        "business_name": "Jaipur Marriott Hotel",
        "category": "venue",
        "city": "Jaipur",
        "locality": "Jaipur",
        "city_tier": "tier_2",
        "latitude": 26.912,
        "longitude": 75.787,
        "source_notes": "Sourced from pickyourtrail.com Jaipur wedding venues list; locality centroid approximation."
    },
    {
        "business_name": "ITC Rajputana",
        "category": "venue",
        "city": "Jaipur",
        "locality": "Palace Road",
        "city_tier": "tier_2",
        "latitude": 26.910,
        "longitude": 75.805,
        "source_notes": "Sourced from pickyourtrail.com Jaipur wedding venues list; locality centroid approximation."
    },
    {
        "business_name": "Rambagh Palace",
        "category": "venue",
        "city": "Jaipur",
        "locality": "Bhawani Singh Rd, Rambagh",
        "city_tier": "tier_2",
        "latitude": 26.897,
        "longitude": 75.807,
        "source_notes": "Sourced from pickyourtrail.com Jaipur wedding venues list; locality centroid approximation."
    },
    {
        "business_name": "Samode Palace",
        "category": "venue",
        "city": "Jaipur",
        "locality": "Village Samode, Chomu",
        "city_tier": "tier_2",
        "latitude": 27.167,
        "longitude": 75.733,
        "source_notes": "Sourced from pickyourtrail.com Jaipur wedding venues list; locality centroid approximation."
    },
    {
        "business_name": "Golden Tulip Jaipur",
        "category": "venue",
        "city": "Jaipur",
        "locality": "Kukas",
        "city_tier": "tier_2",
        "latitude": 27.050,
        "longitude": 75.880,
        "source_notes": "Sourced from sarovarhotels.com Golden Tulip Kukas page; locality centroid approximation."
    },
    {
        "business_name": "Royal Palace Marriage Garden & Banquet Hall",
        "category": "marriage_garden",
        "city": "Jaipur",
        "locality": "Sanganer",
        "city_tier": "tier_2",
        "latitude": 26.817,
        "longitude": 75.800,
        "source_notes": "Sourced from venuelook.com Sanganer listings; locality centroid approximation."
    },
    {
        "business_name": "Gathbandhan Marriage Garden & Banquet Hall",
        "category": "marriage_garden",
        "city": "Jaipur",
        "locality": "Sanganer",
        "city_tier": "tier_2",
        "latitude": 26.817,
        "longitude": 75.800,
        "source_notes": "Sourced from venuelook.com Sanganer listings; locality centroid approximation."
    },
    {
        "business_name": "Jaipur Exhibition & Convention Centre",
        "category": "convention_centre",
        "city": "Jaipur",
        "locality": "Sanganer",
        "city_tier": "tier_2",
        "latitude": 26.817,
        "longitude": 75.800,
        "source_notes": "Sourced from venuelook.com Sanganer listings; locality centroid approximation."
    },
    {
        "business_name": "Heera Valley Resort",
        "category": "resort",
        "city": "Jaipur",
        "locality": "Sanganer",
        "city_tier": "tier_2",
        "latitude": 26.817,
        "longitude": 75.800,
        "source_notes": "Sourced from venuelook.com Sanganer listings; locality centroid approximation."
    },
    {
        "business_name": "Chandan Van",
        "category": "marriage_garden",
        "city": "Jaipur",
        "locality": "Sanganer",
        "city_tier": "tier_2",
        "latitude": 26.817,
        "longitude": 75.800,
        "source_notes": "Sourced from venuelook.com Sanganer listings; locality centroid approximation."
    },

    # Pune (8 venues)
    {
        "business_name": "Bharti Banquet & Lawn",
        "category": "banquet_lawn",
        "city": "Pune",
        "locality": "Bhukum",
        "city_tier": "tier_1",
        "latitude": 18.440,
        "longitude": 73.830,
        "source_notes": "Sourced from venuelook.com Pune locality listings; locality centroid approximation."
    },
    {
        "business_name": "Mahalaxmi Lawns",
        "category": "lawn",
        "city": "Pune",
        "locality": "Karve Nagar",
        "city_tier": "tier_1",
        "latitude": 18.485,
        "longitude": 73.812,
        "source_notes": "Sourced from venuelook.com Pune locality listings; locality centroid approximation."
    },
    {
        "business_name": "Ranade's Magenta Lawns",
        "category": "lawn",
        "city": "Pune",
        "locality": "Karve Nagar",
        "city_tier": "tier_1",
        "latitude": 18.485,
        "longitude": 73.812,
        "source_notes": "Sourced from venuelook.com Pune locality listings; locality centroid approximation."
    },
    {
        "business_name": "Kalashree Banquets",
        "category": "banquet_hall",
        "city": "Pune",
        "locality": "Manjari Budruk",
        "city_tier": "tier_1",
        "latitude": 18.510,
        "longitude": 73.950,
        "source_notes": "Sourced from venuelook.com Pune locality listings; locality centroid approximation."
    },
    {
        "business_name": "Indraprasth Lawns",
        "category": "lawn",
        "city": "Pune",
        "locality": "Manjari Budruk",
        "city_tier": "tier_1",
        "latitude": 18.510,
        "longitude": 73.950,
        "source_notes": "Sourced from venuelook.com Pune locality listings; locality centroid approximation."
    },
    {
        "business_name": "Shubharambh Banquet Hall",
        "category": "banquet_hall",
        "city": "Pune",
        "locality": "Manjari Budruk",
        "city_tier": "tier_1",
        "latitude": 18.510,
        "longitude": 73.950,
        "source_notes": "Sourced from venuelook.com Pune locality listings; locality centroid approximation."
    },
    {
        "business_name": "Shivai Lawns",
        "category": "lawn",
        "city": "Pune",
        "locality": "Manjari Budruk",
        "city_tier": "tier_1",
        "latitude": 18.510,
        "longitude": 73.950,
        "source_notes": "Sourced from venuelook.com Pune locality listings; locality centroid approximation."
    },
    {
        "business_name": "Tejomaya Lawns and Banquet",
        "category": "banquet_lawn",
        "city": "Pune",
        "locality": "Hadapsar",
        "city_tier": "tier_1",
        "latitude": 18.509,
        "longitude": 73.926,
        "source_notes": "Sourced from odoo.com Hadapsar venue page; locality centroid approximation."
    }
]


def seed_vendor_profiles(target_db_url: str | None = None):
    print("Ensuring tables exist...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        inserted = 0
        updated = 0
        for data in SEED_VENUES:
            existing = db.query(VendorProfile).filter(
                VendorProfile.business_name == data["business_name"],
                VendorProfile.city == data["city"]
            ).first()

            if not existing:
                vp = VendorProfile(
                    business_name=data["business_name"],
                    category=data["category"],
                    city=data["city"],
                    locality=data["locality"],
                    city_tier=data["city_tier"],
                    latitude=data["latitude"],
                    longitude=data["longitude"],
                    average_rating=None,  # Unrated
                    rating_count=0,
                    is_verified_profile=False,
                    coordinate_precision="locality_approximate",
                    source_notes=data["source_notes"],
                    metadata_json={}
                )
                db.add(vp)
                inserted += 1
            else:
                existing.category = data["category"]
                existing.locality = data["locality"]
                existing.latitude = data["latitude"]
                existing.longitude = data["longitude"]
                existing.source_notes = data["source_notes"]
                existing.is_verified_profile = False
                existing.coordinate_precision = "locality_approximate"
                updated += 1

        db.commit()
        total = db.query(VendorProfile).count()
        print(f"Successfully seeded vendor profiles! Inserted: {inserted}, Updated: {updated}, Total in DB: {total}")
        return total
    finally:
        db.close()


if __name__ == "__main__":
    seed_vendor_profiles()
