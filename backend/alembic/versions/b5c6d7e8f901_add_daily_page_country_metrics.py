"""add_daily_page_country_metrics

Revision ID: b5c6d7e8f901
Revises: a9714ee5d121
Create Date: 2026-10-27 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b5c6d7e8f901'
down_revision: Union[str, None] = 'a9714ee5d121'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'daily_page_country_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=True),
        sa.Column('page_url', sa.String(length=1000), nullable=False),
        sa.Column('normalized_url', sa.String(length=1000), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('country_code', sa.String(length=10), nullable=False),
        sa.Column('clicks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('impressions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ctr', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('position', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(['property_id'], ['gsc_properties.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('property_id', 'normalized_url', 'date', 'country_code', name='uq_country_metrics_prop_url_date_country')
    )
    op.create_index('idx_country_metrics_date_normurl', 'daily_page_country_metrics', ['date', 'normalized_url'])
    op.create_index('idx_country_metrics_country_date', 'daily_page_country_metrics', ['country_code', 'date'])
    op.create_index('ix_daily_page_country_metrics_id', 'daily_page_country_metrics', ['id'])
    op.create_index('ix_daily_page_country_metrics_normalized_url', 'daily_page_country_metrics', ['normalized_url'])
    op.create_index('ix_daily_page_country_metrics_date', 'daily_page_country_metrics', ['date'])
    op.create_index('ix_daily_page_country_metrics_country_code', 'daily_page_country_metrics', ['country_code'])

def downgrade() -> None:
    op.drop_index('ix_daily_page_country_metrics_country_code', table_name='daily_page_country_metrics')
    op.drop_index('ix_daily_page_country_metrics_date', table_name='daily_page_country_metrics')
    op.drop_index('ix_daily_page_country_metrics_normalized_url', table_name='daily_page_country_metrics')
    op.drop_index('ix_daily_page_country_metrics_id', table_name='daily_page_country_metrics')
    op.drop_index('idx_country_metrics_country_date', table_name='daily_page_country_metrics')
    op.drop_index('idx_country_metrics_date_normurl', table_name='daily_page_country_metrics')
    op.drop_table('daily_page_country_metrics')
