"""
One-Time Data Migration & Backfill Script: Synchronize budget_items.scaling_rule to DEC-018

Audits and updates existing database rows in `budget_items` so that the persistent
`scaling_rule` column strictly conforms to the canonical DEC-018 scaling rules:
  - Fixed: venue, photography, entertainment, rituals, ritual_priest
  - Tiered: decor, sound_light, sound_and_lighting
  - Per-guest: catering, rentals, wardrobe, logistics, gifts_favors, invitations, contingency
"""
import sys
import os
import argparse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Ensure backend can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.config import settings
from backend.app.services.budget_rescaling_engine import BudgetRescalingEngine


def run_backfill(database_url: str = None, dry_run: bool = False):
    db_url = database_url or settings.DATABASE_URL
    print(f"Connecting to database: {db_url.split('@')[-1] if '@' in db_url else db_url}")

    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False} if "sqlite" in db_url else {}
    )

    with engine.begin() as conn:
        # Check rows in budget_items
        result = conn.execute(text("SELECT id, event_id, category, scaling_rule FROM budget_items")).fetchall()
        print(f"Total budget_items audited: {len(result)}")

        to_update = []
        for row in result:
            b_id, event_id, category, current_rule = row
            canonical = BudgetRescalingEngine.resolve_scaling_rule(category)
            if not current_rule or current_rule.lower() != canonical:
                to_update.append((canonical, b_id, event_id, category, current_rule))

        print(f"Discrepant rows identified: {len(to_update)}")

        if not to_update:
            print("All budget items already conform to canonical DEC-018 scaling rules.")
            return len(result), 0

        for canonical, b_id, event_id, category, current_rule in to_update:
            print(f"  [FIX] Item {b_id[:8]} (Event: {event_id[:8]}, Cat: {category:15s}): '{current_rule}' -> '{canonical}'")
            if not dry_run:
                conn.execute(
                    text("UPDATE budget_items SET scaling_rule = :rule WHERE id = :id"),
                    {"rule": canonical, "id": b_id}
                )

        if dry_run:
            print("\nDRY RUN: No modifications were committed to the database.")
        else:
            print(f"\nSUCCESS: Successfully updated {len(to_update)} rows to canonical scaling rules.")

        return len(result), len(to_update)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill budget_items.scaling_rule")
    parser.add_argument("--database-url", help="Override DATABASE_URL", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Audit without committing changes")
    args = parser.parse_args()

    run_backfill(database_url=args.database_url, dry_run=args.dry_run)
