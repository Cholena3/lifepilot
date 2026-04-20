"""Pydantic schemas for expense module.

Includes schemas for expense and category CRUD operations.

Validates: Requirements 10.1, 10.4, 10.5, 10.6
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Expense Category Schemas
# ============================================================================

class ExpenseCategoryCreate(BaseModel):
    """Schema for creating a new expense category.
    
    Validates: Requirements 10.4
    """
    
    name: str = Field(..., min_length=1, max_length=100, description="Category name")
    icon: Optional[str] = Field(None, max_length=50, description="Icon identifier")
    color: Optional[str] = Field(None, max_length=7, description="Hex color code (e.g., #FF5733)")
    
    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        """Validate hex color format."""
        if v is not None:
            if not v.startswith("#") or len(v) != 7:
                raise ValueError("Color must be a valid hex code (e.g., #FF5733)")
            try:
                int(v[1:], 16)
            except ValueError:
                raise ValueError("Color must be a valid hex code (e.g., #FF5733)")
        return v


class ExpenseCategoryUpdate(BaseModel):
    """Schema for updating an expense category.
    
    Validates: Requirements 10.4
    """
    
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Category name")
    icon: Optional[str] = Field(None, max_length=50, description="Icon identifier")
    color: Optional[str] = Field(None, max_length=7, description="Hex color code")
    
    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        """Validate hex color format."""
        if v is not None:
            if not v.startswith("#") or len(v) != 7:
                raise ValueError("Color must be a valid hex code (e.g., #FF5733)")
            try:
                int(v[1:], 16)
            except ValueError:
                raise ValueError("Color must be a valid hex code (e.g., #FF5733)")
        return v


class ExpenseCategoryResponse(BaseModel):
    """Response schema for expense category.
    
    Validates: Requirements 10.4
    """
    
    id: UUID
    user_id: Optional[UUID] = None
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None
    is_default: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


# ============================================================================
# Expense Schemas
# ============================================================================

class ExpenseCreate(BaseModel):
    """Schema for creating a new expense.
    
    Validates: Requirements 10.1
    """
    
    category_id: UUID = Field(..., description="ID of the expense category")
    amount: Decimal = Field(..., gt=0, description="Expense amount (must be positive)")
    description: Optional[str] = Field(None, max_length=1000, description="Expense description")
    expense_date: date = Field(..., description="Date when the expense occurred")
    
    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Validate amount is positive and round to 2 decimal places."""
        if v <= 0:
            raise ValueError("Amount must be positive")
        # Round to 2 decimal places
        return round(v, 2)


class ExpenseUpdate(BaseModel):
    """Schema for updating an expense.
    
    Validates: Requirements 10.5
    """
    
    category_id: Optional[UUID] = Field(None, description="ID of the expense category")
    amount: Optional[Decimal] = Field(None, gt=0, description="Expense amount")
    description: Optional[str] = Field(None, max_length=1000, description="Expense description")
    expense_date: Optional[date] = Field(None, description="Date when the expense occurred")
    
    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """Validate amount is positive and round to 2 decimal places."""
        if v is not None:
            if v <= 0:
                raise ValueError("Amount must be positive")
            return round(v, 2)
        return v


class ExpenseResponse(BaseModel):
    """Response schema for an expense.
    
    Validates: Requirements 10.1
    """
    
    id: UUID
    user_id: UUID
    category_id: UUID
    amount: Decimal
    description: Optional[str] = None
    expense_date: date
    receipt_url: Optional[str] = None
    ocr_data: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class ExpenseWithCategoryResponse(ExpenseResponse):
    """Response schema for an expense with category details."""
    
    category: ExpenseCategoryResponse


class ExpenseListFilters(BaseModel):
    """Schema for expense list filters."""
    
    category_id: Optional[UUID] = Field(None, description="Filter by category ID")
    start_date: Optional[date] = Field(None, description="Filter expenses from this date")
    end_date: Optional[date] = Field(None, description="Filter expenses until this date")
    min_amount: Optional[Decimal] = Field(None, ge=0, description="Minimum expense amount")
    max_amount: Optional[Decimal] = Field(None, ge=0, description="Maximum expense amount")
    
    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v: Optional[date], info) -> Optional[date]:
        """Validate that end_date is not before start_date."""
        if v is not None and info.data.get("start_date") is not None:
            if v < info.data["start_date"]:
                raise ValueError("end_date must not be before start_date")
        return v


# ============================================================================
# Receipt Upload Schema
# ============================================================================

class ReceiptUploadResponse(BaseModel):
    """Response schema for receipt upload."""
    
    expense_id: UUID
    receipt_url: str
    ocr_data: Optional[dict] = None
    message: str = "Receipt uploaded successfully"
