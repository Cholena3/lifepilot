"""Split repository for database operations.

Validates: Requirements 13.1, 13.2, 13.3, 13.5, 13.7
"""

from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.split import (
    SplitGroup,
    SplitGroupMember,
    SharedExpense,
    ExpenseSplit,
    Settlement,
)
from app.schemas.split import (
    SplitGroupCreate,
    SplitGroupUpdate,
    SplitGroupMemberCreate,
    SharedExpenseCreate,
    SettlementCreate,
)


class SplitGroupRepository:
    """Repository for SplitGroup database operations.
    
    Validates: Requirements 13.1
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session."""
        self.db = db
    
    async def create_group(
        self,
        user_id: UUID,
        data: SplitGroupCreate,
    ) -> SplitGroup:
        """Create a new split group.
        
        Args:
            user_id: User's UUID (creator)
            data: Group creation data
            
        Returns:
            Created SplitGroup model instance
        """
        group = SplitGroup(
            created_by=user_id,
            name=data.name,
            description=data.description,
        )
        self.db.add(group)
        await self.db.flush()
        await self.db.refresh(group)
        return group
    
    async def get_group_by_id(
        self,
        group_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> Optional[SplitGroup]:
        """Get a split group by ID.
        
        Args:
            group_id: Group's UUID
            user_id: Optional user ID to verify membership
            
        Returns:
            SplitGroup if found, None otherwise
        """
        stmt = (
            select(SplitGroup)
            .options(
                selectinload(SplitGroup.members),
                selectinload(SplitGroup.shared_expenses).selectinload(SharedExpense.splits),
                selectinload(SplitGroup.settlements),
            )
            .where(SplitGroup.id == group_id)
        )
        
        result = await self.db.execute(stmt)
        group = result.scalar_one_or_none()
        
        if group is None:
            return None
        
        # If user_id provided, verify user is creator or member
        if user_id is not None:
            if group.created_by != user_id:
                # Check if user is a member
                is_member = any(m.user_id == user_id for m in group.members)
                if not is_member:
                    return None
        
        return group
    
    async def get_groups_for_user(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[SplitGroup]:
        """Get all split groups for a user (created by or member of).
        
        Args:
            user_id: User's UUID
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of SplitGroup model instances
        """
        # Get groups where user is creator or member
        member_subquery = (
            select(SplitGroupMember.group_id)
            .where(SplitGroupMember.user_id == user_id)
        )
        
        stmt = (
            select(SplitGroup)
            .options(selectinload(SplitGroup.members))
            .where(
                or_(
                    SplitGroup.created_by == user_id,
                    SplitGroup.id.in_(member_subquery),
                )
            )
            .order_by(SplitGroup.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())
    
    async def count_groups_for_user(self, user_id: UUID) -> int:
        """Count split groups for a user.
        
        Args:
            user_id: User's UUID
            
        Returns:
            Total count of groups
        """
        member_subquery = (
            select(SplitGroupMember.group_id)
            .where(SplitGroupMember.user_id == user_id)
        )
        
        stmt = select(func.count(SplitGroup.id)).where(
            or_(
                SplitGroup.created_by == user_id,
                SplitGroup.id.in_(member_subquery),
            )
        )
        
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def update_group(
        self,
        group: SplitGroup,
        data: SplitGroupUpdate,
    ) -> SplitGroup:
        """Update a split group.
        
        Args:
            group: Existing SplitGroup model instance
            data: Group update data
            
        Returns:
            Updated SplitGroup model instance
        """
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(group, field, value)
        
        await self.db.flush()
        await self.db.refresh(group)
        return group
    
    async def delete_group(self, group: SplitGroup) -> None:
        """Delete a split group.
        
        Args:
            group: SplitGroup model instance to delete
        """
        await self.db.delete(group)
        await self.db.flush()


class SplitGroupMemberRepository:
    """Repository for SplitGroupMember database operations.
    
    Validates: Requirements 13.1
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session."""
        self.db = db
    
    async def add_member(
        self,
        group_id: UUID,
        data: SplitGroupMemberCreate,
    ) -> SplitGroupMember:
        """Add a member to a split group.
        
        Args:
            group_id: Group's UUID
            data: Member creation data
            
        Returns:
            Created SplitGroupMember model instance
        """
        member = SplitGroupMember(
            group_id=group_id,
            user_id=data.user_id,
            name=data.name,
            email=data.email,
            phone=data.phone,
        )
        self.db.add(member)
        await self.db.flush()
        await self.db.refresh(member)
        return member
    
    async def get_member_by_id(
        self,
        member_id: UUID,
        group_id: Optional[UUID] = None,
    ) -> Optional[SplitGroupMember]:
        """Get a member by ID.
        
        Args:
            member_id: Member's UUID
            group_id: Optional group ID to verify membership
            
        Returns:
            SplitGroupMember if found, None otherwise
        """
        stmt = select(SplitGroupMember).where(SplitGroupMember.id == member_id)
        if group_id is not None:
            stmt = stmt.where(SplitGroupMember.group_id == group_id)
        
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_members_for_group(
        self,
        group_id: UUID,
    ) -> List[SplitGroupMember]:
        """Get all members of a split group.
        
        Args:
            group_id: Group's UUID
            
        Returns:
            List of SplitGroupMember model instances
        """
        stmt = (
            select(SplitGroupMember)
            .where(SplitGroupMember.group_id == group_id)
            .order_by(SplitGroupMember.created_at)
        )
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def delete_member(self, member: SplitGroupMember) -> None:
        """Delete a member from a split group.
        
        Args:
            member: SplitGroupMember model instance to delete
        """
        await self.db.delete(member)
        await self.db.flush()
    
    async def member_has_expenses(self, member_id: UUID) -> bool:
        """Check if a member has any associated expenses.
        
        Args:
            member_id: Member's UUID
            
        Returns:
            True if member has expenses, False otherwise
        """
        # Check if member paid for any expenses
        paid_stmt = select(func.count(SharedExpense.id)).where(
            SharedExpense.paid_by == member_id
        )
        paid_result = await self.db.execute(paid_stmt)
        paid_count = paid_result.scalar() or 0
        
        if paid_count > 0:
            return True
        
        # Check if member has any splits
        split_stmt = select(func.count(ExpenseSplit.id)).where(
            ExpenseSplit.member_id == member_id
        )
        split_result = await self.db.execute(split_stmt)
        split_count = split_result.scalar() or 0
        
        return split_count > 0


class SharedExpenseRepository:
    """Repository for SharedExpense database operations.
    
    Validates: Requirements 13.2, 13.3
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session."""
        self.db = db
    
    async def create_expense(
        self,
        group_id: UUID,
        data: SharedExpenseCreate,
    ) -> SharedExpense:
        """Create a new shared expense.
        
        Args:
            group_id: Group's UUID
            data: Expense creation data
            
        Returns:
            Created SharedExpense model instance
        """
        expense = SharedExpense(
            group_id=group_id,
            paid_by=data.paid_by,
            amount=float(data.amount),
            description=data.description,
            expense_date=data.expense_date,
            split_type=data.split_type.value,
        )
        self.db.add(expense)
        await self.db.flush()
        await self.db.refresh(expense)
        return expense
    
    async def get_expense_by_id(
        self,
        expense_id: UUID,
        group_id: Optional[UUID] = None,
    ) -> Optional[SharedExpense]:
        """Get a shared expense by ID.
        
        Args:
            expense_id: Expense's UUID
            group_id: Optional group ID to verify ownership
            
        Returns:
            SharedExpense if found, None otherwise
        """
        stmt = (
            select(SharedExpense)
            .options(
                selectinload(SharedExpense.paid_by_member),
                selectinload(SharedExpense.splits).selectinload(ExpenseSplit.member),
            )
            .where(SharedExpense.id == expense_id)
        )
        if group_id is not None:
            stmt = stmt.where(SharedExpense.group_id == group_id)
        
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_expenses_for_group(
        self,
        group_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[SharedExpense]:
        """Get all shared expenses for a group.
        
        Args:
            group_id: Group's UUID
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of SharedExpense model instances
        """
        stmt = (
            select(SharedExpense)
            .options(
                selectinload(SharedExpense.paid_by_member),
                selectinload(SharedExpense.splits).selectinload(ExpenseSplit.member),
            )
            .where(SharedExpense.group_id == group_id)
            .order_by(SharedExpense.expense_date.desc(), SharedExpense.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def count_expenses_for_group(self, group_id: UUID) -> int:
        """Count shared expenses for a group.
        
        Args:
            group_id: Group's UUID
            
        Returns:
            Total count of expenses
        """
        stmt = select(func.count(SharedExpense.id)).where(
            SharedExpense.group_id == group_id
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def delete_expense(self, expense: SharedExpense) -> None:
        """Delete a shared expense.
        
        Args:
            expense: SharedExpense model instance to delete
        """
        await self.db.delete(expense)
        await self.db.flush()


class ExpenseSplitRepository:
    """Repository for ExpenseSplit database operations.
    
    Validates: Requirements 13.2, 13.3
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session."""
        self.db = db
    
    async def create_split(
        self,
        shared_expense_id: UUID,
        member_id: UUID,
        amount: Decimal,
    ) -> ExpenseSplit:
        """Create an expense split entry.
        
        Args:
            shared_expense_id: Shared expense's UUID
            member_id: Member's UUID
            amount: Split amount
            
        Returns:
            Created ExpenseSplit model instance
        """
        split = ExpenseSplit(
            shared_expense_id=shared_expense_id,
            member_id=member_id,
            amount=float(amount),
            is_settled=False,
        )
        self.db.add(split)
        await self.db.flush()
        await self.db.refresh(split)
        return split
    
    async def get_splits_for_expense(
        self,
        shared_expense_id: UUID,
    ) -> List[ExpenseSplit]:
        """Get all splits for a shared expense.
        
        Args:
            shared_expense_id: Shared expense's UUID
            
        Returns:
            List of ExpenseSplit model instances
        """
        stmt = (
            select(ExpenseSplit)
            .options(selectinload(ExpenseSplit.member))
            .where(ExpenseSplit.shared_expense_id == shared_expense_id)
        )
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_splits_for_member(
        self,
        member_id: UUID,
        group_id: Optional[UUID] = None,
    ) -> List[ExpenseSplit]:
        """Get all splits for a member.
        
        Args:
            member_id: Member's UUID
            group_id: Optional group ID to filter
            
        Returns:
            List of ExpenseSplit model instances
        """
        stmt = (
            select(ExpenseSplit)
            .options(selectinload(ExpenseSplit.shared_expense))
            .where(ExpenseSplit.member_id == member_id)
        )
        
        if group_id is not None:
            stmt = stmt.join(SharedExpense).where(SharedExpense.group_id == group_id)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


class SettlementRepository:
    """Repository for Settlement database operations.
    
    Validates: Requirements 13.5
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session."""
        self.db = db
    
    async def create_settlement(
        self,
        group_id: UUID,
        data: SettlementCreate,
    ) -> Settlement:
        """Create a settlement record.
        
        Args:
            group_id: Group's UUID
            data: Settlement creation data
            
        Returns:
            Created Settlement model instance
        """
        settlement = Settlement(
            group_id=group_id,
            from_member=data.from_member,
            to_member=data.to_member,
            amount=float(data.amount),
            settlement_date=data.settlement_date,
        )
        self.db.add(settlement)
        await self.db.flush()
        await self.db.refresh(settlement)
        return settlement
    
    async def get_settlement_by_id(
        self,
        settlement_id: UUID,
        group_id: Optional[UUID] = None,
    ) -> Optional[Settlement]:
        """Get a settlement by ID.
        
        Args:
            settlement_id: Settlement's UUID
            group_id: Optional group ID to verify ownership
            
        Returns:
            Settlement if found, None otherwise
        """
        stmt = (
            select(Settlement)
            .options(
                selectinload(Settlement.from_member_rel),
                selectinload(Settlement.to_member_rel),
            )
            .where(Settlement.id == settlement_id)
        )
        if group_id is not None:
            stmt = stmt.where(Settlement.group_id == group_id)
        
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_settlements_for_group(
        self,
        group_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Settlement]:
        """Get all settlements for a group.
        
        Args:
            group_id: Group's UUID
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of Settlement model instances
        """
        stmt = (
            select(Settlement)
            .options(
                selectinload(Settlement.from_member_rel),
                selectinload(Settlement.to_member_rel),
            )
            .where(Settlement.group_id == group_id)
            .order_by(Settlement.settlement_date.desc(), Settlement.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def sum_settlements_for_group(self, group_id: UUID) -> Decimal:
        """Sum all settlements for a group.
        
        Args:
            group_id: Group's UUID
            
        Returns:
            Total sum of settlements
        """
        stmt = select(func.coalesce(func.sum(Settlement.amount), 0)).where(
            Settlement.group_id == group_id
        )
        result = await self.db.execute(stmt)
        return Decimal(str(result.scalar() or 0))
