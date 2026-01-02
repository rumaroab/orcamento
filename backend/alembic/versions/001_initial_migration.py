"""Initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    side_enum = postgresql.ENUM('REVENUE', 'EXPENSE', name='sideenum')
    side_enum.create(op.get_bind(), checkfirst=True)
    
    category_enum = postgresql.ENUM(
        'Personal taxes', 'Corporate taxes', 'Taxes on purchases',
        'Social security contributions', 'Other revenue',
        'Health', 'Education', 'Pensions & social support',
        'Running the government', 'Security & defense', 'Justice',
        'Infrastructure & environment', 'Public debt',
        name='categoryenum'
    )
    category_enum.create(op.get_bind(), checkfirst=True)
    
    unit_enum = postgresql.ENUM('EUR', 'THOUSAND_EUR', 'MILLION_EUR', 'UNKNOWN', name='unitenum')
    unit_enum.create(op.get_bind(), checkfirst=True)
    
    job_status_enum = postgresql.ENUM('PENDING', 'RUNNING', 'DONE', 'FAILED', name='importjobstatusenum')
    job_status_enum.create(op.get_bind(), checkfirst=True)
    
    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('filepath', sa.String(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_documents_year', 'documents', ['year'], unique=False)
    
    # Create pages table
    op.create_table(
        'pages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id'), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('text_raw', sa.Text(), nullable=False),
    )
    op.create_index('ix_pages_document_id', 'pages', ['document_id'], unique=False)
    
    # Create sections table
    op.create_table(
        'sections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id'), nullable=False),
        sa.Column('title_path', sa.String(), nullable=False),
        sa.Column('page_start', sa.Integer(), nullable=False),
        sa.Column('page_end', sa.Integer(), nullable=False),
    )
    op.create_index('ix_sections_document_id', 'sections', ['document_id'], unique=False)
    
    # Create budget_items table
    op.create_table(
        'budget_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id'), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('side', side_enum, nullable=False),
        sa.Column('category', category_enum, nullable=False),
        sa.Column('description_original', sa.Text(), nullable=False),
        sa.Column('value', sa.Numeric(20, 2), nullable=True),
        sa.Column('unit', unit_enum, nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('evidence_text', sa.Text(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_budget_items_document_id', 'budget_items', ['document_id'], unique=False)
    op.create_index('ix_budget_items_year', 'budget_items', ['year'], unique=False)
    op.create_index('ix_budget_items_side', 'budget_items', ['side'], unique=False)
    op.create_index('ix_budget_items_category', 'budget_items', ['category'], unique=False)
    
    # Create import_jobs table
    op.create_table(
        'import_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id'), nullable=False),
        sa.Column('status', job_status_enum, nullable=False),
        sa.Column('progress', sa.Integer(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_import_jobs_document_id', 'import_jobs', ['document_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_import_jobs_document_id', table_name='import_jobs')
    op.drop_table('import_jobs')
    op.drop_index('ix_budget_items_category', table_name='budget_items')
    op.drop_index('ix_budget_items_side', table_name='budget_items')
    op.drop_index('ix_budget_items_year', table_name='budget_items')
    op.drop_index('ix_budget_items_document_id', table_name='budget_items')
    op.drop_table('budget_items')
    op.drop_index('ix_sections_document_id', table_name='sections')
    op.drop_table('sections')
    op.drop_index('ix_pages_document_id', table_name='pages')
    op.drop_table('pages')
    op.drop_index('ix_documents_year', table_name='documents')
    op.drop_table('documents')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS importjobstatusenum')
    op.execute('DROP TYPE IF EXISTS unitenum')
    op.execute('DROP TYPE IF EXISTS categoryenum')
    op.execute('DROP TYPE IF EXISTS sideenum')

