"""Health record sharing tables.

Revision ID: 027
Revises: 026
Create Date: 2024-01-01 00:00:00.000000

Validates: Requirements 18.1, 18.2, 18.3, 18.4, 18.5
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '027'
down_revision: Union[str, None] = '026'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create health_record_shares and health_share_access_logs tables."""
    # Create health_record_shares table
    op.create_table(
        'health_record_shares',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('public_token', sa.String(64), nullable=False),
        sa.Column('doctor_name', sa.String(255), nullable=True),
        sa.Column('doctor_email', sa.String(255), nullable=True),
        sa.Column('purpose', sa.String(255), nullable=True),
        sa.Column('record_ids', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('access_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('public_token', name='uq_health_record_shares_public_token'),
    )
    op.create_index('ix_health_record_shares_user_id', 'health_record_shares', ['user_id'])
    op.create_index('ix_health_record_shares_public_token', 'health_record_shares', ['public_token'])

    # Create health_share_access_logs table
    op.create_table(
        'health_share_access_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('share_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('accessed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['share_id'], ['health_record_shares.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_health_share_access_logs_share_id', 'health_share_access_logs', ['share_id'])


def downgrade() -> None:
    """Drop health share tables in reverse dependency order."""
    op.drop_index('ix_health_share_access_logs_share_id', table_name='health_share_access_logs')
    op.drop_table('health_share_access_logs')

    op.drop_index('ix_health_record_shares_public_token', table_name='health_record_shares')
    op.drop_index('ix_health_record_shares_user_id', table_name='health_record_shares')
    op.drop_table('health_record_shares')
