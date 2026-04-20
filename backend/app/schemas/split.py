"""Pydantic schemas for bill splitting module.

Includes schemas for split groups, members, shared expenses, and settlements.

Validates: Requirements 13.1, 13.2, 13.3, 13.7
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class SplitType(str, Enum):
    """Enum for split types."""
    EQUAL = "equal"
    PERCENTAGE = "percentage"
    EXACT = "exact"


# ============================================================================
# Split Group Member Schemas
# ============================================================================

class SplitGroupMemberCreate(BaseModel):
    """Schema for adding a member to a split group.
    
    Validates: Requirements 13.1
    """
    
    user_id: Optional[UUID] = Field(None, description="ID of registered user (optional)")
    name: str = Field(..., min_length=1, max_length=100, description="Member's display name")
    email: Optional[str] = Field(None, max_length=255, description="Member's email")
    phone: Optional[str] = Field(None, max_length=20, description="Member's phone number")


class SplitGroupMemberResponse(BaseModel):
    """Response schema for a split group member."""
    
    id: UUID
    group_id: UUID
    user_id: Optional[UUID] = None
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


# ============================================================================
# Split Group Schemas
# ============================================================================

class SplitGroupCreate(BaseModel):
    """Schema for creating a split group.
    
    Validates: Requirements 13.1
    """
    
    name: str = Field(..., min_length=1, max_length=100, description="Group name")
    description: Optional[str] = Field(None, max_length=1000, description="Group description")
    members: Optional[List[SplitGroupMemberCreate]] = Field(
        None, 
        description="Initial members to add to the group"
    )


class SplitGroupUpdate(BaseModel):
    """Schema for updating a split group."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Group name")
    description: Optional[str] = Field(None, max_length=1000, description="Group description")


class SplitGroupResponse(BaseModel):
    """Response schema for a split group."""
    
    id: UUID
    created_by: UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class SplitGroupWithMembersResponse(SplitGroupResponse):
    """Response schema for a split group with members."""
    
    members: List[SplitGroupMemberResponse] = []


# ============================================================================
# Expense Split Schemas
# ============================================================================

class ExpenseSplitCreate(BaseModel):
    """Schema for creating an expense split entry."""
    
    member_id: UUID = Field(..., description="ID of the group member")
    amount: Optional[Decimal] = Field(None, ge=0, description="Exact amount for this member")
    percentage: Optional[Decimal] = Field(None, ge=0, le=100, description="Percentage for this member")


class ExpenseSplitResponse(BaseModel):
    """Response schema for an expense split."""
    
    id: UUID
    shared_expense_id: UUID
    member_id: UUID
    amount: Decimal
    is_settled: bool
    created_at: datetime
    updated_at: datetime
    member: Optional[SplitGroupMemberResponse] = None
    
    model_config = {"from_attributes": True}


# ============================================================================
# Shared Expense Schemas
# ============================================================================

