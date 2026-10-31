"""add owner tokens and vendor profile directory

Revision ID: 0009_owner_tokens_and_vendor_profiles
Revises: 0008_f16_invitation_cards
Create Date: 2026-10-29 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0009_owner_tokens_and_vendor_profiles"
down_revision = "0008_f16_invitation_cards"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("events", sa.Column("owner_token", sa.String(length=64), nullable=True))
    op.create_index("ix_events_owner_token", "events", ["owner_token"])

    op.create_table(
        "vendor_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("business_name", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("service_area_radius_km", sa.Integer(), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("locality", sa.String(length=150), nullable=True),
        sa.Column("city_tier", sa.String(length=20), nullable=True),
        sa.Column("contact_phone", sa.String(length=20), nullable=True),
        sa.Column("average_rating", sa.Numeric(precision=2, scale=1), nullable=True),
        sa.Column("rating_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_verified_profile", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "coordinate_precision",
            sa.String(length=50),
            nullable=False,
            server_default="locality_approximate",
        ),
        sa.Column("source_notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vendor_profiles_category", "vendor_profiles", ["category"])
    op.create_index("ix_vendor_profiles_city", "vendor_profiles", ["city"])


def downgrade() -> None:
    op.drop_index("ix_vendor_profiles_city", table_name="vendor_profiles")
    op.drop_index("ix_vendor_profiles_category", table_name="vendor_profiles")
    op.drop_table("vendor_profiles")
    op.drop_index("ix_events_owner_token", table_name="events")
    op.drop_column("events", "owner_token")
