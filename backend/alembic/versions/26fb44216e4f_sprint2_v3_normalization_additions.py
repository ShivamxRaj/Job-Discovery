"""sprint2_v3_normalization_additions

Revision ID: 26fb44216e4f
Revises: be0fc3a9f472
Create Date: 2026-07-07 11:09:03.333751

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '26fb44216e4f'
down_revision: Union[str, Sequence[str], None] = 'be0fc3a9f472'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create canonical_companies
    op.create_table('canonical_companies',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('display_name', sa.String(length=255), nullable=False),
    sa.Column('normalized_name', sa.String(length=255), nullable=False),
    sa.Column('domain', sa.String(length=255), nullable=True),
    sa.Column('is_verified', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_canonical_companies_id'), 'canonical_companies', ['id'], unique=False)
    op.create_index(op.f('ix_canonical_companies_normalized_name'), 'canonical_companies', ['normalized_name'], unique=True)

    # 2. Create company_aliases
    op.create_table('company_aliases',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('alias', sa.String(length=255), nullable=False),
    sa.Column('company_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['canonical_companies.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_company_aliases_alias'), 'company_aliases', ['alias'], unique=True)
    op.create_index(op.f('ix_company_aliases_id'), 'company_aliases', ['id'], unique=False)

    # 3. Add parent_id to skills
    op.add_column('skills', sa.Column('parent_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'skills', 'skills', ['parent_id'], ['id'], ondelete='SET NULL')

    # 4. Add new columns to jobs
    op.add_column('jobs', sa.Column('normalization_version', sa.String(length=50), server_default='v1', nullable=False))
    op.add_column('jobs', sa.Column('title_confidence', sa.Float(), server_default='1.0', nullable=False))
    op.add_column('jobs', sa.Column('salary_confidence', sa.Float(), server_default='1.0', nullable=False))
    op.add_column('jobs', sa.Column('location_confidence', sa.Float(), server_default='1.0', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('jobs', 'location_confidence')
    op.drop_column('jobs', 'salary_confidence')
    op.drop_column('jobs', 'title_confidence')
    op.drop_column('jobs', 'normalization_version')
    op.drop_constraint(None, 'skills', type_='foreignkey')
    op.drop_column('skills', 'parent_id')
    op.drop_index(op.f('ix_company_aliases_id'), table_name='company_aliases')
    op.drop_index(op.f('ix_company_aliases_alias'), table_name='company_aliases')
    op.drop_table('company_aliases')
    op.drop_index(op.f('ix_canonical_companies_normalized_name'), table_name='canonical_companies')
    op.drop_index(op.f('ix_canonical_companies_id'), table_name='canonical_companies')
    op.drop_table('canonical_companies')
