"""add_festival_management_models

Revision ID: a9714ee5d121
Revises: e4a0084b73f1
Create Date: 2026-10-27 17:29:22.877160

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a9714ee5d121'
down_revision: Union[str, None] = 'e4a0084b73f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. festivals table
    op.create_table(
        'festivals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('country_code', sa.String(length=10), nullable=False, server_default='IN'),
        sa.Column('region', sa.String(length=255), nullable=True),
        sa.Column('category_group', sa.String(length=100), nullable=False, server_default='Cultural'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('assigned_leader_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['assigned_leader_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_festivals_id'), 'festivals', ['id'], unique=False)
    op.create_index(op.f('ix_festivals_name'), 'festivals', ['name'], unique=False)
    op.create_index(op.f('ix_festivals_slug'), 'festivals', ['slug'], unique=True)
    op.create_index(op.f('ix_festivals_country_code'), 'festivals', ['country_code'], unique=False)
    op.create_index(op.f('ix_festivals_assigned_leader_id'), 'festivals', ['assigned_leader_id'], unique=False)
    op.create_index('idx_festival_country_active', 'festivals', ['country_code', 'is_active'], unique=False)

    # 2. festival_year_dates table
    op.create_table(
        'festival_year_dates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('festival_id', sa.Integer(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('prep_start_date', sa.Date(), nullable=True),
        sa.Column('prep_deadline_date', sa.Date(), nullable=True),
        sa.Column('season_comparison_start', sa.Date(), nullable=True),
        sa.Column('season_comparison_end', sa.Date(), nullable=True),
        sa.Column('date_status', sa.String(length=50), nullable=False, server_default='ESTIMATED'),
        sa.Column('approval_status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('approved_by_user_id', sa.Integer(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['festival_id'], ['festivals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approved_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('festival_id', 'year', name='uq_festival_year')
    )
    op.create_index(op.f('ix_festival_year_dates_id'), 'festival_year_dates', ['id'], unique=False)
    op.create_index(op.f('ix_festival_year_dates_festival_id'), 'festival_year_dates', ['festival_id'], unique=False)
    op.create_index(op.f('ix_festival_year_dates_year'), 'festival_year_dates', ['year'], unique=False)
    op.create_index('idx_festival_year_dates', 'festival_year_dates', ['festival_id', 'year'], unique=False)

    # 3. festival_subcategories table
    op.create_table(
        'festival_subcategories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('festival_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('target_keywords', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['festival_id'], ['festivals.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('festival_id', 'slug', name='uq_festival_subcategory_slug')
    )
    op.create_index(op.f('ix_festival_subcategories_id'), 'festival_subcategories', ['id'], unique=False)
    op.create_index(op.f('ix_festival_subcategories_festival_id'), 'festival_subcategories', ['festival_id'], unique=False)
    op.create_index('idx_festival_subcat_fest_id', 'festival_subcategories', ['festival_id'], unique=False)

    # 4. festival_pages table
    op.create_table(
        'festival_pages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('festival_id', sa.Integer(), nullable=False),
        sa.Column('subcategory_id', sa.Integer(), nullable=True),
        sa.Column('category_page_id', sa.Integer(), nullable=True),
        sa.Column('full_url', sa.String(length=1000), nullable=False),
        sa.Column('normalized_url', sa.String(length=1000), nullable=False),
        sa.Column('page_title', sa.String(length=500), nullable=True),
        sa.Column('priority', sa.String(length=50), nullable=False, server_default='PRIMARY'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='ACTIVE'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['festival_id'], ['festivals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subcategory_id'], ['festival_subcategories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['category_page_id'], ['category_pages.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('festival_id', 'normalized_url', name='uq_festival_page_norm_url')
    )
    op.create_index(op.f('ix_festival_pages_id'), 'festival_pages', ['id'], unique=False)
    op.create_index(op.f('ix_festival_pages_festival_id'), 'festival_pages', ['festival_id'], unique=False)
    op.create_index(op.f('ix_festival_pages_subcategory_id'), 'festival_pages', ['subcategory_id'], unique=False)
    op.create_index(op.f('ix_festival_pages_category_page_id'), 'festival_pages', ['category_page_id'], unique=False)
    op.create_index(op.f('ix_festival_pages_normalized_url'), 'festival_pages', ['normalized_url'], unique=False)
    op.create_index('idx_festival_page_fest_norm', 'festival_pages', ['festival_id', 'normalized_url'], unique=False)

    # 5. festival_tasks table
    op.create_table(
        'festival_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('festival_id', sa.Integer(), nullable=False),
        sa.Column('festival_year_date_id', sa.Integer(), nullable=True),
        sa.Column('landing_page_id', sa.Integer(), nullable=True),
        sa.Column('assigned_user_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('task_type', sa.String(length=100), nullable=False, server_default='CONTENT'),
        sa.Column('milestone_stage', sa.String(length=50), nullable=False, server_default='T_MINUS_30'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='NOT_STARTED'),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('completion_date', sa.DateTime(), nullable=True),
        sa.Column('completed_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['festival_id'], ['festivals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['festival_year_date_id'], ['festival_year_dates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['landing_page_id'], ['festival_pages.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['assigned_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['completed_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_festival_tasks_id'), 'festival_tasks', ['id'], unique=False)
    op.create_index(op.f('ix_festival_tasks_festival_id'), 'festival_tasks', ['festival_id'], unique=False)
    op.create_index(op.f('ix_festival_tasks_festival_year_date_id'), 'festival_tasks', ['festival_year_date_id'], unique=False)
    op.create_index(op.f('ix_festival_tasks_landing_page_id'), 'festival_tasks', ['landing_page_id'], unique=False)
    op.create_index(op.f('ix_festival_tasks_assigned_user_id'), 'festival_tasks', ['assigned_user_id'], unique=False)
    op.create_index('idx_festival_task_status_due', 'festival_tasks', ['festival_id', 'status', 'due_date'], unique=False)

    # 6. festival_notifications table
    op.create_table(
        'festival_notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recipient_user_id', sa.Integer(), nullable=True),
        sa.Column('festival_id', sa.Integer(), nullable=True),
        sa.Column('year_date_id', sa.Integer(), nullable=True),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('notification_type', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('action_url', sa.String(length=1000), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('dedup_key', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['recipient_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['festival_id'], ['festivals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['year_date_id'], ['festival_year_dates.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['task_id'], ['festival_tasks.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_festival_notifications_id'), 'festival_notifications', ['id'], unique=False)
    op.create_index(op.f('ix_festival_notifications_recipient_user_id'), 'festival_notifications', ['recipient_user_id'], unique=False)
    op.create_index(op.f('ix_festival_notifications_festival_id'), 'festival_notifications', ['festival_id'], unique=False)
    op.create_index(op.f('ix_festival_notifications_notification_type'), 'festival_notifications', ['notification_type'], unique=False)
    op.create_index(op.f('ix_festival_notifications_is_read'), 'festival_notifications', ['is_read'], unique=False)
    op.create_index(op.f('ix_festival_notifications_dedup_key'), 'festival_notifications', ['dedup_key'], unique=False)
    op.create_index('idx_festival_notif_recipient_read', 'festival_notifications', ['recipient_user_id', 'is_read'], unique=False)
    op.create_index('idx_festival_notif_dedup', 'festival_notifications', ['dedup_key'], unique=False)

def downgrade() -> None:
    op.drop_table('festival_notifications')
    op.drop_table('festival_tasks')
    op.drop_table('festival_pages')
    op.drop_table('festival_subcategories')
    op.drop_table('festival_year_dates')
    op.drop_table('festivals')
