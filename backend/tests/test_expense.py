"""Tests for expense module.

Validates: Requirements 10.1, 10.4, 10.5, 10.6
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.expense import (
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseCategoryCreate,
    ExpenseCategoryUpdate,
    ExpenseResponse,
    ExpenseCategoryResponse,
)
from app.services.expense import ExpenseService


class TestExpenseSchemas:
    """Test expense Pydantic schemas."""
    
    def test_expense_create_valid(self):
        """Test creating a valid expense."""
        data = ExpenseCreate(
            category_id=uuid.uuid4(),
            amount=Decimal("25.50"),
            description="Lunch at cafe",
            expense_date=date.today(),
        )
        assert data.amount == Decimal("25.50")
        assert data.description == "Lunch at cafe"
    
    def test_expense_create_amount_rounded(self):
        """Test that amount is rounded to 2 decimal places."""
        data = ExpenseCreate(
            category_id=uuid.uuid4(),
            amount=Decimal("25.555"),
            expense_date=date.today(),
        )
        assert data.amount == Decimal("25.56")
    
    def test_expense_create_negative_amount_rejected(self):
        """Test that negative amounts are rejected."""
        with pytest.raises(ValueError):
            ExpenseCreate(
                category_id=uuid.uuid4(),
                amount=Decimal("-10.00"),
                expense_date=date.today(),
            )
    
    def test_expense_create_zero_amount_rejected(self):
        """Test that zero amounts are rejected."""
        with pytest.raises(ValueError):
            ExpenseCreate(
                category_id=uuid.uuid4(),
                amount=Decimal("0"),
                expense_date=date.today(),
            )
    
    def test_expense_update_partial(self):
        """Test partial expense update."""
        data = ExpenseUpdate(amount=Decimal("30.00"))
        assert data.amount == Decimal("30.00")
        assert data.category_id is None
        assert data.description is None
    
    def test_category_create_valid(self):
        """Test creating a valid category."""
        data = ExpenseCategoryCreate(
            name="Groceries",
            icon="shopping-cart",
            color="#FF5733",
        )
        assert data.name == "Groceries"
        assert data.color == "#FF5733"
    
    def test_category_create_invalid_color(self):
        """Test that invalid color format is rejected."""
        with pytest.raises(ValueError):
            ExpenseCategoryCreate(
                name="Test",
                color="invalid",
            )
    
    def test_category_create_color_without_hash(self):
        """Test that color without # is rejected."""
        with pytest.raises(ValueError):
            ExpenseCategoryCreate(
                name="Test",
                color="FF5733",
            )
    
    def test_category_create_color_wrong_length(self):
        """Test that color with wrong length is rejected."""
        with pytest.raises(ValueError):
            ExpenseCategoryCreate(
                name="Test",
                color="#FFF",
            )


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
    mock.id = category_id or uuid.uuid4()
    mock.user_id = user_id
    mock.name = name
    mock.icon = icon
    mock.color = color
    mock.is_default = is_default
    mock.created_at = datetime.now(timezone.utc)
    mock.updated_at = datetime.now(timezone.utc)
    return mock


def create_mock_expense(
    expense_id=None,
    user_id=None,
    category_id=None,
    amount=25.50,
    description="Test expense",
    expense_date=None,
    receipt_url=None,
    ocr_data=None,
    category=None,
):
    """Create a mock expense object."""
    mock = MagicMock()
    mock.id = expense_id or uuid.uuid4()
    mock.user_id = user_id or uuid.uuid4()
    mock.category_id = category_id or uuid.uuid4()
    mock.amount = amount
    mock.description = description
    mock.expense_date = expense_date or date.today()
    mock.receipt_url = receipt_url
    mock.ocr_data = ocr_data
    mock.created_at = datetime.now(timezone.utc)
    mock.updated_at = datetime.now(timezone.utc)
    mock.category = category
    return mock


