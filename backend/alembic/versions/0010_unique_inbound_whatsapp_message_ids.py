"""prevent duplicate inbound WhatsApp message processing

Revision ID: 0010_unique_inbound_whatsapp_message_ids
Revises: 0009_owner_tokens_and_vendor_profiles
Create Date: 2026-10-30 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0010_unique_inbound_whatsapp_message_ids"
down_revision = "0009_owner_tokens_and_vendor_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_message_log_inbound_whatsapp_id",
        "message_log",
        ["whatsapp_message_id"],
        unique=True,
        postgresql_where=sa.text("whatsapp_message_id IS NOT NULL"),
        sqlite_where=sa.text("whatsapp_message_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_message_log_inbound_whatsapp_id", table_name="message_log")
