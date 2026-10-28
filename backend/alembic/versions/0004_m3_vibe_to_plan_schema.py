"""m3 vibe to plan schema

Revision ID: 0004_m3_vibe_to_plan_schema
Revises: 0003_m2_replanning_schema
Create Date: 2026-10-22 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0004_m3_vibe_to_plan_schema"
down_revision = "0003_m2_replanning_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create style_profiles table
    op.create_table(
        "style_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("uploaded_image_refs", sa.JSON(), nullable=False),
        sa.Column("extracted_palette", sa.JSON(), nullable=False),
        sa.Column("style_tags", sa.JSON(), nullable=False),
        sa.Column("mood_words", sa.JSON(), nullable=False),
        sa.Column("text_description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_style_profiles_event_id", "style_profiles", ["event_id"])

    # 2. Create uploaded_images table (binary image storage per DEC-017)
    op.create_table(
        "uploaded_images",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("style_profile_id", sa.String(length=36), nullable=False),
        sa.Column("image_data", sa.LargeBinary(), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["style_profile_id"], ["style_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_uploaded_images_style_profile_id", "uploaded_images", ["style_profile_id"])

    # 3. Create theme_proposals table
    op.create_table(
        "theme_proposals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("style_profile_id", sa.String(length=36), nullable=False),
        sa.Column("theme_name", sa.String(length=255), nullable=False),
        sa.Column("palette", sa.JSON(), nullable=False),
        sa.Column("menu_direction", sa.Text(), nullable=True),
        sa.Column("playlist_genres", sa.JSON(), nullable=False),
        sa.Column("dress_code_suggestion", sa.Text(), nullable=True),
        sa.Column("invitation_design_brief", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="proposed"),
        sa.Column("provider_used", sa.String(length=100), nullable=True),
        sa.Column("fallback_warning", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["style_profile_id"], ["style_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_theme_proposals_style_profile_id", "theme_proposals", ["style_profile_id"])
    op.create_index("ix_theme_proposals_status", "theme_proposals", ["status"])

    # 4. Create decor_items table
    op.create_table(
        "decor_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("theme_proposal_id", sa.String(length=36), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("quantity_formula", sa.Text(), nullable=False),
        sa.Column("computed_quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("cost_tier", sa.String(length=50), nullable=False, server_default="medium"),
        sa.Column("cost_range_low", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("cost_range_high", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("sourcing_type", sa.String(length=50), nullable=False, server_default="rent"),
        sa.Column("budget_item_id", sa.String(length=36), nullable=True),
        sa.Column("task_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="proposed"),
        sa.Column("reasoning", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["theme_proposal_id"], ["theme_proposals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["budget_item_id"], ["budget_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decor_items_theme_proposal_id", "decor_items", ["theme_proposal_id"])
    op.create_index("ix_decor_items_budget_item_id", "decor_items", ["budget_item_id"])
    op.create_index("ix_decor_items_task_id", "decor_items", ["task_id"])
    op.create_index("ix_decor_items_status", "decor_items", ["status"])


def downgrade() -> None:
    op.drop_table("decor_items")
    op.drop_table("theme_proposals")
    op.drop_table("uploaded_images")
    op.drop_table("style_profiles")
