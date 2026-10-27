"""m2 replanning schema

Revision ID: 0003_m2_replanning_schema
Revises: 0002_m1_quote_audit_schema
Create Date: 2026-10-22 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '0003_m2_replanning_schema'
down_revision = '0002_m1_quote_audit_schema'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Add venue_capacity to events
    op.add_column('events', sa.Column('venue_capacity', sa.Integer(), nullable=True))

    # 2. Add scaling_rule to budget_items
    op.add_column(
        'budget_items',
        sa.Column('scaling_rule', sa.String(length=50), nullable=False, server_default='per_guest')
    )

    # Backfill scaling_rule for existing categories per DEC-018
    op.execute("""
        UPDATE budget_items
        SET scaling_rule = CASE
            WHEN lower(category) IN ('catering', 'rentals', 'wardrobe', 'gifts_favors', 'invitations') THEN 'per_guest'
            WHEN lower(category) IN ('venue', 'photography', 'entertainment', 'ritual_priest') THEN 'fixed'
            WHEN lower(category) IN ('decor', 'sound_light') THEN 'tiered'
            ELSE 'per_guest'
        END
    """)

    # 3. Create change_events table
    op.create_table(
        'change_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('event_id', sa.String(length=36), nullable=False),
        sa.Column('change_type', sa.String(length=50), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_change_events_event_id', 'change_events', ['event_id'])
    op.create_index('ix_change_events_status', 'change_events', ['status'])

    # 4. Create ai_suggestions table
    op.create_table(
        'ai_suggestions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('event_id', sa.String(length=36), nullable=False),
        sa.Column('change_event_id', sa.String(length=36), nullable=True),
        sa.Column('agent_name', sa.String(length=100), nullable=False),
        sa.Column('proposal_payload', sa.JSON(), nullable=False),
        sa.Column('reasoning', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['change_event_id'], ['change_events.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ai_suggestions_event_id', 'ai_suggestions', ['event_id'])
    op.create_index('ix_ai_suggestions_change_event_id', 'ai_suggestions', ['change_event_id'])
    op.create_index('ix_ai_suggestions_status', 'ai_suggestions', ['status'])


def downgrade() -> None:
    op.drop_table('ai_suggestions')
    op.drop_table('change_events')
    op.drop_column('budget_items', 'scaling_rule')
    op.drop_column('events', 'venue_capacity')
