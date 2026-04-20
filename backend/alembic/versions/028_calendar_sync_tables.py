"""Calendar sync tables for Google Calendar integration.

Revision ID: 028
Revises: 027
Create Date: 2024-01-01 00:00:00.000000

Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '028'
down_revision: Union[str, None] = '027'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create google_calendar_tokens and calendar_syncs tables."""
    # Create google_calendar_tokens table
    op.create_table(
        'google_calendar_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expiry', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scope', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', name='uq_google_calendar_tokens_user_id'),
    )
    op.create_index('ix_google_calendar_tokens_user_id', 'google_calendar_tokens', ['user_id'])

    # Create calendar_syncs table
    op.create_table(
        'calendar_syncs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('exam_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('google_event_id', sa.String(255), nullable=False),
        sa.Column('synced_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['exam_id'], ['exams.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_calendar_syncs_user_id', 'calendar_syncs', ['user_id'])
    op.create_index('ix_calendar_syncs_exam_id', 'calendar_syncs', ['exam_id'])


def downgrade() -> None:
    """Drop calendar sync tables in reverse dependency order."""
    op.drop_index('ix_calendar_syncs_exam_id', table_name='calendar_syncs')
    op.drop_index('ix_calendar_syncs_user_id', table_name='calendar_syncs')
    op.drop_table('calendar_syncs')

    op.drop_index('ix_google_calendar_tokens_user_id', table_name='google_calendar_tokens')
    op.drop_table('google_calendar_tokens')
