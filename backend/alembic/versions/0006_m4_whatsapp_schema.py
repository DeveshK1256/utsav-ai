"""m4 whatsapp native guest coordination schema

Revision ID: 0006_m4_whatsapp_schema
Revises: 0005_backfill_scaling_rules
Create Date: 2026-10-23 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0006_m4_whatsapp_schema"
down_revision = "0005_backfill_scaling_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create guests table
    op.create_table(
        "guests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=False),
        sa.Column("group_side", sa.String(length=50), nullable=True),
        sa.Column("diet", sa.String(length=50), server_default="veg", nullable=True),
        sa.Column("mobility_needs", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("kids_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("headcount", sa.Integer(), server_default="1", nullable=False),
        sa.Column("rsvp_status", sa.String(length=30), server_default="pending", nullable=False),
        sa.Column("accommodation", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("language", sa.String(length=10), server_default="en", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("needs_host_review", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_guests_event_id", "guests", ["event_id"])
    op.create_index("ix_guests_phone", "guests", ["phone"])
    op.create_index("idx_guests_event_phone", "guests", ["event_id", "phone"], unique=True)

    # 2. Create message_templates table
    op.create_table(
        "message_templates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("template_name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("language", sa.String(length=10), server_default="en", nullable=False),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("meta_template_id", sa.String(length=100), nullable=True),
        sa.Column(
            "approval_status", sa.String(length=50), server_default="approved", nullable=False
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_message_templates_template_name", "message_templates", ["template_name"], unique=True
    )

    # 3. Create message_log table
    op.create_table(
        "message_log",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("guest_id", sa.String(length=36), nullable=True),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("phone_number", sa.String(length=30), nullable=False),
        sa.Column("direction", sa.String(length=20), nullable=False),
        sa.Column("message_type", sa.String(length=30), nullable=False),
        sa.Column("content_snapshot", sa.Text(), nullable=False),
        sa.Column("whatsapp_message_id", sa.String(length=100), nullable=True),
        sa.Column("delivery_status", sa.String(length=30), server_default="queued", nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["guest_id"], ["guests.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_message_log_event_id", "message_log", ["event_id"])
    op.create_index("ix_message_log_phone_number", "message_log", ["phone_number"])
    op.create_index("ix_message_log_whatsapp_message_id", "message_log", ["whatsapp_message_id"])
    op.create_index("ix_message_log_created_at", "message_log", ["created_at"])

    # 4. Create event_fact_sheets table
    op.create_table(
        "event_fact_sheets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("venue_address", sa.Text(), nullable=True),
        sa.Column("parking_info", sa.Text(), nullable=True),
        sa.Column("dress_code", sa.Text(), nullable=True),
        sa.Column("timing_notes", sa.Text(), nullable=True),
        sa.Column("map_link", sa.String(length=500), nullable=True),
        sa.Column("other_facts", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_fact_sheet_event_id"),
    )
    op.create_index("ix_event_fact_sheets_event_id", "event_fact_sheets", ["event_id"])

    # 5. Create opt_outs table
    op.create_table(
        "opt_outs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=False),
        sa.Column("reason", sa.String(length=100), server_default="STOP", nullable=False),
        sa.Column("opted_out_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_opt_outs_phone", "opt_outs", ["phone"], unique=True)


def downgrade() -> None:
    op.drop_table("opt_outs")
    op.drop_table("event_fact_sheets")
    op.drop_table("message_log")
    op.drop_table("message_templates")
    op.drop_table("guests")
