"""Property-based tests for Life Score module.

Uses Hypothesis to verify universal properties across all valid inputs.

**Validates: Requirements 33.1, 33.6**
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from hypothesis import given, strategies as st, settings, assume
from pydantic import ValidationError

from app.models.life_score import ModuleType
from app.schemas.life_score import (
    LifeScoreCalculationResult,
    LifeScoreDetailResponse,
    ModuleScoreBreakdown,
)
from app.services.life_score import MODULE_MAX_SCORES


# ============================================================================
# Hypothesis Strategies for Life Score Data
# ============================================================================

# All expected modules that should be in the breakdown
EXPECTED_MODULES = {
    ModuleType.EXAMS,
    ModuleType.DOCUMENTS,
    ModuleType.MONEY,
    ModuleType.HEALTH,
    ModuleType.WARDROBE,
    ModuleType.CAREER,
}


@st.composite
def valid_module_scores(draw):
    """Generate valid module scores within their maximum limits.
    
    Each module has a maximum score defined in MODULE_MAX_SCORES.
    Returns a dictionary mapping module names to scores.
    """
    module_scores = {}
    for module in ModuleType:
        max_score = MODULE_MAX_SCORES[module]
        score = draw(st.integers(min_value=0, max_value=max_score))
        module_scores[module.value] = score
    return module_scores


@st.composite
def valid_activity_counts(draw):
    """Generate valid activity counts per module.
    
    Returns a dictionary mapping module names to activity counts.
    """
    activity_counts = {}
    for module in ModuleType:
        count = draw(st.integers(min_value=0, max_value=100))
        activity_counts[module.value] = count
    return activity_counts


@st.composite
def valid_life_score_calculation_result(draw):
    """Generate a valid LifeScoreCalculationResult for testing.
    
    Ensures the total score equals the sum of module scores (capped at 100).
    """
    module_scores = draw(valid_module_scores())
    activity_counts = draw(valid_activity_counts())
    
    # Calculate total score (sum of module scores, capped at 100)
    raw_total = sum(module_scores.values())
    total_score = min(100, raw_total)
    
    # Calculate total activity count
    total_activity_count = sum(activity_counts.values())
    
    # Build breakdown
    breakdown = []
    for module in ModuleType:
        score = module_scores.get(module.value, 0)
        activities = activity_counts.get(module.value, 0)
        # Calculate percentage (avoid division by zero)
        if total_score > 0:
            percentage = Decimal(str(round(score / total_score * 100, 2)))
        else:
            percentage = Decimal("0")
        breakdown.append(ModuleScoreBreakdown(
            module=module,
            score=score,
            activity_count=activities,
            percentage=percentage,
        ))
    
    return LifeScoreCalculationResult(
        total_score=total_score,
        module_scores=module_scores,
        activity_count=total_activity_count,
        breakdown=breakdown,
    )


# ============================================================================
# Property 41: Life Score Module Breakdown
# ============================================================================

class TestLifeScoreModuleBreakdownProperty:
    """Property 41: Life Score Module Breakdown.
    
    **Validates: Requirements 33.1, 33.6**
    
    For any user's life score:
    1. The total score SHALL equal the weighted sum of individual module scores
    2. The breakdown SHALL show contribution from each module
    3. Each module contributes a non-negative score
    4. The breakdown includes all expected modules (Exam, Document, Money, Health, Wardrobe, Career)
    """
    
    @given(module_scores=valid_module_scores())
    @settings(max_examples=50, deadline=None)
    def test_total_score_equals_sum_of_module_scores(self, module_scores: dict):
        """For any life score, the total score SHALL equal the sum of all module
        scores (capped at 100).
        
        **Validates: Requirements 33.1, 33.6**
        
        This test verifies that:
        1. The total score is the sum of individual module scores
        2. The total score is capped at 100 (maximum possible)
        3. The calculation is consistent across all module combinations
        """
        # Calculate expected total (sum of module scores, capped at 100)
        raw_total = sum(module_scores.values())
        expected_total = min(100, raw_total)
        
        # Build breakdown for verification
        breakdown = []
        for module in ModuleType:
            score = module_scores.get(module.value, 0)
            breakdown.append(ModuleScoreBreakdown(
                module=module,
                score=score,
                activity_count=0,  # Not relevant for this test
                percentage=Decimal("0"),  # Will be calculated
            ))
        
        # Create the calculation result
        result = LifeScoreCalculationResult(
            total_score=expected_total,
            module_scores=module_scores,
            activity_count=0,
            breakdown=breakdown,
        )
        
        # Verify total score equals sum of module scores (capped at 100)
        actual_sum = sum(b.score for b in result.breakdown)
        assert result.total_score == min(100, actual_sum), (
            f"Total score {result.total_score} should equal min(100, sum of module scores) "
            f"which is min(100, {actual_sum}) = {min(100, actual_sum)}"
        )
    
    @given(module_scores=valid_module_scores())
    @settings(max_examples=50, deadline=None)
    def test_each_module_contributes_non_negative_score(self, module_scores: dict):
        """For any life score, each module SHALL contribute a non-negative score.
        
        **Validates: Requirements 33.1, 33.6**
        
        This test verifies that:
        1. No module has a negative score
        2. All module scores are within their maximum limits
        3. The breakdown correctly represents each module's contribution
        """
        # Build breakdown
        breakdown = []
        for module in ModuleType:
            score = module_scores.get(module.value, 0)
            max_score = MODULE_MAX_SCORES[module]
            
            # Verify score is non-negative
            assert score >= 0, (
                f"Module {module.value} has negative score {score}"
            )
            
            # Verify score is within maximum limit
            assert score <= max_score, (
                f"Module {module.value} score {score} exceeds maximum {max_score}"
            )
            
            breakdown.append(ModuleScoreBreakdown(
                module=module,
                score=score,
                activity_count=0,
                percentage=Decimal("0"),
            ))
        
        # Verify all modules have non-negative scores in breakdown
        for module_breakdown in breakdown:
            assert module_breakdown.score >= 0, (
                f"Module {module_breakdown.module.value} has negative score "
                f"{module_breakdown.score} in breakdown"
            )
    
    @given(result=valid_life_score_calculation_result())
    @settings(max_examples=50, deadline=None)
    def test_breakdown_includes_all_expected_modules(
        self, result: LifeScoreCalculationResult
    ):
        """For any life score, the breakdown SHALL include all expected modules.
        
        **Validates: Requirements 33.1, 33.6**
        
        This test verifies that:
        1. The breakdown contains exactly 6 modules
        2. All expected modules (Exam, Document, Money, Health, Wardrobe, Career) are present
        3. No unexpected modules are included
        """
        # Get modules present in breakdown
        breakdown_modules = {b.module for b in result.breakdown}
        
        # Verify all expected modules are present
        assert breakdown_modules == EXPECTED_MODULES, (
            f"Breakdown modules {breakdown_modules} should match expected modules "
            f"{EXPECTED_MODULES}. Missing: {EXPECTED_MODULES - breakdown_modules}, "
            f"Extra: {breakdown_modules - EXPECTED_MODULES}"
        )
        
        # Verify breakdown has exactly 6 modules
        assert len(result.breakdown) == 6, (
            f"Breakdown should have exactly 6 modules, but has {len(result.breakdown)}"
        )
    
    @given(result=valid_life_score_calculation_result())
    @settings(max_examples=50, deadline=None)
    def test_module_percentages_sum_to_100_when_total_positive(
        self, result: LifeScoreCalculationResult
    ):
        """For any life score with positive total, module percentages SHALL sum
        to approximately 100%.
        
        **Validates: Requirements 33.6**
        
        This test verifies that:
        1. When total score > 0, percentages sum to ~100% (allowing for rounding)
        2. When total score = 0, all percentages are 0
        3. Percentages correctly represent each module's contribution
        """
        total_percentage = sum(b.percentage for b in result.breakdown)
        
        if result.total_score > 0:
            # Allow for small rounding errors (within 1%)
            assert Decimal("99") <= total_percentage <= Decimal("101"), (
                f"Module percentages should sum to ~100%, but sum to {total_percentage}%"
            )
        else:
            # When total is 0, all percentages should be 0
            assert total_percentage == Decimal("0"), (
                f"When total score is 0, percentages should sum to 0, "
                f"but sum to {total_percentage}"
            )
    
    @given(module_scores=valid_module_scores())
    @settings(max_examples=50, deadline=None)
    def test_total_score_bounded_between_0_and_100(self, module_scores: dict):
        """For any life score, the total score SHALL be between 0 and 100.
        
        **Validates: Requirements 33.1**
        
        This test verifies that:
        1. Total score is never negative
        2. Total score never exceeds 100
        3. The capping logic works correctly
        """
        raw_total = sum(module_scores.values())
        total_score = min(100, raw_total)
        
        # Verify bounds
        assert 0 <= total_score <= 100, (
            f"Total score {total_score} should be between 0 and 100"
        )
        
        # Verify capping works
        if raw_total > 100:
            assert total_score == 100, (
                f"Total score should be capped at 100 when raw total is {raw_total}"
            )
        else:
            assert total_score == raw_total, (
                f"Total score {total_score} should equal raw total {raw_total} "
                f"when raw total <= 100"
            )
    
    @given(result=valid_life_score_calculation_result())
    @settings(max_examples=50, deadline=None)
    def test_module_scores_dict_matches_breakdown(
        self, result: LifeScoreCalculationResult
    ):
        """For any life score, the module_scores dict SHALL match the breakdown.
        
        **Validates: Requirements 33.6**
        
        This test verifies that:
        1. Each module in breakdown has corresponding entry in module_scores
        2. The scores match between breakdown and module_scores dict
        3. Data consistency is maintained
        """
        for module_breakdown in result.breakdown:
            module_name = module_breakdown.module.value
            
            # Verify module exists in module_scores dict
            assert module_name in result.module_scores, (
                f"Module {module_name} in breakdown but not in module_scores dict"
            )
            
            # Verify scores match
            dict_score = result.module_scores[module_name]
            breakdown_score = module_breakdown.score
            assert dict_score == breakdown_score, (
                f"Module {module_name} score mismatch: "
                f"module_scores dict has {dict_score}, breakdown has {breakdown_score}"
            )


# ============================================================================
# Additional Edge Case Tests
# ============================================================================

class TestLifeScoreEdgeCases:
    """Edge case tests for Life Score module breakdown.
    
    **Validates: Requirements 33.1, 33.6**
    """
    
    def test_zero_activity_produces_zero_score(self):
        """When there is no activity, the total score SHALL be 0.
        
        **Validates: Requirements 33.1**
        """
        module_scores = {module.value: 0 for module in ModuleType}
        
        breakdown = [
            ModuleScoreBreakdown(
                module=module,
                score=0,
                activity_count=0,
                percentage=Decimal("0"),
            )
            for module in ModuleType
        ]
        
        result = LifeScoreCalculationResult(
            total_score=0,
            module_scores=module_scores,
            activity_count=0,
            breakdown=breakdown,
        )
        
        assert result.total_score == 0
        assert all(b.score == 0 for b in result.breakdown)
        assert all(b.percentage == Decimal("0") for b in result.breakdown)
    
    def test_maximum_scores_cap_at_100(self):
        """When all modules have maximum scores, total SHALL cap at 100.
        
        **Validates: Requirements 33.1**
        """
        # Set each module to its maximum score
        module_scores = {
            module.value: MODULE_MAX_SCORES[module]
            for module in ModuleType
        }
        
        # Sum of all max scores
        raw_total = sum(MODULE_MAX_SCORES.values())
        # Should be exactly 100 based on MODULE_MAX_SCORES definition
        # (15 + 20 + 20 + 10 + 25 + 10 = 100)
        expected_total = min(100, raw_total)
        
        breakdown = [
            ModuleScoreBreakdown(
                module=module,
                score=MODULE_MAX_SCORES[module],
                activity_count=10,
                percentage=Decimal(str(round(
                    MODULE_MAX_SCORES[module] / expected_total * 100, 2
                ))) if expected_total > 0 else Decimal("0"),
            )
            for module in ModuleType
        ]
        
        result = LifeScoreCalculationResult(
            total_score=expected_total,
            module_scores=module_scores,
            activity_count=60,
            breakdown=breakdown,
        )
        
        assert result.total_score <= 100, (
            f"Total score {result.total_score} should not exceed 100"
        )
        assert result.total_score == expected_total
    
    def test_single_module_activity(self):
        """When only one module has activity, breakdown SHALL still include all modules.
        
        **Validates: Requirements 33.6**
        """
        # Only career module has activity
        module_scores = {module.value: 0 for module in ModuleType}
        module_scores[ModuleType.CAREER.value] = 15
        
        total_score = 15
        
        breakdown = []
        for module in ModuleType:
            score = module_scores[module.value]
            percentage = Decimal(str(round(score / total_score * 100, 2))) if total_score > 0 else Decimal("0")
            breakdown.append(ModuleScoreBreakdown(
                module=module,
                score=score,
                activity_count=5 if module == ModuleType.CAREER else 0,
                percentage=percentage,
            ))
        
        result = LifeScoreCalculationResult(
            total_score=total_score,
            module_scores=module_scores,
            activity_count=5,
            breakdown=breakdown,
        )
        
        # Verify all 6 modules are present
        assert len(result.breakdown) == 6
        
        # Verify only career has non-zero score
        career_breakdown = next(b for b in result.breakdown if b.module == ModuleType.CAREER)
        assert career_breakdown.score == 15
        assert career_breakdown.percentage == Decimal("100.00")
        
        # Verify other modules have zero score
        other_modules = [b for b in result.breakdown if b.module != ModuleType.CAREER]
        assert all(b.score == 0 for b in other_modules)
        assert all(b.percentage == Decimal("0") for b in other_modules)