class TestExpenseService:
    """Test expense service business logic."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock()
    
    @pytest.fixture
    def service(self, mock_db):
        """Create expense service with mocked dependencies."""
        return ExpenseService(mock_db)
    
    @pytest.mark.asyncio
    async def test_create_category(self, service):
        """Test creating a new category."""
        user_id = uuid.uuid4()
        category_id = uuid.uuid4()
        
        mock_category = create_mock_category(
            category_id=category_id,
            user_id=user_id,
            name="Custom Category",
            icon="star",
            color="#123456",
            is_default=False,
        )
        
        service.category_repo.create_category = AsyncMock(return_value=mock_category)
        
        data = ExpenseCategoryCreate(
            name="Custom Category",
            icon="star",
            color="#123456",
        )
        
        result = await service.create_category(user_id, data)
        
        assert result.name == "Custom Category"
        assert result.is_default is False
        service.category_repo.create_category.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_expense(self, service):
        """Test creating a new expense."""
        user_id = uuid.uuid4()
        category_id = uuid.uuid4()
        expense_id = uuid.uuid4()
        
        mock_category = create_mock_category(
            category_id=category_id,
            user_id=user_id,
            name="Food",
            is_default=False,
        )
        
        mock_expense = create_mock_expense(
            expense_id=expense_id,
            user_id=user_id,
            category_id=category_id,
            amount=25.50,
            description="Lunch",
            category=mock_category,
        )
        
        service.category_repo.get_category_by_id = AsyncMock(return_value=mock_category)
        service.expense_repo.create_expense = AsyncMock(return_value=mock_expense)
        service.expense_repo.get_expense_with_category = AsyncMock(return_value=mock_expense)
        
        data = ExpenseCreate(
            category_id=category_id,
            amount=Decimal("25.50"),
            description="Lunch",
            expense_date=date.today(),
        )
        
        result = await service.create_expense(user_id, data)
        
        assert result.amount == Decimal("25.50")
        assert result.description == "Lunch"
        service.expense_repo.create_expense.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_expense_invalid_category(self, service):
        """Test creating expense with invalid category raises error."""
        user_id = uuid.uuid4()
        category_id = uuid.uuid4()
        
        # Mock category not found
        service.category_repo.get_category_by_id = AsyncMock(return_value=None)
        
        data = ExpenseCreate(
            category_id=category_id,
            amount=Decimal("25.50"),
            expense_date=date.today(),
        )
        
        with pytest.raises(ValueError, match="not found"):
            await service.create_expense(user_id, data)
    
    @pytest.mark.asyncio
    async def test_update_expense(self, service):
        """Test updating an expense."""
        user_id = uuid.uuid4()
        expense_id = uuid.uuid4()
        category_id = uuid.uuid4()
        
        mock_category = create_mock_category(
            category_id=category_id,
            user_id=user_id,
            name="Food",
            is_default=False,
        )
        
        mock_expense = create_mock_expense(
            expense_id=expense_id,
            user_id=user_id,
            category_id=category_id,
            amount=25.50,
            description="Lunch",
            category=mock_category,
        )
        
        service.expense_repo.get_expense_by_id = AsyncMock(return_value=mock_expense)
        service.expense_repo.update_expense = AsyncMock(return_value=mock_expense)
        service.expense_repo.get_expense_with_category = AsyncMock(return_value=mock_expense)
        
        data = ExpenseUpdate(amount=Decimal("30.00"))
        
        result = await service.update_expense(expense_id, user_id, data)
        
        assert result is not None
        service.expense_repo.update_expense.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_expense(self, service):
        """Test deleting an expense."""
        user_id = uuid.uuid4()
        expense_id = uuid.uuid4()
        
        mock_expense = create_mock_expense(
            expense_id=expense_id,
            user_id=user_id,
            receipt_url=None,
        )
        
        service.expense_repo.get_expense_by_id = AsyncMock(return_value=mock_expense)
        service.expense_repo.delete_expense = AsyncMock()
        
        result = await service.delete_expense(expense_id, user_id)
        
        assert result is True
        service.expense_repo.delete_expense.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_expense_not_found(self, service):
        """Test deleting non-existent expense returns False."""
        user_id = uuid.uuid4()
        expense_id = uuid.uuid4()
        
        service.expense_repo.get_expense_by_id = AsyncMock(return_value=None)
        
        result = await service.delete_expense(expense_id, user_id)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_delete_category_with_expenses_fails(self, service):
        """Test deleting category with expenses raises error."""
        user_id = uuid.uuid4()
        category_id = uuid.uuid4()
        
        mock_category = create_mock_category(
            category_id=category_id,
            user_id=user_id,
            name="Custom",
            is_default=False,
        )
        
        service.category_repo.get_category_by_id = AsyncMock(return_value=mock_category)
        service.category_repo.category_has_expenses = AsyncMock(return_value=True)
        
        with pytest.raises(ValueError, match="existing expenses"):
            await service.delete_category(category_id, user_id)
    
    @pytest.mark.asyncio
    async def test_delete_default_category_fails(self, service):
        """Test deleting default category raises error."""
        user_id = uuid.uuid4()
        category_id = uuid.uuid4()
        
        mock_category = create_mock_category(
            category_id=category_id,
            user_id=None,
            name="Food",
            is_default=True,
        )
        
        service.category_repo.get_category_by_id = AsyncMock(return_value=mock_category)
        
        with pytest.raises(ValueError, match="default categories"):
            await service.delete_category(category_id, user_id)
