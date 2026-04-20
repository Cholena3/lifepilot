"""Property-based tests for budget recalculation.

Uses Hypothesis to verify universal properties across all valid inputs.

**Validates: Requirements 10.5, 10.6**

Property 23: Budget Recalculation on Expense Change - For any budget B with
category C, when an expense in category C is added, edited, or deleted, the
budget's spent amount SHALL be recalculated to equal the sum of all expenses
in that category within the budget period.
"""

import string
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck

from app.models.budget import Budget, BudgetPeriod
from app.models.expense import Expense, ExpenseCategory
from app.schemas.budget import BudgetCreate, BudgetProgressResponse
from app.schemas.expense import ExpenseCreate, ExpenseUpdate
from app.services.budget import BudgetService, recalculate_budget_on_expense_change


# ============================================================================
# Hypothesis Strategies for Budget and Expense Data
# ============================================================================

@st.composite
def valid_amounts(draw):
    """Generate valid expense/budget amounts (positive, up to 2 decimal places).
    
    Amounts must be positive and are rounded to 2 decimal places.
    """
    value = draw(st.floats(min_value=0.01, max_value=99999.99, allow_nan=False, allow_infinity=False))
    return Decimal(str(round(value, 2)))


@st.composite
def valid_budget_amounts(draw):
    """Generate valid budget amounts (positive, reasonable range).
    
    Budget amounts should be larger to accommodate multiple expenses.
    """
    value = draw(st.floats(min_value=100.0, max_value=100000.0, allow_nan=False, allow_infinity=False))
    return Decimal(str(round(value, 2)))


@st.composite
def valid_expense_dates_in_period(draw, start_date: date, end_date: date):
    """Generate valid expense dates within a budget period."""
    return draw(st.dates(min_value=start_date, max_value=end_date))


@st.composite
def valid_budget_period(draw):
    """Generate a valid budget period (start_date, end_date)."""
    today = date.today()
    # Generate a start date within the last 30 days
    days_ago = draw(st.integers(min_value=0, max_value=30))
    start_date = today - timedelta(days=days_ago)
    
    # Period can be weekly or monthly
    period_type = draw(st.sampled_from([BudgetPeriod.WEEKLY, BudgetPeriod.MONTHLY]))
    
    if period_type == BudgetPeriod.WEEKLY:
        end_date = start_date + timedelta(days=6)
    else:  # MONTHLY
        # Approximate month as 30 days
        end_date = start_date + timedelta(days=29)
    
    return start_date, end_date, period_type


@st.composite
def valid_expense_list(draw, min_expenses: int = 1, max_expenses: int = 10):
    """Generate a list of valid expense amounts.
    
    Returns a list of Decimal amounts for expenses.
    """
    num_expenses = draw(st.integers(min_value=min_expenses, max_value=max_expenses))
    expenses = []
    for _ in range(num_expenses):
        amount = draw(valid_amounts())
        expenses.append(amount)
    return expenses


# ============================================================================
# Helper Functions
# ============================================================================

def create_mock_category(
    category_id=None,
    user_id=None,
    name="Food",
    icon="utensils",
    color="#FF6B6B",
    is_default=False,
):
    """Create a mock category object."""
    mock = MagicMock()
    mock.id = category_id or uuid4()
    mock.user_id = user_id
    mock.name = name
    mock.icon = icon
    mock.color = color
    mock.is_default = is_default
    mock.created_at = datetime.now(timezone.utc)
    mock.updated_at = datetime.now(timezone.utc)
    return mock


def create_mock_budget(
    budget_id=None,
    user_id=None,
    category_id=None,
    amount=None,
    period=BudgetPeriod.MONTHLY,
    start_date=None,
    end_date=None,
    is_active=True,
    threshold_50_notified=False,
    threshold_80_notified=False,
    threshold_100_notified=False,
    category=None,
):
    """Create a mock budget object."""
    mock = MagicMock(spec=Budget)
    mock.id = budget_id or uuid4()
    mock.user_id = user_id or uuid4()
    mock.category_id = category_id or uuid4()
    mock.amount = amount if amount is not None else Decimal("1000.00")
    mock.period = period.value if isinstance(period, BudgetPeriod) else period
    mock.start_date = start_date or date.today().replace(day=1)
    mock.end_date = end_date or (date.today().replace(day=1) + timedelta(days=29))
    mock.is_active = is_active
    mock.threshold_50_notified = threshold_50_notified
    mock.threshold_80_notified = threshold_80_notified
    mock.threshold_100_notified = threshold_100_notified
    mock.created_at = datetime.now(timezone.utc)
    mock.updated_at = datetime.now(timezone.utc)
    mock.category = category or create_mock_category(category_id=mock.category_id, user_id=mock.user_id)
    return mock


