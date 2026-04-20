"""Emergency info table for Emergency Health Information module.

Revision ID: 011
Revises: 010
Create Date: 2024-01-28 10:00:00.000000

Validates: Requirements 17.1, 17.2, 17.3, 17.4, 17.5
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '011'
down_revision: Union[str, None] = '010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create emergency_info table."""
    op.create_table(
        'emergency_info',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('public_token', sa.String(64), nullable=False),
        sa.Column('blood_type', sa.String(10), nullable=True),
        sa.Column('allergies', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('medical_conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('emergency_contacts', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('current_medications', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('visible_fields', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('qr_code_path', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id'),
        sa.UniqueConstraint('public_token'),
    )
    
    # Create indexes
    op.create_index('ix_emergency_info_user_id', 'emergency_info', ['user_id'])
    op.create_index('ix_emergency_info_public_token', 'emergency_info', ['public_token'])


def downgrade() -> None:
    """Drop emergency_info table."""
    op.drop_index('ix_emergency_info_public_token', table_name='emergency_info')
    op.drop_index('ix_emergency_info_user_id', table_name='emergency_info')
    op.drop_table('emergency_info')
