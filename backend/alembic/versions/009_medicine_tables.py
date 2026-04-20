"""Medicine tables for Medicine Tracking module.

Revision ID: 009
Revises: 008
Create Date: 2024-01-26 10:00:00.000000

Validates: Requirements 15.1, 15.2, 15.3, 15.4, 15.5, 15.6
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '009'
down_revision: Union[str, None] = '008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create medicines and medicine_doses tables."""
    # Create medicines table
    op.create_table(
        'medicines',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('health_record_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('dosage', sa.String(100), nullable=True),
        sa.Column('frequency', sa.String(50), nullable=False, server_default='once_daily'),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('reminder_times', postgresql.JSONB(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('total_quantity', sa.Integer(), nullable=True),
        sa.Column('remaining_quantity', sa.Integer(), nullable=True),
        sa.Column('refill_threshold', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['health_record_id'], ['health_records.id'], ondelete='SET NULL'),
    )
    
    # Create indexes for medicines
    op.create_index('ix_medicines_user_id', 'medicines', ['user_id'])
    op.create_index('ix_medicines_health_record_id', 'medicines', ['health_record_id'])
    
    # Create medicine_doses table
    op.create_table(
        'medicine_doses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('medicine_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('scheduled_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('taken_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='scheduled'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('reminder_sent', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('followup_reminder_sent', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['medicine_id'], ['medicines.id'], ondelete='CASCADE'),
    )
    
    # Create indexes for medicine_doses
    op.create_index('ix_medicine_doses_medicine_id', 'medicine_doses', ['medicine_id'])
    op.create_index('ix_medicine_doses_scheduled_time', 'medicine_doses', ['scheduled_time'])
    op.create_index('ix_medicine_doses_status', 'medicine_doses', ['status'])


def downgrade() -> None:
    """Drop medicine_doses and medicines tables."""
    op.drop_index('ix_medicine_doses_status', table_name='medicine_doses')
    op.drop_index('ix_medicine_doses_scheduled_time', table_name='medicine_doses')
    op.drop_index('ix_medicine_doses_medicine_id', table_name='medicine_doses')
    op.drop_table('medicine_doses')
    
    op.drop_index('ix_medicines_health_record_id', table_name='medicines')
    op.drop_index('ix_medicines_user_id', table_name='medicines')
    op.drop_table('medicines')
