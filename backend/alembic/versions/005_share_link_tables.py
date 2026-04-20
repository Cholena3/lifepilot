"""Share link tables for document sharing.

Revision ID: 005
Revises: 004
Create Date: 2024-01-15 10:00:00.000000

Validates: Requirements 9.1, 9.2, 9.4, 9.5, 9.6
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create share_links and share_link_accesses tables."""
    # Create share_links table
    op.create_table(
        'share_links',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token', sa.String(64), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    # Create indexes for share_links
    op.create_index('ix_share_links_document_id', 'share_links', ['document_id'])
    op.create_index('ix_share_links_user_id', 'share_links', ['user_id'])
    op.create_index('ix_share_links_token', 'share_links', ['token'], unique=True)
    
    # Create share_link_accesses table
    op.create_table(
        'share_link_accesses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('share_link_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=False),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('accessed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['share_link_id'], ['share_links.id'], ondelete='CASCADE'),
    )
    
    # Create index for share_link_accesses
    op.create_index('ix_share_link_accesses_share_link_id', 'share_link_accesses', ['share_link_id'])


def downgrade() -> None:
    """Drop share_links and share_link_accesses tables."""
    op.drop_index('ix_share_link_accesses_share_link_id', table_name='share_link_accesses')
    op.drop_table('share_link_accesses')
    
    op.drop_index('ix_share_links_token', table_name='share_links')
    op.drop_index('ix_share_links_user_id', table_name='share_links')
    op.drop_index('ix_share_links_document_id', table_name='share_links')
    op.drop_table('share_links')
