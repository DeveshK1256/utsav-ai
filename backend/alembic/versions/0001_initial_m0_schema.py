"""initial m0 schema

Revision ID: 0001_initial_m0_schema
Revises: 
Create Date: 2026-10-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_initial_m0_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. users
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('phone_number', sa.String(length=20), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('full_name', sa.String(length=150), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='host'),
        sa.Column('preferred_language', sa.String(length=10), nullable=False, server_default='en'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phone_number')
    )
    op.create_index('ix_users_phone_number', 'users', ['phone_number'])

    # 2. traditions
    op.create_table(
        'traditions',
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('regional_name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('cultural_notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('code')
    )

    # 3. ritual_items
    op.create_table(
        'ritual_items',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tradition_code', sa.String(length=50), nullable=False),
        sa.Column('item_name', sa.String(length=150), nullable=False),
        sa.Column('regional_name', sa.String(length=150), nullable=True),
        sa.Column('standard_quantity', sa.String(length=100), nullable=False),
        sa.Column('spiritual_purpose', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['tradition_code'], ['traditions.code'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ritual_items_tradition_code', 'ritual_items', ['tradition_code'])

    # 4. events
    op.create_table(
        'events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('owner_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('tradition_code', sa.String(length=50), nullable=True),
        sa.Column('guest_count', sa.Integer(), nullable=False),
        sa.Column('total_budget', sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('pincode', sa.String(length=10), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='planning'),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('guest_count > 0', name='check_positive_guest_count'),
        sa.CheckConstraint('total_budget >= 0', name='check_non_negative_budget'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tradition_code'], ['traditions.code'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_events_owner_id', 'events', ['owner_id'])
    op.create_index('ix_events_status', 'events', ['status'])
    op.create_index('idx_events_dates', 'events', ['start_date', 'end_date'])

    # 5. sub_events
    op.create_table(
        'sub_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('event_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.Column('venue_name', sa.String(length=255), nullable=False),
        sa.Column('venue_address', sa.Text(), nullable=True),
        sa.Column('is_outdoor', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_muhurat_locked', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('muhurat_notes', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sub_events_event_id', 'sub_events', ['event_id'])

    # 6. budget_items
    op.create_table(
        'budget_items',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('event_id', sa.String(length=36), nullable=False),
        sa.Column('vendor_id', sa.String(length=36), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('planned_amount', sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column('actual_amount', sa.Numeric(precision=14, scale=2), nullable=False, server_default='0.00'),
        sa.Column('is_paid', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('reasoning_spec', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_budget_items_event_id', 'budget_items', ['event_id'])

    # 7. tasks
    op.create_table(
        'tasks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('event_id', sa.String(length=36), nullable=False),
        sa.Column('sub_event_id', sa.String(length=36), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('scheduled_start', sa.DateTime(), nullable=True),
        sa.Column('scheduled_end', sa.DateTime(), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('dependency_task_ids', sa.JSON(), nullable=False),
        sa.Column('assigned_role', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sub_event_id'], ['sub_events.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tasks_event_id', 'tasks', ['event_id'])
    op.create_index('ix_tasks_sub_event_id', 'tasks', ['sub_event_id'])

    # 8. event_log
    op.create_table(
        'event_log',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('event_id', sa.String(length=36), nullable=False),
        sa.Column('action_type', sa.String(length=100), nullable=False),
        sa.Column('diff_payload', sa.JSON(), nullable=False),
        sa.Column('actor_id', sa.String(length=36), nullable=True),
        sa.Column('logged_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_event_log_event_id', 'event_log', ['event_id'])

def downgrade() -> None:
    op.drop_table('event_log')
    op.drop_table('tasks')
    op.drop_table('budget_items')
    op.drop_table('sub_events')
    op.drop_table('events')
    op.drop_table('ritual_items')
    op.drop_table('traditions')
    op.drop_table('users')
