"""Expense service for managing expenses and categories.

Provides business logic for expense CRUD operations, category management,
and receipt handling.

Validates: Requirements 10.1, 10.4, 10.5, 10.6
"""

import logging
import uuid
from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.models.expense import Expense, ExpenseCategory
from app.repositories.expense import ExpenseRepository, ExpenseCategoryRepository
from app.schemas.expense import (
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseCategoryCreate,
    ExpenseCategoryUpdate,
    ExpenseResponse,
    ExpenseWithCategoryResponse,
    ExpenseCategoryResponse,
)
from app.schemas.document import PaginatedResponse

logger = logging.getLogger(__name__)


class ExpenseService:
    """Service for managing expenses and categories.
    
    Validates: Requirements 10.1, 10.4, 10.5, 10.6
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize the expense service.
        
        Args:
            db: Async database session
        """
        self.db = db
        self.expense_repo = ExpenseRepository(db)
        self.category_repo = ExpenseCategoryRepository(db)
    
    # ========================================================================
    # Category Operations
    # ========================================================================
    
    async def create_category(
        self,
        user_id: uuid.UUID,
        data: ExpenseCategoryCreate,
    ) -> ExpenseCategoryResponse:
        """Create a new expense category for a user.
        
        Validates: Requirements 10.4
        
        Args:
            user_id: User's UUID
            data: Category creation data
            
        Returns:
            Created category response
        """
        category = await self.category_repo.create_category(user_id, data)
        logger.info(f"Created expense category '{data.name}' for user {user_id}")
        return ExpenseCategoryResponse.model_validate(category)
    
    async def get_category(
        self,
        category_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[ExpenseCategoryResponse]:
        """Get a category by ID.
        
        Args:
            category_id: Category's UUID
            user_id: User's UUID for ownership verification
            
        Returns:
            Category response if found, None otherwise
        """
        category = await self.category_repo.get_category_by_id(category_id, user_id)
        if category is None:
            return None
        return ExpenseCategoryResponse.model_validate(category)
    
    async def get_categories(
        self,
        user_id: uuid.UUID,
    ) -> List[ExpenseCategoryResponse]:
        """Get all categories available to a user.
        
        Validates: Requirements 10.4
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of category responses
        """
        categories = await self.category_repo.get_categories_for_user(user_id)
        return [ExpenseCategoryResponse.model_validate(c) for c in categories]
    
    async def update_category(
        self,
        category_id: uuid.UUID,
        user_id: uuid.UUID,
        data: ExpenseCategoryUpdate,
    ) -> Optional[ExpenseCategoryResponse]:
        """Update an expense category.
        
        Validates: Requirements 10.4
        
        Args:
            category_id: Category's UUID
            user_id: User's UUID for ownership verification
            data: Category update data
            
        Returns:
            Updated category response if found, None otherwise
            
        Raises:
            ValueError: If trying to update a default category
        """
        category = await self.category_repo.get_category_by_id(category_id, user_id)
        if category is None:
            return None
        
        # Cannot update default categories
        if category.is_default:
            raise ValueError("Cannot update default categories")
        
        # Cannot update categories owned by other users
        if category.user_id != user_id:
            raise ValueError("Cannot update categories owned by other users")
        
        updated = await self.category_repo.update_category(category, data)
        logger.info(f"Updated expense category {category_id} for user {user_id}")
        return ExpenseCategoryResponse.model_validate(updated)
    
    async def delete_category(
        self,
        category_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Delete an expense category.
        
        Validates: Requirements 10.4
        
        Args:
            category_id: Category's UUID
            user_id: User's UUID for ownership verification
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            ValueError: If trying to delete a default category or category with expenses
        """
        category = await self.category_repo.get_category_by_id(category_id, user_id)
        if category is None:
            return False
        
        # Cannot delete default categories
        if category.is_default:
            raise ValueError("Cannot delete default categories")
        
        # Cannot delete categories owned by other users
        if category.user_id != user_id:
            raise ValueError("Cannot delete categories owned by other users")
        
        # Check if category has expenses
        has_expenses = await self.category_repo.category_has_expenses(category_id)
        if has_expenses:
            raise ValueError("Cannot delete category with existing expenses. Move or delete expenses first.")
        
        await self.category_repo.delete_category(category)
        logger.info(f"Deleted expense category {category_id} for user {user_id}")
        return True
    
    # ========================================================================
    # Expense Operations
    # ========================================================================
    
    async def create_expense(
        self,
        user_id: uuid.UUID,
        data: ExpenseCreate,
    ) -> ExpenseWithCategoryResponse:
        """Create a new expense.
        
        Validates: Requirements 10.1
        
        Args:
            user_id: User's UUID
            data: Expense creation data
            
        Returns:
            Created expense response with category
            
        Raises:
            ValueError: If category not found or not accessible
        """
        # Verify category exists and is accessible to user
        category = await self.category_repo.get_category_by_id(data.category_id, user_id)
        if category is None:
            raise ValueError(f"Category {data.category_id} not found or not accessible")
        
        expense = await self.expense_repo.create_expense(user_id, data)
        
        # Load category for response
        expense_with_category = await self.expense_repo.get_expense_with_category(
            expense.id, user_id
        )
        
        logger.info(f"Created expense {expense.id} for user {user_id}: {data.amount}")
        
        # Trigger budget threshold check asynchronously
        # Validates: Requirements 11.2, 11.3, 11.4
        try:
            from app.tasks.budget_tasks import check_budget_thresholds
            check_budget_thresholds.delay(str(user_id), str(data.category_id))
        except Exception as e:
            # Don't fail expense creation if task queueing fails
            logger.warning(f"Failed to queue budget threshold check: {e}")
        
        return ExpenseWithCategoryResponse.model_validate(expense_with_category)
    
    async def get_expense(
        self,
        expense_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[ExpenseWithCategoryResponse]:
        """Get an expense by ID.
        
        Args:
            expense_id: Expense's UUID
            user_id: User's UUID for ownership verification
            
        Returns:
            Expense response with category if found, None otherwise
        """
        expense = await self.expense_repo.get_expense_with_category(expense_id, user_id)
        if expense is None:
            return None
        return ExpenseWithCategoryResponse.model_validate(expense)
    
    async def get_expenses(
        self,
        user_id: uuid.UUID,
        category_id: Optional[uuid.UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        min_amount: Optional[Decimal] = None,
        max_amount: Optional[Decimal] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[ExpenseWithCategoryResponse]:
        """Get expenses for a user with optional filtering and pagination.
        
        Args:
            user_id: User's UUID
            category_id: Optional category filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            min_amount: Optional minimum amount filter
            max_amount: Optional maximum amount filter
            page: Page number (1-indexed)
            page_size: Number of results per page
            
        Returns:
            Paginated response with expenses
        """
        offset = (page - 1) * page_size
        
        expenses = await self.expense_repo.get_expenses_for_user(
            user_id=user_id,
            category_id=category_id,
            start_date=start_date,
            end_date=end_date,
            min_amount=min_amount,
            max_amount=max_amount,
            limit=page_size,
            offset=offset,
        )
        
        total = await self.expense_repo.count_expenses_for_user(
            user_id=user_id,
            category_id=category_id,
            start_date=start_date,
            end_date=end_date,
            min_amount=min_amount,
            max_amount=max_amount,
        )
        
        items = [ExpenseWithCategoryResponse.model_validate(e) for e in expenses]
        
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )
    
    async def update_expense(
        self,
        expense_id: uuid.UUID,
        user_id: uuid.UUID,
        data: ExpenseUpdate,
    ) -> Optional[ExpenseWithCategoryResponse]:
        """Update an expense.
        
        Validates: Requirements 10.5
        
        Args:
            expense_id: Expense's UUID
            user_id: User's UUID for ownership verification
            data: Expense update data
            
        Returns:
            Updated expense response if found, None otherwise
            
        Raises:
            ValueError: If new category not found or not accessible
        """
        expense = await self.expense_repo.get_expense_by_id(expense_id, user_id)
        if expense is None:
            return None
        
        # Track original category for budget recalculation
        original_category_id = expense.category_id
        
        # If category is being changed, verify new category exists
        if data.category_id is not None:
            category = await self.category_repo.get_category_by_id(data.category_id, user_id)
            if category is None:
                raise ValueError(f"Category {data.category_id} not found or not accessible")
        
        updated = await self.expense_repo.update_expense(expense, data)
        
        # Load category for response
        expense_with_category = await self.expense_repo.get_expense_with_category(
            updated.id, user_id
        )
        
        logger.info(f"Updated expense {expense_id} for user {user_id}")
        
        # Trigger budget threshold check asynchronously
        # Validates: Requirements 11.2, 11.3, 11.4
        try:
            from app.tasks.budget_tasks import check_budget_thresholds
            # Check original category budget
            check_budget_thresholds.delay(str(user_id), str(original_category_id))
            # If category changed, also check new category budget
            if data.category_id is not None and data.category_id != original_category_id:
                check_budget_thresholds.delay(str(user_id), str(data.category_id))
        except Exception as e:
            # Don't fail expense update if task queueing fails
            logger.warning(f"Failed to queue budget threshold check: {e}")
        
        return ExpenseWithCategoryResponse.model_validate(expense_with_category)
    
    async def delete_expense(
        self,
        expense_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Delete an expense.
        
        Validates: Requirements 10.6
        
        Args:
            expense_id: Expense's UUID
            user_id: User's UUID for ownership verification
            
        Returns:
            True if deleted, False if not found
        """
        expense = await self.expense_repo.get_expense_by_id(expense_id, user_id)
        if expense is None:
            return False
        
        # Store category_id before deletion for budget recalculation
        category_id = expense.category_id
        
        # Delete receipt from storage if exists
        if expense.receipt_url:
            try:
                await storage.delete_file(expense.receipt_url)
                logger.info(f"Deleted receipt for expense {expense_id}")
            except Exception as e:
                logger.warning(f"Failed to delete receipt for expense {expense_id}: {e}")
        
        await self.expense_repo.delete_expense(expense)
        logger.info(f"Deleted expense {expense_id} for user {user_id}")
        
        # Note: Budget threshold check is not needed on delete since
        # deleting an expense can only decrease the spent amount,
        # which won't trigger new threshold notifications.
        # However, we could reset notifications if spent drops below thresholds.
        
        return True
    
    # ========================================================================
    # Receipt Operations
    # ========================================================================
    
    async def upload_receipt(
        self,
        expense_id: uuid.UUID,
        user_id: uuid.UUID,
        file: UploadFile,
    ) -> Tuple[str, Optional[dict]]:
        """Upload a receipt image for an expense.
        
        Args:
            expense_id: Expense's UUID
            user_id: User's UUID for ownership verification
            file: Uploaded file
            
        Returns:
            Tuple of (receipt_url, ocr_data)
            
        Raises:
            ValueError: If expense not found or file type not supported
        """
        expense = await self.expense_repo.get_expense_by_id(expense_id, user_id)
        if expense is None:
            raise ValueError(f"Expense {expense_id} not found")
        
        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "image/webp", "application/pdf"]
        if file.content_type not in allowed_types:
            raise ValueError(f"File type {file.content_type} not supported. Allowed: {allowed_types}")
        
        # Delete old receipt if exists
        if expense.receipt_url:
            try:
                await storage.delete_file(expense.receipt_url)
            except Exception as e:
                logger.warning(f"Failed to delete old receipt: {e}")
        
        # Generate storage key
        file_ext = file.filename.split(".")[-1] if file.filename else "jpg"
        storage_key = f"receipts/{user_id}/{expense_id}/{uuid.uuid4()}.{file_ext}"
        
        # Read file content
        file_content = await file.read()
        
        # Upload to storage
        await storage.upload_file(
            file_data=file_content,
            key=storage_key,
            content_type=file.content_type or "application/octet-stream",
            metadata={"expense_id": str(expense_id), "user_id": str(user_id)},
        )
        
        # Update expense with receipt URL
        await self.expense_repo.update_expense_receipt(expense, storage_key, None)
        
        # Trigger async OCR processing for receipt
        # Validates: Requirements 10.2, 10.3
        try:
            from app.tasks.ocr_tasks import process_receipt_ocr
            process_receipt_ocr.delay(
                expense_id=str(expense_id),
                user_id=str(user_id),
                receipt_path=storage_key,
            )
            logger.info(f"Queued receipt OCR processing for expense {expense_id}")
        except Exception as e:
            # Don't fail upload if OCR task queueing fails
            logger.warning(f"Failed to queue receipt OCR for expense {expense_id}: {e}")
        
        logger.info(f"Uploaded receipt for expense {expense_id}")
        return storage_key, None
    
    async def get_receipt_url(
        self,
        expense_id: uuid.UUID,
        user_id: uuid.UUID,
        expiry_seconds: int = 3600,
    ) -> Optional[str]:
        """Get a presigned URL for downloading a receipt.
        
        Args:
            expense_id: Expense's UUID
            user_id: User's UUID for ownership verification
            expiry_seconds: URL validity period in seconds
            
        Returns:
            Presigned URL if receipt exists, None otherwise
        """
        expense = await self.expense_repo.get_expense_by_id(expense_id, user_id)
        if expense is None or expense.receipt_url is None:
            return None
        
        try:
            url = await storage.generate_presigned_url(
                key=expense.receipt_url,
                expiry_seconds=expiry_seconds,
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for receipt: {e}")
            return None
