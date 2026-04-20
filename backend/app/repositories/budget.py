"""Budget repository for database operations.

Validates: Requirements 11.1, 11.5, 11.6
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.budget import Budget, BudgetHistory, BudgetPeriod
from app.models.expense import Expense, ExpenseCategory
from app.schemas.budget import BudgetCreate, BudgetUpdate


class BudgetRepository:
    """Repository for Budget database operations.
    
    Validates: Requirements 11.1, 11.5, 11.6
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session."""
        self.db = db
    
    def _calculate_period_dates(
        self,
        period: str,
        reference_date: Optional[date] = None,
    ) -> tuple[date, date]:
        """Calculate start and end dates for a budget period.
        
        Args:
            period: Budget period (weekly/monthly)
            reference_date: Reference date (defaults to today)
            
        Returns:
            Tuple of (start_date, end_date)
        """
        if reference_date is None:
            reference_date = date.today()
        
        if period == BudgetPeriod.WEEKLY.value:
            # Start from Monday of current week
            start_date = reference_date - timedelta(days=reference_date.weekday())
            end_date = start_date + timedelta(days=6)
        else:  # monthly
            # Start from first day of current month
            start_date = reference_date.replace(day=1)
            # End on last day of current month
            if reference_date.month == 12:
                end_date = date(reference_date.year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(reference_date.year, reference_date.month + 1, 1) - timedelta(days=1)
        
        return start_date, end_date
    
    async def create_budget(
        self,
        user_id: UUID,
        data: BudgetCreate,
    ) -> Budget:
        """Create a new budget.
        
        Validates: Requirements 11.1
        
        Args:
            user_id: User's UUID
            data: Budget creation data
            
        Returns:
            Created Budget model instance
        """
        start_date, end_date = self._calculate_period_dates(data.period.value)
        
        budget = Budget(
            user_id=user_id,
            category_id=data.category_id,
            amount=data.amount,
            period=data.period.value,
            start_date=start_date,
            end_date=end_date,
            is_active=True,
            threshold_50_notified=False,
            threshold_80_notified=False,
            threshold_100_notified=False,
        )
        self.db.add(budget)
        await self.db.flush()
        await self.db.refresh(budget)
        return budget
    
    async def get_budget_by_id(
        self,
        budget_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> Optional[Budget]:
        """Get a budget by ID.
        
        Args:
            budget_id: Budget's UUID
            user_id: Optional user ID to verify ownership
            
        Returns:
            Budget if found, None otherwise
        """
        stmt = (
            select(Budget)
            .options(selectinload(Budget.category))
            .where(Budget.id == budget_id)
        )
        if user_id is not None:
            stmt = stmt.where(Budget.user_id == user_id)
        
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_budget_by_category(
        self,
        user_id: UUID,
        category_id: UUID,
        active_only: bool = True,
    ) -> Optional[Budget]:
        """Get a budget by category for a user.
        
        Args:
            user_id: User's UUID
            category_id: Category's UUID
            active_only: Only return active budgets
            
        Returns:
            Budget if found, None otherwise
        """
        stmt = (
            select(Budget)
            .options(selectinload(Budget.category))
            .where(
                and_(
                    Budget.user_id == user_id,
                    Budget.category_id == category_id,
                )
            )
        )
        if active_only:
            stmt = stmt.where(Budget.is_active == True)
        
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_budgets_for_user(
        self,
        user_id: UUID,
        active_only: bool = True,
    ) -> List[Budget]:
        """Get all budgets for a user.
        
        Args:
            user_id: User's UUID
            active_only: Only return active budgets
            
        Returns:
            List of Budget model instances
        """
        stmt = (
            select(Budget)
            .options(selectinload(Budget.category))
            .where(Budget.user_id == user_id)
        )
        if active_only:
            stmt = stmt.where(Budget.is_active == True)
        
        stmt = stmt.order_by(Budget.created_at.desc())
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def update_budget(
        self,
        budget: Budget,
        data: BudgetUpdate,
    ) -> Budget:
        """Update a budget.
        
        Args:
            budget: Existing Budget model instance
            data: Budget update data
            
        Returns:
            Updated Budget model instance
        """
        update_data = data.model_dump(exclude_unset=True)
        
        # If period is changing, recalculate dates
        if "period" in update_data:
            start_date, end_date = self._calculate_period_dates(update_data["period"])
            budget.start_date = start_date
            budget.end_date = end_date
            budget.period = update_data["period"]
            # Reset threshold notifications for new period
            budget.threshold_50_notified = False
            budget.threshold_80_notified = False
            budget.threshold_100_notified = False
            del update_data["period"]
        
        for field, value in update_data.items():
            setattr(budget, field, value)
        
        await self.db.flush()
        await self.db.refresh(budget)
        return budget
    
    async def delete_budget(self, budget: Budget) -> None:
        """Delete a budget.
        
        Args:
            budget: Budget model instance to delete
        """
        await self.db.delete(budget)
        await self.db.flush()
    
    async def update_threshold_notification(
        self,
        budget_id: UUID,
        threshold: int,
    ) -> None:
        """Mark a threshold notification as sent.
        
        Args:
            budget_id: Budget's UUID
            threshold: Threshold percentage (50, 80, or 100)
        """
        field_map = {
            50: "threshold_50_notified",
            80: "threshold_80_notified",
            100: "threshold_100_notified",
        }
        
        if threshold not in field_map:
            raise ValueError(f"Invalid threshold: {threshold}")
        
        stmt = (
            update(Budget)
            .where(Budget.id == budget_id)
            .values({field_map[threshold]: True})
        )
        await self.db.execute(stmt)
        await self.db.flush()
    
    async def reset_threshold_notifications(self, budget_id: UUID) -> None:
        """Reset all threshold notifications for a budget.
        
        Args:
            budget_id: Budget's UUID
        """
        stmt = (
            update(Budget)
            .where(Budget.id == budget_id)
            .values(
                threshold_50_notified=False,
                threshold_80_notified=False,
                threshold_100_notified=False,
            )
        )
        await self.db.execute(stmt)
        await self.db.flush()
    
    async def get_expired_budgets(self) -> List[Budget]:
        """Get all active budgets that have expired (end_date < today).
        
        Validates: Requirements 11.6
        
        Returns:
            List of expired Budget model instances
        """
        today = date.today()
        stmt = (
            select(Budget)
            .options(selectinload(Budget.category))
            .where(
                and_(
                    Budget.is_active == True,
                    Budget.end_date < today,
                )
            )
        )
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def archive_budget(
        self,
        budget: Budget,
        spent_amount: Decimal,
    ) -> BudgetHistory:
        """Archive a budget and create history record.
        
        Validates: Requirements 11.6
        
        Args:
            budget: Budget to archive
            spent_amount: Total spent during the period
            
        Returns:
            Created BudgetHistory model instance
        """
        # Create history record
        history = BudgetHistory(
            user_id=budget.user_id,
            category_id=budget.category_id,
            category_name=budget.category.name,
            budget_amount=budget.amount,
            spent_amount=spent_amount,
            period=budget.period,
            start_date=budget.start_date,
            end_date=budget.end_date,
        )
        self.db.add(history)
        
        # Start new period for the budget
        new_start, new_end = self._calculate_period_dates(budget.period)
        budget.start_date = new_start
        budget.end_date = new_end
        budget.threshold_50_notified = False
        budget.threshold_80_notified = False
        budget.threshold_100_notified = False
        
        await self.db.flush()
        await self.db.refresh(history)
        return history
    
    async def get_budget_history(
        self,
        user_id: UUID,
        category_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[BudgetHistory]:
        """Get budget history for a user.
        
        Validates: Requirements 11.6
        
        Args:
            user_id: User's UUID
            category_id: Optional category filter
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of BudgetHistory model instances
        """
        stmt = (
            select(BudgetHistory)
            .where(BudgetHistory.user_id == user_id)
        )
        
        if category_id is not None:
            stmt = stmt.where(BudgetHistory.category_id == category_id)
        
        stmt = stmt.order_by(BudgetHistory.archived_at.desc())
        stmt = stmt.limit(limit).offset(offset)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def count_budget_history(
        self,
        user_id: UUID,
        category_id: Optional[UUID] = None,
    ) -> int:
        """Count budget history records for a user.
        
        Args:
            user_id: User's UUID
            category_id: Optional category filter
            
        Returns:
            Total count of history records
        """
        stmt = select(func.count(BudgetHistory.id)).where(
            BudgetHistory.user_id == user_id
        )
        
        if category_id is not None:
            stmt = stmt.where(BudgetHistory.category_id == category_id)
        
        result = await self.db.execute(stmt)
        return result.scalar() or 0
