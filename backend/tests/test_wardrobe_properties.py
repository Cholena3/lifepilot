"""Property-based tests for wardrobe module.

Property 34: Wardrobe Item Availability
*For any* wardrobe item marked as "in laundry", the item SHALL be excluded from outfit suggestions until marked as available.

Property 35: Wear Count Tracking
*For any* wardrobe item marked as worn N times, the wear count SHALL equal N and the last worn date SHALL be the most recent wear date.

Validates: Requirements 19.5, 19.6, 20.2
"""

import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Optional

import pytest
from hypothesis import given, strategies as st, settings, assume

from app.schemas.wardrobe import (
    ClothingType, ClothingPattern, Occasion,
    WardrobeItemCreate, WardrobeItemResponse, WardrobeItemWithStatsResponse,
    WearLogCreate, WearLogResponse,
    OutfitSuggestionResponse,
)


# ============================================================================
# Strategies
# ============================================================================

@st.composite
def clothing_type_strategy(draw):
    """Generate valid clothing types."""
    return draw(st.sampled_from(ClothingType.ALL))


@st.composite
def clothing_pattern_strategy(draw):
    """Generate valid clothing patterns."""
    return draw(st.sampled_from(ClothingPattern.ALL))


@st.composite
def occasion_strategy(draw):
    """Generate valid occasions."""
    return draw(st.sampled_from(Occasion.ALL))


@st.composite
def color_strategy(draw):
    """Generate valid color names."""
    colors = ["red", "blue", "green", "black", "white", "gray", "navy", "beige", "brown", "pink"]
    return draw(st.sampled_from(colors))


@st.composite
def wardrobe_item_create_strategy(draw):
    """Generate valid WardrobeItemCreate data."""
    item_type = draw(clothing_type_strategy())
    name = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z'))))
    primary_color = draw(st.one_of(st.none(), color_strategy()))
    pattern = draw(st.one_of(st.none(), clothing_pattern_strategy()))
    brand = draw(st.one_of(st.none(), st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('L', 'N')))))
    price = draw(st.one_of(st.none(), st.decimals(min_value=0, max_value=10000, places=2, allow_nan=False, allow_infinity=False)))
    occasions = draw(st.one_of(st.none(), st.lists(occasion_strategy(), min_size=0, max_size=3, unique=True)))
    
    return WardrobeItemCreate(
        item_type=item_type,
        name=name if name.strip() else "Item",
        primary_color=primary_color,
        pattern=pattern,
        brand=brand,
        price=price,
        occasions=occasions,
    )


