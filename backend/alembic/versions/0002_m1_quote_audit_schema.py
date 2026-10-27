"""m1 quote audit schema

Revision ID: 0002_m1_quote_audit_schema
Revises: 0001_initial_m0_schema
Create Date: 2026-10-22 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '0002_m1_quote_audit_schema'
down_revision = '0001_initial_m0_schema'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. vendors
    op.create_table(
        'vendors',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('event_id', sa.String(length=36), nullable=False),
        sa.Column('business_name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('contact_person', sa.String(length=150), nullable=True),
        sa.Column('contact_phone', sa.String(length=20), nullable=True),
        sa.Column('agreed_quote', sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column('advance_paid', sa.Numeric(precision=14, scale=2), nullable=False, server_default='0.00'),
        sa.Column('contract_terms', sa.JSON(), nullable=False),
        sa.Column('hidden_cost_alerts', sa.JSON(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_vendors_event_id', 'vendors', ['event_id'])

    # 2. quote_documents
    op.create_table(
        'quote_documents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('event_id', sa.String(length=36), nullable=False),
        sa.Column('vendor_id', sa.String(length=36), nullable=True),
        sa.Column('vendor_name', sa.String(length=200), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_type', sa.String(length=100), nullable=False),
        sa.Column('uploaded_file', sa.LargeBinary(), nullable=False),  # Stored in DB bytea per DEC-017
        sa.Column('extraction_status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('raw_extracted_json', sa.JSON(), nullable=False),
        sa.Column('total_quoted_amount', sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column('tax_amount', sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_quote_documents_event_id', 'quote_documents', ['event_id'])
    op.create_index('ix_quote_documents_vendor_id', 'quote_documents', ['vendor_id'])
    op.create_index('ix_quote_documents_category', 'quote_documents', ['category'])
    op.create_index('ix_quote_documents_extraction_status', 'quote_documents', ['extraction_status'])

    # 3. quote_line_items
    op.create_table(
        'quote_line_items',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('quote_document_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('qty', sa.Numeric(precision=10, scale=2), nullable=False, server_default='1.00'),
        sa.Column('unit', sa.String(length=50), nullable=False, server_default='units'),
        sa.Column('unit_price', sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column('total', sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column('category_tag', sa.String(length=50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['quote_document_id'], ['quote_documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_quote_line_items_quote_document_id', 'quote_line_items', ['quote_document_id'])

    # 4. vendor_benchmark_samples
    op.create_table(
        'vendor_benchmark_samples',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('city_tier', sa.String(length=20), nullable=False),
        sa.Column('normalized_unit_cost', sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column('source_event_id', sa.String(length=36), nullable=True),
        sa.Column('notes', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['source_event_id'], ['events.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_vendor_benchmark_samples_category', 'vendor_benchmark_samples', ['category'])
    op.create_index('ix_vendor_benchmark_samples_city_tier', 'vendor_benchmark_samples', ['city_tier'])

def downgrade() -> None:
    op.drop_table('vendor_benchmark_samples')
    op.drop_table('quote_line_items')
    op.drop_table('quote_documents')
    op.drop_table('vendors')
