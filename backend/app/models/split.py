"""Split models for the Bill Splitting module.

Includes SplitGroup, SplitGroupMember, SharedExpense, ExpenseSplit, and Settlement models.

Validates: Requirements 13.1, 13.2, 13.3, 13.7
"""

import uuid
from datetime import datetime, date
from typing import TYPE_CHECKING, Optional, List
from enum import Enum

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, Boolean, func, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class SplitType(str, Enum):
    """Enum for split types."""
    EQUAL = "equal"
    PERCENTAGE = "percentage"
    EXACT = "exact"


class SplitGroup(Base, UUIDMixin, TimestampMixin):
    """Split group model for managing expense sharing groups.
    
    Validates: Requirements 13.1
    
    Attributes:
        id: Unique identifier for the group
        created_by: Foreign key to the user who created the group
        name: Group name
        description: Optional group description
        created_at: Timestamp when group was created
        updated_at: Timestamp when group was last updated
    """
    
    __tablename__ = "split_groups"
    
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Relationships
    members: Mapped[List["SplitGroupMember"]] = relationship(
        "SplitGroupMember",
        back_populates="group",
        cascade="all, delete-orphan",
    )
    
    shared_expenses: Mapped[List["SharedExpense"]] = relationship(
        "SharedExpense",
        back_populates="group",
        cascade="all, delete-orphan",
    )
    
    settlements: Mapped[List["Settlement"]] = relationship(
        "Settlement",
        back_populates="group",
        cascade="all, delete-orphan",
    )


class SplitGroupMember(Base, UUIDMixin, TimestampMixin):
    """Split group member model for tracking group participants.
    
    Validates: Requirements 13.1
    
    Members can be either registered users (user_id set) or external contacts
    (name, email, phone set without user_id).
    
    Attributes:
        id: Unique identifier for the member
        group_id: Foreign key to the split group
        user_id: Optional foreign key to a registered user
        name: Member's display name
        email: Optional member email
        phone: Optional member phone number
        created_at: Timestamp when member was added
        updated_at: Timestamp when member was last updated
    """
    
    __tablename__ = "split_group_members"
    
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("split_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    
    phone: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    
    # Relationships
    group: Mapped["SplitGroup"] = relationship(
        "SplitGroup",
        back_populates="members",
    )
    
    expense_splits: Mapped[List["ExpenseSplit"]] = relationship(
        "ExpenseSplit",
        back_populates="member",
        cascade="all, delete-orphan",
    )
    
    paid_expenses: Mapped[List["SharedExpense"]] = relationship(
        "SharedExpense",
        back_populates="paid_by_member",
        foreign_keys="SharedExpense.paid_by",
    )
    
    settlements_from: Mapped[List["Settlement"]] = relationship(
        "Settlement",
        back_populates="from_member_rel",
        foreign_keys="Settlement.from_member",
    )
    
    settlements_to: Mapped[List["Settlement"]] = relationship(
        "Settlement",
        back_populates="to_member_rel",
        foreign_keys="Settlement.to_member",
    )


class SharedExpense(Base, UUIDMixin, TimestampMixin):
    """Shared expense model for tracking expenses within a split group.
    
    Validates: Requirements 13.2, 13.3
    
    Attributes:
        id: Unique identifier for the shared expense
        group_id: Foreign key to the split group
        paid_by: Foreign key to the member who paid
        amount: Total expense amount
        description: Description of the expense
        expense_date: Date when the expense occurred
        split_type: Type of split (equal, percentage, exact)
        created_at: Timestamp when expense was created
        updated_at: Timestamp when expense was last updated
    """
    
    __tablename__ = "shared_expenses"
    
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("split_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    paid_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("split_group_members.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    
    amount: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    expense_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    
    split_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=SplitType.EQUAL.value,
    )
    
    # Relationships
    group: Mapped["SplitGroup"] = relationship(
        "SplitGroup",
        back_populates="shared_expenses",
    )
    
    paid_by_member: Mapped["SplitGroupMember"] = relationship(
        "SplitGroupMember",
        back_populates="paid_expenses",
        foreign_keys=[paid_by],
    )
    
    splits: Mapped[List["ExpenseSplit"]] = relationship(
        "ExpenseSplit",
        back_populates="shared_expense",
        cascade="all, delete-orphan",
    )


class ExpenseSplit(Base, UUIDMixin, TimestampMixin):
    """Expense split model for tracking individual member shares.
    
    Validates: Requirements 13.2, 13.3
    
    Attributes:
        id: Unique identifier for the split
        shared_expense_id: Foreign key to the shared expense
        member_id: Foreign key to the group member
        amount: Amount owed by this member
        is_settled: Whether this split has been settled
        created_at: Timestamp when split was created
        updated_at: Timestamp when split was last updated
    """
    
    __tablename__ = "expense_splits"
    
    shared_expense_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shared_expenses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("split_group_members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    amount: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    
    is_settled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    
    # Relationships
    shared_expense: Mapped["SharedExpense"] = relationship(
        "SharedExpense",
        back_populates="splits",
    )
    
    member: Mapped["SplitGroupMember"] = relationship(
        "SplitGroupMember",
        back_populates="expense_splits",
    )


class Settlement(Base, UUIDMixin, TimestampMixin):
    """Settlement model for recording payments between members.
    
    Validates: Requirements 13.5
    
    Attributes:
        id: Unique identifier for the settlement
        group_id: Foreign key to the split group
        from_member: Foreign key to the member who paid
        to_member: Foreign key to the member who received
        amount: Settlement amount
        settlement_date: Date when settlement occurred
        created_at: Timestamp when settlement was recorded
        updated_at: Timestamp when settlement was last updated
    """
    
    __tablename__ = "settlements"
    
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("split_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    from_member: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("split_group_members.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    
    to_member: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("split_group_members.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    
    amount: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    
    settlement_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    
    # Relationships
    group: Mapped["SplitGroup"] = relationship(
        "SplitGroup",
        back_populates="settlements",
    )
    
    from_member_rel: Mapped["SplitGroupMember"] = relationship(
        "SplitGroupMember",
        back_populates="settlements_from",
        foreign_keys=[from_member],
    )
    
    to_member_rel: Mapped["SplitGroupMember"] = relationship(
        "SplitGroupMember",
        back_populates="settlements_to",
        foreign_keys=[to_member],
    )
