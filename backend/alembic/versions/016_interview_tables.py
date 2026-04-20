"""Create interview preparation tables.

Revision ID: 016
Revises: 015
Create Date: 2024-01-17

Validates: Requirements 28.1, 28.2, 28.3, 28.4, 28.5
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create interview_notes table
    # Requirement 28.1: Associate interview notes with a job application
    # Requirement 28.2: Store company research, questions asked, and answers prepared
    # Requirement 28.4: Allow users to rate their interview performance
    op.create_table(
        "interview_notes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("application_id", sa.UUID(), nullable=False),
        sa.Column(
            "interview_type",
            postgresql.ENUM(
                "phone_screen",
                "technical",
                "behavioral",
                "system_design",
                "coding",
                "panel",
                "hr",
                "final",
                "other",
                name="interviewtype",
            ),
            nullable=False,
            default="other",
        ),
        sa.Column("interview_date", sa.Date(), nullable=True),
        sa.Column("interview_time", sa.String(length=5), nullable=True),
        sa.Column("company_research", sa.Text(), nullable=True),
        sa.Column("questions_asked", postgresql.JSONB(), nullable=True),
        sa.Column("answers_prepared", postgresql.JSONB(), nullable=True),
        sa.Column("performance_rating", sa.Integer(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("outcome", sa.String(length=50), nullable=True),
        sa.Column("reminder_sent", sa.Boolean(), nullable=False, default=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["job_applications.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_interview_notes_application_id"),
        "interview_notes",
        ["application_id"],
        unique=False,
    )

    # Create interview_preparation_reminders table
    # Requirement 28.3: Send preparation reminders when interview is scheduled
    op.create_table(
        "interview_preparation_reminders",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("interview_note_id", sa.UUID(), nullable=False),
        sa.Column("reminder_date", sa.Date(), nullable=False),
        sa.Column("reminder_time", sa.String(length=5), nullable=True),
        sa.Column("is_sent", sa.Boolean(), nullable=False, default=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["interview_note_id"],
            ["interview_notes.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_interview_preparation_reminders_interview_note_id"),
        "interview_preparation_reminders",
        ["interview_note_id"],
        unique=False,
    )

    # Create interview_qa table
    # Requirement 28.2: Store questions asked and answers prepared
    op.create_table(
        "interview_qa",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("interview_note_id", sa.UUID(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("is_asked", sa.Boolean(), nullable=False, default=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["interview_note_id"],
            ["interview_notes.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_interview_qa_interview_note_id"),
        "interview_qa",
        ["interview_note_id"],
        unique=False,
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(
        op.f("ix_interview_qa_interview_note_id"),
        table_name="interview_qa",
    )
    op.drop_table("interview_qa")

    op.drop_index(
        op.f("ix_interview_preparation_reminders_interview_note_id"),
        table_name="interview_preparation_reminders",
    )
    op.drop_table("interview_preparation_reminders")

    op.drop_index(
        op.f("ix_interview_notes_application_id"),
        table_name="interview_notes",
    )
    op.drop_table("interview_notes")

    # Drop enum
    op.execute("DROP TYPE IF EXISTS interviewtype")
