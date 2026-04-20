"""Wardrobe tables for clothing management module.

Revision ID: 029
Revises: 028
Create Date: 2024-01-01 00:00:00.000000

Validates: Requirements 19.1-19.6, 20.1-20.6, 21.1-21.5, 22.1-22.5, 23.1-23.5
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '029'
down_revision: Union[str, None] = '028'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create wardrobe_items, wear_logs, outfits, outfit_items, outfit_plans, packing_lists, and packing_list_items tables."""
    # Create wardrobe_items table
    op.create_table(
        'wardrobe_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('image_url', sa.String(500), nullable=False),
        sa.Column('processed_image_url', sa.String(500), nullable=True),
        sa.Column('item_type', sa.String(50), nullable=False),
        sa.Column('primary_color', sa.String(50), nullable=True),
        sa.Column('pattern', sa.String(50), nullable=True),
        sa.Column('brand', sa.String(100), nullable=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('price', sa.Numeric(10, 2), nullable=True),
        sa.Column('purchase_date', sa.Date(), nullable=True),
        sa.Column('in_laundry', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('wear_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('last_worn', sa.DateTime(timezone=True), nullable=True),
        sa.Column('occasions', postgresql.JSONB(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_wardrobe_items_user_id', 'wardrobe_items', ['user_id'])
    op.create_index('ix_wardrobe_items_item_type', 'wardrobe_items', ['item_type'])

    # Create wear_logs table
    op.create_table(
        'wear_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('item_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('worn_date', sa.Date(), nullable=False),
        sa.Column('occasion', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['item_id'], ['wardrobe_items.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_wear_logs_item_id', 'wear_logs', ['item_id'])
    op.create_index('ix_wear_logs_worn_date', 'wear_logs', ['worn_date'])

    # Create outfits table
    op.create_table(
        'outfits',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('occasion', sa.String(50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_outfits_user_id', 'outfits', ['user_id'])

    # Create outfit_items table
    op.create_table(
        'outfit_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('outfit_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('wardrobe_item_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['outfit_id'], ['outfits.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['wardrobe_item_id'], ['wardrobe_items.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_outfit_items_outfit_id', 'outfit_items', ['outfit_id'])
    op.create_index('ix_outfit_items_wardrobe_item_id', 'outfit_items', ['wardrobe_item_id'])

    # Create outfit_plans table
    op.create_table(
        'outfit_plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('outfit_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('planned_date', sa.Date(), nullable=False),
        sa.Column('event_name', sa.String(255), nullable=True),
        sa.Column('is_completed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['outfit_id'], ['outfits.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_outfit_plans_user_id', 'outfit_plans', ['user_id'])
    op.create_index('ix_outfit_plans_outfit_id', 'outfit_plans', ['outfit_id'])
    op.create_index('ix_outfit_plans_planned_date', 'outfit_plans', ['planned_date'])

    # Create packing_lists table
    op.create_table(
        'packing_lists',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('destination', sa.String(255), nullable=True),
        sa.Column('trip_start', sa.Date(), nullable=True),
        sa.Column('trip_end', sa.Date(), nullable=True),
        sa.Column('is_template', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_packing_lists_user_id', 'packing_lists', ['user_id'])

    # Create packing_list_items table
    op.create_table(
        'packing_list_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('packing_list_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('wardrobe_item_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('custom_item_name', sa.String(255), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.Column('is_packed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['packing_list_id'], ['packing_lists.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['wardrobe_item_id'], ['wardrobe_items.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_packing_list_items_packing_list_id', 'packing_list_items', ['packing_list_id'])
    op.create_index('ix_packing_list_items_wardrobe_item_id', 'packing_list_items', ['wardrobe_item_id'])


def downgrade() -> None:
    """Drop wardrobe tables in reverse dependency order."""
    op.drop_index('ix_packing_list_items_wardrobe_item_id', table_name='packing_list_items')
    op.drop_index('ix_packing_list_items_packing_list_id', table_name='packing_list_items')
    op.drop_table('packing_list_items')

    op.drop_index('ix_packing_lists_user_id', table_name='packing_lists')
    op.drop_table('packing_lists')

    op.drop_index('ix_outfit_plans_planned_date', table_name='outfit_plans')
    op.drop_index('ix_outfit_plans_outfit_id', table_name='outfit_plans')
    op.drop_index('ix_outfit_plans_user_id', table_name='outfit_plans')
    op.drop_table('outfit_plans')

    op.drop_index('ix_outfit_items_wardrobe_item_id', table_name='outfit_items')
    op.drop_index('ix_outfit_items_outfit_id', table_name='outfit_items')
    op.drop_table('outfit_items')

    op.drop_index('ix_outfits_user_id', table_name='outfits')
    op.drop_table('outfits')

    op.drop_index('ix_wear_logs_worn_date', table_name='wear_logs')
    op.drop_index('ix_wear_logs_item_id', table_name='wear_logs')
    op.drop_table('wear_logs')

    op.drop_index('ix_wardrobe_items_item_type', table_name='wardrobe_items')
    op.drop_index('ix_wardrobe_items_user_id', table_name='wardrobe_items')
    op.drop_table('wardrobe_items')
