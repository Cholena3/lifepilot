"""Skill tables for Career Module skill inventory management.

Revision ID: 012
Revises: 011
Create Date: 2024-01-27 10:00:00.000000

Validates: Requirements 24.1, 24.2, 24.3, 24.4, 24.5
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '012'
down_revision: Union[str, None] = '011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create skills and skill_proficiency_history tables."""
    # Create skills table
    # Requirement 24.1: Store skill name, category, and proficiency level
    # Requirement 24.2: Support proficiency levels: Beginner, Intermediate, Advanced, Expert
    op.create_table(
        'skills',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('category', postgresql.ENUM(
            'programming', 'framework', 'database', 'devops', 'cloud',
            'soft_skill', 'language', 'design', 'data_science', 'other',
            name='skillcategory',
        ), nullable=False, server_default='other'),
        sa.Column('proficiency', postgresql.ENUM(
            'beginner', 'intermediate', 'advanced', 'expert',
            name='proficiencylevel',
        ), nullable=False, server_default='beginner'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    # Create indexes for skills
    op.create_index('ix_skills_user_id', 'skills', ['user_id'])
    op.create_index('ix_skills_category', 'skills', ['category'])
    op.create_index('ix_skills_proficiency', 'skills', ['proficiency'])
    
    # Create skill_proficiency_history table
    # Requirement 24.3: Record proficiency changes with timestamp
    op.create_table(
        'skill_proficiency_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('skill_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('previous_level', postgresql.ENUM(
            'beginner', 'intermediate', 'advanced', 'expert',
            name='proficiencylevel',
        ), nullable=True),
        sa.Column('new_level', postgresql.ENUM(
            'beginner', 'intermediate', 'advanced', 'expert',
            name='proficiencylevel',
        ), nullable=False),
        sa.Column('changed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='CASCADE'),
    )
    
    # Create indexes for skill_proficiency_history
    op.create_index('ix_skill_proficiency_history_skill_id', 'skill_proficiency_history', ['skill_id'])
    op.create_index('ix_skill_proficiency_history_changed_at', 'skill_proficiency_history', ['changed_at'])


def downgrade() -> None:
    """Drop skill_proficiency_history and skills tables."""
    op.drop_index('ix_skill_proficiency_history_changed_at', table_name='skill_proficiency_history')
    op.drop_index('ix_skill_proficiency_history_skill_id', table_name='skill_proficiency_history')
    op.drop_table('skill_proficiency_history')
    
    op.drop_index('ix_skills_proficiency', table_name='skills')
    op.drop_index('ix_skills_category', table_name='skills')
    op.drop_index('ix_skills_user_id', table_name='skills')
    op.drop_table('skills')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS skillcategory')
    op.execute('DROP TYPE IF EXISTS proficiencylevel')
