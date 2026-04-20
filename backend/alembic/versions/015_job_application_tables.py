"""Create job application tables.

Revision ID: 015
Revises: 014
Create Date: 2024-01-16

Validates: Requirements 27.1, 27.2, 27.3, 27.4, 27.5, 27.6
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create job_applications table
    # Requirement 27.1: Store company, role, date, source, and status
    op.create_table(
        "job_applications",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=255), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column(
            "source",
            postgresql.ENUM(
                "linkedin",
                "indeed",
                "company_website",
                "referral",
                "recruiter",
                "job_board",
                "networking",
                "other",
                name="applicationsource",
            ),
            nullable=False,
            default="other",
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "applied",
                "screening",
                "interview",
                "offer",
                "rejected",
                "withdrawn",
                name="applicationstatus",
            ),
            nullable=False,
            default="applied",
        ),
        sa.Column("salary_min", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("salary_max", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("applied_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("is_remote", sa.Boolean(), nullable=False, default=False),
        sa.Column(
            "last_status_update",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
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
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_job_applications_user_id"),
        "job_applications",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_job_applications_status"),
        "job_applications",
        ["status"],
        unique=False,
    )

    # Create application_status_history table
    # Requirement 27.3: Record status changes with timestamp
    op.create_table(
        "application_status_history",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("application_id", sa.UUID(), nullable=False),
        sa.Column(
            "previous_status",
            postgresql.ENUM(
                "applied",
                "screening",
                "interview",
                "offer",
                "rejected",
                "withdrawn",
                name="applicationstatus",
            ),
            nullable=True,
        ),
        sa.Column(
            "new_status",
            postgresql.ENUM(
                "applied",
                "screening",
                "interview",
                "offer",
                "rejected",
                "withdrawn",
                name="applicationstatus",
            ),
            nullable=False,
        ),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["job_applications.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_application_status_history_application_id"),
        "application_status_history",
        ["application_id"],
        unique=False,
    )

    # Create application_follow_up_reminders table
    # Requirement 27.5: Follow-up reminders
    op.create_table(
        "application_follow_up_reminders",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("application_id", sa.UUID(), nullable=False),
        sa.Column("reminder_date", sa.Date(), nullable=False),
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
            ["application_id"],
            ["job_applications.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_application_follow_up_reminders_application_id"),
        "application_follow_up_reminders",
        ["application_id"],
        unique=False,
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(
        op.f("ix_application_follow_up_reminders_application_id"),
        table_name="application_follow_up_reminders",
    )
    op.drop_table("application_follow_up_reminders")

    op.drop_index(
        op.f("ix_application_status_history_application_id"),
        table_name="application_status_history",
    )
    op.drop_table("application_status_history")

    op.drop_index(op.f("ix_job_applications_status"), table_name="job_applications")
    op.drop_index(op.f("ix_job_applications_user_id"), table_name="job_applications")
    op.drop_table("job_applications")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS applicationsource")
    op.execute("DROP TYPE IF EXISTS applicationstatus")
