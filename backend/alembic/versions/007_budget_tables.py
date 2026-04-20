"""Budget tables for Money Manager module.

Revision ID: 007
Revises: 006
Create Date: 2024-01-21 10:00:00.000000

Validates: Requirements 11.1, 11.5, 11.6
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create budgets and budget_history tables."""
    # Create budgets table
    op.create_table(
        'budgets',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('period', sa.String(20), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('threshold_50_notified', sa.Boolean(), nullable=False, default=False),
        sa.Column('threshold_80_notified', sa.Boolean(), nullable=False, default=False),
        sa.Column('threshold_100_notified', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['expense_categories.id'], ondelete='CASCADE'),
    )
    
    # Create indexes for budgets
    op.create_index('ix_budgets_user_id', 'budgets', ['user_id'])
    op.create_index('ix_budgets_category_id', 'budgets', ['category_id'])
    
    # Create budget_history table
    op.create_table(
        'budget_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('category_name', sa.String(100), nullable=False),
        sa.Column('budget_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('spent_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('period', sa.String(20), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('archived_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['expense_categories.id'], ondelete='SET NULL'),
    )
    
    # Create indexes for budget_history
    op.create_index('ix_budget_history_user_id', 'budget_history', ['user_id'])
    op.create_index('ix_budget_history_category_id', 'budget_history', ['category_id'])


def downgrade() -> None:
    """Drop budgets and budget_history tables."""
    op.drop_index('ix_budget_history_category_id', table_name='budget_history')
    op.drop_index('ix_budget_history_user_id', table_name='budget_history')
    op.drop_table('budget_history')
    
    op.drop_index('ix_budgets_category_id', table_name='budgets')
    op.drop_index('ix_budgets_user_id', table_name='budgets')
    op.drop_table('budgets')