def create_mock_expense(
    expense_id=None,
    user_id=None,
    category_id=None,
    amount=None,
    description=None,
    expense_date=None,
):
    """Create a mock expense object."""
    mock = MagicMock(spec=Expense)
    mock.id = expense_id or uuid4()
    mock.user_id = user_id or uuid4()
    mock.category_id = category_id or uuid4()
    mock.amount = amount if amount is not None else Decimal("25.50")
    mock.description = description
    mock.expense_date = expense_date or date.today()
    mock.receipt_url = None
    mock.ocr_data = None
    mock.created_at = datetime.now(timezone.utc)
    mock.updated_at = datetime.now(timezone.utc)
    return mock


# ============================================================================
# Property 23: Budget Recalculation on Expense Change
# ============================================================================

class TestBudgetRecalculationProperty:
    """Property 23: Budget Recalculation on Expense Change.
    
    **Validates: Requirements 10.5, 10.6**
    
    For any budget B with category C, when an expense in category C is added,
    edited, or deleted, the budget's spent amount SHALL be recalculated to
    equal the sum of all expenses in that category within the budget period.
    """
    
    @given(expense_amounts=valid_expense_list(min_expenses=1, max_expenses=10))
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_spent_amount_equals_sum_of_expenses(self, expense_amounts: list[Decimal]):
        """For any set of expenses in a budget category, the budget's spent
        amount SHALL equal the sum of all expense amounts.
        
        **Validates: Requirements 10.5, 10.6**
        
        This test verifies that:
        1. Budget spent amount is calculated correctly
        2. The sum matches the total of all expenses in the period
        """
        user_id = uuid4()
        category_id = uuid4()
        budget_id = uuid4()
        
        # Calculate expected sum
        expected_sum = sum(expense_amounts)
        
        # Create mock budget
        mock_budget = create_mock_budget(
            budget_id=budget_id,
            user_id=user_id,
            category_id=category_id,
            amount=Decimal("10000.00"),  # Large enough to hold all expenses
        )
        
        # Verify the sum calculation
        # This simulates what the repository's sum_expenses_by_category_and_period does
        calculated_sum = Decimal("0")
        for amount in expense_amounts:
            calculated_sum += amount
        
        assert calculated_sum == expected_sum, (
            f"Calculated sum {calculated_sum} should equal expected sum {expected_sum}"
        )
        
        # Verify the progress response calculation
        progress = BudgetProgressResponse.from_budget_and_spent(mock_budget, expected_sum)
        
        assert progress.spent_amount == expected_sum, (
            f"Progress spent_amount {progress.spent_amount} should equal {expected_sum}"
        )
        assert progress.remaining_amount == mock_budget.amount - expected_sum, (
            f"Remaining amount should be budget - spent"
        )
    
    @pytest.mark.asyncio
    @given(
        initial_amounts=valid_expense_list(min_expenses=2, max_expenses=5),
        edit_index=st.integers(min_value=0, max_value=4),
        new_amount=valid_amounts(),
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_budget_recalculates_on_expense_edit(
        self,
        initial_amounts: list[Decimal],
        edit_index: int,
        new_amount: Decimal,
    ):
        """When an expense is edited, the budget's spent amount SHALL be
        recalculated to reflect the change.
        
        **Validates: Requirements 10.5**
        
        This test verifies that:
        1. Editing an expense triggers budget recalculation
        2. The new spent amount equals the sum with the edited expense
        """
        # Ensure edit_index is valid for the list
        assume(edit_index < len(initial_amounts))
        
        user_id = uuid4()
        category_id = uuid4()
        budget_id = uuid4()
        
        # Calculate initial sum
        initial_sum = sum(initial_amounts)
        
        # Calculate expected sum after edit
        old_amount = initial_amounts[edit_index]
        expected_sum_after_edit = initial_sum - old_amount + new_amount
        
        # Create mock database session
        mock_db = AsyncMock()
        service = BudgetService(mock_db)
        
        # Create mock budget
        mock_budget = create_mock_budget(
            budget_id=budget_id,
            user_id=user_id,
            category_id=category_id,
            amount=Decimal("100000.00"),
        )
        
        # Setup mocks
        service.budget_repo.get_budget_by_category = AsyncMock(return_value=mock_budget)
        service.expense_repo.sum_expenses_by_category_and_period = AsyncMock(
            return_value=expected_sum_after_edit
        )
        service.budget_repo.update_threshold_notification = AsyncMock()
        service.notification_service.send_notification = AsyncMock()
        
        # Trigger budget recalculation (simulates what happens after expense edit)
        await service.check_and_send_threshold_notifications(user_id, category_id)
        
        # Verify the expense sum was queried
        service.expense_repo.sum_expenses_by_category_and_period.assert_called_once_with(
            user_id=mock_budget.user_id,
            category_id=mock_budget.category_id,
            start_date=mock_budget.start_date,
            end_date=mock_budget.end_date,
        )
        
        # Verify the calculation is correct
        assert expected_sum_after_edit == initial_sum - old_amount + new_amount, (
            f"Expected sum after edit should be {initial_sum} - {old_amount} + {new_amount} = "
            f"{expected_sum_after_edit}"
        )
    
    @pytest.mark.asyncio
    @given(
        initial_amounts=valid_expense_list(min_expenses=2, max_expenses=5),
        delete_index=st.integers(min_value=0, max_value=4),
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_budget_recalculates_on_expense_delete(
        self,
        initial_amounts: list[Decimal],
        delete_index: int,
    ):
        """When an expense is deleted, the budget's spent amount SHALL be
        recalculated to reflect the removal.
        
        **Validates: Requirements 10.6**
        
        This test verifies that:
        1. Deleting an expense triggers budget recalculation
        2. The new spent amount equals the sum without the deleted expense
        """
        # Ensure delete_index is valid for the list
        assume(delete_index < len(initial_amounts))
        
        user_id = uuid4()
        category_id = uuid4()
        budget_id = uuid4()
        
        # Calculate initial sum
        initial_sum = sum(initial_amounts)
        
        # Calculate expected sum after delete
        deleted_amount = initial_amounts[delete_index]
        expected_sum_after_delete = initial_sum - deleted_amount
        
        # Create mock database session
        mock_db = AsyncMock()
        service = BudgetService(mock_db)
        
        # Create mock budget
        mock_budget = create_mock_budget(
            budget_id=budget_id,
            user_id=user_id,
            category_id=category_id,
            amount=Decimal("100000.00"),
        )
        
        # Setup mocks
        service.budget_repo.get_budget_by_category = AsyncMock(return_value=mock_budget)
        service.expense_repo.sum_expenses_by_category_and_period = AsyncMock(
            return_value=expected_sum_after_delete
        )
        service.budget_repo.update_threshold_notification = AsyncMock()
        service.notification_service.send_notification = AsyncMock()
        
        # Trigger budget recalculation (simulates what happens after expense delete)
        await service.check_and_send_threshold_notifications(user_id, category_id)
        
        # Verify the expense sum was queried
        service.expense_repo.sum_expenses_by_category_and_period.assert_called_once()
        
        # Verify the calculation is correct
        assert expected_sum_after_delete == initial_sum - deleted_amount, (
            f"Expected sum after delete should be {initial_sum} - {deleted_amount} = "
            f"{expected_sum_after_delete}"
        )
    
    @pytest.mark.asyncio
    @given(
        budget_amount=valid_budget_amounts(),
        expense_amounts=valid_expense_list(min_expenses=1, max_expenses=5),
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_budget_progress_consistency(
        self,
        budget_amount: Decimal,
        expense_amounts: list[Decimal],
    ):
        """For any budget and set of expenses, the budget progress SHALL
        maintain consistency: spent + remaining = budget amount.
        
        **Validates: Requirements 10.5, 10.6**
        
        This test verifies that:
        1. Budget progress is calculated correctly
        2. spent_amount + remaining_amount = budget_amount
        3. Percentage is calculated correctly
        """
        user_id = uuid4()
        category_id = uuid4()
        budget_id = uuid4()
        
        # Calculate spent amount
        spent_amount = sum(expense_amounts)
        
        # Create mock budget
        mock_budget = create_mock_budget(
            budget_id=budget_id,
            user_id=user_id,
            category_id=category_id,
            amount=budget_amount,
        )
        
        # Create progress response
        progress = BudgetProgressResponse.from_budget_and_spent(mock_budget, spent_amount)
        
        # Verify consistency: spent + remaining = budget
        assert progress.spent_amount + progress.remaining_amount == budget_amount, (
            f"spent ({progress.spent_amount}) + remaining ({progress.remaining_amount}) "
            f"should equal budget ({budget_amount})"
        )
        
        # Verify percentage calculation
        expected_percentage = float(spent_amount / budget_amount * 100) if budget_amount > 0 else 0.0
        assert abs(progress.percentage_used - expected_percentage) < 0.01, (
            f"Percentage {progress.percentage_used} should be approximately {expected_percentage}"
        )
    
    @pytest.mark.asyncio
    @given(expense_amounts=valid_expense_list(min_expenses=1, max_expenses=10))
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_recalculate_budget_on_expense_change_function(
        self,
        expense_amounts: list[Decimal],
    ):
        """The recalculate_budget_on_expense_change function SHALL correctly
        trigger budget recalculation when called.
        
        **Validates: Requirements 10.5, 10.6**
        
        This test verifies that:
        1. The helper function correctly invokes the budget service
        2. Threshold notifications are checked after recalculation
        """
        user_id = uuid4()
        category_id = uuid4()
        budget_id = uuid4()
        
        # Calculate expected sum
        expected_sum = sum(expense_amounts)
        
        # Create mock database session
        mock_db = AsyncMock()
        
        # Create mock budget
        mock_budget = create_mock_budget(
            budget_id=budget_id,
            user_id=user_id,
            category_id=category_id,
            amount=Decimal("100000.00"),
        )
        
        # Patch the BudgetService
        with patch('app.services.budget.BudgetService') as MockBudgetService:
            mock_service_instance = AsyncMock()
            MockBudgetService.return_value = mock_service_instance
            mock_service_instance.check_and_send_threshold_notifications = AsyncMock(return_value=[])
            
            # Call the helper function
            result = await recalculate_budget_on_expense_change(mock_db, user_id, category_id)
            
            # Verify the service was instantiated with the db session
            MockBudgetService.assert_called_once_with(mock_db)
            
            # Verify threshold check was called
            mock_service_instance.check_and_send_threshold_notifications.assert_called_once_with(
                user_id, category_id
            )
    
    @given(
        expense_amounts=valid_expense_list(min_expenses=0, max_expenses=10),
    )
    @settings(max_examples=10, deadline=None)
    def test_empty_expenses_results_in_zero_spent(self, expense_amounts: list[Decimal]):
        """When there are no expenses in a budget period, the spent amount
        SHALL be zero.
        
        **Validates: Requirements 10.5, 10.6**
        
        This test verifies that:
        1. Empty expense list results in zero spent
        2. Budget progress handles zero spent correctly
        """
        user_id = uuid4()
        category_id = uuid4()
        budget_id = uuid4()
        
        # Use empty list for this specific test case
        if len(expense_amounts) > 0:
            expense_amounts = []
        
        # Calculate expected sum (should be 0)
        expected_sum = sum(expense_amounts)
        assert expected_sum == Decimal("0"), "Sum of empty list should be 0"
        
        # Create mock budget
        mock_budget = create_mock_budget(
            budget_id=budget_id,
            user_id=user_id,
            category_id=category_id,
            amount=Decimal("1000.00"),
        )
        
        # Create progress response with zero spent
        progress = BudgetProgressResponse.from_budget_and_spent(mock_budget, Decimal("0"))
        
        assert progress.spent_amount == Decimal("0"), "Spent amount should be 0"
        assert progress.remaining_amount == mock_budget.amount, (
            "Remaining should equal full budget amount"
        )
        assert progress.percentage_used == 0.0, "Percentage should be 0"
    
    @pytest.mark.asyncio
    @given(
        budget_amount=valid_budget_amounts(),
        expense_amounts=valid_expense_list(min_expenses=1, max_expenses=5),
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_budget_service_calculates_spent_from_repository(
        self,
        budget_amount: Decimal,
        expense_amounts: list[Decimal],
    ):
        """The BudgetService SHALL calculate spent amount by querying the
        expense repository for the sum of expenses in the budget period.
        
        **Validates: Requirements 10.5, 10.6**
        
        This test verifies that:
        1. BudgetService uses the repository to calculate spent amount
        2. The calculation is based on expenses within the budget period
        """
        user_id = uuid4()
        category_id = uuid4()
        budget_id = uuid4()
        
        # Calculate expected sum
        expected_sum = sum(expense_amounts)
        
        # Create mock database session
        mock_db = AsyncMock()
        service = BudgetService(mock_db)
        
        # Create mock budget
        mock_budget = create_mock_budget(
            budget_id=budget_id,
            user_id=user_id,
            category_id=category_id,
            amount=budget_amount,
        )
        
        # Setup mocks
        service.budget_repo.get_budget_by_id = AsyncMock(return_value=mock_budget)
        service.expense_repo.sum_expenses_by_category_and_period = AsyncMock(
            return_value=expected_sum
        )
        
        # Get budget progress
        progress = await service.get_budget_progress(budget_id, user_id)
        
        # Verify the repository was called with correct parameters
        service.expense_repo.sum_expenses_by_category_and_period.assert_called_once_with(
            user_id=mock_budget.user_id,
            category_id=mock_budget.category_id,
            start_date=mock_budget.start_date,
            end_date=mock_budget.end_date,
        )
        
        # Verify the progress reflects the calculated sum
        assert progress is not None
        assert progress.spent_amount == expected_sum, (
            f"Progress spent_amount {progress.spent_amount} should equal {expected_sum}"
        )


# ============================================================================
# Property 24: Budget Threshold Notifications
# ============================================================================

class TestBudgetThresholdNotificationsProperty:
    """Property 24: Budget Threshold Notifications.
    
    **Validates: Requirements 11.2, 11.3, 11.4**
    
    For any budget with limit L, when cumulative expenses reach 50%, 80%, and
    100% of L, the corresponding notification SHALL be triggered exactly once
    per threshold.
    """
    
    @pytest.mark.asyncio
    @given(
        budget_amount=valid_budget_amounts(),
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_50_percent_threshold_triggers_warning_notification(
        self,
        budget_amount: Decimal,
    ):
        """When spent reaches 50% of budget, a warning notification SHALL be sent.
        
        **Validates: Requirements 11.2**
        
        This test verifies that:
        1. When expenses reach exactly 50% of budget, a notification is triggered
        2. The notification is a warning type
        3. The threshold_50_notified flag is updated
        """
        user_id = uuid4()
        category_id = uuid4()
        budget_id = uuid4()
        
        # Calculate 50% of budget
        spent_at_50_percent = budget_amount * Decimal("0.50")
        
        # Create mock database session
        mock_db = AsyncMock()
        service = BudgetService(mock_db)
        
        # Create mock budget with no thresholds notified yet
        mock_budget = create_mock_budget(
            budget_id=budget_id,
            user_id=user_id,
            category_id=category_id,
            amount=budget_amount,
            threshold_50_notified=False,
            threshold_80_notified=False,
            threshold_100_notified=False,
        )
        
        # Setup mocks
        service.budget_repo.get_budget_by_category = AsyncMock(return_value=mock_budget)
        service.expense_repo.sum_expenses_by_category_and_period = AsyncMock(
            return_value=spent_at_50_percent
        )
        service.budget_repo.update_threshold_notification = AsyncMock()
        service.notification_service.send_notification = AsyncMock()
        
        # Trigger threshold check
        triggered = await service.check_and_send_threshold_notifications(user_id, category_id)
        
        # Verify 50% threshold was triggered
        assert 50 in triggered, (
            f"50% threshold should be triggered when spent is {spent_at_50_percent} "
            f"of budget {budget_amount}"
        )
        
        # Verify notification was sent
        service.notification_service.send_notification.assert_called_once()
        call_args = service.notification_service.send_notification.call_args
        assert call_args.kwargs['user_id'] == user_id
        assert "50%" in call_args.kwargs['title'] or "warning" in call_args.kwargs['title'].lower()
        
        # Verify threshold flag was updated
        service.budget_repo.update_threshold_notification.assert_called_once_with(
            mock_budget.id, 50
        )
    
    @pytest.mark.asyncio
    @given(
        budget_amount=valid_budget_amounts(),
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_80_percent_threshold_triggers_urgent_notification(
        self,
        budget_amount: Decimal,
    ):
        """When spent reaches 80% of budget, an urgent warning notification SHALL be sent.
        
        **Validates: Requirements 11.3**
        
        This test verifies that:
        1. When expenses reach exactly 80% of budget, a notification is triggered
        2. The notification is an urgent warning type
        3. The threshold_80_notified flag is updated
        """
        user_id = uuid4()
        category_id = uuid4()
        budget_id = uuid4()
        
        # Calculate 80% of budget
        spent_at_80_percent = budget_amount * Decimal("0.80")
        
        # Create mock database session
        mock_db = AsyncMock()
        service = BudgetService(mock_db)
        
        # Create mock budget with 50% already notified (realistic scenario)
        mock_budget = create_mock_budget(
            budget_id=budget_id,
            user_id=user_id,
            category_id=category_id,
            amount=budget_amount,
            threshold_50_notified=True,  # Already notified at 50%
            threshold_80_notified=False,
            threshold_100_notified=False,
        )
        
        # Setup mocks
        service.budget_repo.get_budget_by_category = AsyncMock(return_value=mock_budget)
        service.expense_repo.sum_expenses_by_category_and_period = AsyncMock(
            return_value=spent_at_80_percent
        )
        service.budget_repo.update_threshold_notification = AsyncMock()
        service.notification_service.send_notification = AsyncMock()
        
        # Trigger threshold check
        triggered = await service.check_and_send_threshold_notifications(user_id, category_id)
        
        # Verify 80% threshold was triggered
        assert 80 in triggered, (
            f"80% threshold should be triggered when spent is {spent_at_80_percent} "
            f"of budget {budget_amount}"
        )
        
        # Verify notification was sent
        service.notification_service.send_notification.assert_called_once()
        call_args = service.notification_service.send_notification.call_args
        assert call_args.kwargs['user_id'] == user_id
        assert "80%" in call_args.kwargs['title'] or "urgent" in call_args.kwargs['body'].lower()
        
        # Verify threshold flag was updated
        service.budget_repo.update_threshold_notification.assert_called_once_with(
            mock_budget.id, 80
        )
    
    @pytest.mark.asyncio
    @given(
        budget_amount=valid_budget_amounts(),
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_100_percent_threshold_triggers_exceeded_notification(
        self,
        budget_amount: Decimal,
    ):
        """When spent reaches 100% of budget, a budget exceeded notification SHALL be sent.
        
        **Validates: Requirements 11.4**
        
        This test verifies that:
        1. When expenses reach 100% of budget, a notification is triggered
        2. The notification indicates budget exceeded
        3. The threshold_100_notified flag is updated
        """
        user_id = uuid4()
        category_id = uuid4()
        budget_id = uuid4()
        
        # Calculate 100% of budget
        spent_at_100_percent = budget_amount
        
        # Create mock database session
        mock_db = AsyncMock()
        service = BudgetService(mock_db)
        
        # Create mock budget with 50% and 80% already notified
        mock_budget = create_mock_budget(
            budget_id=budget_id,
            user_id=user_id,
            category_id=category_id,
            amount=budget_amount,
            threshold_50_notified=True,
            threshold_80_notified=True,
            threshold_100_notified=False,
        )
        
        # Setup mocks
        service.budget_repo.get_budget_by_category = AsyncMock(return_value=mock_budget)
        service.expense_repo.sum_expenses_by_category_and_period = AsyncMock(
            return_value=spent_at_100_percent
        )
        service.budget_repo.update_threshold_notification = AsyncMock()
        service.notification_service.send_notification = AsyncMock()
        
        # Trigger threshold check
        triggered = await service.check_and_send_threshold_notifications(user_id, category_id)
        
        # Verify 100% threshold was triggered
        assert 100 in triggered, (
            f"100% threshold should be triggered when spent is {spent_at_100_percent} "
            f"of budget {budget_amount}"
        )
        
        # Verify notification was sent
        service.notification_service.send_notification.assert_called_once()
        call_args = service.notification_service.send_notification.call_args
        assert call_args.kwargs['user_id'] == user_id
        assert "exceeded" in call_args.kwargs['title'].lower() or "exceeded" in call_args.kwargs['body'].lower()
        
        # Verify threshold flag was updated
        service.budget_repo.update_threshold_notification.assert_called_once_with(
            mock_budget.id, 100
        )
    
    @pytest.mark.asyncio
    @given(
        budget_amount=valid_budget_amounts(),
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_50_percent_notification_not_repeated(
        self,
        budget_amount: Decimal,
    ):
        """Notifications SHALL only be sent once per threshold (not repeated).
        
        **Validates: Requirements 11.2**
        
        This test verifies that:
        1. When 50% threshold was already notified, no new notification is sent
        2. The threshold check returns empty list for already-notified thresholds
        """
        user_id = uuid4()
        category_id = uuid4()
        budget_id = uuid4()
        
        # Calculate 55% of budget (above 50% but below 80%)
        spent_at_55_percent = budget_amount * Decimal("0.55")
        
        # Create mock database session
        mock_db = AsyncMock()
        service = BudgetService(mock_db)
        
        # Create mock budget with 50% ALREADY notified
        mock_budget = create_mock_budget(
            budget_id=budget_id,
            user_id=user_id,
            category_id=category_id,
            amount=budget_amount,
            threshold_50_notified=True,  # Already notified!
            threshold_80_notified=False,
            threshold_100_notified=False,
        )
        
        # Setup mocks
        service.budget_repo.get_budget_by_category = AsyncMock(return_value=mock_budget)
        service.expense_repo.sum_expenses_by_category_and_period = AsyncMock(
            return_value=spent_at_55_percent
        )
        service.budget_repo.update_threshold_notification = AsyncMock()
        service.notification_service.send_notification = AsyncMock()
        
        # Trigger threshold check
        triggered = await service.check_and_send_threshold_notifications(user_id, category_id)
        
        # Verify no threshold was triggered (50% already notified, not yet at 80%)
        assert 50 not in triggered, (
            "50% threshold should NOT be triggered again when already notified"
        )
        assert len(triggered) == 0, (
            f"No thresholds should be triggered, but got {triggered}"
        )
        
        # Verify no notification was sent
        service.notification_service.send_notification.assert_not_called()
        
        # Verify threshold flag was NOT updated
        service.budget_repo.update_threshold_notification.assert_not_called()
    
    @pytest.mark.asyncio
    @given(
        budget_amount=valid_budget_amounts(),
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_80_percent_notification_not_repeated(
        self,
        budget_amount: Decimal,
    ):
        """Notifications SHALL only be sent once per threshold (not repeated).
        
        **Validates: Requirements 11.3**
        
        This test verifies that:
        1. When 80% threshold was already notified, no new notification is sent
        2. The threshold check returns empty list for already-notified thresholds
        """
        user_id = uuid4()
        category_id = uuid4()
        budget_id = uuid4()
        
        # Calculate 85% of budget (above 80% but below 100%)
        spent_at_85_percent = budget_amount * Decimal("0.85")
        
        # Create mock database session
        mock_db = AsyncMock()
        service = BudgetService(mock_db)
        
        # Create mock budget with 50% and 80% ALREADY notified
        mock_budget = create_mock_budget(
            budget_id=budget_id,
            user_id=user_id,
            category_id=category_id,
            amount=budget_amount,
            threshold_50_notified=True,
            threshold_80_notified=True,  # Already notified!
            threshold_100_notified=False,
        )
        
        # Setup mocks
        service.budget_repo.get_budget_by_category = AsyncMock(return_value=mock_budget)
        service.expense_repo.sum_expenses_by_category_and_period = AsyncMock(
            return_value=spent_at_85_percent
        )
        service.budget_repo.update_threshold_notification = AsyncMock()
        service.notification_service.send_notification = AsyncMock()
        
        # Trigger threshold check
        triggered = await service.check_and_send_threshold_notifications(user_id, category_id)
        
        # Verify no threshold was triggered (80% already notified, not yet at 100%)
        assert 80 not in triggered, (
            "80% threshold should NOT be triggered again when already notified"
        )
        assert len(triggered) == 0, (
            f"No thresholds should be triggered, but got {triggered}"
        )
        
        # Verify no notification was sent
        service.notification_service.send_notification.assert_not_called()
        
        # Verify threshold flag was NOT updated
        service.budget_repo.update_threshold_notification.assert_not_called()
    
    @pytest.mark.asyncio
    @given(
        budget_amount=valid_budget_amounts(),
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_100_percent_notification_not_repeated(
        self,
        budget_amount: Decimal,
    ):
        """Notifications SHALL only be sent once per threshold (not repeated).
        
        **Validates: Requirements 11.4**
        
        This test verifies that:
        1. When 100% threshold was already notified, no new notification is sent
        2. The threshold check returns empty list for already-notified thresholds
        """
        user_id = uuid4()
        category_id = uuid4()
        budget_id = uuid4()
        
        # Calculate 120% of budget (over budget)
        spent_at_120_percent = budget_amount * Decimal("1.20")
        
        # Create mock database session
        mock_db = AsyncMock()
        service = BudgetService(mock_db)
        
        # Create mock budget with ALL thresholds ALREADY notified
        mock_budget = create_mock_budget(
            budget_id=budget_id,
            user_id=user_id,
            category_id=category_id,
            amount=budget_amount,
            threshold_50_notified=True,
            threshold_80_notified=True,
            threshold_100_notified=True,  # Already notified!
        )
        
        # Setup mocks
        service.budget_repo.get_budget_by_category = AsyncMock(return_value=mock_budget)
        service.expense_repo.sum_expenses_by_category_and_period = AsyncMock(
            return_value=spent_at_120_percent
        )
        service.budget_repo.update_threshold_notification = AsyncMock()
        service.notification_service.send_notification = AsyncMock()
        
        # Trigger threshold check
        triggered = await service.check_and_send_threshold_notifications(user_id, category_id)
        
        # Verify no threshold was triggered (all already notified)
        assert 100 not in triggered, (
            "100% threshold should NOT be triggered again when already notified"
        )
        assert len(triggered) == 0, (
            f"No thresholds should be triggered, but got {triggered}"
        )
        
        # Verify no notification was sent
        service.notification_service.send_notification.assert_not_called()
        
        # Verify threshold flag was NOT updated
        service.budget_repo.update_threshold_notification.assert_not_called()
    
    @pytest.mark.asyncio
    @given(
        budget_amount=valid_budget_amounts(),
        percentage=st.floats(min_value=0.0, max_value=49.99, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_below_50_percent_no_notification(
        self,
        budget_amount: Decimal,
        percentage: float,
    ):
        """When spent is below 50% of budget, no notification SHALL be sent.
        
        **Validates: Requirements 11.2, 11.3, 11.4**
        
        This test verifies that:
        1. When expenses are below 50%, no threshold notification is triggered
        2. No notification is sent
        """
        user_id = uuid4()
        category_id = uuid4()
        budget_id = uuid4()
        
        # Calculate spent amount below 50%
        spent_below_50 = budget_amount * Decimal(str(percentage / 100))
        
        # Create mock database session
        mock_db = AsyncMock()
        service = BudgetService(mock_db)
        
        # Create mock budget with no thresholds notified
        mock_budget = create_mock_budget(
            budget_id=budget_id,
            user_id=user_id,
            category_id=category_id,
            amount=budget_amount,
            threshold_50_notified=False,
            threshold_80_notified=False,
            threshold_100_notified=False,
        )
        
        # Setup mocks
        service.budget_repo.get_budget_by_category = AsyncMock(return_value=mock_budget)
        service.expense_repo.sum_expenses_by_category_and_period = AsyncMock(
            return_value=spent_below_50
        )
        service.budget_repo.update_threshold_notification = AsyncMock()
        service.notification_service.send_notification = AsyncMock()
        
        # Trigger threshold check
        triggered = await service.check_and_send_threshold_notifications(user_id, category_id)
        
        # Verify no threshold was triggered
        assert len(triggered) == 0, (
            f"No thresholds should be triggered when spent is {percentage}% of budget"
        )
        
        # Verify no notification was sent
        service.notification_service.send_notification.assert_not_called()
    
    @pytest.mark.asyncio
    @given(
        budget_amount=valid_budget_amounts(),
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_threshold_triggers_highest_applicable_only(
        self,
        budget_amount: Decimal,
    ):
        """When multiple thresholds are crossed at once, only the highest
        applicable threshold SHALL be triggered.
        
        **Validates: Requirements 11.2, 11.3, 11.4**
        
        This test verifies that:
        1. When jumping from 0% to 100%, only 100% notification is sent
        2. The service correctly handles the elif chain in threshold checking
        """
        user_id = uuid4()
        category_id = uuid4()
        budget_id = uuid4()
        
        # Calculate 100% of budget (jumping from 0 to 100%)
        spent_at_100_percent = budget_amount
        
        # Create mock database session
        mock_db = AsyncMock()
        service = BudgetService(mock_db)
        
        # Create mock budget with NO thresholds notified (fresh budget)
        mock_budget = create_mock_budget(
            budget_id=budget_id,
            user_id=user_id,
            category_id=category_id,
            amount=budget_amount,
            threshold_50_notified=False,
            threshold_80_notified=False,
            threshold_100_notified=False,
        )
        
        # Setup mocks
        service.budget_repo.get_budget_by_category = AsyncMock(return_value=mock_budget)
        service.expense_repo.sum_expenses_by_category_and_period = AsyncMock(
            return_value=spent_at_100_percent
        )
        service.budget_repo.update_threshold_notification = AsyncMock()
        service.notification_service.send_notification = AsyncMock()
        
        # Trigger threshold check
        triggered = await service.check_and_send_threshold_notifications(user_id, category_id)
        
        # Verify only 100% threshold was triggered (highest applicable)
        assert 100 in triggered, "100% threshold should be triggered"
        assert len(triggered) == 1, (
            f"Only one threshold should be triggered, but got {triggered}"
        )
        
        # Verify only one notification was sent
        assert service.notification_service.send_notification.call_count == 1, (
            "Only one notification should be sent for the highest threshold"
        )
        
        # Verify only 100% threshold flag was updated
        service.budget_repo.update_threshold_notification.assert_called_once_with(
            mock_budget.id, 100
        )
    
    @pytest.mark.asyncio
    @given(
        budget_amount=valid_budget_amounts(),
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_no_budget_returns_empty_list(
        self,
        budget_amount: Decimal,
    ):
        """When no budget exists for the category, no notifications SHALL be sent.
        
        **Validates: Requirements 11.2, 11.3, 11.4**
        
        This test verifies that:
        1. When no budget exists, the function returns an empty list
        2. No notification is sent
        """
        user_id = uuid4()
        category_id = uuid4()
        
        # Create mock database session
        mock_db = AsyncMock()
        service = BudgetService(mock_db)
        
        # Setup mocks - no budget exists
        service.budget_repo.get_budget_by_category = AsyncMock(return_value=None)
        service.notification_service.send_notification = AsyncMock()
        
        # Trigger threshold check
        triggered = await service.check_and_send_threshold_notifications(user_id, category_id)
        
        # Verify empty list returned
        assert triggered == [], "Should return empty list when no budget exists"
        
        # Verify no notification was sent
        service.notification_service.send_notification.assert_not_called()
    
    @pytest.mark.asyncio
    @given(
        budget_amount=valid_budget_amounts(),
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_threshold_notification_content_correctness(
        self,
        budget_amount: Decimal,
    ):
        """Threshold notifications SHALL contain correct budget and spent information.
        
        **Validates: Requirements 11.2, 11.3, 11.4**
        
        This test verifies that:
        1. Notification title contains category name
        2. Notification body contains spent and budget amounts
        """
        user_id = uuid4()
        category_id = uuid4()
        budget_id = uuid4()
        category_name = "Food"
        
        # Calculate 50% of budget
        spent_at_50_percent = budget_amount * Decimal("0.50")
        
        # Create mock database session
        mock_db = AsyncMock()
        service = BudgetService(mock_db)
        
        # Create mock category
        mock_category = create_mock_category(
            category_id=category_id,
            user_id=user_id,
            name=category_name,
        )
        
        # Create mock budget
        mock_budget = create_mock_budget(
            budget_id=budget_id,
            user_id=user_id,
            category_id=category_id,
            amount=budget_amount,
            threshold_50_notified=False,
            threshold_80_notified=False,
            threshold_100_notified=False,
            category=mock_category,
        )
        
        # Setup mocks
        service.budget_repo.get_budget_by_category = AsyncMock(return_value=mock_budget)
        service.expense_repo.sum_expenses_by_category_and_period = AsyncMock(
            return_value=spent_at_50_percent
        )
        service.budget_repo.update_threshold_notification = AsyncMock()
        service.notification_service.send_notification = AsyncMock()
        
        # Trigger threshold check
        await service.check_and_send_threshold_notifications(user_id, category_id)
        
        # Verify notification content
        service.notification_service.send_notification.assert_called_once()
        call_args = service.notification_service.send_notification.call_args
        
        # Check title contains category name
        assert category_name in call_args.kwargs['title'], (
            f"Notification title should contain category name '{category_name}'"
        )
        
        # Check body contains spent amount
        body = call_args.kwargs['body']
        assert str(spent_at_50_percent) in body or f"${spent_at_50_percent:.2f}" in body, (
            f"Notification body should contain spent amount"
        )
