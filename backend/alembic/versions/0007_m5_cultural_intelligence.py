"""m5 cultural intelligence and ritual schema

Revision ID: 0007_m5_cultural_intelligence
Revises: 0006_m4_whatsapp_schema
Create Date: 2026-10-23 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0007_m5_cultural_intelligence"
down_revision = "0006_m4_whatsapp_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add verification columns to traditions
    op.add_column(
        "traditions", sa.Column("is_verified", sa.Boolean(), server_default="0", nullable=False)
    )
    op.add_column(
        "traditions", sa.Column("verification_source", sa.String(length=255), nullable=True)
    )

    # 2. Add columns to ritual_items
    op.add_column("ritual_items", sa.Column("ritual_name", sa.String(length=100), nullable=True))
    op.add_column(
        "ritual_items",
        sa.Column("category", sa.String(length=50), server_default="puja_samagri", nullable=True),
    )
    op.add_column(
        "ritual_items", sa.Column("is_verified", sa.Boolean(), server_default="0", nullable=False)
    )

    # 3. Add secondary_tradition_code to events (for multi-tradition cross-cultural ceremonies)
    op.add_column(
        "events", sa.Column("secondary_tradition_code", sa.String(length=50), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("events", "secondary_tradition_code")
    op.drop_column("ritual_items", "is_verified")
    op.drop_column("ritual_items", "category")
    op.drop_column("ritual_items", "ritual_name")
    op.drop_column("traditions", "verification_source")
    op.drop_column("traditions", "is_verified")
