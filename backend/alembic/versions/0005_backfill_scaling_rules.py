"""backfill budget_items scaling_rule to canonical DEC-018

Revision ID: 0005_backfill_scaling_rules
Revises: 0004_m3_vibe_to_plan_schema
Create Date: 2026-10-23 00:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '0005_backfill_scaling_rules'
down_revision = '0004_m3_vibe_to_plan_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Synchronize persistent database rows to DEC-018 canonical scaling rules
    op.execute("""
        UPDATE budget_items
        SET scaling_rule = CASE
            WHEN lower(category) IN ('venue', 'photography', 'entertainment', 'rituals', 'ritual_priest') THEN 'fixed'
            WHEN lower(category) IN ('decor', 'sound_light', 'sound_and_lighting') THEN 'tiered'
            WHEN lower(category) IN ('catering', 'rentals', 'wardrobe', 'gifts_favors', 'invitations', 'logistics', 'contingency') THEN 'per_guest'
            ELSE 'per_guest'
        END
        WHERE scaling_rule IS NULL
           OR (scaling_rule = 'per_guest' AND lower(category) IN ('venue', 'photography', 'entertainment', 'rituals', 'ritual_priest', 'decor', 'sound_light', 'sound_and_lighting'))
           OR (scaling_rule = 'fixed' AND lower(category) IN ('decor', 'sound_light', 'sound_and_lighting', 'catering', 'rentals', 'wardrobe', 'gifts_favors', 'invitations', 'logistics', 'contingency'));
    """)


def downgrade() -> None:
    pass
