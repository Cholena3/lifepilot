"""Vital tables for Vitals Tracking module.

Revision ID: 010
Revises: 009
Create Date: 2024-01-27 10:00:00.000000

Validates: Requirements 16.1, 16.2, 16.3, 16.4, 16.5
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '010'
down_revision: Union[str, None] = '009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create vitals and vital_target_ranges tables."""
    # Create vitals table
    op.create_table(
        'vitals',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('family_member_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('vital_type', sa.String(50), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(20), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['family_member_id'], ['family_members.id'], ondelete='SET NULL'),
    )
    
    # Create indexes for vitals
    op.create_index('ix_vitals_user_id', 'vitals', ['user_id'])
    op.create_index('ix_vitals_family_member_id', 'vitals', ['family_member_id'])
    op.create_index('ix_vitals_vital_type', 'vitals', ['vital_type'])
    op.create_index('ix_vitals_recorded_at', 'vitals', ['recorded_at'])
    
    # Create vital_target_ranges table
    op.create_table(
        'vital_target_ranges',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('family_member_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('vital_type', sa.String(50), nullable=False),
        sa.Column('min_value', sa.Float(), nullable=True),
        sa.Column('max_value', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['family_member_id'], ['family_members.id'], ondelete='SET NULL'),
    )
    
    # Create indexes for vital_target_ranges
    op.create_index('ix_vital_target_ranges_user_id', 'vital_target_ranges', ['user_id'])
    op.create_index('ix_vital_target_ranges_family_member_id', 'vital_target_ranges', ['family_member_id'])
    op.create_index('ix_vital_target_ranges_vital_type', 'vital_target_ranges', ['vital_type'])
    
    # Create unique constraint for user + family_member + vital_type combination
    op.create_index(
        'ix_vital_target_ranges_unique',
        'vital_target_ranges',
        ['user_id', 'family_member_id', 'vital_type'],
        unique=True,
    )


def downgrade() -> None:
    """Drop vital_target_ranges and vitals tables."""
    op.drop_index('ix_vital_target_ranges_unique', table_name='vital_target_ranges')
    op.drop_index('ix_vital_target_ranges_vital_type', table_name='vital_target_ranges')
    op.drop_index('ix_vital_target_ranges_family_member_id', table_name='vital_target_ranges')
    op.drop_index('ix_vital_target_ranges_user_id', table_name='vital_target_ranges')
    op.drop_table('vital_target_ranges')
    
    op.drop_index('ix_vitals_recorded_at', table_name='vitals')
    op.drop_index('ix_vitals_vital_type', table_name='vitals')
    op.drop_index('ix_vitals_family_member_id', table_name='vitals')
    op.drop_index('ix_vitals_user_id', table_name='vitals')
    op.drop_table('vitals')
