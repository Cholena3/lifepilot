"""Split tables for Bill Splitting module.

Revision ID: 026
Revises: 025
Create Date: 2024-01-01 00:00:00.000000

Validates: Requirements 13.1, 13.2, 13.3, 13.5, 13.7
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '026'
down_revision: Union[str, None] = '025'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create split_groups, split_group_members, shared_expenses, expense_splits, and settlements tables."""
    # Create split_groups table
    op.create_table(
        'split_groups',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_split_groups_created_by', 'split_groups', ['created_by'])

    # Create split_group_members table
    op.create_table(
        'split_group_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['group_id'], ['split_groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_split_group_members_group_id', 'split_group_members', ['group_id'])
    op.create_index('ix_split_group_members_user_id', 'split_group_members', ['user_id'])

    # Create shared_expenses table
    op.create_table(
        'shared_expenses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('paid_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('expense_date', sa.Date(), nullable=False),
        sa.Column('split_type', sa.String(20), nullable=False, server_default='equal'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['group_id'], ['split_groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['paid_by'], ['split_group_members.id'], ondelete='RESTRICT'),
    )
    op.create_index('ix_shared_expenses_group_id', 'shared_expenses', ['group_id'])
    op.create_index('ix_shared_expenses_paid_by', 'shared_expenses', ['paid_by'])
    op.create_index('ix_shared_expenses_expense_date', 'shared_expenses', ['expense_date'])

    # Create expense_splits table
    op.create_table(
        'expense_splits',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('shared_expense_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('member_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('is_settled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['shared_expense_id'], ['shared_expenses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['member_id'], ['split_group_members.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_expense_splits_shared_expense_id', 'expense_splits', ['shared_expense_id'])
    op.create_index('ix_expense_splits_member_id', 'expense_splits', ['member_id'])

    # Create settlements table
    op.create_table(
        'settlements',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('from_member', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('to_member', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('settlement_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['group_id'], ['split_groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['from_member'], ['split_group_members.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['to_member'], ['split_group_members.id'], ondelete='RESTRICT'),
    )
    op.create_index('ix_settlements_group_id', 'settlements', ['group_id'])
    op.create_index('ix_settlements_from_member', 'settlements', ['from_member'])
    op.create_index('ix_settlements_to_member', 'settlements', ['to_member'])
    op.create_index('ix_settlements_settlement_date', 'settlements', ['settlement_date'])


def downgrade() -> None:
    """Drop split tables in reverse dependency order."""
    op.drop_index('ix_settlements_settlement_date', table_name='settlements')
    op.drop_index('ix_settlements_to_member', table_name='settlements')
    op.drop_index('ix_settlements_from_member', table_name='settlements')
    op.drop_index('ix_settlements_group_id', table_name='settlements')
    op.drop_table('settlements')

    op.drop_index('ix_expense_splits_member_id', table_name='expense_splits')
    op.drop_index('ix_expense_splits_shared_expense_id', table_name='expense_splits')
    op.drop_table('expense_splits')

    op.drop_index('ix_shared_expenses_expense_date', table_name='shared_expenses')
    op.drop_index('ix_shared_expenses_paid_by', table_name='shared_expenses')
    op.drop_index('ix_shared_expenses_group_id', table_name='shared_expenses')
    op.drop_table('shared_expenses')

    op.drop_index('ix_split_group_members_user_id', table_name='split_group_members')
    op.drop_index('ix_split_group_members_group_id', table_name='split_group_members')
    op.drop_table('split_group_members')

    op.drop_index('ix_split_groups_created_by', table_name='split_groups')
    op.drop_table('split_groups')
