"""Exam tables for exam feed and discovery module.

Revision ID: 019
Revises: 018
Create Date: 2024-01-28 10:00:00.000000

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.8
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '019'
down_revision: Union[str, None] = '018'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create exam, exam_bookmarks, and exam_applications tables."""
    # Create exams table
    # Requirement 3.1: Filter by degree, branch, graduation year
    # Requirement 3.2: Apply CGPA filter
    # Requirement 3.3: Apply backlog filter
    # Requirement 3.8: Return syllabus, cutoffs, previous papers, and resource links
    op.create_table(
        'exams',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('organization', sa.String(255), nullable=False),
        sa.Column('exam_type', postgresql.ENUM(
            'campus_placement', 'off_campus', 'internship',
            'higher_education', 'government', 'scholarship',
            name='examtype',
        ), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('registration_start', sa.Date(), nullable=True),
        sa.Column('registration_end', sa.Date(), nullable=True),
        sa.Column('exam_date', sa.Date(), nullable=True),
        # Eligibility criteria
        sa.Column('min_cgpa', sa.Numeric(3, 1), nullable=True),
        sa.Column('max_backlogs', sa.Integer(), nullable=True),
        sa.Column('eligible_degrees', postgresql.JSONB(), nullable=True),
        sa.Column('eligible_branches', postgresql.JSONB(), nullable=True),
        sa.Column('graduation_year_min', sa.Integer(), nullable=True),
        sa.Column('graduation_year_max', sa.Integer(), nullable=True),
        # Exam details
        sa.Column('syllabus', sa.Text(), nullable=True),
        sa.Column('cutoffs', postgresql.JSONB(), nullable=True),
        sa.Column('resources', postgresql.JSONB(), nullable=True),
        # Scraping metadata
        sa.Column('source_url', sa.String(500), nullable=True),
        sa.Column('scraped_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('min_cgpa IS NULL OR (min_cgpa >= 0.0 AND min_cgpa <= 10.0)', name='check_exam_min_cgpa_range'),
        sa.CheckConstraint('max_backlogs IS NULL OR max_backlogs >= 0', name='check_exam_max_backlogs_non_negative'),
    )
    
    # Create indexes for exams
    op.create_index('ix_exams_name', 'exams', ['name'])
    op.create_index('ix_exams_organization', 'exams', ['organization'])
    op.create_index('ix_exams_exam_type', 'exams', ['exam_type'])
    op.create_index('ix_exams_registration_end', 'exams', ['registration_end'])
    op.create_index('ix_exams_exam_date', 'exams', ['exam_date'])
    op.create_index('ix_exams_is_active', 'exams', ['is_active'])
    
    # Create exam_bookmarks table
    # Requirement 3.5: Add exam to user's saved exams list
    op.create_table(
        'exam_bookmarks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('exam_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['exam_id'], ['exams.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'exam_id', name='uq_exam_bookmark_user_exam'),
    )
    
    # Create indexes for exam_bookmarks
    op.create_index('ix_exam_bookmarks_user_id', 'exam_bookmarks', ['user_id'])
    op.create_index('ix_exam_bookmarks_exam_id', 'exam_bookmarks', ['exam_id'])
    
    # Create exam_applications table
    # Requirement 3.6: Record application date and update status
    op.create_table(
        'exam_applications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('exam_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', postgresql.ENUM(
            'applied', 'shortlisted', 'rejected', 'selected', 'withdrawn',
            name='examapplicationstatus',
        ), nullable=False, server_default='applied'),
        sa.Column('applied_date', sa.Date(), nullable=False, server_default=sa.func.current_date()),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['exam_id'], ['exams.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'exam_id', name='uq_exam_application_user_exam'),
    )
    
    # Create indexes for exam_applications
    op.create_index('ix_exam_applications_user_id', 'exam_applications', ['user_id'])
    op.create_index('ix_exam_applications_exam_id', 'exam_applications', ['exam_id'])
    op.create_index('ix_exam_applications_status', 'exam_applications', ['status'])


def downgrade() -> None:
    """Drop exam_applications, exam_bookmarks, and exams tables."""
    # Drop exam_applications
    op.drop_index('ix_exam_applications_status', table_name='exam_applications')
    op.drop_index('ix_exam_applications_exam_id', table_name='exam_applications')
    op.drop_index('ix_exam_applications_user_id', table_name='exam_applications')
    op.drop_table('exam_applications')
    
    # Drop exam_bookmarks
    op.drop_index('ix_exam_bookmarks_exam_id', table_name='exam_bookmarks')
    op.drop_index('ix_exam_bookmarks_user_id', table_name='exam_bookmarks')
    op.drop_table('exam_bookmarks')
    
    # Drop exams
    op.drop_index('ix_exams_is_active', table_name='exams')
    op.drop_index('ix_exams_exam_date', table_name='exams')
    op.drop_index('ix_exams_registration_end', table_name='exams')
    op.drop_index('ix_exams_exam_type', table_name='exams')
    op.drop_index('ix_exams_organization', table_name='exams')
    op.drop_index('ix_exams_name', table_name='exams')
    op.drop_table('exams')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS examapplicationstatus')
    op.execute('DROP TYPE IF EXISTS examtype')
