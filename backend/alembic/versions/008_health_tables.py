"""Health tables for Health module.

Revision ID: 008
Revises: 007
Create Date: 2024-01-25 10:00:00.000000

Validates: Requirements 14.1, 14.2, 14.5
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '008'
down_revision: Union[str, None] = '007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create family_members and health_records tables."""
    # Create family_members table
    op.create_table(
        'family_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('relationship', sa.String(50), nullable=False),
        sa.Column('date_of_birth', sa.Date(), nullable=True),
        sa.Column('gender', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    # Create index for family_members
    op.create_index('ix_family_members_user_id', 'family_members', ['user_id'])
    
    # Create health_records table
    op.create_table(
        'health_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('family_member_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('content_type', sa.String(100), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('encryption_key', sa.String(255), nullable=False),
        sa.Column('ocr_text', sa.Text(), nullable=True),
        sa.Column('extracted_data', postgresql.JSONB(), nullable=True),
        sa.Column('record_date', sa.Date(), nullable=True),
        sa.Column('doctor_name', sa.String(255), nullable=True),
        sa.Column('hospital_name', sa.String(255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['family_member_id'], ['family_members.id'], ondelete='SET NULL'),
    )
    
    # Create indexes for health_records
    op.create_index('ix_health_records_user_id', 'health_records', ['user_id'])
    op.create_index('ix_health_records_family_member_id', 'health_records', ['family_member_id'])
    op.create_index('ix_health_records_category', 'health_records', ['category'])
    op.create_index('ix_health_records_record_date', 'health_records', ['record_date'])


def downgrade() -> None:
    """Drop health_records and family_members tables."""
    op.drop_index('ix_health_records_record_date', table_name='health_records')
    op.drop_index('ix_health_records_category', table_name='health_records')
    op.drop_index('ix_health_records_family_member_id', table_name='health_records')
    op.drop_index('ix_health_records_user_id', table_name='health_records')
    op.drop_table('health_records')
    
    op.drop_index('ix_family_members_user_id', table_name='family_members')
    op.drop_table('family_members')
