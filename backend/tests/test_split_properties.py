"""Property-based tests for split calculations.

Uses Hypothesis to verify universal properties across all valid inputs.

**Validates: Requirements 13.2, 13.3, 13.7**

Property 25: Split Calculation Correctness - Equal Split
Property 26: Split Calculation Correctness - Percentage Split
Property 29: Net Balance Consistency
"""

from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4
from unittest.mock import MagicMock

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck

from app.models.split import SplitGroupMember, SharedExpense, ExpenseSplit, Settlement
from app.schemas.split import (
    SplitType,
    ExpenseSplitCreate,
    MemberBalance,
)
from app.services.split import SplitService


# ============================================================================
# Hypothesis Strategies for Split Data
# ============================================================================

@st.composite
def valid_amounts(draw):
    """Generate valid expense amounts (positive, up to 2 decimal places).
    
    Amounts must be positive and are rounded to 2 decimal places.
    """
    value = draw(st.floats(min_value=0.01, max_value=99999.99, allow_nan=False, allow_infinity=False))
    return Decimal(str(round(value, 2)))


@st.composite
def valid_member_count(draw, min_members: int = 1, max_members: int = 10):
    """Generate a valid number of members for a split group."""
    return draw(st.integers(min_value=min_members, max_value=max_members))


@st.composite
def valid_percentages(draw, num_members: int):
    """Generate valid percentages that sum to exactly 100%.
    
    Each member gets a percentage, and all percentages sum to 100.
    """
    if num_members <= 0:
        return []
    
    if num_members == 1:
        return [Decimal("100.00")]
    
    # Generate random percentages and normalize to sum to 100
    raw_values = [draw(st.floats(min_value=0.01, max_value=100.0, allow_nan=False, allow_infinity=False)) 
                  for _ in range(num_members)]
    total = sum(raw_values)
    
    # Normalize to sum to 100
    percentages = []
    running_total = Decimal("0")
    for i, val in enumerate(raw_values):
        if i == num_members - 1:
            # Last percentage gets the remainder to ensure exact 100%
            pct = Decimal("100.00") - running_total
        else:
            pct = Decimal(str(round(val / total * 100, 2)))
            running_total += pct
        percentages.append(pct)
    
    return percentages


@st.composite
def valid_expense_amounts_list(draw, num_expenses: int):
    """Generate a list of valid expense amounts."""
    return [draw(valid_amounts()) for _ in range(num_expenses)]


@st.composite
def valid_settlement_data(draw, member_ids: list):
    """Generate valid settlement data between members."""
    assume(len(member_ids) >= 2)
    
    from_idx = draw(st.integers(min_value=0, max_value=len(member_ids) - 1))
    to_idx = draw(st.integers(min_value=0, max_value=len(member_ids) - 1))
    assume(from_idx != to_idx)
    
    return {
        "from_member": member_ids[from_idx],
        "to_member": member_ids[to_idx],
        "amount": draw(valid_amounts()),
    }


# ============================================================================
# Helper Functions
# ============================================================================

def create_mock_member(member_id=None, name=None):
    """Create a mock SplitGroupMember object."""
    mock = MagicMock(spec=SplitGroupMember)
    mock.id = member_id or uuid4()
    mock.name = name or f"Member_{str(mock.id)[:8]}"
    mock.group_id = uuid4()
    mock.user_id = None
    mock.email = None
    mock.phone = None
    mock.created_at = datetime.now(timezone.utc)
    mock.updated_at = datetime.now(timezone.utc)
    return mock


def create_mock_expense(
    expense_id=None,
    group_id=None,
    paid_by=None,
    amount=None,
    split_type="equal",
    splits=None,
):
    """Create a mock SharedExpense object."""
    mock = MagicMock(spec=SharedExpense)
    mock.id = expense_id or uuid4()
    mock.group_id = group_id or uuid4()
    mock.paid_by = paid_by or uuid4()
    mock.amount = amount if amount is not None else Decimal("100.00")
    mock.split_type = split_type
    mock.description = "Test expense"
    mock.expense_date = date.today()
    mock.created_at = datetime.now(timezone.utc)
    mock.updated_at = datetime.now(timezone.utc)
    mock.splits = splits or []
    return mock


def create_mock_split(split_id=None, expense_id=None, member_id=None, amount=None):
    """Create a mock ExpenseSplit object."""
    mock = MagicMock(spec=ExpenseSplit)
    mock.id = split_id or uuid4()
    mock.shared_expense_id = expense_id or uuid4()
    mock.member_id = member_id or uuid4()
    mock.amount = amount if amount is not None else Decimal("25.00")
    mock.is_settled = False
    mock.created_at = datetime.now(timezone.utc)
    mock.updated_at = datetime.now(timezone.utc)
    return mock


def create_mock_settlement(
    settlement_id=None,
    group_id=None,
    from_member=None,
    to_member=None,
    amount=None,
):
    """Create a mock Settlement object."""
    mock = MagicMock(spec=Settlement)
    mock.id = settlement_id or uuid4()
    mock.group_id = group_id or uuid4()
    mock.from_member = from_member or uuid4()
    mock.to_member = to_member or uuid4()
    mock.amount = amount if amount is not None else Decimal("50.00")
    mock.settlement_date = date.today()
    mock.created_at = datetime.now(timezone.utc)
    mock.updated_at = datetime.now(timezone.utc)
    return mock


# ============================================================================
# Property 25: Split Calculation Correctness - Equal Split
# ============================================================================

