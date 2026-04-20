"""Expense repository for database operations.

Validates: Requirements 10.1, 10.4, 10.5, 10.6
"""

from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.expense import Expense, ExpenseCategory
from app.schemas.expense import (
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseCategoryCreate,
    ExpenseCategoryUpdate,
)


class ExpenseCategoryRepository:
    """Repository for ExpenseCategory database operations.
    
    Validates: Requirements 10.4
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session."""
        self.db = db
    
    async def create_category(
        self,
        user_id: UUID,
        data: ExpenseCategoryCreate,
    ) -> ExpenseCategory:
        """Create a new expense category for a user.
        
        Args:
            user_id: User's UUID
            data: Category creation data
            
        Returns:
            Created ExpenseCategory model instance
        """
        category = ExpenseCategory(
            user_id=user_id,
            name=data.name,
            icon=data.icon,
            color=data.color,
            is_default=False,
        )
        self.db.add(category)
        await self.db.flush()
        await self.db.refresh(category)
        return category
    
    async def get_category_by_id(
        self,
        category_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> Optional[ExpenseCategory]:
        """Get a category by ID.
        
        Args:
            category_id: Category's UUID
            user_id: Optional user ID to verify ownership
            
        Returns:
            ExpenseCategory if found, None otherwise
        """
        stmt = select(ExpenseCategory).where(ExpenseCategory.id == category_id)
        
        # If user_id provided, ensure category belongs to user or is a default
        if user_id is not None:
            stmt = stmt.where(
                or_(
                    ExpenseCategory.user_id == user_id,
                    ExpenseCategory.is_default == True,
                )
            )
        
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_categories_for_user(
        self,
        user_id: UUID,
    ) -> List[ExpenseCategory]:
        """Get all categories available to a user (user's own + defaults).
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of ExpenseCategory model instances
        """
        stmt = select(ExpenseCategory).where(
            or_(
                ExpenseCategory.user_id == user_id,
                ExpenseCategory.is_default == True,
            )
        ).order_by(ExpenseCategory.is_default.desc(), ExpenseCategory.name)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def update_category(
        self,
        category: ExpenseCategory,
        data: ExpenseCategoryUpdate,
    ) -> ExpenseCategory:
        """Update an expense category.
        
        Args:
            category: Existing ExpenseCategory model instance
            data: Category update data
            
        Returns:
            Updated ExpenseCategory model instance
        """
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(category, field, value)
        
        await self.db.flush()
        await self.db.refresh(category)
        return category
    
    async def delete_category(self, category: ExpenseCategory) -> None:
        """Delete an expense category.
        
        Args:
            category: ExpenseCategory model instance to delete
        """
        await self.db.delete(category)
        await self.db.flush()
    
    async def category_has_expenses(self, category_id: UUID) -> bool:
        """Check if a category has any associated expenses.
        
        Args:
            category_id: Category's UUID
            
        Returns:
            True if category has expenses, False otherwise
        """
        stmt = select(func.count(Expense.id)).where(Expense.category_id == category_id)
        result = await self.db.execute(stmt)
        count = result.scalar() or 0
        return count > 0


class ExpenseRepository:
    """Repository for Expense database operations.
    
    Validates: Requirements 10.1, 10.5, 10.6
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session."""
        self.db = db
    
    async def create_expense(
        self,
        user_id: UUID,
        data: ExpenseCreate,
        receipt_url: Optional[str] = None,
        ocr_data: Optional[dict] = None,
    ) -> Expense:
        """Create a new expense.
        
        Validates: Requirements 10.1
        
        Args:
            user_id: User's UUID
            data: Expense creation data
            receipt_url: Optional URL to receipt image
            ocr_data: Optional OCR extracted data
            
        Returns:
            Created Expense model instance
        """
        expense = Expense(
            user_id=user_id,
            category_id=data.category_id,
            amount=float(data.amount),
            description=data.description,
            expense_date=data.expense_date,
            receipt_url=receipt_url,
            ocr_data=ocr_data,
        )
        self.db.add(expense)
        await self.db.flush()
        await self.db.refresh(expense)
        return expense
    
    async def get_expense_by_id(
        self,
        expense_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> Optional[Expense]:
        """Get an expense by ID.
        
        Args:
            expense_id: Expense's UUID
            user_id: Optional user ID to verify ownership
            
        Returns:
            Expense if found, None otherwise
        """
        stmt = select(Expense).where(Expense.id == expense_id)
        if user_id is not None:
            stmt = stmt.where(Expense.user_id == user_id)
        
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_expense_with_category(
        self,
        expense_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> Optional[Expense]:
        """Get an expense by ID with category loaded.
        
        Args:
            expense_id: Expense's UUID
            user_id: Optional user ID to verify ownership
            
        Returns:
            Expense with category if found, None otherwise
        """
        stmt = (
            select(Expense)
            .options(selectinload(Expense.category))
            .where(Expense.id == expense_id)
        )
        if user_id is not None:
            stmt = stmt.where(Expense.user_id == user_id)
        
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_expenses_for_user(
        self,
        user_id: UUID,
        category_id: Optional[UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        min_amount: Optional[Decimal] = None,
        max_amount: Optional[Decimal] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Expense]:
        """Get expenses for a user with optional filtering.
        
        Args:
            user_id: User's UUID
            category_id: Optional category filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            min_amount: Optional minimum amount filter
            max_amount: Optional maximum amount filter
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of Expense model instances
        """
        stmt = (
            select(Expense)
            .options(selectinload(Expense.category))
            .where(Expense.user_id == user_id)
        )
        
        # Apply filters
        if category_id is not None:
            stmt = stmt.where(Expense.category_id == category_id)
        if start_date is not None:
            stmt = stmt.where(Expense.expense_date >= start_date)
        if end_date is not None:
            stmt = stmt.where(Expense.expense_date <= end_date)
        if min_amount is not None:
            stmt = stmt.where(Expense.amount >= float(min_amount))
        if max_amount is not None:
            stmt = stmt.where(Expense.amount <= float(max_amount))
        
        # Order by expense_date descending, then created_at descending
        stmt = stmt.order_by(Expense.expense_date.desc(), Expense.created_at.desc())
        stmt = stmt.limit(limit).offset(offset)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def count_expenses_for_user(
        self,
        user_id: UUID,
        category_id: Optional[UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        min_amount: Optional[Decimal] = None,
        max_amount: Optional[Decimal] = None,
    ) -> int:
        """Count expenses for a user with optional filtering.
        
        Args:
            user_id: User's UUID
            category_id: Optional category filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            min_amount: Optional minimum amount filter
            max_amount: Optional maximum amount filter
            
        Returns:
            Total count of matching expenses
        """
        stmt = select(func.count(Expense.id)).where(Expense.user_id == user_id)
        
        # Apply filters
        if category_id is not None:
            stmt = stmt.where(Expense.category_id == category_id)
        if start_date is not None:
            stmt = stmt.where(Expense.expense_date >= start_date)
        if end_date is not None:
            stmt = stmt.where(Expense.expense_date <= end_date)
        if min_amount is not None:
            stmt = stmt.where(Expense.amount >= float(min_amount))
        if max_amount is not None:
            stmt = stmt.where(Expense.amount <= float(max_amount))
        
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def update_expense(
        self,
        expense: Expense,
        data: ExpenseUpdate,
    ) -> Expense:
        """Update an expense.
        
        Validates: Requirements 10.5
        
        Args:
            expense: Existing Expense model instance
            data: Expense update data
            
        Returns:
            Updated Expense model instance
        """
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "amount" and value is not None:
                value = float(value)
            setattr(expense, field, value)
        
        await self.db.flush()
        await self.db.refresh(expense)
        return expense
    
    async def update_expense_receipt(
        self,
        expense: Expense,
        receipt_url: str,
        ocr_data: Optional[dict] = None,
    ) -> Expense:
        """Update expense with receipt information.
        
        Args:
            expense: Existing Expense model instance
            receipt_url: URL to the receipt image
            ocr_data: Optional OCR extracted data
            
        Returns:
            Updated Expense model instance
        """
        expense.receipt_url = receipt_url
        if ocr_data is not None:
            expense.ocr_data = ocr_data
        
        await self.db.flush()
        await self.db.refresh(expense)
        return expense
    
    async def delete_expense(self, expense: Expense) -> None:
        """Delete an expense.
        
        Validates: Requirements 10.6
        
        Args:
            expense: Expense model instance to delete
        """
        await self.db.delete(expense)
        await self.db.flush()
    
    async def get_expenses_by_category_and_period(
        self,
        user_id: UUID,
        category_id: UUID,
        start_date: date,
        end_date: date,
    ) -> List[Expense]:
        """Get expenses for a specific category and date range.
        
        Used for budget calculations.
        
        Args:
            user_id: User's UUID
            category_id: Category's UUID
            start_date: Period start date
            end_date: Period end date
            
        Returns:
            List of Expense model instances
        """
        stmt = (
            select(Expense)
            .where(
                and_(
                    Expense.user_id == user_id,
                    Expense.category_id == category_id,
                    Expense.expense_date >= start_date,
                    Expense.expense_date <= end_date,
                )
            )
            .order_by(Expense.expense_date.desc())
        )
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def sum_expenses_by_category_and_period(
        self,
        user_id: UUID,
        category_id: UUID,
        start_date: date,
        end_date: date,
    ) -> Decimal:
        """Sum expenses for a specific category and date range.
        
        Used for budget calculations.
        
        Args:
            user_id: User's UUID
            category_id: Category's UUID
            start_date: Period start date
            end_date: Period end date
            
        Returns:
            Total sum of expenses
        """
        stmt = select(func.coalesce(func.sum(Expense.amount), 0)).where(
            and_(
                Expense.user_id == user_id,
                Expense.category_id == category_id,
                Expense.expense_date >= start_date,
                Expense.expense_date <= end_date,
            )
        )
        
        result = await self.db.execute(stmt)
        return Decimal(str(result.scalar() or 0))
