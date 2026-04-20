"""Expense tables for Money Manager module.

Revision ID: 006
Revises: 005
Create Date: 2024-01-20 10:00:00.000000

Validates: Requirements 10.1, 10.4, 10.5, 10.6
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create expense_categories and expenses tables."""
    # Create expense_categories table
    op.create_table(
        'expense_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('color', sa.String(7), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    # Create index for expense_categories
    op.create_index('ix_expense_categories_user_id', 'expense_categories', ['user_id'])
    
    # Create expenses table
    op.create_table(
        'expenses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('expense_date', sa.Date(), nullable=False),
        sa.Column('receipt_url', sa.String(500), nullable=True),
        sa.Column('ocr_data', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['expense_categories.id'], ondelete='RESTRICT'),
    )
    
    # Create indexes for expenses
    op.create_index('ix_expenses_user_id', 'expenses', ['user_id'])
    op.create_index('ix_expenses_category_id', 'expenses', ['category_id'])
    op.create_index('ix_expenses_expense_date', 'expenses', ['expense_date'])
    
    # Insert default expense categories
    op.execute("""
        INSERT INTO expense_categories (id, user_id, name, icon, color, is_default, created_at, updated_at)
        VALUES 
            (gen_random_uuid(), NULL, 'Food & Dining', 'utensils', '#FF6B6B', true, NOW(), NOW()),
            (gen_random_uuid(), NULL, 'Transportation', 'car', '#4ECDC4', true, NOW(), NOW()),
            (gen_random_uuid(), NULL, 'Shopping', 'shopping-bag', '#45B7D1', true, NOW(), NOW()),
            (gen_random_uuid(), NULL, 'Entertainment', 'film', '#96CEB4', true, NOW(), NOW()),
            (gen_random_uuid(), NULL, 'Bills & Utilities', 'file-text', '#FFEAA7', true, NOW(), NOW()),
            (gen_random_uuid(), NULL, 'Healthcare', 'heart', '#DDA0DD', true, NOW(), NOW()),
            (gen_random_uuid(), NULL, 'Education', 'book', '#98D8C8', true, NOW(), NOW()),
            (gen_random_uuid(), NULL, 'Personal Care', 'user', '#F7DC6F', true, NOW(), NOW()),
            (gen_random_uuid(), NULL, 'Travel', 'plane', '#BB8FCE', true, NOW(), NOW()),
            (gen_random_uuid(), NULL, 'Other', 'more-horizontal', '#AEB6BF', true, NOW(), NOW())
    """)


def downgrade() -> None:
    """Drop expenses and expense_categories tables."""
    op.drop_index('ix_expenses_expense_date', table_name='expenses')
    op.drop_index('ix_expenses_category_id', table_name='expenses')
    op.drop_index('ix_expenses_user_id', table_name='expenses')
    op.drop_table('expenses')
    
    op.drop_index('ix_expense_categories_user_id', table_name='expense_categories')
    op.drop_table('expense_categories')
