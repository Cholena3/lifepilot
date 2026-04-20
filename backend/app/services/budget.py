"""Budget service for managing budgets and threshold notifications.

Provides business logic for budget CRUD operations, progress calculation,
and threshold notification triggers.

Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5, 11.6
"""

import logging
import uuid
from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import Budget, BudgetHistory
from app.models.notification import NotificationChannel
from app.repositories.budget import BudgetRepository
from app.repositories.expense import ExpenseCategoryRepository, ExpenseRepository
from app.schemas.budget import (
    BudgetCreate,
    BudgetUpdate,
    BudgetResponse,
    BudgetWithCategoryResponse,
    BudgetProgressResponse,
    BudgetHistoryResponse,
    BudgetSummaryResponse,
    BudgetCategoryResponse,
)
from app.schemas.document import PaginatedResponse
from app.services.notification import NotificationService

logger = logging.getLogger(__name__)


class BudgetService:
    """Service for managing budgets and threshold notifications.
    
    Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5, 11.6
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize the budget service.
        
        Args:
            db: Async database session
        """
        self.db = db
        self.budget_repo = BudgetRepository(db)
        self.expense_repo = ExpenseRepository(db)
        self.category_repo = ExpenseCategoryRepository(db)
        self.notification_service = NotificationService(db)
    
    # ========================================================================
    # Budget CRUD Operations
    # ========================================================================
    
    async def create_budget(
        self,
        user_id: uuid.UUID,
        data: BudgetCreate,
    ) -> BudgetWithCategoryResponse:
        """Create a new budget for a category.
        
        Validates: Requirements 11.1
        
        Args:
            user_id: User's UUID
            data: Budget creation data
            
        Returns:
            Created budget response with category
            
        Raises:
            ValueError: If category not found or budget already exists
        """
        # Verify category exists and is accessible to user
        category = await self.category_repo.get_category_by_id(data.category_id, user_id)
        if category is None:
            raise ValueError(f"Category {data.category_id} not found or not accessible")
        
        # Check if budget already exists for this category
        existing = await self.budget_repo.get_budget_by_category(
            user_id, data.category_id, active_only=True
        )
        if existing is not None:
            raise ValueError(f"Budget already exists for category {category.name}")
        
        budget = await self.budget_repo.create_budget(user_id, data)
        
        logger.info(
            f"Created budget for user {user_id}, category {category.name}: "
            f"{data.amount} {data.period.value}"
        )
        
        return self._to_budget_with_category_response(budget)
    
    async def get_budget(
        self,
        budget_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[BudgetWithCategoryResponse]:
        """Get a budget by ID.
        
        Args:
            budget_id: Budget's UUID
            user_id: User's UUID for ownership verification
            
        Returns:
            Budget response with category if found, None otherwise
        """
        budget = await self.budget_repo.get_budget_by_id(budget_id, user_id)
        if budget is None:
            return None
        return self._to_budget_with_category_response(budget)
    
    async def get_budgets(
        self,
        user_id: uuid.UUID,
        active_only: bool = True,
    ) -> List[BudgetWithCategoryResponse]:
        """Get all budgets for a user.
        
        Args:
            user_id: User's UUID
            active_only: Only return active budgets
            
        Returns:
            List of budget responses with categories
        """
        budgets = await self.budget_repo.get_budgets_for_user(user_id, active_only)
        return [self._to_budget_with_category_response(b) for b in budgets]
    
    async def update_budget(
        self,
        budget_id: uuid.UUID,
        user_id: uuid.UUID,
        data: BudgetUpdate,
    ) -> Optional[BudgetWithCategoryResponse]:
        """Update a budget.
        
        Args:
            budget_id: Budget's UUID
            user_id: User's UUID for ownership verification
            data: Budget update data
            
        Returns:
            Updated budget response if found, None otherwise
        """
        budget = await self.budget_repo.get_budget_by_id(budget_id, user_id)
        if budget is None:
            return None
        
        updated = await self.budget_repo.update_budget(budget, data)
        logger.info(f"Updated budget {budget_id} for user {user_id}")
        return self._to_budget_with_category_response(updated)
    
    async def delete_budget(
        self,
        budget_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Delete a budget.
        
        Args:
            budget_id: Budget's UUID
            user_id: User's UUID for ownership verification
            
        Returns:
            True if deleted, False if not found
        """
        budget = await self.budget_repo.get_budget_by_id(budget_id, user_id)
        if budget is None:
            return False
        
        await self.budget_repo.delete_budget(budget)
        logger.info(f"Deleted budget {budget_id} for user {user_id}")
        return True
    
    # ========================================================================
    # Budget Progress Operations
    # ========================================================================
    
    async def get_budget_progress(
        self,
        budget_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[BudgetProgressResponse]:
        """Get budget progress with spent amount and status.
        
        Validates: Requirements 11.5
        
        Args:
            budget_id: Budget's UUID
            user_id: User's UUID for ownership verification
            
        Returns:
            Budget progress response if found, None otherwise
        """
        budget = await self.budget_repo.get_budget_by_id(budget_id, user_id)
        if budget is None:
            return None
        
        spent = await self._calculate_spent_amount(budget)
        return BudgetProgressResponse.from_budget_and_spent(budget, spent)
    
    async def get_all_budget_progress(
        self,
        user_id: uuid.UUID,
    ) -> List[BudgetProgressResponse]:
        """Get progress for all active budgets.
        
        Validates: Requirements 11.5
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of budget progress responses
        """
        budgets = await self.budget_repo.get_budgets_for_user(user_id, active_only=True)
        
        progress_list = []
        for budget in budgets:
            spent = await self._calculate_spent_amount(budget)
            progress_list.append(
                BudgetProgressResponse.from_budget_and_spent(budget, spent)
            )
        
        return progress_list
    
    async def get_budget_summary(
        self,
        user_id: uuid.UUID,
    ) -> BudgetSummaryResponse:
        """Get overall budget summary with all budgets.
        
        Validates: Requirements 11.5
        
        Args:
            user_id: User's UUID
            
        Returns:
            Budget summary response
        """
        progress_list = await self.get_all_budget_progress(user_id)
        
        total_budget = sum(p.budget_amount for p in progress_list)
        total_spent = sum(p.spent_amount for p in progress_list)
        total_remaining = total_budget - total_spent
        overall_percentage = (
            float(total_spent / total_budget * 100) if total_budget > 0 else 0.0
        )
        
        # Get period dates from first budget or use current period
        if progress_list:
            period_start = min(p.start_date for p in progress_list)
            period_end = max(p.end_date for p in progress_list)
        else:
            today = date.today()
            period_start = today.replace(day=1)
            if today.month == 12:
                period_end = date(today.year + 1, 1, 1)
            else:
                period_end = date(today.year, today.month + 1, 1)
        
        return BudgetSummaryResponse(
            total_budget=total_budget,
            total_spent=total_spent,
            total_remaining=total_remaining,
            overall_percentage=round(overall_percentage, 2),
            budgets=progress_list,
            period_start=period_start,
            period_end=period_end,
        )
    
    # ========================================================================
    # Threshold Notification Operations
    # ========================================================================
    
    async def check_and_send_threshold_notifications(
        self,
        user_id: uuid.UUID,
        category_id: uuid.UUID,
    ) -> List[int]:
        """Check budget thresholds and send notifications if needed.
        
        Validates: Requirements 11.2, 11.3, 11.4
        
        Args:
            user_id: User's UUID
            category_id: Category's UUID
            
        Returns:
            List of thresholds that triggered notifications
        """
        budget = await self.budget_repo.get_budget_by_category(
            user_id, category_id, active_only=True
        )
        if budget is None:
            return []
        
        spent = await self._calculate_spent_amount(budget)
        percentage = float(spent / Decimal(str(budget.amount)) * 100) if budget.amount > 0 else 0.0
        
        triggered_thresholds = []
        
        # Check 100% threshold (exceeded)
        if percentage >= 100 and not budget.threshold_100_notified:
            await self._send_threshold_notification(
                user_id, budget, 100, spent, "exceeded"
            )
            await self.budget_repo.update_threshold_notification(budget.id, 100)
            triggered_thresholds.append(100)
            logger.info(f"Budget exceeded notification sent for budget {budget.id}")
        
        # Check 80% threshold (urgent warning)
        elif percentage >= 80 and not budget.threshold_80_notified:
            await self._send_threshold_notification(
                user_id, budget, 80, spent, "urgent"
            )
            await self.budget_repo.update_threshold_notification(budget.id, 80)
            triggered_thresholds.append(80)
            logger.info(f"Budget 80% warning sent for budget {budget.id}")
        
        # Check 50% threshold (warning)
        elif percentage >= 50 and not budget.threshold_50_notified:
            await self._send_threshold_notification(
                user_id, budget, 50, spent, "warning"
            )
            await self.budget_repo.update_threshold_notification(budget.id, 50)
            triggered_thresholds.append(50)
            logger.info(f"Budget 50% warning sent for budget {budget.id}")
        
        return triggered_thresholds
    
    async def check_all_budgets_thresholds(
        self,
        user_id: uuid.UUID,
    ) -> dict[uuid.UUID, List[int]]:
        """Check thresholds for all active budgets.
        
        Validates: Requirements 11.2, 11.3, 11.4
        
        Args:
            user_id: User's UUID
            
        Returns:
            Dict mapping budget IDs to triggered thresholds
        """
        budgets = await self.budget_repo.get_budgets_for_user(user_id, active_only=True)
        
        results = {}
        for budget in budgets:
            triggered = await self.check_and_send_threshold_notifications(
                user_id, budget.category_id
            )
            if triggered:
                results[budget.id] = triggered
        
        return results
    
    # ========================================================================
    # Budget Archival Operations
    # ========================================================================
    
    async def archive_expired_budgets(self) -> List[BudgetHistoryResponse]:
        """Archive all expired budgets and start new periods.
        
        Validates: Requirements 11.6
        
        Returns:
            List of archived budget history records
        """
        expired_budgets = await self.budget_repo.get_expired_budgets()
        
        archived = []
        for budget in expired_budgets:
            spent = await self._calculate_spent_amount(budget)
            history = await self.budget_repo.archive_budget(budget, spent)
            archived.append(BudgetHistoryResponse.model_validate(history))
            logger.info(
                f"Archived budget {budget.id}: spent {spent} of {budget.amount}"
            )
        
        return archived
    
    async def get_budget_history(
        self,
        user_id: uuid.UUID,
        category_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[BudgetHistoryResponse]:
        """Get budget history for a user.
        
        Validates: Requirements 11.6
        
        Args:
            user_id: User's UUID
            category_id: Optional category filter
            page: Page number (1-indexed)
            page_size: Number of results per page
            
        Returns:
            Paginated response with budget history
        """
        offset = (page - 1) * page_size
        
        history = await self.budget_repo.get_budget_history(
            user_id, category_id, page_size, offset
        )
        total = await self.budget_repo.count_budget_history(user_id, category_id)
        
        items = [BudgetHistoryResponse.model_validate(h) for h in history]
        
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    async def _calculate_spent_amount(self, budget: Budget) -> Decimal:
        """Calculate total spent amount for a budget's current period.
        
        Args:
            budget: Budget model instance
            
        Returns:
            Total spent amount
        """
        return await self.expense_repo.sum_expenses_by_category_and_period(
            user_id=budget.user_id,
            category_id=budget.category_id,
            start_date=budget.start_date,
            end_date=budget.end_date,
        )
    
    async def _send_threshold_notification(
        self,
        user_id: uuid.UUID,
        budget: Budget,
        threshold: int,
        spent: Decimal,
        severity: str,
    ) -> None:
        """Send a budget threshold notification.
        
        Validates: Requirements 11.2, 11.3, 11.4
        
        Args:
            user_id: User's UUID
            budget: Budget model instance
            threshold: Threshold percentage
            spent: Amount spent
            severity: Notification severity (warning, urgent, exceeded)
        """
        category_name = budget.category.name
        budget_amount = budget.amount
        
        if severity == "exceeded":
            title = f"Budget Exceeded: {category_name}"
            body = (
                f"You have exceeded your {category_name} budget! "
                f"Spent: ${spent:.2f} of ${budget_amount:.2f} budget."
            )
        elif severity == "urgent":
            title = f"Budget Alert: {category_name} at {threshold}%"
            body = (
                f"Urgent: You've used {threshold}% of your {category_name} budget. "
                f"Spent: ${spent:.2f} of ${budget_amount:.2f}."
            )
        else:  # warning
            title = f"Budget Warning: {category_name} at {threshold}%"
            body = (
                f"You've used {threshold}% of your {category_name} budget. "
                f"Spent: ${spent:.2f} of ${budget_amount:.2f}."
            )
        
        # Send notification via push channel
        await self.notification_service.send_notification(
            user_id=user_id,
            title=title,
            body=body,
            channel=NotificationChannel.PUSH,
        )
    
    def _to_budget_with_category_response(
        self,
        budget: Budget,
    ) -> BudgetWithCategoryResponse:
        """Convert Budget model to BudgetWithCategoryResponse.
        
        Args:
            budget: Budget model instance
            
        Returns:
            BudgetWithCategoryResponse
        """
        return BudgetWithCategoryResponse(
            id=budget.id,
            user_id=budget.user_id,
            category_id=budget.category_id,
            amount=budget.amount,
            period=budget.period,
            start_date=budget.start_date,
            end_date=budget.end_date,
            is_active=budget.is_active,
            created_at=budget.created_at,
            updated_at=budget.updated_at,
            category=BudgetCategoryResponse(
                id=budget.category.id,
                name=budget.category.name,
                icon=budget.category.icon,
                color=budget.category.color,
            ),
        )


async def recalculate_budget_on_expense_change(
    db: AsyncSession,
    user_id: uuid.UUID,
    category_id: uuid.UUID,
) -> Optional[List[int]]:
    """Recalculate budget and check thresholds after expense change.
    
    Validates: Requirements 10.5, 10.6, 11.2, 11.3, 11.4
    
    This function should be called after creating, updating, or deleting
    an expense to check if any budget thresholds have been crossed.
    
    Args:
        db: Async database session
        user_id: User's UUID
        category_id: Category's UUID of the changed expense
        
    Returns:
        List of triggered thresholds, or None if no budget exists
    """
    service = BudgetService(db)
    return await service.check_and_send_threshold_notifications(user_id, category_id)