class SharedExpenseCreate(BaseModel):
    """Schema for creating a shared expense.
    
    Validates: Requirements 13.2, 13.3
    """
    
    paid_by: UUID = Field(..., description="ID of the member who paid")
    amount: Decimal = Field(..., gt=0, description="Total expense amount")
    description: Optional[str] = Field(None, max_length=1000, description="Expense description")
    expense_date: date = Field(..., description="Date when the expense occurred")
    split_type: SplitType = Field(SplitType.EQUAL, description="Type of split")
    splits: Optional[List[ExpenseSplitCreate]] = Field(
        None,
        description="Individual splits (required for percentage and exact split types)"
    )
    
    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Validate amount is positive and round to 2 decimal places."""
        if v <= 0:
            raise ValueError("Amount must be positive")
        return round(v, 2)
    
    @model_validator(mode="after")
    def validate_splits(self) -> "SharedExpenseCreate":
        """Validate splits based on split type."""
        if self.split_type == SplitType.PERCENTAGE:
            if not self.splits:
                raise ValueError("Splits are required for percentage split type")
            total_percentage = sum(s.percentage or Decimal(0) for s in self.splits)
            if abs(total_percentage - Decimal(100)) > Decimal("0.01"):
                raise ValueError(f"Percentages must sum to 100%, got {total_percentage}%")
        
        elif self.split_type == SplitType.EXACT:
            if not self.splits:
                raise ValueError("Splits are required for exact split type")
            total_amount = sum(s.amount or Decimal(0) for s in self.splits)
            if abs(total_amount - self.amount) > Decimal("0.01"):
                raise ValueError(f"Split amounts must sum to total amount {self.amount}, got {total_amount}")
        
        return self


class SharedExpenseUpdate(BaseModel):
    """Schema for updating a shared expense."""
    
    description: Optional[str] = Field(None, max_length=1000, description="Expense description")
    expense_date: Optional[date] = Field(None, description="Date when the expense occurred")


class SharedExpenseResponse(BaseModel):
    """Response schema for a shared expense."""
    
    id: UUID
    group_id: UUID
    paid_by: UUID
    amount: Decimal
    description: Optional[str] = None
    expense_date: date
    split_type: str
    created_at: datetime
    updated_at: datetime
    paid_by_member: Optional[SplitGroupMemberResponse] = None
    splits: List[ExpenseSplitResponse] = []
    
    model_config = {"from_attributes": True}


# ============================================================================
# Settlement Schemas
# ============================================================================

class SettlementCreate(BaseModel):
    """Schema for creating a settlement.
    
    Validates: Requirements 13.5
    """
    
    from_member: UUID = Field(..., description="ID of the member who is paying")
    to_member: UUID = Field(..., description="ID of the member who is receiving")
    amount: Decimal = Field(..., gt=0, description="Settlement amount")
    settlement_date: date = Field(..., description="Date of settlement")
    
    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Validate amount is positive and round to 2 decimal places."""
        if v <= 0:
            raise ValueError("Amount must be positive")
        return round(v, 2)


class SettlementResponse(BaseModel):
    """Response schema for a settlement."""
    
    id: UUID
    group_id: UUID
    from_member: UUID
    to_member: UUID
    amount: Decimal
    settlement_date: date
    created_at: datetime
    updated_at: datetime
    from_member_rel: Optional[SplitGroupMemberResponse] = None
    to_member_rel: Optional[SplitGroupMemberResponse] = None
    
    model_config = {"from_attributes": True}


# ============================================================================
# Balance Schemas
# ============================================================================

class MemberBalance(BaseModel):
    """Schema for a member's balance in a group.
    
    Validates: Requirements 13.7
    """
    
    member_id: UUID
    member_name: str
    total_paid: Decimal = Field(description="Total amount paid by this member")
    total_owed: Decimal = Field(description="Total amount owed by this member")
    net_balance: Decimal = Field(description="Net balance (positive = owed to, negative = owes)")


class GroupBalancesResponse(BaseModel):
    """Response schema for group balances.
    
    Validates: Requirements 13.7
    """
    
    group_id: UUID
    group_name: str
    balances: List[MemberBalance]
    total_expenses: Decimal
    total_settlements: Decimal


# ============================================================================
# Simplified Debt Schemas
# ============================================================================

class SimplifiedDebt(BaseModel):
    """Schema for a simplified debt transaction.
    
    Validates: Requirements 13.4, 13.6
    """
    
    from_member_id: UUID = Field(description="ID of the member who owes money")
    from_member_name: str = Field(description="Name of the member who owes money")
    to_member_id: UUID = Field(description="ID of the member who is owed money")
    to_member_name: str = Field(description="Name of the member who is owed money")
    amount: Decimal = Field(description="Amount to be paid")
    upi_link: Optional[str] = Field(None, description="UPI deep link for payment")


class SimplifiedDebtsResponse(BaseModel):
    """Response schema for simplified debts.
    
    Validates: Requirements 13.4, 13.6
    """
    
    group_id: UUID
    group_name: str
    debts: List[SimplifiedDebt]
    total_transactions: int = Field(description="Number of transactions needed to settle all debts")
