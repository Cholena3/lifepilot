"""Split service for managing bill splitting.

Provides business logic for split groups, shared expenses, and settlements.

Validates: Requirements 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7
"""

import logging
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.split import (
    SplitGroup,
    SplitGroupMember,
    SharedExpense,
    ExpenseSplit,
    Settlement,
    SplitType,
)
from app.repositories.split import (
    SplitGroupRepository,
    SplitGroupMemberRepository,
    SharedExpenseRepository,
    ExpenseSplitRepository,
    SettlementRepository,
)
from app.schemas.split import (
    SplitGroupCreate,
    SplitGroupUpdate,
    SplitGroupResponse,
    SplitGroupWithMembersResponse,
    SplitGroupMemberCreate,
    SplitGroupMemberResponse,
    SharedExpenseCreate,
    SharedExpenseResponse,
    ExpenseSplitResponse,
    SettlementCreate,
    SettlementResponse,
    MemberBalance,
    GroupBalancesResponse,
    SimplifiedDebt,
    SimplifiedDebtsResponse,
    SplitType as SplitTypeSchema,
)
from app.schemas.document import PaginatedResponse

logger = logging.getLogger(__name__)


class SplitService:
    """Service for managing bill splitting.
    
    Validates: Requirements 13.1, 13.2, 13.3, 13.7
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize the split service.
        
        Args:
            db: Async database session
        """
        self.db = db
        self.group_repo = SplitGroupRepository(db)
        self.member_repo = SplitGroupMemberRepository(db)
        self.expense_repo = SharedExpenseRepository(db)
        self.split_repo = ExpenseSplitRepository(db)
        self.settlement_repo = SettlementRepository(db)
    
    # ========================================================================
    # Split Group Operations
    # ========================================================================
    
    async def create_group(
        self,
        user_id: uuid.UUID,
        data: SplitGroupCreate,
    ) -> SplitGroupWithMembersResponse:
        """Create a new split group.
        
        Validates: Requirements 13.1
        
        Args:
            user_id: User's UUID (creator)
            data: Group creation data
            
        Returns:
            Created group response with members
        """
        # Create the group
        group = await self.group_repo.create_group(user_id, data)
        
        # Add the creator as a member automatically
        creator_member = SplitGroupMemberCreate(
            user_id=user_id,
            name="Me",  # Will be updated with actual name if available
        )
        await self.member_repo.add_member(group.id, creator_member)
        
        # Add initial members if provided
        if data.members:
            for member_data in data.members:
                await self.member_repo.add_member(group.id, member_data)
        
        # Refresh to get all members
        group = await self.group_repo.get_group_by_id(group.id)
        
        logger.info(f"Created split group '{data.name}' for user {user_id}")
        return SplitGroupWithMembersResponse.model_validate(group)
    
    async def get_group(
        self,
        group_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[SplitGroupWithMembersResponse]:
        """Get a split group by ID.
        
        Args:
            group_id: Group's UUID
            user_id: User's UUID for access verification
            
        Returns:
            Group response with members if found, None otherwise
        """
        group = await self.group_repo.get_group_by_id(group_id, user_id)
        if group is None:
            return None
        return SplitGroupWithMembersResponse.model_validate(group)
    
    async def get_groups(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[SplitGroupWithMembersResponse]:
        """Get all split groups for a user.
        
        Validates: Requirements 13.1
        
        Args:
            user_id: User's UUID
            page: Page number (1-indexed)
            page_size: Number of results per page
            
        Returns:
            Paginated response with groups
        """
        offset = (page - 1) * page_size
        
        groups = await self.group_repo.get_groups_for_user(
            user_id=user_id,
            limit=page_size,
            offset=offset,
        )
        
        total = await self.group_repo.count_groups_for_user(user_id)
        
        items = [SplitGroupWithMembersResponse.model_validate(g) for g in groups]
        
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )
    
    async def update_group(
        self,
        group_id: uuid.UUID,
        user_id: uuid.UUID,
        data: SplitGroupUpdate,
    ) -> Optional[SplitGroupWithMembersResponse]:
        """Update a split group.
        
        Args:
            group_id: Group's UUID
            user_id: User's UUID for access verification
            data: Group update data
            
        Returns:
            Updated group response if found, None otherwise
            
        Raises:
            ValueError: If user is not the group creator
        """
        group = await self.group_repo.get_group_by_id(group_id, user_id)
        if group is None:
            return None
        
        # Only creator can update the group
        if group.created_by != user_id:
            raise ValueError("Only the group creator can update the group")
        
        updated = await self.group_repo.update_group(group, data)
        logger.info(f"Updated split group {group_id}")
        return SplitGroupWithMembersResponse.model_validate(updated)
    
    async def delete_group(
        self,
        group_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Delete a split group.
        
        Args:
            group_id: Group's UUID
            user_id: User's UUID for access verification
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            ValueError: If user is not the group creator
        """
        group = await self.group_repo.get_group_by_id(group_id, user_id)
        if group is None:
            return False
        
        # Only creator can delete the group
        if group.created_by != user_id:
            raise ValueError("Only the group creator can delete the group")
        
        await self.group_repo.delete_group(group)
        logger.info(f"Deleted split group {group_id}")
        return True
    
    # ========================================================================
    # Member Operations
    # ========================================================================
    
    async def add_member(
        self,
        group_id: uuid.UUID,
        user_id: uuid.UUID,
        data: SplitGroupMemberCreate,
    ) -> SplitGroupMemberResponse:
        """Add a member to a split group.
        
        Validates: Requirements 13.1
        
        Args:
            group_id: Group's UUID
            user_id: User's UUID for access verification
            data: Member creation data
            
        Returns:
            Created member response
            
        Raises:
            ValueError: If group not found or user not authorized
        """
        group = await self.group_repo.get_group_by_id(group_id, user_id)
        if group is None:
            raise ValueError(f"Group {group_id} not found or not accessible")
        
        member = await self.member_repo.add_member(group_id, data)
        logger.info(f"Added member '{data.name}' to group {group_id}")
        return SplitGroupMemberResponse.model_validate(member)
    
    async def remove_member(
        self,
        group_id: uuid.UUID,
        member_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Remove a member from a split group.
        
        Args:
            group_id: Group's UUID
            member_id: Member's UUID
            user_id: User's UUID for access verification
            
        Returns:
            True if removed, False if not found
            
        Raises:
            ValueError: If member has expenses or user not authorized
        """
        group = await self.group_repo.get_group_by_id(group_id, user_id)
        if group is None:
            raise ValueError(f"Group {group_id} not found or not accessible")
        
        member = await self.member_repo.get_member_by_id(member_id, group_id)
        if member is None:
            return False
        
        # Check if member has expenses
        has_expenses = await self.member_repo.member_has_expenses(member_id)
        if has_expenses:
            raise ValueError("Cannot remove member with existing expenses. Settle all debts first.")
        
        await self.member_repo.delete_member(member)
        logger.info(f"Removed member {member_id} from group {group_id}")
        return True
    
    # ========================================================================
    # Shared Expense Operations
    # ========================================================================
    
    async def add_expense(
        self,
        group_id: uuid.UUID,
        user_id: uuid.UUID,
        data: SharedExpenseCreate,
    ) -> SharedExpenseResponse:
        """Add a shared expense to a group.
        
        Validates: Requirements 13.2, 13.3
        
        Args:
            group_id: Group's UUID
            user_id: User's UUID for access verification
            data: Expense creation data
            
        Returns:
            Created expense response with splits
            
        Raises:
            ValueError: If group not found, payer not a member, or invalid splits
        """
        group = await self.group_repo.get_group_by_id(group_id, user_id)
        if group is None:
            raise ValueError(f"Group {group_id} not found or not accessible")
        
        # Verify payer is a member
        payer = await self.member_repo.get_member_by_id(data.paid_by, group_id)
        if payer is None:
            raise ValueError(f"Payer {data.paid_by} is not a member of this group")
        
        # Create the expense
        expense = await self.expense_repo.create_expense(group_id, data)
        
        # Calculate and create splits
        members = await self.member_repo.get_members_for_group(group_id)
        splits = self._calculate_splits(
            total_amount=data.amount,
            split_type=data.split_type,
            members=members,
            split_data=data.splits,
        )
        
        for member_id, amount in splits.items():
            await self.split_repo.create_split(expense.id, member_id, amount)
        
        # Refresh to get all splits
        expense = await self.expense_repo.get_expense_by_id(expense.id)
        
        logger.info(f"Added shared expense {expense.id} to group {group_id}: {data.amount}")
        return SharedExpenseResponse.model_validate(expense)
    
    def _calculate_splits(
        self,
        total_amount: Decimal,
        split_type: SplitTypeSchema,
        members: List[SplitGroupMember],
        split_data: Optional[List] = None,
    ) -> Dict[uuid.UUID, Decimal]:
        """Calculate individual splits based on split type.
        
        Validates: Requirements 13.2, 13.3
        
        Args:
            total_amount: Total expense amount
            split_type: Type of split (equal, percentage, exact)
            members: List of group members
            split_data: Optional split data for percentage/exact splits
            
        Returns:
            Dictionary mapping member_id to split amount
        """
        splits: Dict[uuid.UUID, Decimal] = {}
        
        if split_type == SplitTypeSchema.EQUAL:
            # Equal split: divide amount equally among all members
            num_members = len(members)
            if num_members == 0:
                return splits
            
            base_amount = (total_amount / Decimal(num_members)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            
            # Handle rounding by giving remainder to first member
            total_split = base_amount * num_members
            remainder = total_amount - total_split
            
            for i, member in enumerate(members):
                if i == 0:
                    splits[member.id] = base_amount + remainder
                else:
                    splits[member.id] = base_amount
        
        elif split_type == SplitTypeSchema.PERCENTAGE:
            # Percentage split: divide by specified percentages
            if not split_data:
                raise ValueError("Split data required for percentage split")
            
            total_split = Decimal(0)
            for split_entry in split_data:
                percentage = split_entry.percentage or Decimal(0)
                amount = (total_amount * percentage / Decimal(100)).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                splits[split_entry.member_id] = amount
                total_split += amount
            
            # Handle rounding remainder
            remainder = total_amount - total_split
            if remainder != 0 and splits:
                first_member = list(splits.keys())[0]
                splits[first_member] += remainder
        
        elif split_type == SplitTypeSchema.EXACT:
            # Exact split: use specified amounts
            if not split_data:
                raise ValueError("Split data required for exact split")
            
            for split_entry in split_data:
                amount = split_entry.amount or Decimal(0)
                splits[split_entry.member_id] = amount.quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
        
        return splits
    
    async def get_expenses(
        self,
        group_id: uuid.UUID,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[SharedExpenseResponse]:
        """Get all shared expenses for a group.
        
        Args:
            group_id: Group's UUID
            user_id: User's UUID for access verification
            page: Page number (1-indexed)
            page_size: Number of results per page
            
        Returns:
            Paginated response with expenses
            
        Raises:
            ValueError: If group not found or user not authorized
        """
        group = await self.group_repo.get_group_by_id(group_id, user_id)
        if group is None:
            raise ValueError(f"Group {group_id} not found or not accessible")
        
        offset = (page - 1) * page_size
        
        expenses = await self.expense_repo.get_expenses_for_group(
            group_id=group_id,
            limit=page_size,
            offset=offset,
        )
        
        total = await self.expense_repo.count_expenses_for_group(group_id)
        
        items = [SharedExpenseResponse.model_validate(e) for e in expenses]
        
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )
    
    async def delete_expense(
        self,
        group_id: uuid.UUID,
        expense_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Delete a shared expense.
        
        Args:
            group_id: Group's UUID
            expense_id: Expense's UUID
            user_id: User's UUID for access verification
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            ValueError: If group not found or user not authorized
        """
        group = await self.group_repo.get_group_by_id(group_id, user_id)
        if group is None:
            raise ValueError(f"Group {group_id} not found or not accessible")
        
        expense = await self.expense_repo.get_expense_by_id(expense_id, group_id)
        if expense is None:
            return False
        
        await self.expense_repo.delete_expense(expense)
        logger.info(f"Deleted shared expense {expense_id} from group {group_id}")
        return True
    
    # ========================================================================
    # Balance Operations
    # ========================================================================
    
    async def get_balances(
        self,
        group_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> GroupBalancesResponse:
        """Get member balances for a group.
        
        Validates: Requirements 13.7
        
        Args:
            group_id: Group's UUID
            user_id: User's UUID for access verification
            
        Returns:
            Group balances response
            
        Raises:
            ValueError: If group not found or user not authorized
        """
        group = await self.group_repo.get_group_by_id(group_id, user_id)
        if group is None:
            raise ValueError(f"Group {group_id} not found or not accessible")
        
        members = await self.member_repo.get_members_for_group(group_id)
        expenses = await self.expense_repo.get_expenses_for_group(group_id, limit=1000, offset=0)
        settlements = await self.settlement_repo.get_settlements_for_group(group_id, limit=1000, offset=0)
        
        # Calculate balances
        balances = self._calculate_balances(members, expenses, settlements)
        
        # Calculate totals
        total_expenses = sum(Decimal(str(e.amount)) for e in expenses)
        total_settlements = sum(Decimal(str(s.amount)) for s in settlements)
        
        return GroupBalancesResponse(
            group_id=group_id,
            group_name=group.name,
            balances=balances,
            total_expenses=total_expenses,
            total_settlements=total_settlements,
        )
    
    def _calculate_balances(
        self,
        members: List[SplitGroupMember],
        expenses: List[SharedExpense],
        settlements: List[Settlement],
    ) -> List[MemberBalance]:
        """Calculate net balances for all members.
        
        Validates: Requirements 13.7
        
        For each member:
        - total_paid: Sum of all expenses they paid for
        - total_owed: Sum of all their splits (what they should pay)
        - net_balance: total_paid - total_owed + settlements_received - settlements_paid
        
        Positive net_balance means others owe them money.
        Negative net_balance means they owe others money.
        
        Args:
            members: List of group members
            expenses: List of shared expenses
            settlements: List of settlements
            
        Returns:
            List of member balances
        """
        balances: Dict[uuid.UUID, Dict] = {}
        
        # Initialize balances for all members
        for member in members:
            balances[member.id] = {
                "member_id": member.id,
                "member_name": member.name,
                "total_paid": Decimal(0),
                "total_owed": Decimal(0),
                "settlements_received": Decimal(0),
                "settlements_paid": Decimal(0),
            }
        
        # Calculate total paid and total owed from expenses
        for expense in expenses:
            # Add to payer's total_paid
            if expense.paid_by in balances:
                balances[expense.paid_by]["total_paid"] += Decimal(str(expense.amount))
            
            # Add splits to each member's total_owed
            for split in expense.splits:
                if split.member_id in balances:
                    balances[split.member_id]["total_owed"] += Decimal(str(split.amount))
        
        # Apply settlements
        for settlement in settlements:
            if settlement.from_member in balances:
                balances[settlement.from_member]["settlements_paid"] += Decimal(str(settlement.amount))
            if settlement.to_member in balances:
                balances[settlement.to_member]["settlements_received"] += Decimal(str(settlement.amount))
        
        # Calculate net balances
        result = []
        for member_id, data in balances.items():
            # Net balance = what they paid - what they owe + settlements received - settlements paid
            net_balance = (
                data["total_paid"] 
                - data["total_owed"] 
                + data["settlements_received"] 
                - data["settlements_paid"]
            )
            
            result.append(MemberBalance(
                member_id=data["member_id"],
                member_name=data["member_name"],
                total_paid=data["total_paid"],
                total_owed=data["total_owed"],
                net_balance=net_balance.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            ))
        
        return result
    
    # ========================================================================
    # Settlement Operations
    # ========================================================================
    
    def generate_upi_link(
        self,
        payee_upi_id: Optional[str],
        payee_name: str,
        amount: Decimal,
        note: str,
    ) -> Optional[str]:
        """Generate a UPI deep link for payment.
        
        Validates: Requirements 13.6
        
        Args:
            payee_upi_id: UPI ID of the payee (e.g., "name@upi")
            payee_name: Name of the payee
            amount: Payment amount
            note: Transaction note/description
            
        Returns:
            UPI deep link string if payee_upi_id is provided, None otherwise
        """
        if not payee_upi_id:
            return None
        
        # URL encode the parameters
        from urllib.parse import quote
        
        # Format: upi://pay?pa={upi_id}&pn={name}&am={amount}&cu=INR&tn={note}
        encoded_name = quote(payee_name)
        encoded_note = quote(note)
        amount_str = str(amount.quantize(Decimal("0.01")))
        
        upi_link = (
            f"upi://pay?"
            f"pa={quote(payee_upi_id)}"
            f"&pn={encoded_name}"
            f"&am={amount_str}"
            f"&cu=INR"
            f"&tn={encoded_note}"
        )
        
        return upi_link
    
    async def simplify_debts(
        self,
        group_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> SimplifiedDebtsResponse:
        """Simplify debts to minimize the number of transactions.
        
        Validates: Requirements 13.4, 13.6
        
        Uses a greedy algorithm to match debtors with creditors:
        1. Calculate net balance for each member
        2. Members with negative balance owe money (debtors)
        3. Members with positive balance are owed money (creditors)
        4. Match largest debtor with largest creditor iteratively
        
        Args:
            group_id: Group's UUID
            user_id: User's UUID for access verification
            
        Returns:
            Simplified debts response with UPI links
            
        Raises:
            ValueError: If group not found or user not authorized
        """
        group = await self.group_repo.get_group_by_id(group_id, user_id)
        if group is None:
            raise ValueError(f"Group {group_id} not found or not accessible")
        
        # Get current balances
        balances_response = await self.get_balances(group_id, user_id)
        
        # Build member info map for UPI links and names
        members = await self.member_repo.get_members_for_group(group_id)
        member_info: Dict[uuid.UUID, Dict] = {}
        for member in members:
            member_info[member.id] = {
                "name": member.name,
                "email": member.email,
                "phone": member.phone,
            }
        
        # Separate debtors (negative balance) and creditors (positive balance)
        debtors: List[Dict] = []  # Members who owe money
        creditors: List[Dict] = []  # Members who are owed money
        
        for balance in balances_response.balances:
            if balance.net_balance < 0:
                # This member owes money (negative balance means they owe)
                debtors.append({
                    "member_id": balance.member_id,
                    "member_name": balance.member_name,
                    "amount": abs(balance.net_balance),  # Convert to positive
                })
            elif balance.net_balance > 0:
                # This member is owed money
                creditors.append({
                    "member_id": balance.member_id,
                    "member_name": balance.member_name,
                    "amount": balance.net_balance,
                })
        
        # Simplify debts using greedy algorithm
        simplified_debts = self._simplify_debts_greedy(
            debtors=debtors,
            creditors=creditors,
            member_info=member_info,
            group_name=group.name,
        )
        
        logger.info(f"Simplified debts for group {group_id}: {len(simplified_debts)} transactions")
        
        return SimplifiedDebtsResponse(
            group_id=group_id,
            group_name=group.name,
            debts=simplified_debts,
            total_transactions=len(simplified_debts),
        )
    
    def _simplify_debts_greedy(
        self,
        debtors: List[Dict],
        creditors: List[Dict],
        member_info: Dict[uuid.UUID, Dict],
        group_name: str,
    ) -> List[SimplifiedDebt]:
        """Simplify debts using a greedy algorithm.
        
        Validates: Requirements 13.4
        
        Algorithm:
        1. Sort debtors by amount (descending)
        2. Sort creditors by amount (descending)
        3. Match largest debtor with largest creditor
        4. Create a transaction for the minimum of the two amounts
        5. Update remaining amounts and repeat
        
        Args:
            debtors: List of members who owe money with amounts
            creditors: List of members who are owed money with amounts
            member_info: Dictionary mapping member_id to member details
            group_name: Name of the group for UPI note
            
        Returns:
            List of simplified debt transactions
        """
        simplified: List[SimplifiedDebt] = []
        
        # Make copies to avoid modifying original lists
        debtors = [d.copy() for d in debtors]
        creditors = [c.copy() for c in creditors]
        
        # Sort by amount descending for greedy matching
        debtors.sort(key=lambda x: x["amount"], reverse=True)
        creditors.sort(key=lambda x: x["amount"], reverse=True)
        
        debtor_idx = 0
        creditor_idx = 0
        
        while debtor_idx < len(debtors) and creditor_idx < len(creditors):
            debtor = debtors[debtor_idx]
            creditor = creditors[creditor_idx]
            
            # Skip if amounts are effectively zero (floating point tolerance)
            if debtor["amount"] < Decimal("0.01"):
                debtor_idx += 1
                continue
            if creditor["amount"] < Decimal("0.01"):
                creditor_idx += 1
                continue
            
            # Calculate transaction amount (minimum of what debtor owes and creditor is owed)
            transaction_amount = min(debtor["amount"], creditor["amount"])
            
            # Round to 2 decimal places
            transaction_amount = transaction_amount.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            
            if transaction_amount >= Decimal("0.01"):
                # Get creditor's contact info for UPI link
                creditor_info = member_info.get(creditor["member_id"], {})
                
                # Generate UPI link (use email as UPI ID if available, or phone)
                # In a real app, members would have a dedicated UPI ID field
                upi_id = creditor_info.get("email") or creditor_info.get("phone")
                upi_link = self.generate_upi_link(
                    payee_upi_id=upi_id,
                    payee_name=creditor["member_name"],
                    amount=transaction_amount,
                    note=f"Settlement for {group_name}",
                )
                
                simplified.append(SimplifiedDebt(
                    from_member_id=debtor["member_id"],
                    from_member_name=debtor["member_name"],
                    to_member_id=creditor["member_id"],
                    to_member_name=creditor["member_name"],
                    amount=transaction_amount,
                    upi_link=upi_link,
                ))
            
            # Update remaining amounts
            debtor["amount"] -= transaction_amount
            creditor["amount"] -= transaction_amount
            
            # Move to next debtor/creditor if fully settled
            if debtor["amount"] < Decimal("0.01"):
                debtor_idx += 1
            if creditor["amount"] < Decimal("0.01"):
                creditor_idx += 1
        
        return simplified
    
    async def create_settlement(
        self,
        group_id: uuid.UUID,
        user_id: uuid.UUID,
        data: SettlementCreate,
    ) -> SettlementResponse:
        """Create a settlement between members.
        
        Validates: Requirements 13.5
        
        Args:
            group_id: Group's UUID
            user_id: User's UUID for access verification
            data: Settlement creation data
            
        Returns:
            Created settlement response
            
        Raises:
            ValueError: If group not found, members not valid, or user not authorized
        """
        group = await self.group_repo.get_group_by_id(group_id, user_id)
        if group is None:
            raise ValueError(f"Group {group_id} not found or not accessible")
        
        # Verify both members exist in the group
        from_member = await self.member_repo.get_member_by_id(data.from_member, group_id)
        if from_member is None:
            raise ValueError(f"From member {data.from_member} is not a member of this group")
        
        to_member = await self.member_repo.get_member_by_id(data.to_member, group_id)
        if to_member is None:
            raise ValueError(f"To member {data.to_member} is not a member of this group")
        
        if data.from_member == data.to_member:
            raise ValueError("Cannot settle with yourself")
        
        settlement = await self.settlement_repo.create_settlement(group_id, data)
        
        # Refresh to get member details
        settlement = await self.settlement_repo.get_settlement_by_id(settlement.id)
        
        logger.info(f"Created settlement {settlement.id} in group {group_id}: {data.amount}")
        return SettlementResponse.model_validate(settlement)
    
    async def get_settlements(
        self,
        group_id: uuid.UUID,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[SettlementResponse]:
        """Get all settlements for a group.
        
        Args:
            group_id: Group's UUID
            user_id: User's UUID for access verification
            page: Page number (1-indexed)
            page_size: Number of results per page
            
        Returns:
            Paginated response with settlements
            
        Raises:
            ValueError: If group not found or user not authorized
        """
        group = await self.group_repo.get_group_by_id(group_id, user_id)
        if group is None:
            raise ValueError(f"Group {group_id} not found or not accessible")
        
        offset = (page - 1) * page_size
        
        settlements = await self.settlement_repo.get_settlements_for_group(
            group_id=group_id,
            limit=page_size,
            offset=offset,
        )
        
        # Count total (we don't have a count method, so use len for now)
        all_settlements = await self.settlement_repo.get_settlements_for_group(
            group_id=group_id,
            limit=10000,
            offset=0,
        )
        total = len(all_settlements)
        
        items = [SettlementResponse.model_validate(s) for s in settlements]
        
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )
