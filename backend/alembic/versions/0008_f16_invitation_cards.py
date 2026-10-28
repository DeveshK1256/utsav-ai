"""f16 invitation cards schema

Revision ID: 0008_f16_invitation_cards
Revises: 0007_m5_cultural_intelligence
Create Date: 2026-10-23 20:20:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0008_f16_invitation_cards"
down_revision = "0007_m5_cultural_intelligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "invitation_cards",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "event_id",
            sa.String(length=36),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "theme_proposal_id",
            sa.String(length=36),
            sa.ForeignKey("theme_proposals.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("layout_variant", sa.String(length=50), nullable=False),
        sa.Column("wording_text", sa.Text(), nullable=False),
        sa.Column(
            "guest_id",
            sa.String(length=36),
            sa.ForeignKey("guests.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("rendered_png", sa.LargeBinary(), nullable=True),
        sa.Column("rendered_pdf", sa.LargeBinary(), nullable=True),
        sa.Column("generated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_invitation_cards_event_id", "invitation_cards", ["event_id"])
    op.create_index(
        "ix_invitation_cards_theme_proposal_id", "invitation_cards", ["theme_proposal_id"]
    )
    op.create_index("ix_invitation_cards_guest_id", "invitation_cards", ["guest_id"])


def downgrade() -> None:
    op.drop_index("ix_invitation_cards_guest_id", table_name="invitation_cards")
    op.drop_index("ix_invitation_cards_theme_proposal_id", table_name="invitation_cards")
    op.drop_index("ix_invitation_cards_event_id", table_name="invitation_cards")
    op.drop_table("invitation_cards")
