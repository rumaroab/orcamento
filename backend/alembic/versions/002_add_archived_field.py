"""Add archived field to documents

Revision ID: 002_add_archived
Revises: 001_initial
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_add_archived'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add archived column to documents table
    op.add_column('documents', sa.Column('archived', sa.Boolean(), nullable=False, server_default='false'))
    op.create_index('ix_documents_archived', 'documents', ['archived'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_documents_archived', table_name='documents')
    op.drop_column('documents', 'archived')

