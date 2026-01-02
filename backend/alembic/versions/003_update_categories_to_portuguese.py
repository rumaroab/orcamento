"""Update categories to Portuguese

Revision ID: 003_portuguese_categories
Revises: 002_add_archived
Create Date: 2024-01-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_portuguese_categories'
down_revision = '002_add_archived'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update category enum values to Portuguese
    # First, update existing data
    op.execute("""
        UPDATE budget_items 
        SET category = CASE category
            WHEN 'Personal taxes' THEN 'Impostos sobre pessoas'
            WHEN 'Corporate taxes' THEN 'Impostos sobre empresas'
            WHEN 'Taxes on purchases' THEN 'Impostos sobre compras'
            WHEN 'Social security contributions' THEN 'Contribuições para segurança social'
            WHEN 'Other revenue' THEN 'Outras receitas'
            WHEN 'Health' THEN 'Saúde'
            WHEN 'Education' THEN 'Educação'
            WHEN 'Pensions & social support' THEN 'Pensões e apoio social'
            WHEN 'Running the government' THEN 'Funcionamento do governo'
            WHEN 'Security & defense' THEN 'Segurança e defesa'
            WHEN 'Justice' THEN 'Justiça'
            WHEN 'Infrastructure & environment' THEN 'Infraestrutura e ambiente'
            WHEN 'Public debt' THEN 'Dívida pública'
            ELSE category
        END
    """)
    
    # Drop old enum and create new one
    op.execute('ALTER TYPE categoryenum RENAME TO categoryenum_old')
    
    # Create new enum with Portuguese values
    op.execute("""
        CREATE TYPE categoryenum AS ENUM (
            'Impostos sobre pessoas',
            'Impostos sobre empresas',
            'Impostos sobre compras',
            'Contribuições para segurança social',
            'Outras receitas',
            'Saúde',
            'Educação',
            'Pensões e apoio social',
            'Funcionamento do governo',
            'Segurança e defesa',
            'Justiça',
            'Infraestrutura e ambiente',
            'Dívida pública'
        )
    """)
    
    # Update column to use new enum
    op.execute('ALTER TABLE budget_items ALTER COLUMN category TYPE categoryenum USING category::text::categoryenum')
    
    # Drop old enum
    op.execute('DROP TYPE categoryenum_old')


def downgrade() -> None:
    # Revert to English categories
    op.execute("""
        UPDATE budget_items 
        SET category = CASE category
            WHEN 'Impostos sobre pessoas' THEN 'Personal taxes'
            WHEN 'Impostos sobre empresas' THEN 'Corporate taxes'
            WHEN 'Impostos sobre compras' THEN 'Taxes on purchases'
            WHEN 'Contribuições para segurança social' THEN 'Social security contributions'
            WHEN 'Outras receitas' THEN 'Other revenue'
            WHEN 'Saúde' THEN 'Health'
            WHEN 'Educação' THEN 'Education'
            WHEN 'Pensões e apoio social' THEN 'Pensions & social support'
            WHEN 'Funcionamento do governo' THEN 'Running the government'
            WHEN 'Segurança e defesa' THEN 'Security & defense'
            WHEN 'Justiça' THEN 'Justice'
            WHEN 'Infraestrutura e ambiente' THEN 'Infrastructure & environment'
            WHEN 'Dívida pública' THEN 'Public debt'
            ELSE category
        END
    """)
    
    op.execute('ALTER TYPE categoryenum RENAME TO categoryenum_old')
    
    op.execute("""
        CREATE TYPE categoryenum AS ENUM (
            'Personal taxes',
            'Corporate taxes',
            'Taxes on purchases',
            'Social security contributions',
            'Other revenue',
            'Health',
            'Education',
            'Pensions & social support',
            'Running the government',
            'Security & defense',
            'Justice',
            'Infrastructure & environment',
            'Public debt'
        )
    """)
    
    op.execute('ALTER TABLE budget_items ALTER COLUMN category TYPE categoryenum USING category::text::categoryenum')
    op.execute('DROP TYPE categoryenum_old')