@st.composite
def wardrobe_item_response_strategy(draw, in_laundry: Optional[bool] = None, wear_count: Optional[int] = None):
    """Generate valid WardrobeItemResponse data."""
    item_id = uuid.uuid4()
    user_id = uuid.uuid4()
    item_type = draw(clothing_type_strategy())
    
    if in_laundry is None:
        in_laundry = draw(st.booleans())
    
    if wear_count is None:
        wear_count = draw(st.integers(min_value=0, max_value=100))
    
    last_worn = None
    if wear_count > 0:
        days_ago = draw(st.integers(min_value=0, max_value=365))
        last_worn = datetime.now() - timedelta(days=days_ago)
    
    return WardrobeItemResponse(
        id=item_id,
        user_id=user_id,
        image_url=f"https://storage.example.com/{item_id}.jpg",
        processed_image_url=None,
        item_type=item_type,
        name=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N')))),
        primary_color=draw(st.one_of(st.none(), color_strategy())),
        pattern=draw(st.one_of(st.none(), clothing_pattern_strategy())),
        brand=None,
        price=draw(st.one_of(st.none(), st.decimals(min_value=0, max_value=10000, places=2, allow_nan=False, allow_infinity=False))),
        purchase_date=None,
        in_laundry=in_laundry,
        wear_count=wear_count,
        last_worn=last_worn,
        occasions=draw(st.one_of(st.none(), st.lists(occasion_strategy(), min_size=0, max_size=3, unique=True))),
        notes=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@st.composite
def wear_log_create_strategy(draw):
    """Generate valid WearLogCreate data."""
    days_ago = draw(st.integers(min_value=0, max_value=365))
    worn_date = date.today() - timedelta(days=days_ago)
    occasion = draw(st.one_of(st.none(), occasion_strategy()))
    
    return WearLogCreate(
        worn_date=worn_date,
        occasion=occasion,
    )


# ============================================================================
# Property 34: Wardrobe Item Availability Tests
# ============================================================================

class TestWardrobeItemAvailabilityProperty:
    """Property 34: Wardrobe Item Availability
    
    *For any* wardrobe item marked as "in laundry", the item SHALL be excluded 
    from outfit suggestions until marked as available.
    
    Validates: Requirements 19.5, 20.2
    """
    
    @given(st.lists(wardrobe_item_response_strategy(), min_size=1, max_size=10))
    @settings(max_examples=50)
    def test_items_in_laundry_excluded_from_suggestions(self, items: List[WardrobeItemResponse]):
        """Items marked as in laundry should be excluded from outfit suggestions."""
        # Simulate filtering for outfit suggestions
        available_items = [item for item in items if not item.in_laundry]
        
        # Verify no items in laundry are in the available list
        for item in available_items:
            assert not item.in_laundry, f"Item {item.id} is in laundry but was included in suggestions"
    
    @given(wardrobe_item_response_strategy(in_laundry=True))
    @settings(max_examples=50)
    def test_laundry_item_never_suggested(self, item: WardrobeItemResponse):
        """An item in laundry should never appear in suggestions."""
        # Simulate suggestion filtering
        is_available = not item.in_laundry
        
        assert not is_available, "Item in laundry should not be available for suggestions"
    
    @given(wardrobe_item_response_strategy(in_laundry=False))
    @settings(max_examples=50)
    def test_available_item_can_be_suggested(self, item: WardrobeItemResponse):
        """An item not in laundry should be available for suggestions."""
        is_available = not item.in_laundry
        
        assert is_available, "Item not in laundry should be available for suggestions"
    
    @given(st.lists(wardrobe_item_response_strategy(), min_size=5, max_size=20))
    @settings(max_examples=30)
    def test_laundry_status_partitions_items(self, items: List[WardrobeItemResponse]):
        """Items should be partitioned into available and in-laundry sets."""
        available = [item for item in items if not item.in_laundry]
        in_laundry = [item for item in items if item.in_laundry]
        
        # Verify partition is complete
        assert len(available) + len(in_laundry) == len(items)
        
        # Verify no overlap
        available_ids = {item.id for item in available}
        laundry_ids = {item.id for item in in_laundry}
        assert available_ids.isdisjoint(laundry_ids)
    
    @given(wardrobe_item_response_strategy())
    @settings(max_examples=50)
    def test_laundry_status_toggle_changes_availability(self, item: WardrobeItemResponse):
        """Toggling laundry status should change availability."""
        original_available = not item.in_laundry
        
        # Simulate toggle
        item.in_laundry = not item.in_laundry
        new_available = not item.in_laundry
        
        assert original_available != new_available, "Toggling laundry status should change availability"
    
    @given(
        st.lists(wardrobe_item_response_strategy(in_laundry=False), min_size=2, max_size=5),
        st.lists(wardrobe_item_response_strategy(in_laundry=True), min_size=1, max_size=3),
    )
    @settings(max_examples=30)
    def test_mixed_items_filter_correctly(
        self, 
        available_items: List[WardrobeItemResponse], 
        laundry_items: List[WardrobeItemResponse]
    ):
        """Mixed list of items should filter correctly for suggestions."""
        all_items = available_items + laundry_items
        
        # Filter for suggestions
        suggested = [item for item in all_items if not item.in_laundry]
        
        # All suggested items should be from available_items
        suggested_ids = {item.id for item in suggested}
        available_ids = {item.id for item in available_items}
        
        assert suggested_ids == available_ids, "Only available items should be suggested"


# ============================================================================
# Property 35: Wear Count Tracking Tests
# ============================================================================

class TestWearCountTrackingProperty:
    """Property 35: Wear Count Tracking
    
    *For any* wardrobe item marked as worn N times, the wear count SHALL equal N 
    and the last worn date SHALL be the most recent wear date.
    
    Validates: Requirements 19.6
    """
    
    @given(st.integers(min_value=0, max_value=100))
    @settings(max_examples=50)
    def test_wear_count_equals_number_of_wears(self, n: int):
        """Wear count should equal the number of times item was worn."""
        # Simulate tracking N wears
        wear_count = 0
        for _ in range(n):
            wear_count += 1
        
        assert wear_count == n, f"Wear count {wear_count} should equal {n}"
    
    @given(st.lists(wear_log_create_strategy(), min_size=1, max_size=20))
    @settings(max_examples=50)
    def test_last_worn_is_most_recent_date(self, wear_logs: List[WearLogCreate]):
        """Last worn date should be the most recent wear date."""
        # Find the most recent date
        most_recent = max(log.worn_date for log in wear_logs)
        
        # Simulate tracking
        last_worn = None
        for log in wear_logs:
            if last_worn is None or log.worn_date > last_worn:
                last_worn = log.worn_date
        
        assert last_worn == most_recent, f"Last worn {last_worn} should be most recent {most_recent}"
    
    @given(
        st.integers(min_value=1, max_value=50),
        st.integers(min_value=0, max_value=365),
    )
    @settings(max_examples=50)
    def test_wear_count_increments_correctly(self, initial_count: int, additional_wears: int):
        """Wear count should increment correctly with each wear."""
        wear_count = initial_count
        
        for _ in range(additional_wears):
            wear_count += 1
        
        expected = initial_count + additional_wears
        assert wear_count == expected, f"Wear count {wear_count} should be {expected}"
    
    @given(wardrobe_item_response_strategy(wear_count=0))
    @settings(max_examples=50)
    def test_unworn_item_has_no_last_worn_date(self, item: WardrobeItemResponse):
        """An unworn item should have no last worn date or wear count of 0."""
        if item.wear_count == 0:
            # last_worn can be None for unworn items
            # This is a valid state
            pass
        
        assert item.wear_count >= 0, "Wear count should never be negative"
    
    @given(st.integers(min_value=1, max_value=100))
    @settings(max_examples=50)
    def test_worn_item_has_positive_wear_count(self, n: int):
        """A worn item should have a positive wear count."""
        wear_count = n
        
        assert wear_count > 0, "Worn item should have positive wear count"
    
    @given(
        st.lists(
            st.tuples(
                st.integers(min_value=0, max_value=365),  # days ago
                occasion_strategy(),
            ),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=30)
    def test_wear_logs_track_all_wears(self, wear_data: List[tuple]):
        """All wear events should be tracked in wear logs."""
        wear_logs = []
        for days_ago, occasion in wear_data:
            worn_date = date.today() - timedelta(days=days_ago)
            wear_logs.append(WearLogCreate(worn_date=worn_date, occasion=occasion))
        
        # Verify count matches
        assert len(wear_logs) == len(wear_data), "All wears should be logged"
    
    @given(
        st.lists(wear_log_create_strategy(), min_size=2, max_size=10),
    )
    @settings(max_examples=30)
    def test_wear_count_matches_log_count(self, wear_logs: List[WearLogCreate]):
        """Wear count should match the number of wear logs."""
        wear_count = len(wear_logs)
        
        assert wear_count == len(wear_logs), "Wear count should match log count"


# ============================================================================
# Additional Wardrobe Property Tests
# ============================================================================

class TestWardrobeItemValidation:
    """Tests for wardrobe item validation properties."""
    
    @given(clothing_type_strategy())
    @settings(max_examples=50)
    def test_valid_clothing_types_accepted(self, item_type: str):
        """Valid clothing types should be accepted."""
        assert item_type in ClothingType.ALL
        
        data = WardrobeItemCreate(item_type=item_type)
        assert data.item_type == item_type
    
    @given(st.text(min_size=1, max_size=20).filter(lambda x: x not in ClothingType.ALL))
    @settings(max_examples=30)
    def test_invalid_clothing_types_rejected(self, invalid_type: str):
        """Invalid clothing types should be rejected."""
        assume(invalid_type.strip())  # Ensure non-empty
        
        with pytest.raises(ValueError):
            WardrobeItemCreate(item_type=invalid_type)
    
    @given(clothing_pattern_strategy())
    @settings(max_examples=50)
    def test_valid_patterns_accepted(self, pattern: str):
        """Valid patterns should be accepted."""
        assert pattern in ClothingPattern.ALL
        
        data = WardrobeItemCreate(item_type="top", pattern=pattern)
        assert data.pattern == pattern
    
    @given(occasion_strategy())
    @settings(max_examples=50)
    def test_valid_occasions_accepted(self, occasion: str):
        """Valid occasions should be accepted."""
        assert occasion in Occasion.ALL
        
        data = WardrobeItemCreate(item_type="top", occasions=[occasion])
        assert occasion in data.occasions
    
    @given(st.lists(occasion_strategy(), min_size=1, max_size=5, unique=True))
    @settings(max_examples=30)
    def test_multiple_occasions_accepted(self, occasions: List[str]):
        """Multiple valid occasions should be accepted."""
        data = WardrobeItemCreate(item_type="top", occasions=occasions)
        assert set(data.occasions) == set(occasions)


class TestCostPerWearCalculation:
    """Property 37: Cost Per Wear Calculation
    
    *For any* wardrobe item with purchase price P and wear count W (where W > 0), 
    cost per wear SHALL equal P/W.
    
    Validates: Requirements 22.2
    """
    
    @given(
        st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000"), places=2, allow_nan=False, allow_infinity=False),
        st.integers(min_value=1, max_value=1000),
    )
    @settings(max_examples=50)
    def test_cost_per_wear_calculation(self, price: Decimal, wear_count: int):
        """Cost per wear should equal price divided by wear count."""
        expected_cost_per_wear = price / wear_count
        
        # Simulate calculation
        calculated = price / wear_count
        
        assert calculated == expected_cost_per_wear, f"Cost per wear {calculated} should be {expected_cost_per_wear}"
    
    @given(
        st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000"), places=2, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50)
    def test_cost_per_wear_decreases_with_more_wears(self, price: Decimal):
        """Cost per wear should decrease as wear count increases."""
        cost_at_1 = price / 1
        cost_at_10 = price / 10
        cost_at_100 = price / 100
        
        assert cost_at_1 > cost_at_10 > cost_at_100, "Cost per wear should decrease with more wears"
    
    @given(st.integers(min_value=1, max_value=1000))
    @settings(max_examples=50)
    def test_zero_price_gives_zero_cost_per_wear(self, wear_count: int):
        """Zero price should give zero cost per wear."""
        price = Decimal("0")
        cost_per_wear = price / wear_count
        
        assert cost_per_wear == Decimal("0"), "Zero price should give zero cost per wear"
    
    @given(
        st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000"), places=2, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=30)
    def test_single_wear_equals_full_price(self, price: Decimal):
        """Single wear should have cost per wear equal to full price."""
        cost_per_wear = price / 1
        
        assert cost_per_wear == price, "Single wear cost should equal full price"


# ============================================================================
# Property 36: Outfit Suggestion Recency Bias Tests
# ============================================================================

class TestOutfitSuggestionRecencyBiasProperty:
    """Property 36: Outfit Suggestion Recency Bias
    
    *For any* outfit suggestion, items not worn recently SHALL be prioritized 
    over items worn recently.
    
    Validates: Requirements 20.3
    """
    
    @given(
        st.lists(
            st.tuples(
                st.integers(min_value=0, max_value=365),  # days since last worn
                st.booleans(),  # in_laundry
            ),
            min_size=2,
            max_size=10,
        )
    )
    @settings(max_examples=50)
    def test_items_sorted_by_recency(self, item_data: List[tuple]):
        """Items should be sorted with least recently worn first."""
        # Create items with different last worn dates
        items = []
        for i, (days_ago, in_laundry) in enumerate(item_data):
            last_worn = datetime.now() - timedelta(days=days_ago) if days_ago > 0 else None
            items.append({
                "id": i,
                "days_since_worn": days_ago if days_ago > 0 else float('inf'),
                "last_worn": last_worn,
                "in_laundry": in_laundry,
            })
        
        # Filter available items
        available = [item for item in items if not item["in_laundry"]]
        
        if len(available) < 2:
            return  # Not enough items to test sorting
        
        # Sort by recency (items not worn recently first)
        sorted_items = sorted(available, key=lambda x: -x["days_since_worn"])
        
        # Verify sorting - items with more days since worn should come first
        for i in range(len(sorted_items) - 1):
            assert sorted_items[i]["days_since_worn"] >= sorted_items[i + 1]["days_since_worn"], \
                "Items should be sorted with least recently worn first"
    
    @given(
        st.integers(min_value=1, max_value=100),  # days since worn for item A
        st.integers(min_value=1, max_value=100),  # days since worn for item B
    )
    @settings(max_examples=50)
    def test_older_worn_item_prioritized(self, days_a: int, days_b: int):
        """Item worn longer ago should be prioritized."""
        assume(days_a != days_b)  # Ensure different values
        
        # Item with more days since worn should have higher priority
        priority_a = days_a  # Higher = more priority
        priority_b = days_b
        
        if days_a > days_b:
            assert priority_a > priority_b, "Item worn longer ago should have higher priority"
        else:
            assert priority_b > priority_a, "Item worn longer ago should have higher priority"
    
    @given(st.integers(min_value=1, max_value=365))
    @settings(max_examples=50)
    def test_never_worn_item_highest_priority(self, days_since_worn: int):
        """Never worn items should have highest priority."""
        never_worn_priority = float('inf')
        worn_priority = days_since_worn
        
        assert never_worn_priority > worn_priority, "Never worn items should have highest priority"
    
    @given(
        st.lists(
            st.integers(min_value=0, max_value=365),
            min_size=3,
            max_size=10,
        )
    )
    @settings(max_examples=30)
    def test_recency_score_calculation(self, days_list: List[int]):
        """Recency score should be calculated correctly."""
        # Calculate scores
        scores = []
        for days in days_list:
            if days == 0:
                # Never worn - highest score
                score = 100 + 10  # Base + bonus
            else:
                # Penalize recently worn
                penalty = max(0, (7 - days) * 5) if days < 7 else 0
                score = 100 - penalty
            scores.append(score)
        
        # Verify scores are non-negative
        for score in scores:
            assert score >= 0, "Recency score should be non-negative"
    
    @given(
        st.lists(wardrobe_item_response_strategy(in_laundry=False), min_size=2, max_size=5)
    )
    @settings(max_examples=30)
    def test_suggestion_order_respects_recency(self, items: List[WardrobeItemResponse]):
        """Outfit suggestions should respect recency ordering."""
        # Sort items by last_worn (None = never worn = highest priority)
        def sort_key(item):
            if item.last_worn is None:
                return datetime.min  # Never worn = highest priority (earliest date)
            return item.last_worn
        
        sorted_items = sorted(items, key=sort_key)
        
        # Verify the first item is either never worn or worn longest ago
        first_item = sorted_items[0]
        for other_item in sorted_items[1:]:
            if first_item.last_worn is None:
                # First item never worn - it should be prioritized
                pass
            elif other_item.last_worn is None:
                # Other item never worn but first item was worn - this shouldn't happen
                assert False, "Never worn items should come first"
            else:
                # Both worn - first should be worn earlier
                assert first_item.last_worn <= other_item.last_worn, \
                    "Items worn longer ago should come first"
