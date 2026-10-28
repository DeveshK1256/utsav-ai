import logging

from sqlalchemy import select

from backend.app.db.session import SessionLocal
from backend.app.models.models import VendorBenchmarkSample

logger = logging.getLogger(__name__)

BENCHMARK_SEEDS = [
    # Caterer - Tier 1 (Normalized per-plate cost in INR)
    {
        "category": "caterer",
        "city_tier": "tier_1",
        "normalized_unit_cost": 1150.0,
        "notes": "Verified Delhi wedding quote",
    },
    {
        "category": "caterer",
        "city_tier": "tier_1",
        "normalized_unit_cost": 1200.0,
        "notes": "Verified Mumbai hospitality contract",
    },
    {
        "category": "caterer",
        "city_tier": "tier_1",
        "normalized_unit_cost": 1250.0,
        "notes": "Verified Bengaluru luxury buffet",
    },
    {
        "category": "caterer",
        "city_tier": "tier_1",
        "normalized_unit_cost": 1300.0,
        "notes": "Verified Hyderabad royal spread",
    },
    {
        "category": "caterer",
        "city_tier": "tier_1",
        "normalized_unit_cost": 1350.0,
        "notes": "Verified Chennai banquet spread",
    },
    {
        "category": "caterer",
        "city_tier": "tier_1",
        "normalized_unit_cost": 1400.0,
        "notes": "Verified Pune premium caterer",
    },
    # Caterer - Tier 2
    {
        "category": "caterer",
        "city_tier": "tier_2",
        "normalized_unit_cost": 800.0,
        "notes": "Verified Jaipur royal thali",
    },
    {
        "category": "caterer",
        "city_tier": "tier_2",
        "normalized_unit_cost": 850.0,
        "notes": "Verified Lucknow nawabi catering",
    },
    {
        "category": "caterer",
        "city_tier": "tier_2",
        "normalized_unit_cost": 900.0,
        "notes": "Verified Indore traditional banquet",
    },
    {
        "category": "caterer",
        "city_tier": "tier_2",
        "normalized_unit_cost": 920.0,
        "notes": "Verified Chandigarh buffet",
    },
    {
        "category": "caterer",
        "city_tier": "tier_2",
        "normalized_unit_cost": 950.0,
        "notes": "Verified Nagpur wedding caterer",
    },
    # Venue - Tier 1 (Normalized day rental)
    {
        "category": "venue",
        "city_tier": "tier_1",
        "normalized_unit_cost": 600000.0,
        "notes": "Mumbai banquet lawn rental",
    },
    {
        "category": "venue",
        "city_tier": "tier_1",
        "normalized_unit_cost": 650000.0,
        "notes": "Delhi NCR heritage hall",
    },
    {
        "category": "venue",
        "city_tier": "tier_1",
        "normalized_unit_cost": 700000.0,
        "notes": "Bengaluru palace ground",
    },
    {
        "category": "venue",
        "city_tier": "tier_1",
        "normalized_unit_cost": 750000.0,
        "notes": "Hyderabad convention center",
    },
    {
        "category": "venue",
        "city_tier": "tier_1",
        "normalized_unit_cost": 800000.0,
        "notes": "Pune resort full day",
    },
    # Venue - Tier 2
    {
        "category": "venue",
        "city_tier": "tier_2",
        "normalized_unit_cost": 350000.0,
        "notes": "Jaipur haveli lawn",
    },
    {
        "category": "venue",
        "city_tier": "tier_2",
        "normalized_unit_cost": 400000.0,
        "notes": "Udaipur lakeside garden",
    },
    {
        "category": "venue",
        "city_tier": "tier_2",
        "normalized_unit_cost": 420000.0,
        "notes": "Bhopal heritage hall",
    },
    {
        "category": "venue",
        "city_tier": "tier_2",
        "normalized_unit_cost": 450000.0,
        "notes": "Varanasi resort banquet",
    },
    {
        "category": "venue",
        "city_tier": "tier_2",
        "normalized_unit_cost": 480000.0,
        "notes": "Vadodara palace grounds",
    },
    # Decorator - Tier 1
    {
        "category": "decorator",
        "city_tier": "tier_1",
        "normalized_unit_cost": 400000.0,
        "notes": "Floral & mandap setup",
    },
    {
        "category": "decorator",
        "city_tier": "tier_1",
        "normalized_unit_cost": 450000.0,
        "notes": "Full truss lighting & floral",
    },
    {
        "category": "decorator",
        "city_tier": "tier_1",
        "normalized_unit_cost": 500000.0,
        "notes": "Theme decor Delhi",
    },
    {
        "category": "decorator",
        "city_tier": "tier_1",
        "normalized_unit_cost": 520000.0,
        "notes": "Grand entrance & mandap",
    },
    {
        "category": "decorator",
        "city_tier": "tier_1",
        "normalized_unit_cost": 550000.0,
        "notes": "Vedic mandap setup",
    },
    # Photographer - Tier 1
    {
        "category": "photographer",
        "city_tier": "tier_1",
        "normalized_unit_cost": 250000.0,
        "notes": "2-day candid & 4K package",
    },
    {
        "category": "photographer",
        "city_tier": "tier_1",
        "normalized_unit_cost": 280000.0,
        "notes": "Lead cinematic crew",
    },
    {
        "category": "photographer",
        "city_tier": "tier_1",
        "normalized_unit_cost": 300000.0,
        "notes": "Full photo & drone team",
    },
    {
        "category": "photographer",
        "city_tier": "tier_1",
        "normalized_unit_cost": 320000.0,
        "notes": "Traditional + candid lead",
    },
    {
        "category": "photographer",
        "city_tier": "tier_1",
        "normalized_unit_cost": 350000.0,
        "notes": "Luxury documentary studio",
    },
    # Sparse category to test DEC-014 (n < 5)
    {
        "category": "drone_light_show",
        "city_tier": "tier_1",
        "normalized_unit_cost": 150000.0,
        "notes": "Only 2 recorded vendors",
    },
    {
        "category": "drone_light_show",
        "city_tier": "tier_1",
        "normalized_unit_cost": 180000.0,
        "notes": "Only 2 recorded vendors",
    },
]


def seed_benchmarks() -> None:
    db = SessionLocal()
    try:
        count = db.scalar(select(VendorBenchmarkSample).limit(1))
        if count is not None:
            logger.info("Benchmarks already seeded.")
            return

        logger.info("Seeding %d benchmark samples...", len(BENCHMARK_SEEDS))
        for b in BENCHMARK_SEEDS:
            sample = VendorBenchmarkSample(
                category=b["category"],
                city_tier=b["city_tier"],
                normalized_unit_cost=b["normalized_unit_cost"],
                notes=b["notes"],
            )
            db.add(sample)
        db.commit()
        logger.info("Benchmark samples successfully seeded.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_benchmarks()