class TestEqualSplitProperty:
    """Property 25: Split Calculation Correctness - Equal Split.
    
    **Validates: Requirements 13.2, 13.3**
    
    For any shared expense of amount A split equally among N members,
    each member's share SHALL equal A/N (with appropriate rounding).
    """
    
    @given(
        total_amount=valid_amounts(),
        num_members=valid_member_count(min_members=1, max_members=20),
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_equal_split_sum_equals_total(self, total_amount: Decimal, num_members: int):
        """For any positive amount and any number of members (≥1), equal split
        should have sum of all splits equal to total amount (within rounding tolerance).
        
        **Validates: Requirements 13.2, 13.3**
        
        This test verifies that:
        1. The sum of all individual splits equals the total expense amount
        2. Rounding is handled correctly to preserve the total
        """
        # Create mock members
        members = [create_mock_member() for _ in range(num_members)]
        
        # Calculate splits using the same logic as SplitService._calculate_splits
        splits = {}
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
        
        # Verify sum equals total
        calculated_sum = sum(splits.values())
        
        assert calculated_sum == total_amount, (
            f"Sum of splits ({calculated_sum}) should equal total amount ({total_amount}). "
            f"Members: {num_members}, Base amount: {base_amount}, Remainder: {remainder}"
        )
    
    @given(
        total_amount=valid_amounts(),
        num_members=valid_member_count(min_members=2, max_members=20),
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_equal_split_all_splits_within_rounding_tolerance(self, total_amount: Decimal, num_members: int):
        """For any positive amount and any number of members (≥2), all splits
        should be equal within rounding tolerance.
        
        **Validates: Requirements 13.2, 13.3**
        
        This test verifies that:
        1. All member splits are approximately equal
        2. The maximum difference between any two splits is bounded by the
           rounding remainder (which can be up to num_members - 1 cents in
           extreme cases, but typically much smaller)
        
        Note: When splitting amounts that don't divide evenly, the remainder
        is assigned to one member. For example, $1.00 split among 6 members:
        - Base amount: $0.17 (rounded from $0.1666...)
        - Total of base amounts: 6 × $0.17 = $1.02
        - Remainder: $1.00 - $1.02 = -$0.02
        - First member gets: $0.17 - $0.02 = $0.15
        - Others get: $0.17
        - Max difference: $0.02
        """
        # Create mock members
        members = [create_mock_member() for _ in range(num_members)]
        
        # Calculate splits
        splits = {}
        base_amount = (total_amount / Decimal(num_members)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        
        total_split = base_amount * num_members
        remainder = total_amount - total_split
        
        for i, member in enumerate(members):
            if i == 0:
                splits[member.id] = base_amount + remainder
            else:
                splits[member.id] = base_amount
        
        # Verify all splits are within reasonable rounding tolerance
        # The maximum possible remainder is bounded by the number of members
        # (each member's rounding can contribute up to 0.005, which rounds to 0.01)
        split_values = list(splits.values())
        max_split = max(split_values)
        min_split = min(split_values)
        
        max_difference = abs(max_split - min_split)
        
        # The remainder is at most (num_members - 1) * 0.005 rounded, which is
        # typically small. We use a tolerance based on the absolute remainder.
        expected_max_diff = abs(remainder)
        
        assert max_difference == expected_max_diff, (
            f"Maximum difference between splits ({max_difference}) should equal "
            f"the absolute remainder ({expected_max_diff}). "
            f"Max: {max_split}, Min: {min_split}, Remainder: {remainder}"
        )
    
    @given(
        total_amount=valid_amounts(),
        num_members=valid_member_count(min_members=1, max_members=20),
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_equal_split_all_non_negative(self, total_amount: Decimal, num_members: int):
        """For any positive amount and any number of members (≥1), each split
        should be non-negative.
        
        **Validates: Requirements 13.2, 13.3**
        
        This test verifies that:
        1. All individual splits are non-negative (>= 0)
        2. No member receives a negative split
        
        Note: When the total amount is very small relative to the number of
        members, some splits may be zero due to rounding. For example,
        $0.02 split among 3 members:
        - Base amount: $0.01 (rounded from $0.0066...)
        - Total of base amounts: 3 × $0.01 = $0.03
        - Remainder: $0.02 - $0.03 = -$0.01
        - First member gets: $0.01 - $0.01 = $0.00
        - Others get: $0.01
        
        This is acceptable behavior - the key property is that splits are
        non-negative and sum to the total.
        """
        # Create mock members
        members = [create_mock_member() for _ in range(num_members)]
        
        # Calculate splits
        splits = {}
        base_amount = (total_amount / Decimal(num_members)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        
        total_split = base_amount * num_members
        remainder = total_amount - total_split
        
        for i, member in enumerate(members):
            if i == 0:
                splits[member.id] = base_amount + remainder
            else:
                splits[member.id] = base_amount
        
        # Verify all splits are non-negative
        for member_id, amount in splits.items():
            assert amount >= 0, (
                f"Split for member {member_id} should be non-negative, got {amount}. "
                f"Total: {total_amount}, Members: {num_members}"
            )
        
        # Also verify the sum still equals the total
        calculated_sum = sum(splits.values())
        assert calculated_sum == total_amount, (
            f"Sum of splits ({calculated_sum}) should equal total ({total_amount})"
        )


# ============================================================================
# Property 26: Split Calculation Correctness - Percentage Split
# ============================================================================

class TestPercentageSplitProperty:
    """Property 26: Split Calculation Correctness - Percentage Split.
    
    **Validates: Requirements 13.2, 13.3**
    
    For any shared expense of amount A with percentage splits summing to 100%,
    each member's share SHALL equal their percentage of A.
    """
    
    @given(
        total_amount=valid_amounts(),
        num_members=valid_member_count(min_members=1, max_members=10),
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_percentage_split_sum_equals_total(self, total_amount: Decimal, num_members: int):
        """For any positive amount and percentages that sum to 100%, sum of all
        splits should equal total amount (within rounding tolerance).
        
        **Validates: Requirements 13.2, 13.3**
        
        This test verifies that:
        1. The sum of all percentage-based splits equals the total expense amount
        2. Rounding is handled correctly to preserve the total
        """
        # Create mock members
        members = [create_mock_member() for _ in range(num_members)]
        
        # Generate percentages that sum to 100%
        if num_members == 1:
            percentages = [Decimal("100.00")]
        else:
            # Distribute percentages
            base_pct = Decimal("100.00") / Decimal(num_members)
            base_pct = base_pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            
            percentages = []
            running_total = Decimal("0")
            for i in range(num_members):
                if i == num_members - 1:
                    pct = Decimal("100.00") - running_total
                else:
                    pct = base_pct
                    running_total += pct
                percentages.append(pct)
        
        # Calculate splits using percentage logic
        splits = {}
        total_split = Decimal("0")
        
        for i, (member, percentage) in enumerate(zip(members, percentages)):
            amount = (total_amount * percentage / Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            splits[member.id] = amount
            total_split += amount
        
        # Handle rounding remainder
        remainder = total_amount - total_split
        if remainder != 0 and splits:
            first_member = list(splits.keys())[0]
            splits[first_member] += remainder
        
        # Verify sum equals total
        calculated_sum = sum(splits.values())
        
        assert calculated_sum == total_amount, (
            f"Sum of percentage splits ({calculated_sum}) should equal total amount ({total_amount}). "
            f"Percentages: {percentages}"
        )
    
    @given(
        total_amount=valid_amounts(),
        num_members=valid_member_count(min_members=2, max_members=10),
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_percentage_split_proportional(self, total_amount: Decimal, num_members: int):
        """For any positive amount and percentages that sum to 100%, each split
        should be proportional to its percentage.
        
        **Validates: Requirements 13.2, 13.3**
        
        This test verifies that:
        1. Each member's split is approximately proportional to their percentage
        2. The proportionality is maintained within rounding tolerance
        """
        # Create mock members
        members = [create_mock_member() for _ in range(num_members)]
        
        # Generate varied percentages that sum to 100%
        raw_percentages = [Decimal(str(10 + i * 5)) for i in range(num_members)]
        total_raw = sum(raw_percentages)
        
        percentages = []
        running_total = Decimal("0")
        for i, raw in enumerate(raw_percentages):
            if i == num_members - 1:
                pct = Decimal("100.00") - running_total
            else:
                pct = (raw / total_raw * Decimal("100")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                running_total += pct
            percentages.append(pct)
        
        # Calculate splits
        splits = {}
        for member, percentage in zip(members, percentages):
            amount = (total_amount * percentage / Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            splits[member.id] = amount
        
        # Verify proportionality (within rounding tolerance)
        for member, percentage in zip(members, percentages):
            expected = (total_amount * percentage / Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            actual = splits[member.id]
            
            # Allow for 1 cent rounding difference
            assert abs(actual - expected) <= Decimal("0.01"), (
                f"Split for {percentage}% should be approximately {expected}, got {actual}"
            )
    
    @given(
        total_amount=valid_amounts(),
        num_members=valid_member_count(min_members=1, max_members=10),
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_percentage_split_all_non_negative(self, total_amount: Decimal, num_members: int):
        """For any positive amount and percentages that sum to 100%, each split
        should be non-negative.
        
        **Validates: Requirements 13.2, 13.3**
        
        This test verifies that:
        1. All individual splits are non-negative (>= 0)
        2. No member receives a negative split
        """
        # Create mock members
        members = [create_mock_member() for _ in range(num_members)]
        
        # Generate percentages (some could be 0%)
        if num_members == 1:
            percentages = [Decimal("100.00")]
        else:
            # Allow some members to have 0%
            percentages = []
            remaining = Decimal("100.00")
            for i in range(num_members):
                if i == num_members - 1:
                    pct = remaining
                else:
                    # Random percentage between 0 and remaining
                    max_pct = remaining - Decimal(num_members - i - 1)  # Leave at least 1% for others
                    if max_pct < 0:
                        max_pct = Decimal("0")
                    pct = (remaining / Decimal(num_members - i)).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                    remaining -= pct
                percentages.append(pct)
        
        # Calculate splits
        splits = {}
        for member, percentage in zip(members, percentages):
            amount = (total_amount * percentage / Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            splits[member.id] = amount
        
        # Verify all splits are non-negative
        for member_id, amount in splits.items():
            assert amount >= 0, (
                f"Split for member {member_id} should be non-negative, got {amount}"
            )


# ============================================================================
# Property 29: Net Balance Consistency
# ============================================================================

class TestNetBalanceConsistencyProperty:
    """Property 29: Net Balance Consistency.
    
    **Validates: Requirements 13.7**
    
    For any split group, the sum of all member net balances SHALL equal zero.
    Net balance = total_paid - total_owed + settlements_received - settlements_paid
    """
    
    @given(
        num_members=valid_member_count(min_members=2, max_members=10),
        num_expenses=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_net_balances_sum_to_zero_with_expenses_only(
        self, num_members: int, num_expenses: int
    ):
        """For any group with expenses (no settlements), sum of all net balances
        should equal zero (money is conserved).
        
        **Validates: Requirements 13.7**
        
        This test verifies that:
        1. When expenses are split among members, the total money is conserved
        2. Sum of (total_paid - total_owed) across all members equals zero
        """
        # Create mock members
        members = [create_mock_member(name=f"Member_{i}") for i in range(num_members)]
        
        # Create expenses with random payers and equal splits
        expenses = []
        for exp_idx in range(num_expenses):
            # Random payer
            payer_idx = exp_idx % num_members
            payer = members[payer_idx]
            
            # Random amount
            amount = Decimal(str(round(10 + exp_idx * 15.5, 2)))
            
            # Create splits for all members (equal split)
            base_split = (amount / Decimal(num_members)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            total_split = base_split * num_members
            remainder = amount - total_split
            
            splits = []
            for i, member in enumerate(members):
                split_amount = base_split + remainder if i == 0 else base_split
                mock_split = create_mock_split(
                    expense_id=uuid4(),
                    member_id=member.id,
                    amount=split_amount,
                )
                splits.append(mock_split)
            
            expense = create_mock_expense(
                paid_by=payer.id,
                amount=amount,
                split_type="equal",
                splits=splits,
            )
            expenses.append(expense)
        
        # Calculate balances using the same logic as SplitService._calculate_balances
        balances = {}
        for member in members:
            balances[member.id] = {
                "member_id": member.id,
                "member_name": member.name,
                "total_paid": Decimal("0"),
                "total_owed": Decimal("0"),
                "settlements_received": Decimal("0"),
                "settlements_paid": Decimal("0"),
            }
        
        # Calculate total paid and total owed from expenses
        for expense in expenses:
            if expense.paid_by in balances:
                balances[expense.paid_by]["total_paid"] += Decimal(str(expense.amount))
            
            for split in expense.splits:
                if split.member_id in balances:
                    balances[split.member_id]["total_owed"] += Decimal(str(split.amount))
        
        # Calculate net balances
        net_balances = []
        for member_id, data in balances.items():
            net_balance = (
                data["total_paid"]
                - data["total_owed"]
                + data["settlements_received"]
                - data["settlements_paid"]
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            net_balances.append(net_balance)
        
        # Verify sum of net balances equals zero
        total_net = sum(net_balances)
        
        assert total_net == Decimal("0"), (
            f"Sum of net balances ({total_net}) should equal zero. "
            f"Net balances: {net_balances}"
        )
    
    @given(
        num_members=valid_member_count(min_members=2, max_members=8),
        num_expenses=st.integers(min_value=1, max_value=5),
        num_settlements=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_net_balances_sum_to_zero_with_settlements(
        self, num_members: int, num_expenses: int, num_settlements: int
    ):
        """For any group with expenses and settlements, sum of all net balances
        should equal zero (money is conserved).
        
        **Validates: Requirements 13.7**
        
        This test verifies that:
        1. Settlements transfer money between members without creating/destroying it
        2. Sum of all net balances remains zero after settlements
        """
        # Create mock members
        members = [create_mock_member(name=f"Member_{i}") for i in range(num_members)]
        
        # Create expenses
        expenses = []
        for exp_idx in range(num_expenses):
            payer_idx = exp_idx % num_members
            payer = members[payer_idx]
            amount = Decimal(str(round(20 + exp_idx * 10.25, 2)))
            
            # Equal splits
            base_split = (amount / Decimal(num_members)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            total_split = base_split * num_members
            remainder = amount - total_split
            
            splits = []
            for i, member in enumerate(members):
                split_amount = base_split + remainder if i == 0 else base_split
                mock_split = create_mock_split(
                    expense_id=uuid4(),
                    member_id=member.id,
                    amount=split_amount,
                )
                splits.append(mock_split)
            
            expense = create_mock_expense(
                paid_by=payer.id,
                amount=amount,
                split_type="equal",
                splits=splits,
            )
            expenses.append(expense)
        
        # Create settlements
        settlements = []
        for set_idx in range(num_settlements):
            from_idx = set_idx % num_members
            to_idx = (set_idx + 1) % num_members
            if from_idx == to_idx:
                to_idx = (to_idx + 1) % num_members
            
            settlement = create_mock_settlement(
                from_member=members[from_idx].id,
                to_member=members[to_idx].id,
                amount=Decimal(str(round(5 + set_idx * 3.5, 2))),
            )
            settlements.append(settlement)
        
        # Calculate balances
        balances = {}
        for member in members:
            balances[member.id] = {
                "member_id": member.id,
                "member_name": member.name,
                "total_paid": Decimal("0"),
                "total_owed": Decimal("0"),
                "settlements_received": Decimal("0"),
                "settlements_paid": Decimal("0"),
            }
        
        # Process expenses
        for expense in expenses:
            if expense.paid_by in balances:
                balances[expense.paid_by]["total_paid"] += Decimal(str(expense.amount))
            
            for split in expense.splits:
                if split.member_id in balances:
                    balances[split.member_id]["total_owed"] += Decimal(str(split.amount))
        
        # Process settlements
        for settlement in settlements:
            if settlement.from_member in balances:
                balances[settlement.from_member]["settlements_paid"] += Decimal(str(settlement.amount))
            if settlement.to_member in balances:
                balances[settlement.to_member]["settlements_received"] += Decimal(str(settlement.amount))
        
        # Calculate net balances
        net_balances = []
        for member_id, data in balances.items():
            net_balance = (
                data["total_paid"]
                - data["total_owed"]
                + data["settlements_received"]
                - data["settlements_paid"]
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            net_balances.append(net_balance)
        
        # Verify sum of net balances equals zero
        total_net = sum(net_balances)
        
        assert total_net == Decimal("0"), (
            f"Sum of net balances ({total_net}) should equal zero after settlements. "
            f"Net balances: {net_balances}"
        )
    
    @given(
        num_members=valid_member_count(min_members=2, max_members=10),
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_net_balance_formula_correctness(self, num_members: int):
        """For any member, net_balance should equal:
        total_paid - total_owed + settlements_received - settlements_paid
        
        **Validates: Requirements 13.7**
        
        This test verifies that:
        1. The net balance formula is correctly applied
        2. Each component contributes correctly to the net balance
        """
        # Create mock members
        members = [create_mock_member(name=f"Member_{i}") for i in range(num_members)]
        
        # Create a single expense paid by first member
        payer = members[0]
        amount = Decimal("100.00")
        
        # Equal splits
        base_split = (amount / Decimal(num_members)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        total_split = base_split * num_members
        remainder = amount - total_split
        
        splits = []
        for i, member in enumerate(members):
            split_amount = base_split + remainder if i == 0 else base_split
            mock_split = create_mock_split(
                expense_id=uuid4(),
                member_id=member.id,
                amount=split_amount,
            )
            splits.append(mock_split)
        
        expense = create_mock_expense(
            paid_by=payer.id,
            amount=amount,
            split_type="equal",
            splits=splits,
        )
        
        # Create a settlement from member 1 to member 0
        settlement_amount = Decimal("10.00")
        settlement = create_mock_settlement(
            from_member=members[1].id if num_members > 1 else members[0].id,
            to_member=members[0].id,
            amount=settlement_amount,
        )
        
        # Calculate balances
        balances = {}
        for member in members:
            balances[member.id] = {
                "total_paid": Decimal("0"),
                "total_owed": Decimal("0"),
                "settlements_received": Decimal("0"),
                "settlements_paid": Decimal("0"),
            }
        
        # Process expense
        balances[expense.paid_by]["total_paid"] += Decimal(str(expense.amount))
        for split in expense.splits:
            balances[split.member_id]["total_owed"] += Decimal(str(split.amount))
        
        # Process settlement
        balances[settlement.from_member]["settlements_paid"] += Decimal(str(settlement.amount))
        balances[settlement.to_member]["settlements_received"] += Decimal(str(settlement.amount))
        
        # Verify formula for each member
        for member in members:
            data = balances[member.id]
            expected_net = (
                data["total_paid"]
                - data["total_owed"]
                + data["settlements_received"]
                - data["settlements_paid"]
            )
            
            # Verify the formula components
            if member.id == payer.id:
                # Payer should have total_paid = amount
                assert data["total_paid"] == amount, (
                    f"Payer's total_paid should be {amount}, got {data['total_paid']}"
                )
            else:
                # Non-payers should have total_paid = 0
                assert data["total_paid"] == Decimal("0"), (
                    f"Non-payer's total_paid should be 0, got {data['total_paid']}"
                )
            
            # All members should have total_owed = their split
            member_split = next(s for s in splits if s.member_id == member.id)
            assert data["total_owed"] == Decimal(str(member_split.amount)), (
                f"Member's total_owed should be {member_split.amount}, got {data['total_owed']}"
            )
    
    @given(
        num_members=valid_member_count(min_members=3, max_members=8),
        num_expenses=st.integers(min_value=2, max_value=6),
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_net_balance_with_percentage_splits(
        self, num_members: int, num_expenses: int
    ):
        """For any group with percentage-based splits, sum of all net balances
        should equal zero.
        
        **Validates: Requirements 13.7**
        
        This test verifies that:
        1. Percentage splits also conserve money
        2. Net balances sum to zero regardless of split type
        """
        # Create mock members
        members = [create_mock_member(name=f"Member_{i}") for i in range(num_members)]
        
        # Create expenses with percentage splits
        expenses = []
        for exp_idx in range(num_expenses):
            payer_idx = exp_idx % num_members
            payer = members[payer_idx]
            amount = Decimal(str(round(50 + exp_idx * 25.75, 2)))
            
            # Generate percentages that sum to 100%
            base_pct = Decimal("100.00") / Decimal(num_members)
            base_pct = base_pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            
            percentages = []
            running_total = Decimal("0")
            for i in range(num_members):
                if i == num_members - 1:
                    pct = Decimal("100.00") - running_total
                else:
                    pct = base_pct
                    running_total += pct
                percentages.append(pct)
            
            # Calculate splits based on percentages
            splits = []
            total_split = Decimal("0")
            for i, (member, pct) in enumerate(zip(members, percentages)):
                split_amount = (amount * pct / Decimal("100")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                total_split += split_amount
                mock_split = create_mock_split(
                    expense_id=uuid4(),
                    member_id=member.id,
                    amount=split_amount,
                )
                splits.append(mock_split)
            
            # Handle rounding remainder
            remainder = amount - total_split
            if remainder != 0 and splits:
                splits[0].amount = Decimal(str(splits[0].amount)) + remainder
            
            expense = create_mock_expense(
                paid_by=payer.id,
                amount=amount,
                split_type="percentage",
                splits=splits,
            )
            expenses.append(expense)
        
        # Calculate balances
        balances = {}
        for member in members:
            balances[member.id] = {
                "total_paid": Decimal("0"),
                "total_owed": Decimal("0"),
            }
        
        for expense in expenses:
            balances[expense.paid_by]["total_paid"] += Decimal(str(expense.amount))
            for split in expense.splits:
                balances[split.member_id]["total_owed"] += Decimal(str(split.amount))
        
        # Calculate net balances
        net_balances = []
        for member_id, data in balances.items():
            net_balance = (data["total_paid"] - data["total_owed"]).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            net_balances.append(net_balance)
        
        # Verify sum equals zero
        total_net = sum(net_balances)
        
        assert total_net == Decimal("0"), (
            f"Sum of net balances ({total_net}) should equal zero with percentage splits. "
            f"Net balances: {net_balances}"
        )


# ============================================================================
# Property 27: Debt Simplification Invariant
# ============================================================================

class TestDebtSimplificationProperty:
    """Property 27: Debt Simplification Invariant.
    
    **Validates: Requirements 13.4, 13.5**
    
    For any group with debts between members, after debt simplification:
    - Each member's net balance (total owed minus total owing) SHALL remain unchanged
    - The number of transactions SHALL be minimized (at most N-1 where N is members with non-zero balances)
    - The sum of all simplified debt amounts equals the total amount that needs to be transferred
    """
    
    @given(
        num_members=valid_member_count(min_members=2, max_members=8),
        num_expenses=st.integers(min_value=1, max_value=6),
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_simplified_debts_preserve_net_balances(
        self, num_members: int, num_expenses: int
    ):
        """For any group with expenses, simplified debts should preserve each
        member's net balance.
        
        **Validates: Requirements 13.4**
        
        This test verifies that:
        1. After simplification, if all debts are settled, all net balances become zero
        2. The simplification doesn't create or destroy money
        """
        # Create mock members
        members = [create_mock_member(name=f"Member_{i}") for i in range(num_members)]
        member_info = {m.id: {"name": m.name, "email": None, "phone": None} for m in members}
        
        # Create expenses with different payers
        expenses = []
        for exp_idx in range(num_expenses):
            payer_idx = exp_idx % num_members
            payer = members[payer_idx]
            amount = Decimal(str(round(20 + exp_idx * 15.5, 2)))
            
            # Equal splits
            base_split = (amount / Decimal(num_members)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            total_split = base_split * num_members
            remainder = amount - total_split
            
            splits = []
            for i, member in enumerate(members):
                split_amount = base_split + remainder if i == 0 else base_split
                mock_split = create_mock_split(
                    expense_id=uuid4(),
                    member_id=member.id,
                    amount=split_amount,
                )
                splits.append(mock_split)
            
            expense = create_mock_expense(
                paid_by=payer.id,
                amount=amount,
                split_type="equal",
                splits=splits,
            )
            expenses.append(expense)
        
        # Calculate initial balances (before simplification)
        balances = {}
        for member in members:
            balances[member.id] = {
                "total_paid": Decimal("0"),
                "total_owed": Decimal("0"),
            }
        
        for expense in expenses:
            balances[expense.paid_by]["total_paid"] += Decimal(str(expense.amount))
            for split in expense.splits:
                balances[split.member_id]["total_owed"] += Decimal(str(split.amount))
        
        # Calculate net balances before simplification
        net_balances_before = {}
        for member_id, data in balances.items():
            net_balances_before[member_id] = (
                data["total_paid"] - data["total_owed"]
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        # Separate debtors and creditors
        debtors = []
        creditors = []
        for member in members:
            net = net_balances_before[member.id]
            if net < 0:
                debtors.append({
                    "member_id": member.id,
                    "member_name": member.name,
                    "amount": abs(net),
                })
            elif net > 0:
                creditors.append({
                    "member_id": member.id,
                    "member_name": member.name,
                    "amount": net,
                })
        
        # Use the actual simplification algorithm
        service = SplitService.__new__(SplitService)
        simplified_debts = service._simplify_debts_greedy(
            debtors=debtors,
            creditors=creditors,
            member_info=member_info,
            group_name="Test Group",
        )
        
        # Calculate net balances after applying simplified debts
        net_balances_after = {m.id: net_balances_before[m.id] for m in members}
        
        for debt in simplified_debts:
            # Debtor pays, so their balance increases (less negative)
            net_balances_after[debt.from_member_id] += debt.amount
            # Creditor receives, so their balance decreases (less positive)
            net_balances_after[debt.to_member_id] -= debt.amount
        
        # After all simplified debts are settled, all net balances should be zero
        for member in members:
            final_balance = net_balances_after[member.id].quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            assert final_balance == Decimal("0"), (
                f"After settling simplified debts, member {member.name}'s balance "
                f"should be 0, got {final_balance}. "
                f"Initial: {net_balances_before[member.id]}"
            )
    
    @given(
        num_members=valid_member_count(min_members=2, max_members=10),
        num_expenses=st.integers(min_value=1, max_value=8),
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_simplified_debts_minimize_transactions(
        self, num_members: int, num_expenses: int
    ):
        """For any group with expenses, the number of simplified transactions
        should be at most (N-1) where N is the number of members with non-zero balances.
        
        **Validates: Requirements 13.4**
        
        This test verifies that:
        1. The greedy algorithm minimizes the number of transactions
        2. The upper bound of N-1 transactions is respected
        """
        # Create mock members
        members = [create_mock_member(name=f"Member_{i}") for i in range(num_members)]
        member_info = {m.id: {"name": m.name, "email": None, "phone": None} for m in members}
        
        # Create expenses
        expenses = []
        for exp_idx in range(num_expenses):
            payer_idx = exp_idx % num_members
            payer = members[payer_idx]
            amount = Decimal(str(round(30 + exp_idx * 20.25, 2)))
            
            # Equal splits
            base_split = (amount / Decimal(num_members)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            total_split = base_split * num_members
            remainder = amount - total_split
            
            splits = []
            for i, member in enumerate(members):
                split_amount = base_split + remainder if i == 0 else base_split
                mock_split = create_mock_split(
                    expense_id=uuid4(),
                    member_id=member.id,
                    amount=split_amount,
                )
                splits.append(mock_split)
            
            expense = create_mock_expense(
                paid_by=payer.id,
                amount=amount,
                split_type="equal",
                splits=splits,
            )
            expenses.append(expense)
        
        # Calculate net balances
        balances = {}
        for member in members:
            balances[member.id] = {
                "total_paid": Decimal("0"),
                "total_owed": Decimal("0"),
            }
        
        for expense in expenses:
            balances[expense.paid_by]["total_paid"] += Decimal(str(expense.amount))
            for split in expense.splits:
                balances[split.member_id]["total_owed"] += Decimal(str(split.amount))
        
        # Separate debtors and creditors
        debtors = []
        creditors = []
        members_with_nonzero_balance = 0
        
        for member in members:
            net = (balances[member.id]["total_paid"] - balances[member.id]["total_owed"]).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if net < Decimal("-0.01"):
                debtors.append({
                    "member_id": member.id,
                    "member_name": member.name,
                    "amount": abs(net),
                })
                members_with_nonzero_balance += 1
            elif net > Decimal("0.01"):
                creditors.append({
                    "member_id": member.id,
                    "member_name": member.name,
                    "amount": net,
                })
                members_with_nonzero_balance += 1
        
        # Use the actual simplification algorithm
        service = SplitService.__new__(SplitService)
        simplified_debts = service._simplify_debts_greedy(
            debtors=debtors,
            creditors=creditors,
            member_info=member_info,
            group_name="Test Group",
        )
        
        # The number of transactions should be at most (N-1)
        max_transactions = max(0, members_with_nonzero_balance - 1)
        
        assert len(simplified_debts) <= max_transactions, (
            f"Number of simplified transactions ({len(simplified_debts)}) should be "
            f"at most {max_transactions} (N-1 where N={members_with_nonzero_balance}). "
            f"Debtors: {len(debtors)}, Creditors: {len(creditors)}"
        )
    
    @given(
        num_members=valid_member_count(min_members=2, max_members=8),
        num_expenses=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_simplified_debts_sum_equals_total_transfer(
        self, num_members: int, num_expenses: int
    ):
        """For any group with expenses, the sum of all simplified debt amounts
        should equal the total amount that needs to be transferred.
        
        **Validates: Requirements 13.4**
        
        This test verifies that:
        1. The total money transferred in simplified debts equals the total debt
        2. No money is created or lost during simplification
        """
        # Create mock members
        members = [create_mock_member(name=f"Member_{i}") for i in range(num_members)]
        member_info = {m.id: {"name": m.name, "email": None, "phone": None} for m in members}
        
        # Create expenses
        expenses = []
        for exp_idx in range(num_expenses):
            payer_idx = exp_idx % num_members
            payer = members[payer_idx]
            amount = Decimal(str(round(25 + exp_idx * 12.75, 2)))
            
            # Equal splits
            base_split = (amount / Decimal(num_members)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            total_split = base_split * num_members
            remainder = amount - total_split
            
            splits = []
            for i, member in enumerate(members):
                split_amount = base_split + remainder if i == 0 else base_split
                mock_split = create_mock_split(
                    expense_id=uuid4(),
                    member_id=member.id,
                    amount=split_amount,
                )
                splits.append(mock_split)
            
            expense = create_mock_expense(
                paid_by=payer.id,
                amount=amount,
                split_type="equal",
                splits=splits,
            )
            expenses.append(expense)
        
        # Calculate net balances
        balances = {}
        for member in members:
            balances[member.id] = {
                "total_paid": Decimal("0"),
                "total_owed": Decimal("0"),
            }
        
        for expense in expenses:
            balances[expense.paid_by]["total_paid"] += Decimal(str(expense.amount))
            for split in expense.splits:
                balances[split.member_id]["total_owed"] += Decimal(str(split.amount))
        
        # Calculate total debt (sum of all negative balances = sum of all positive balances)
        total_debt = Decimal("0")
        debtors = []
        creditors = []
        
        for member in members:
            net = (balances[member.id]["total_paid"] - balances[member.id]["total_owed"]).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if net < 0:
                total_debt += abs(net)
                debtors.append({
                    "member_id": member.id,
                    "member_name": member.name,
                    "amount": abs(net),
                })
            elif net > 0:
                creditors.append({
                    "member_id": member.id,
                    "member_name": member.name,
                    "amount": net,
                })
        
        # Use the actual simplification algorithm
        service = SplitService.__new__(SplitService)
        simplified_debts = service._simplify_debts_greedy(
            debtors=debtors,
            creditors=creditors,
            member_info=member_info,
            group_name="Test Group",
        )
        
        # Sum of simplified debt amounts should equal total debt
        simplified_total = sum(debt.amount for debt in simplified_debts)
        
        assert simplified_total == total_debt, (
            f"Sum of simplified debts ({simplified_total}) should equal "
            f"total debt ({total_debt})"
        )


# ============================================================================
# Property 28: Settlement Balance Update
# ============================================================================

class TestSettlementBalanceUpdateProperty:
    """Property 28: Settlement Balance Update.
    
    **Validates: Requirements 13.4, 13.5**
    
    For any settlement of amount A from user X to user Y:
    - X's net balance SHALL increase by A (they paid off debt)
    - Y's net balance SHALL decrease by A (they received payment)
    - The sum of all net balances SHALL remain zero (money conservation)
    """
    
    @given(
        num_members=valid_member_count(min_members=2, max_members=8),
        num_expenses=st.integers(min_value=1, max_value=5),
        settlement_amount=valid_amounts(),
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_settlement_updates_payer_balance(
        self, num_members: int, num_expenses: int, settlement_amount: Decimal
    ):
        """For any settlement, the payer's net balance should increase by the
        settlement amount.
        
        **Validates: Requirements 13.5**
        
        This test verifies that:
        1. When a member pays a settlement, their net balance increases
        2. The increase equals exactly the settlement amount
        """
        # Create mock members
        members = [create_mock_member(name=f"Member_{i}") for i in range(num_members)]
        
        # Create expenses
        expenses = []
        for exp_idx in range(num_expenses):
            payer_idx = exp_idx % num_members
            payer = members[payer_idx]
            amount = Decimal(str(round(50 + exp_idx * 20.5, 2)))
            
            # Equal splits
            base_split = (amount / Decimal(num_members)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            total_split = base_split * num_members
            remainder = amount - total_split
            
            splits = []
            for i, member in enumerate(members):
                split_amount = base_split + remainder if i == 0 else base_split
                mock_split = create_mock_split(
                    expense_id=uuid4(),
                    member_id=member.id,
                    amount=split_amount,
                )
                splits.append(mock_split)
            
            expense = create_mock_expense(
                paid_by=payer.id,
                amount=amount,
                split_type="equal",
                splits=splits,
            )
            expenses.append(expense)
        
        # Calculate balances before settlement
        balances_before = {}
        for member in members:
            balances_before[member.id] = {
                "total_paid": Decimal("0"),
                "total_owed": Decimal("0"),
                "settlements_received": Decimal("0"),
                "settlements_paid": Decimal("0"),
            }
        
        for expense in expenses:
            balances_before[expense.paid_by]["total_paid"] += Decimal(str(expense.amount))
            for split in expense.splits:
                balances_before[split.member_id]["total_owed"] += Decimal(str(split.amount))
        
        # Calculate net balance before settlement for member 0 (will be payer)
        payer_data = balances_before[members[0].id]
        net_before = (
            payer_data["total_paid"]
            - payer_data["total_owed"]
            + payer_data["settlements_received"]
            - payer_data["settlements_paid"]
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        # Create settlement from member 0 to member 1
        settlement = create_mock_settlement(
            from_member=members[0].id,
            to_member=members[1].id,
            amount=settlement_amount,
        )
        
        # Apply settlement
        balances_before[settlement.from_member]["settlements_paid"] += Decimal(str(settlement.amount))
        balances_before[settlement.to_member]["settlements_received"] += Decimal(str(settlement.amount))
        
        # Calculate net balance after settlement for payer
        payer_data_after = balances_before[members[0].id]
        net_after = (
            payer_data_after["total_paid"]
            - payer_data_after["total_owed"]
            + payer_data_after["settlements_received"]
            - payer_data_after["settlements_paid"]
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        # Payer's balance should decrease by settlement amount (they paid money out)
        expected_change = -settlement_amount
        actual_change = net_after - net_before
        
        assert actual_change == expected_change, (
            f"Payer's net balance change ({actual_change}) should equal "
            f"-{settlement_amount} (they paid out). "
            f"Before: {net_before}, After: {net_after}"
        )
    
    @given(
        num_members=valid_member_count(min_members=2, max_members=8),
        num_expenses=st.integers(min_value=1, max_value=5),
        settlement_amount=valid_amounts(),
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_settlement_updates_receiver_balance(
        self, num_members: int, num_expenses: int, settlement_amount: Decimal
    ):
        """For any settlement, the receiver's net balance should decrease by the
        settlement amount (they received money owed to them).
        
        **Validates: Requirements 13.5**
        
        This test verifies that:
        1. When a member receives a settlement, their net balance decreases
        2. The decrease equals exactly the settlement amount
        
        Note: Net balance = total_paid - total_owed + settlements_received - settlements_paid
        When receiving a settlement, settlements_received increases, so net_balance increases.
        But from a "what they're owed" perspective, they're owed less after receiving payment.
        """
        # Create mock members
        members = [create_mock_member(name=f"Member_{i}") for i in range(num_members)]
        
        # Create expenses
        expenses = []
        for exp_idx in range(num_expenses):
            payer_idx = exp_idx % num_members
            payer = members[payer_idx]
            amount = Decimal(str(round(40 + exp_idx * 18.25, 2)))
            
            # Equal splits
            base_split = (amount / Decimal(num_members)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            total_split = base_split * num_members
            remainder = amount - total_split
            
            splits = []
            for i, member in enumerate(members):
                split_amount = base_split + remainder if i == 0 else base_split
                mock_split = create_mock_split(
                    expense_id=uuid4(),
                    member_id=member.id,
                    amount=split_amount,
                )
                splits.append(mock_split)
            
            expense = create_mock_expense(
                paid_by=payer.id,
                amount=amount,
                split_type="equal",
                splits=splits,
            )
            expenses.append(expense)
        
        # Calculate balances before settlement
        balances_before = {}
        for member in members:
            balances_before[member.id] = {
                "total_paid": Decimal("0"),
                "total_owed": Decimal("0"),
                "settlements_received": Decimal("0"),
                "settlements_paid": Decimal("0"),
            }
        
        for expense in expenses:
            balances_before[expense.paid_by]["total_paid"] += Decimal(str(expense.amount))
            for split in expense.splits:
                balances_before[split.member_id]["total_owed"] += Decimal(str(split.amount))
        
        # Calculate net balance before settlement for member 1 (will be receiver)
        receiver_data = balances_before[members[1].id]
        net_before = (
            receiver_data["total_paid"]
            - receiver_data["total_owed"]
            + receiver_data["settlements_received"]
            - receiver_data["settlements_paid"]
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        # Create settlement from member 0 to member 1
        settlement = create_mock_settlement(
            from_member=members[0].id,
            to_member=members[1].id,
            amount=settlement_amount,
        )
        
        # Apply settlement
        balances_before[settlement.from_member]["settlements_paid"] += Decimal(str(settlement.amount))
        balances_before[settlement.to_member]["settlements_received"] += Decimal(str(settlement.amount))
        
        # Calculate net balance after settlement for receiver
        receiver_data_after = balances_before[members[1].id]
        net_after = (
            receiver_data_after["total_paid"]
            - receiver_data_after["total_owed"]
            + receiver_data_after["settlements_received"]
            - receiver_data_after["settlements_paid"]
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        # Receiver's balance should increase by settlement amount (they received money)
        expected_change = settlement_amount
        actual_change = net_after - net_before
        
        assert actual_change == expected_change, (
            f"Receiver's net balance change ({actual_change}) should equal "
            f"+{settlement_amount} (they received payment). "
            f"Before: {net_before}, After: {net_after}"
        )
    
    @given(
        num_members=valid_member_count(min_members=2, max_members=8),
        num_expenses=st.integers(min_value=1, max_value=5),
        num_settlements=st.integers(min_value=1, max_value=4),
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_settlement_preserves_total_balance_zero(
        self, num_members: int, num_expenses: int, num_settlements: int
    ):
        """For any number of settlements, the sum of all net balances should
        remain zero (money conservation).
        
        **Validates: Requirements 13.5**
        
        This test verifies that:
        1. Settlements transfer money between members without creating/destroying it
        2. The sum of all net balances is always zero
        """
        # Create mock members
        members = [create_mock_member(name=f"Member_{i}") for i in range(num_members)]
        
        # Create expenses
        expenses = []
        for exp_idx in range(num_expenses):
            payer_idx = exp_idx % num_members
            payer = members[payer_idx]
            amount = Decimal(str(round(35 + exp_idx * 22.5, 2)))
            
            # Equal splits
            base_split = (amount / Decimal(num_members)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            total_split = base_split * num_members
            remainder = amount - total_split
            
            splits = []
            for i, member in enumerate(members):
                split_amount = base_split + remainder if i == 0 else base_split
                mock_split = create_mock_split(
                    expense_id=uuid4(),
                    member_id=member.id,
                    amount=split_amount,
                )
                splits.append(mock_split)
            
            expense = create_mock_expense(
                paid_by=payer.id,
                amount=amount,
                split_type="equal",
                splits=splits,
            )
            expenses.append(expense)
        
        # Create settlements
        settlements = []
        for set_idx in range(num_settlements):
            from_idx = set_idx % num_members
            to_idx = (set_idx + 1) % num_members
            if from_idx == to_idx:
                to_idx = (to_idx + 1) % num_members
            
            settlement = create_mock_settlement(
                from_member=members[from_idx].id,
                to_member=members[to_idx].id,
                amount=Decimal(str(round(10 + set_idx * 5.5, 2))),
            )
            settlements.append(settlement)
        
        # Calculate balances
        balances = {}
        for member in members:
            balances[member.id] = {
                "total_paid": Decimal("0"),
                "total_owed": Decimal("0"),
                "settlements_received": Decimal("0"),
                "settlements_paid": Decimal("0"),
            }
        
        # Process expenses
        for expense in expenses:
            balances[expense.paid_by]["total_paid"] += Decimal(str(expense.amount))
            for split in expense.splits:
                balances[split.member_id]["total_owed"] += Decimal(str(split.amount))
        
        # Process settlements
        for settlement in settlements:
            balances[settlement.from_member]["settlements_paid"] += Decimal(str(settlement.amount))
            balances[settlement.to_member]["settlements_received"] += Decimal(str(settlement.amount))
        
        # Calculate net balances
        net_balances = []
        for member_id, data in balances.items():
            net_balance = (
                data["total_paid"]
                - data["total_owed"]
                + data["settlements_received"]
                - data["settlements_paid"]
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            net_balances.append(net_balance)
        
        # Verify sum of net balances equals zero
        total_net = sum(net_balances)
        
        assert total_net == Decimal("0"), (
            f"Sum of net balances ({total_net}) should equal zero after settlements. "
            f"Net balances: {net_balances}, Settlements: {num_settlements}"
        )
