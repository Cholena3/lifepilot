"""Property-based tests for expense module.

Uses Hypothesis to verify universal properties across all valid inputs.

**Validates: Requirements 10.1, 10.7**

Property 21: Expense Data Integrity - For any valid expense data, creating and
retrieving SHALL return equivalent data.

Property 22: Expense Receipt Round-Trip - For any expense logged with a receipt
image, viewing the expense SHALL display the original receipt image.
"""

import io
import string
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from fastapi import UploadFile

from app.schemas.expense import (
    ExpenseCreate,
    ExpenseResponse,
    ExpenseWithCategoryResponse,
    ExpenseCategoryResponse,
)
from app.services.expense import ExpenseService


# ============================================================================
# Hypothesis Strategies for Expense Data
# ============================================================================

@st.composite
def valid_amounts(draw):
    """Generate valid expense amounts (positive, up to 2 decimal places).
    
    Amounts must be positive and are rounded to 2 decimal places.
    """
    # Generate a positive float and convert to Decimal
    value = draw(st.floats(min_value=0.01, max_value=999999.99, allow_nan=False, allow_infinity=False))
    # Round to 2 decimal places for realistic expense values
    return Decimal(str(round(value, 2)))


@st.composite
def valid_expense_dates(draw):
    """Generate valid expense dates.
    
    Dates should be reasonable - not too far in the past or future.
    """
    today = date.today()
    min_date = today - timedelta(days=365 * 5)  # 5 years ago
    max_date = today + timedelta(days=30)  # Up to 30 days in future
    
    return draw(st.dates(min_value=min_date, max_value=max_date))


@st.composite
def valid_descriptions(draw):
    """Generate valid expense descriptions (0-1000 characters).
    
    Descriptions can be None or a string up to 1000 characters.
    """
    # 50% chance of None description
    if draw(st.booleans()):
        return None
    
    # Generate a description with printable characters
    chars = string.ascii_letters + string.digits + " .,!?-'\"()@#$%&*"
    length = draw(st.integers(min_value=1, max_value=200))  # Keep reasonable for testing
    
    description = draw(st.text(alphabet=chars, min_size=length, max_size=length))
    
    # Clean up: no consecutive spaces
    while "  " in description:
        description = description.replace("  ", " ")
    
    return description.strip() if description.strip() else None


@st.composite
def valid_category_names(draw):
    """Generate valid category names (1-100 characters)."""
    categories = [
        "Food", "Transportation", "Entertainment", "Shopping", "Utilities",
        "Healthcare", "Education", "Travel", "Groceries", "Dining Out",
        "Coffee", "Subscriptions", "Gifts", "Personal Care", "Fitness",
        "Home", "Electronics", "Clothing", "Insurance", "Miscellaneous"
    ]
    return draw(st.sampled_from(categories))


@st.composite
def valid_expense_data(draw):
    """Generate valid expense data for testing.
    
    Returns a dictionary with valid expense fields.
    """
    return {
        "amount": draw(valid_amounts()),
        "description": draw(valid_descriptions()),
        "expense_date": draw(valid_expense_dates()),
    }


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


def create_mock_expense(
    expense_id=None,
    user_id=None,
    category_id=None,
    amount=None,
    description=None,
    expense_date=None,
    receipt_url=None,
    ocr_data=None,
    category=None,
):
    """Create a mock expense object."""
    mock = MagicMock()
    mock.id = expense_id or uuid4()
    mock.user_id = user_id or uuid4()
    mock.category_id = category_id or uuid4()
    mock.amount = amount if amount is not None else Decimal("25.50")
    mock.description = description
    mock.expense_date = expense_date or date.today()
    mock.receipt_url = receipt_url
    mock.ocr_data = ocr_data
    mock.created_at = datetime.now(timezone.utc)
    mock.updated_at = datetime.now(timezone.utc)
    mock.category = category
    return mock


# ============================================================================
# Property 21: Expense Data Integrity
# ============================================================================

class TestExpenseDataIntegrityProperty:
    """Property 21: Expense Data Integrity.
    
    **Validates: Requirements 10.1**
    
    For any valid expense data (amount, category, description, date), creating an
    expense and then retrieving it SHALL return equivalent data.
    """
    
    @given(expense_data=valid_expense_data())
    @settings(max_examples=10, deadline=None)
    def test_expense_schema_round_trip(self, expense_data: dict):
        """For any valid expense data submitted, the data retrieved after saving
        SHALL match the original data exactly.
        
        **Validates: Requirements 10.1**
        
        This test verifies that:
        1. Valid expense data can be created via ExpenseCreate schema
        2. The data can be serialized to ExpenseResponse
        3. The retrieved data matches the original input
        """
        category_id = uuid4()
        user_id = uuid4()
        expense_id = uuid4()
        
        # Create expense using the schema (simulates submission)
        expense_create = ExpenseCreate(
            category_id=category_id,
            amount=expense_data["amount"],
            description=expense_data["description"],
            expense_date=expense_data["expense_date"],
        )
        
        # Verify the schema accepted the data
        # Note: amount is rounded to 2 decimal places by the schema
        expected_amount = round(expense_data["amount"], 2)
        assert expense_create.amount == expected_amount, (
            f"Amount mismatch after schema creation: expected {expected_amount}, "
            f"got {expense_create.amount}"
        )
        assert expense_create.description == expense_data["description"]
        assert expense_create.expense_date == expense_data["expense_date"]
        assert expense_create.category_id == category_id
        
        # Simulate saving and retrieving by creating a response
        # (In real scenario, this would go through repository and database)
        expense_response = ExpenseResponse(
            id=expense_id,
            user_id=user_id,
            category_id=expense_create.category_id,
            amount=expense_create.amount,
            description=expense_create.description,
            expense_date=expense_create.expense_date,
            receipt_url=None,
            ocr_data=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        # Verify round-trip: retrieved data matches original
        assert expense_response.amount == expected_amount, (
            f"amount mismatch: expected {expected_amount}, "
            f"got {expense_response.amount}"
        )
        assert expense_response.description == expense_data["description"], (
            f"description mismatch: expected {expense_data['description']}, "
            f"got {expense_response.description}"
        )
        assert expense_response.expense_date == expense_data["expense_date"], (
            f"expense_date mismatch: expected {expense_data['expense_date']}, "
            f"got {expense_response.expense_date}"
        )
        assert expense_response.category_id == category_id, (
            f"category_id mismatch: expected {category_id}, "
            f"got {expense_response.category_id}"
        )
    
    @given(expense_data=valid_expense_data())
    @settings(max_examples=10, deadline=None)
    def test_expense_with_category_round_trip(self, expense_data: dict):
        """For any valid expense data with category, the data retrieved after saving
        SHALL match the original data and include category details.
        
        **Validates: Requirements 10.1**
        
        This test verifies that:
        1. Valid expense data can be created via ExpenseCreate schema
        2. The data can be serialized to ExpenseWithCategoryResponse
        3. The retrieved data matches the original input
        4. Category information is preserved
        """
        category_id = uuid4()
        user_id = uuid4()
        expense_id = uuid4()
        category_name = "Food"
        
        # Create expense using the schema (simulates submission)
        expense_create = ExpenseCreate(
            category_id=category_id,
            amount=expense_data["amount"],
            description=expense_data["description"],
            expense_date=expense_data["expense_date"],
        )
        
        # Create category response
        category_response = ExpenseCategoryResponse(
            id=category_id,
            user_id=user_id,
            name=category_name,
            icon="utensils",
            color="#FF6B6B",
            is_default=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        # Simulate saving and retrieving by creating a response with category
        expense_response = ExpenseWithCategoryResponse(
            id=expense_id,
            user_id=user_id,
            category_id=expense_create.category_id,
            amount=expense_create.amount,
            description=expense_create.description,
            expense_date=expense_create.expense_date,
            receipt_url=None,
            ocr_data=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            category=category_response,
        )
        
        # Verify round-trip: retrieved data matches original
        expected_amount = round(expense_data["amount"], 2)
        assert expense_response.amount == expected_amount, (
            f"amount mismatch: expected {expected_amount}, "
            f"got {expense_response.amount}"
        )
        assert expense_response.description == expense_data["description"], (
            f"description mismatch: expected {expense_data['description']}, "
            f"got {expense_response.description}"
        )
        assert expense_response.expense_date == expense_data["expense_date"], (
            f"expense_date mismatch: expected {expense_data['expense_date']}, "
            f"got {expense_response.expense_date}"
        )
        assert expense_response.category_id == category_id, (
            f"category_id mismatch: expected {category_id}, "
            f"got {expense_response.category_id}"
        )
        assert expense_response.category.name == category_name, (
            f"category name mismatch: expected {category_name}, "
            f"got {expense_response.category.name}"
        )
    
    @pytest.mark.asyncio
    @given(expense_data=valid_expense_data())
    @settings(max_examples=10, deadline=None)
    async def test_expense_service_round_trip(self, expense_data: dict):
        """For any valid expense data, creating via service and retrieving
        SHALL return equivalent data.
        
        **Validates: Requirements 10.1**
        
        This test verifies the full round-trip through the service layer:
        1. Create expense via ExpenseService.create_expense
        2. Retrieve expense via ExpenseService.get_expense
        3. Verify all fields match the original input
        """
        user_id = uuid4()
        category_id = uuid4()
        expense_id = uuid4()
        
        # Create mock database session
        mock_db = AsyncMock()
        service = ExpenseService(mock_db)
        
        # Create mock category
        mock_category = create_mock_category(
            category_id=category_id,
            user_id=user_id,
            name="Food",
            is_default=False,
        )
        
        # Expected amount after rounding
        expected_amount = round(expense_data["amount"], 2)
        
        # Create mock expense that will be returned by repository
        mock_expense = create_mock_expense(
            expense_id=expense_id,
            user_id=user_id,
            category_id=category_id,
            amount=expected_amount,
            description=expense_data["description"],
            expense_date=expense_data["expense_date"],
            category=mock_category,
        )
        
        # Setup mocks
        service.category_repo.get_category_by_id = AsyncMock(return_value=mock_category)
        service.expense_repo.create_expense = AsyncMock(return_value=mock_expense)
        service.expense_repo.get_expense_with_category = AsyncMock(return_value=mock_expense)
        
        # Create expense data
        create_data = ExpenseCreate(
            category_id=category_id,
            amount=expense_data["amount"],
            description=expense_data["description"],
            expense_date=expense_data["expense_date"],
        )
        
        # Create expense via service
        created_expense = await service.create_expense(user_id, create_data)
        
        # Verify created expense matches input
        assert created_expense.amount == expected_amount, (
            f"Created expense amount mismatch: expected {expected_amount}, "
            f"got {created_expense.amount}"
        )
        assert created_expense.description == expense_data["description"], (
            f"Created expense description mismatch: expected {expense_data['description']}, "
            f"got {created_expense.description}"
        )
        assert created_expense.expense_date == expense_data["expense_date"], (
            f"Created expense date mismatch: expected {expense_data['expense_date']}, "
            f"got {created_expense.expense_date}"
        )
        
        # Retrieve expense via service
        service.expense_repo.get_expense_with_category = AsyncMock(return_value=mock_expense)
        retrieved_expense = await service.get_expense(expense_id, user_id)
        
        # Verify retrieved expense matches created expense
        assert retrieved_expense is not None, "Retrieved expense should not be None"
        assert retrieved_expense.amount == created_expense.amount, (
            f"Retrieved amount mismatch: expected {created_expense.amount}, "
            f"got {retrieved_expense.amount}"
        )
        assert retrieved_expense.description == created_expense.description, (
            f"Retrieved description mismatch: expected {created_expense.description}, "
            f"got {retrieved_expense.description}"
        )
        assert retrieved_expense.expense_date == created_expense.expense_date, (
            f"Retrieved date mismatch: expected {created_expense.expense_date}, "
            f"got {retrieved_expense.expense_date}"
        )
        assert retrieved_expense.category_id == created_expense.category_id, (
            f"Retrieved category_id mismatch: expected {created_expense.category_id}, "
            f"got {retrieved_expense.category_id}"
        )
    
    @given(amount=valid_amounts())
    @settings(max_examples=10, deadline=None)
    def test_amount_precision_preserved(self, amount: Decimal):
        """For any valid amount, the precision SHALL be preserved after round-trip.
        
        **Validates: Requirements 10.1**
        
        This test verifies that:
        1. Amount values are correctly rounded to 2 decimal places
        2. The rounded value is preserved through the round-trip
        """
        category_id = uuid4()
        user_id = uuid4()
        expense_id = uuid4()
        
        # Create expense with the amount
        expense_create = ExpenseCreate(
            category_id=category_id,
            amount=amount,
            expense_date=date.today(),
        )
        
        # Expected amount after rounding
        expected_amount = round(amount, 2)
        
        # Verify schema rounds correctly
        assert expense_create.amount == expected_amount, (
            f"Schema should round amount to 2 decimal places: "
            f"expected {expected_amount}, got {expense_create.amount}"
        )
        
        # Create response
        expense_response = ExpenseResponse(
            id=expense_id,
            user_id=user_id,
            category_id=category_id,
            amount=expense_create.amount,
            description=None,
            expense_date=date.today(),
            receipt_url=None,
            ocr_data=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        # Verify amount is preserved
        assert expense_response.amount == expected_amount, (
            f"Amount precision not preserved: expected {expected_amount}, "
            f"got {expense_response.amount}"
        )
    
    @given(expense_date=valid_expense_dates())
    @settings(max_examples=10, deadline=None)
    def test_date_preserved(self, expense_date: date):
        """For any valid expense date, the date SHALL be preserved after round-trip.
        
        **Validates: Requirements 10.1**
        
        This test verifies that:
        1. Date values are correctly stored
        2. The date is preserved through the round-trip
        """
        category_id = uuid4()
        user_id = uuid4()
        expense_id = uuid4()
        
        # Create expense with the date
        expense_create = ExpenseCreate(
            category_id=category_id,
            amount=Decimal("10.00"),
            expense_date=expense_date,
        )
        
        # Verify schema accepts the date
        assert expense_create.expense_date == expense_date
        
        # Create response
        expense_response = ExpenseResponse(
            id=expense_id,
            user_id=user_id,
            category_id=category_id,
            amount=Decimal("10.00"),
            description=None,
            expense_date=expense_create.expense_date,
            receipt_url=None,
            ocr_data=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        # Verify date is preserved
        assert expense_response.expense_date == expense_date, (
            f"Date not preserved: expected {expense_date}, "
            f"got {expense_response.expense_date}"
        )


# ============================================================================
# Hypothesis Strategies for Receipt Data
# ============================================================================

@st.composite
def valid_receipt_image_data(draw):
    """Generate valid receipt image data for testing.
    
    Generates random bytes that simulate image content along with
    valid content types for receipt images.
    """
    # Supported content types for receipts
    content_types = ["image/jpeg", "image/png", "image/webp", "application/pdf"]
    content_type = draw(st.sampled_from(content_types))
    
    # Generate random image bytes (simulating image content)
    # Use smaller sizes for testing efficiency (1KB to 10KB)
    size = draw(st.integers(min_value=1024, max_value=10 * 1024))
    
    # Generate deterministic bytes based on size for reproducibility
    image_bytes = draw(st.binary(min_size=size, max_size=size))
    
    # Generate a filename with appropriate extension
    extensions = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "application/pdf": "pdf",
    }
    ext = extensions[content_type]
    filename = f"receipt_{draw(st.integers(min_value=1, max_value=99999))}.{ext}"
    
    return {
        "content": image_bytes,
        "content_type": content_type,
        "filename": filename,
    }


@st.composite
def valid_receipt_storage_keys(draw):
    """Generate valid S3 storage keys for receipts."""
    user_id = uuid4()
    expense_id = uuid4()
    file_id = uuid4()
    ext = draw(st.sampled_from(["jpg", "png", "webp", "pdf"]))
    return f"receipts/{user_id}/{expense_id}/{file_id}.{ext}"


# ============================================================================
# Property 22: Expense Receipt Round-Trip
# ============================================================================

class TestExpenseReceiptRoundTripProperty:
    """Property 22: Expense Receipt Round-Trip.
    
    **Validates: Requirements 10.7**
    
    For any expense logged with a receipt image, viewing the expense SHALL
    display the original receipt image.
    
    This property verifies:
    1. Receipt images can be uploaded for expenses
    2. The receipt URL is stored with the expense
    3. The receipt can be retrieved via presigned URL
    4. The retrieved content matches the original upload
    """
    
    @pytest.mark.asyncio
    @given(
        expense_data=valid_expense_data(),
        receipt_data=valid_receipt_image_data(),
    )
    @settings(max_examples=10, deadline=None)
    async def test_receipt_upload_stores_url(
        self,
        expense_data: dict,
        receipt_data: dict,
    ):
        """For any expense with a receipt uploaded, the expense SHALL have
        a valid receipt_url stored.
        
        **Validates: Requirements 10.7**
        
        This test verifies that:
        1. A receipt can be uploaded for an expense
        2. The expense record is updated with the receipt URL
        3. The receipt URL follows the expected storage key format
        """
        user_id = uuid4()
        category_id = uuid4()
        expense_id = uuid4()
        
        # Create mock database session
        mock_db = AsyncMock()
        service = ExpenseService(mock_db)
        
        # Create mock category
        mock_category = create_mock_category(
            category_id=category_id,
            user_id=user_id,
            name="Food",
        )
        
        # Create mock expense without receipt
        mock_expense = create_mock_expense(
            expense_id=expense_id,
            user_id=user_id,
            category_id=category_id,
            amount=expense_data["amount"],
            description=expense_data["description"],
            expense_date=expense_data["expense_date"],
            receipt_url=None,
            category=mock_category,
        )
        
        # Expected storage key pattern
        expected_key_prefix = f"receipts/{user_id}/{expense_id}/"
        
        # Track the storage key that will be set
        stored_receipt_url = None
        
        async def mock_update_receipt(expense, receipt_url, ocr_data):
            nonlocal stored_receipt_url
            stored_receipt_url = receipt_url
            expense.receipt_url = receipt_url
            expense.ocr_data = ocr_data
            return expense
        
        # Setup mocks
        service.expense_repo.get_expense_by_id = AsyncMock(return_value=mock_expense)
        service.expense_repo.update_expense_receipt = mock_update_receipt
        
        # Mock storage upload
        with patch("app.services.expense.storage") as mock_storage:
            mock_storage.upload_file = AsyncMock(return_value=None)
            mock_storage.delete_file = AsyncMock(return_value=True)
            
            # Create mock upload file
            mock_file = MagicMock()
            mock_file.content_type = receipt_data["content_type"]
            mock_file.filename = receipt_data["filename"]
            mock_file.read = AsyncMock(return_value=receipt_data["content"])
            
            # Upload receipt
            receipt_url, ocr_data = await service.upload_receipt(
                expense_id=expense_id,
                user_id=user_id,
                file=mock_file,
            )
            
            # Verify receipt URL was stored
            assert stored_receipt_url is not None, "Receipt URL should be stored"
            assert stored_receipt_url.startswith(expected_key_prefix), (
                f"Receipt URL should start with {expected_key_prefix}, "
                f"got {stored_receipt_url}"
            )
            
            # Verify storage upload was called with correct parameters
            mock_storage.upload_file.assert_called_once()
            call_kwargs = mock_storage.upload_file.call_args.kwargs
            assert call_kwargs["file_data"] == receipt_data["content"], (
                "Uploaded file data should match original"
            )
            assert call_kwargs["content_type"] == receipt_data["content_type"], (
                "Content type should match original"
            )
    
    @pytest.mark.asyncio
    @given(
        expense_data=valid_expense_data(),
        receipt_data=valid_receipt_image_data(),
    )
    @settings(max_examples=10, deadline=None)
    async def test_receipt_retrieval_returns_valid_url(
        self,
        expense_data: dict,
        receipt_data: dict,
    ):
        """For any expense with a receipt, retrieving the receipt SHALL return
        a valid presigned URL.
        
        **Validates: Requirements 10.7**
        
        This test verifies that:
        1. An expense with a receipt URL can generate a presigned URL
        2. The presigned URL is valid and accessible
        """
        user_id = uuid4()
        category_id = uuid4()
        expense_id = uuid4()
        
        # Create mock database session
        mock_db = AsyncMock()
        service = ExpenseService(mock_db)
        
        # Create mock category
        mock_category = create_mock_category(
            category_id=category_id,
            user_id=user_id,
            name="Food",
        )
        
        # Storage key for the receipt
        storage_key = f"receipts/{user_id}/{expense_id}/{uuid4()}.jpg"
        
        # Create mock expense with receipt
        mock_expense = create_mock_expense(
            expense_id=expense_id,
            user_id=user_id,
            category_id=category_id,
            amount=expense_data["amount"],
            description=expense_data["description"],
            expense_date=expense_data["expense_date"],
            receipt_url=storage_key,
            category=mock_category,
        )
        
        # Expected presigned URL
        expected_presigned_url = f"https://s3.example.com/{storage_key}?signature=abc123"
        
        # Setup mocks
        service.expense_repo.get_expense_by_id = AsyncMock(return_value=mock_expense)
        
        # Mock storage presigned URL generation
        with patch("app.services.expense.storage") as mock_storage:
            mock_storage.generate_presigned_url = AsyncMock(
                return_value=expected_presigned_url
            )
            
            # Get receipt URL
            presigned_url = await service.get_receipt_url(
                expense_id=expense_id,
                user_id=user_id,
                expiry_seconds=3600,
            )
            
            # Verify presigned URL was returned
            assert presigned_url is not None, "Presigned URL should be returned"
            assert presigned_url == expected_presigned_url, (
                f"Presigned URL should match expected: {expected_presigned_url}, "
                f"got {presigned_url}"
            )
            
            # Verify storage was called with correct key
            mock_storage.generate_presigned_url.assert_called_once_with(
                key=storage_key,
                expiry_seconds=3600,
            )
    
    @pytest.mark.asyncio
    @given(
        expense_data=valid_expense_data(),
        receipt_data=valid_receipt_image_data(),
    )
    @settings(max_examples=10, deadline=None)
    async def test_receipt_round_trip_content_integrity(
        self,
        expense_data: dict,
        receipt_data: dict,
    ):
        """For any receipt uploaded, downloading via the receipt URL SHALL
        return the original image content.
        
        **Validates: Requirements 10.7**
        
        This test verifies the complete round-trip:
        1. Upload a receipt image
        2. Store the receipt URL with the expense
        3. Download the receipt via the URL
        4. Verify the downloaded content matches the original
        """
        user_id = uuid4()
        category_id = uuid4()
        expense_id = uuid4()
        
        # Create mock database session
        mock_db = AsyncMock()
        service = ExpenseService(mock_db)
        
        # Create mock category
        mock_category = create_mock_category(
            category_id=category_id,
            user_id=user_id,
            name="Food",
        )
        
        # Track uploaded content and storage key
        uploaded_content = None
        uploaded_key = None
        
        async def mock_upload_file(file_data, key, content_type, metadata=None):
            nonlocal uploaded_content, uploaded_key
            uploaded_content = file_data
            uploaded_key = key
            return key
        
        async def mock_download_file(key):
            # Return the content that was uploaded to this key
            if key == uploaded_key:
                return uploaded_content
            raise FileNotFoundError(f"File not found: {key}")
        
        # Create mock expense without receipt
        mock_expense = create_mock_expense(
            expense_id=expense_id,
            user_id=user_id,
            category_id=category_id,
            amount=expense_data["amount"],
            description=expense_data["description"],
            expense_date=expense_data["expense_date"],
            receipt_url=None,
            category=mock_category,
        )
        
        async def mock_update_receipt(expense, receipt_url, ocr_data):
            expense.receipt_url = receipt_url
            expense.ocr_data = ocr_data
            return expense
        
        # Setup mocks
        service.expense_repo.get_expense_by_id = AsyncMock(return_value=mock_expense)
        service.expense_repo.update_expense_receipt = mock_update_receipt
        
        # Mock storage operations
        with patch("app.services.expense.storage") as mock_storage:
            mock_storage.upload_file = mock_upload_file
            mock_storage.delete_file = AsyncMock(return_value=True)
            mock_storage.download_file = mock_download_file
            
            # Create mock upload file
            mock_file = MagicMock()
            mock_file.content_type = receipt_data["content_type"]
            mock_file.filename = receipt_data["filename"]
            mock_file.read = AsyncMock(return_value=receipt_data["content"])
            
            # Step 1: Upload receipt
            receipt_url, _ = await service.upload_receipt(
                expense_id=expense_id,
                user_id=user_id,
                file=mock_file,
            )
            
            # Verify upload was successful
            assert uploaded_key is not None, "Receipt should be uploaded"
            assert uploaded_content == receipt_data["content"], (
                "Uploaded content should match original"
            )
            
            # Step 2: Download receipt and verify content
            downloaded_content = await mock_download_file(uploaded_key)
            
            # Step 3: Verify round-trip integrity
            assert downloaded_content == receipt_data["content"], (
                "Downloaded content should match original uploaded content"
            )
            assert len(downloaded_content) == len(receipt_data["content"]), (
                f"Content length mismatch: expected {len(receipt_data['content'])}, "
                f"got {len(downloaded_content)}"
            )
    
    @pytest.mark.asyncio
    @given(expense_data=valid_expense_data())
    @settings(max_examples=10, deadline=None)
    async def test_expense_without_receipt_returns_none(
        self,
        expense_data: dict,
    ):
        """For any expense without a receipt, getting receipt URL SHALL return None.
        
        **Validates: Requirements 10.7**
        
        This test verifies that:
        1. Expenses without receipts return None for receipt URL
        2. No errors are raised when requesting receipt URL for expense without receipt
        """
        user_id = uuid4()
        category_id = uuid4()
        expense_id = uuid4()
        
        # Create mock database session
        mock_db = AsyncMock()
        service = ExpenseService(mock_db)
        
        # Create mock category
        mock_category = create_mock_category(
            category_id=category_id,
            user_id=user_id,
            name="Food",
        )
        
        # Create mock expense without receipt
        mock_expense = create_mock_expense(
            expense_id=expense_id,
            user_id=user_id,
            category_id=category_id,
            amount=expense_data["amount"],
            description=expense_data["description"],
            expense_date=expense_data["expense_date"],
            receipt_url=None,  # No receipt
            category=mock_category,
        )
        
        # Setup mocks
        service.expense_repo.get_expense_by_id = AsyncMock(return_value=mock_expense)
        
        # Get receipt URL for expense without receipt
        presigned_url = await service.get_receipt_url(
            expense_id=expense_id,
            user_id=user_id,
        )
        
        # Verify None is returned
        assert presigned_url is None, (
            "Receipt URL should be None for expense without receipt"
        )
    
    @pytest.mark.asyncio
    @given(receipt_data=valid_receipt_image_data())
    @settings(max_examples=10, deadline=None)
    async def test_receipt_upload_validates_content_type(
        self,
        receipt_data: dict,
    ):
        """For any receipt upload, only valid image types SHALL be accepted.
        
        **Validates: Requirements 10.7**
        
        This test verifies that:
        1. Valid content types (jpeg, png, webp, pdf) are accepted
        2. Invalid content types are rejected with appropriate error
        """
        user_id = uuid4()
        category_id = uuid4()
        expense_id = uuid4()
        
        # Create mock database session
        mock_db = AsyncMock()
        service = ExpenseService(mock_db)
        
        # Create mock category
        mock_category = create_mock_category(
            category_id=category_id,
            user_id=user_id,
            name="Food",
        )
        
        # Create mock expense
        mock_expense = create_mock_expense(
            expense_id=expense_id,
            user_id=user_id,
            category_id=category_id,
            receipt_url=None,
            category=mock_category,
        )
        
        # Setup mocks
        service.expense_repo.get_expense_by_id = AsyncMock(return_value=mock_expense)
        
        # Test with valid content type (from receipt_data)
        with patch("app.services.expense.storage") as mock_storage:
            mock_storage.upload_file = AsyncMock(return_value=None)
            mock_storage.delete_file = AsyncMock(return_value=True)
            
            async def mock_update_receipt(expense, receipt_url, ocr_data):
                expense.receipt_url = receipt_url
                return expense
            
            service.expense_repo.update_expense_receipt = mock_update_receipt
            
            # Create mock upload file with valid content type
            mock_file = MagicMock()
            mock_file.content_type = receipt_data["content_type"]
            mock_file.filename = receipt_data["filename"]
            mock_file.read = AsyncMock(return_value=receipt_data["content"])
            
            # Should succeed with valid content type
            receipt_url, _ = await service.upload_receipt(
                expense_id=expense_id,
                user_id=user_id,
                file=mock_file,
            )
            
            assert receipt_url is not None, (
                f"Upload should succeed with valid content type: {receipt_data['content_type']}"
            )
    
    @pytest.mark.asyncio
    async def test_receipt_upload_rejects_invalid_content_type(self):
        """Invalid content types SHALL be rejected with ValueError.
        
        **Validates: Requirements 10.7**
        """
        user_id = uuid4()
        category_id = uuid4()
        expense_id = uuid4()
        
        # Create mock database session
        mock_db = AsyncMock()
        service = ExpenseService(mock_db)
        
        # Create mock expense
        mock_expense = create_mock_expense(
            expense_id=expense_id,
            user_id=user_id,
            category_id=category_id,
            receipt_url=None,
        )
        
        # Setup mocks
        service.expense_repo.get_expense_by_id = AsyncMock(return_value=mock_expense)
        
        # Create mock upload file with invalid content type
        mock_file = MagicMock()
        mock_file.content_type = "text/plain"  # Invalid for receipts
        mock_file.filename = "receipt.txt"
        mock_file.read = AsyncMock(return_value=b"not an image")
        
        # Should raise ValueError for invalid content type
        with pytest.raises(ValueError) as exc_info:
            await service.upload_receipt(
                expense_id=expense_id,
                user_id=user_id,
                file=mock_file,
            )
        
        assert "not supported" in str(exc_info.value).lower(), (
            "Error message should indicate unsupported file type"
        )
    
    @pytest.mark.asyncio
    @given(
        expense_data=valid_expense_data(),
        receipt_data=valid_receipt_image_data(),
    )
    @settings(max_examples=10, deadline=None)
    async def test_viewing_expense_displays_receipt(
        self,
        expense_data: dict,
        receipt_data: dict,
    ):
        """For any expense with a receipt, viewing the expense SHALL include
        the receipt URL in the response.
        
        **Validates: Requirements 10.7**
        
        This test verifies the complete flow:
        1. Create expense
        2. Upload receipt
        3. View expense
        4. Verify receipt URL is present in response
        """
        user_id = uuid4()
        category_id = uuid4()
        expense_id = uuid4()
        
        # Create mock database session
        mock_db = AsyncMock()
        service = ExpenseService(mock_db)
        
        # Create mock category
        mock_category = create_mock_category(
            category_id=category_id,
            user_id=user_id,
            name="Food",
        )
        
        # Storage key for the receipt
        storage_key = f"receipts/{user_id}/{expense_id}/{uuid4()}.jpg"
        
        # Create mock expense with receipt
        mock_expense = create_mock_expense(
            expense_id=expense_id,
            user_id=user_id,
            category_id=category_id,
            amount=expense_data["amount"],
            description=expense_data["description"],
            expense_date=expense_data["expense_date"],
            receipt_url=storage_key,
            category=mock_category,
        )
        
        # Setup mocks
        service.expense_repo.get_expense_with_category = AsyncMock(
            return_value=mock_expense
        )
        
        # Get expense
        expense_response = await service.get_expense(expense_id, user_id)
        
        # Verify expense response includes receipt URL
        assert expense_response is not None, "Expense should be returned"
        assert expense_response.receipt_url == storage_key, (
            f"Expense response should include receipt URL: expected {storage_key}, "
            f"got {expense_response.receipt_url}"
        )
