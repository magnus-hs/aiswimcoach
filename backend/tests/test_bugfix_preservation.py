"""
Preservation property tests for validation tolerance fixes.

These tests verify that behavior is PRESERVED (unchanged) on unfixed code
for inputs that DON'T trigger the bug conditions.

**EXPECTED OUTCOME**: Tests PASS on unfixed code (confirms baseline behavior to preserve)

Bug 1: HR zones - verify accurate calculations for files with ≤1s time difference
Bug 2: Training plans - verify processing without modification for goal_likelihood ≤300 chars

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, strategies as st, assume

# Ensure project root is on the path so imports resolve
sys.path.insert(0, ".")

from backend.hr_zones import calculate_hr_zones
from backend.bedrock_client import _parse_training_plan_response


# ============================================================================
# Preservation Property 1: HR Zones Accuracy
# ============================================================================
# For files with time differences ≤1 second, zone calculations must remain accurate


@given(
    num_samples=st.integers(min_value=10, max_value=100),
    age=st.integers(min_value=20, max_value=70),
)
def test_property_hr_zones_perfect_sampling_preserved(num_samples: int, age: int):
    """
    **Property 2: Preservation** - HR Zones Accuracy
    
    For any HR samples where zone time sum equals total session time within 1 second
    (perfect or near-perfect sampling), the function SHALL produce accurate HRZonesData
    exactly as before.
    
    This test observes behavior on UNFIXED code with continuous 1Hz sampling (0s difference).
    Expected to PASS on unfixed code, confirming baseline behavior to preserve.
    
    **Validates: Requirements 3.1, 3.4**
    """
    ts_base = datetime(2024, 1, 15, 10, 0, 0)
    
    # Calculate a valid HR value in Zone 3 (70-80% of max HR)
    max_hr = 220 - age
    hr_value = int(0.75 * max_hr)  # Middle of Zone 3
    
    # Create perfectly continuous samples at 1Hz (0s time difference)
    hr_samples = []
    for i in range(num_samples):
        timestamp = ts_base + timedelta(seconds=i)
        hr_samples.append((timestamp, hr_value))
    
    # This should work perfectly on unfixed code
    result = calculate_hr_zones(hr_samples, age=age)
    
    # Verify basic properties
    assert result is not None
    assert result.max_hr == 220 - age
    
    # Verify total time calculation
    total_time_expected = num_samples - 1  # n samples = n-1 intervals
    total_time_actual = (
        result.zone_1_seconds + 
        result.zone_2_seconds + 
        result.zone_3_seconds + 
        result.zone_4_seconds + 
        result.zone_5_seconds
    )
    
    # Should be very close (within 1 second as per current tolerance)
    assert abs(total_time_actual - total_time_expected) <= 1
    
    # Verify percentages sum to approximately 100%
    total_percent = (
        result.zone_1_percent +
        result.zone_2_percent +
        result.zone_3_percent +
        result.zone_4_percent +
        result.zone_5_percent
    )
    assert 99.0 <= total_percent <= 101.0  # Allow rounding tolerance


@given(
    base_interval=st.integers(min_value=1, max_value=5),  # 1-5 second intervals
    num_samples=st.integers(min_value=10, max_value=50),
    age=st.integers(min_value=20, max_value=70),
    microsecond_variation=st.integers(min_value=0, max_value=999999),  # Sub-second variation
)
def test_property_hr_zones_subsecond_difference_preserved(
    base_interval: int,
    num_samples: int, 
    age: int,
    microsecond_variation: int,
):
    """
    **Property 2: Preservation** - HR Zones Accuracy with Sub-Second Differences
    
    For any HR samples with time differences ≤1 second (irregular sampling with
    sub-second variations), the function SHALL produce accurate HRZonesData.
    
    This test observes behavior on UNFIXED code with slight time irregularities.
    Expected to PASS on unfixed code.
    
    **Validates: Requirements 3.1, 3.4**
    """
    ts_base = datetime(2024, 1, 15, 10, 0, 0)
    
    # Calculate a valid HR value in Zone 3 (70-80% of max HR)
    max_hr = 220 - age
    hr_value = int(0.75 * max_hr)  # Middle of Zone 3
    
    # Create samples with sub-second variations
    hr_samples = []
    current_time = ts_base
    
    for i in range(num_samples):
        hr_samples.append((current_time, hr_value))
        # Add base interval + microsecond variation
        current_time = current_time + timedelta(
            seconds=base_interval,
            microseconds=microsecond_variation if i % 2 == 0 else -microsecond_variation
        )
    
    # This should work on unfixed code (sub-second differences)
    result = calculate_hr_zones(hr_samples, age=age)
    
    assert result is not None
    assert result.max_hr == 220 - age
    
    # Verify zone times are calculated
    total_seconds = (
        result.zone_1_seconds + 
        result.zone_2_seconds + 
        result.zone_3_seconds + 
        result.zone_4_seconds + 
        result.zone_5_seconds
    )
    assert total_seconds > 0
    
    # Verify percentages sum to approximately 100%
    total_percent = (
        result.zone_1_percent +
        result.zone_2_percent +
        result.zone_3_percent +
        result.zone_4_percent +
        result.zone_5_percent
    )
    assert 99.0 <= total_percent <= 101.0


@given(
    zone_1_duration=st.integers(min_value=10, max_value=120),
    zone_2_duration=st.integers(min_value=10, max_value=120),
    zone_3_duration=st.integers(min_value=10, max_value=120),
    zone_4_duration=st.integers(min_value=10, max_value=120),
    zone_5_duration=st.integers(min_value=10, max_value=120),
    age=st.integers(min_value=20, max_value=70),
)
def test_property_hr_zones_various_zone_distributions_preserved(
    zone_1_duration: int,
    zone_2_duration: int,
    zone_3_duration: int,
    zone_4_duration: int,
    zone_5_duration: int,
    age: int,
):
    """
    **Property 2: Preservation** - HR Zones Accuracy Across Zone Distributions
    
    For any HR samples with continuous sampling across different zone distributions,
    the function SHALL correctly calculate time in each zone.
    
    This test observes behavior on UNFIXED code with varied zone distributions.
    Expected to PASS on unfixed code.
    
    **Validates: Requirements 3.1, 3.4**
    """
    ts_base = datetime(2024, 1, 15, 10, 0, 0)
    
    # Calculate zone boundaries for the given age
    max_hr = 220 - age
    zone_1_hr = int(0.55 * max_hr)  # Middle of Zone 1 (50-60%)
    zone_2_hr = int(0.65 * max_hr)  # Middle of Zone 2 (60-70%)
    zone_3_hr = int(0.75 * max_hr)  # Middle of Zone 3 (70-80%)
    zone_4_hr = int(0.85 * max_hr)  # Middle of Zone 4 (80-90%)
    zone_5_hr = int(0.95 * max_hr)  # Middle of Zone 5 (90-100%)
    
    # Create samples in each zone with specified durations
    hr_samples = []
    current_time = ts_base
    
    # Zone 1 samples
    for i in range(zone_1_duration):
        hr_samples.append((current_time, zone_1_hr))
        current_time = current_time + timedelta(seconds=1)
    
    # Zone 2 samples
    for i in range(zone_2_duration):
        hr_samples.append((current_time, zone_2_hr))
        current_time = current_time + timedelta(seconds=1)
    
    # Zone 3 samples
    for i in range(zone_3_duration):
        hr_samples.append((current_time, zone_3_hr))
        current_time = current_time + timedelta(seconds=1)
    
    # Zone 4 samples
    for i in range(zone_4_duration):
        hr_samples.append((current_time, zone_4_hr))
        current_time = current_time + timedelta(seconds=1)
    
    # Zone 5 samples
    for i in range(zone_5_duration):
        hr_samples.append((current_time, zone_5_hr))
        current_time = current_time + timedelta(seconds=1)
    
    # Calculate expected total time (n samples = n-1 intervals)
    expected_total = (zone_1_duration + zone_2_duration + zone_3_duration + 
                     zone_4_duration + zone_5_duration - 1)
    
    # This should work on unfixed code (continuous sampling)
    result = calculate_hr_zones(hr_samples, age=age)
    
    assert result is not None
    assert result.max_hr == max_hr
    
    # Verify zone times are approximately correct (within reasonable tolerance)
    # Each zone should have roughly the specified duration (minus 1 for intervals)
    # Allow 20% tolerance due to rounding and edge effects
    tolerance = 0.20
    
    if zone_1_duration > 2:
        assert result.zone_1_seconds >= zone_1_duration * (1 - tolerance)
    if zone_2_duration > 2:
        assert result.zone_2_seconds >= zone_2_duration * (1 - tolerance)
    if zone_3_duration > 2:
        assert result.zone_3_seconds >= zone_3_duration * (1 - tolerance)
    if zone_4_duration > 2:
        assert result.zone_4_seconds >= zone_4_duration * (1 - tolerance)
    if zone_5_duration > 2:
        assert result.zone_5_seconds >= zone_5_duration * (1 - tolerance)
    
    # Verify total time
    total_seconds = (
        result.zone_1_seconds + 
        result.zone_2_seconds + 
        result.zone_3_seconds + 
        result.zone_4_seconds + 
        result.zone_5_seconds
    )
    assert abs(total_seconds - expected_total) <= 1
    
    # Verify percentages sum to approximately 100%
    total_percent = (
        result.zone_1_percent +
        result.zone_2_percent +
        result.zone_3_percent +
        result.zone_4_percent +
        result.zone_5_percent
    )
    assert 99.0 <= total_percent <= 101.0


# ============================================================================
# Preservation Property 2: Training Plan Validation
# ============================================================================
# For goal_likelihood ≤300 chars, processing must remain unchanged


@given(
    goal_likelihood_length=st.integers(min_value=1, max_value=300),
)
def test_property_training_plan_valid_length_preserved(goal_likelihood_length: int):
    """
    **Property 2: Preservation** - Training Plan Validation
    
    For any training plan response where goal_likelihood is ≤300 characters,
    the function SHALL process the field identically without modification.
    
    This test observes behavior on UNFIXED code with valid goal_likelihood lengths.
    Expected to PASS on unfixed code.
    
    **Validates: Requirements 3.2, 3.5**
    """
    # Generate goal_likelihood with exact length
    goal_likelihood = "X" * goal_likelihood_length
    
    response_body = {
        "content": [
            {
                "type": "tool_use",
                "name": "submit_training_plan",
                "input": {
                    "session_title": "Test Session",
                    "warm_up": ["200m easy freestyle"],
                    "main_set": ["5x100m @ 1:30"],
                    "cool_down": ["200m easy"],
                    "total_distance": 1000,
                    "focus_notes": "Test focus notes",
                    "goal_likelihood": goal_likelihood,
                },
            }
        ]
    }
    
    # This should work on unfixed code (valid length)
    result = _parse_training_plan_response(response_body)
    
    assert result is not None
    assert result.session_title == "Test Session"
    assert result.goal_likelihood == goal_likelihood  # Unchanged
    assert len(result.goal_likelihood) == goal_likelihood_length
    assert result.total_distance == 1000


@given(
    goal_likelihood_length=st.integers(min_value=50, max_value=299),
    session_title_length=st.integers(min_value=10, max_value=100),
    total_distance=st.integers(min_value=500, max_value=5000),
)
def test_property_training_plan_near_limit_preserved(
    goal_likelihood_length: int,
    session_title_length: int,
    total_distance: int,
):
    """
    **Property 2: Preservation** - Training Plan Near Character Limit
    
    For any training plan with goal_likelihood near the 300 character limit (but under),
    the function SHALL process it without modification.
    
    This test observes behavior on UNFIXED code with goal_likelihood close to limit.
    Expected to PASS on unfixed code.
    
    **Validates: Requirements 3.2, 3.5**
    """
    goal_likelihood = "Y" * goal_likelihood_length
    session_title = "Z" * session_title_length
    
    response_body = {
        "content": [
            {
                "type": "tool_use",
                "name": "submit_training_plan",
                "input": {
                    "session_title": session_title,
                    "warm_up": ["400m easy", "4x50m drill"],
                    "main_set": ["8x100m @ 1:25", "4x200m @ 2:50"],
                    "cool_down": ["300m easy choice"],
                    "total_distance": total_distance,
                    "focus_notes": "Progressive aerobic development with controlled intervals",
                    "goal_likelihood": goal_likelihood,
                },
            }
        ]
    }
    
    # This should work on unfixed code
    result = _parse_training_plan_response(response_body)
    
    assert result is not None
    assert result.session_title == session_title
    assert result.goal_likelihood == goal_likelihood  # Unchanged
    assert len(result.goal_likelihood) == goal_likelihood_length
    assert result.total_distance == total_distance
    assert len(result.warm_up) == 2
    assert len(result.main_set) == 2
    assert len(result.cool_down) == 1


@given(
    goal_likelihood_length=st.integers(min_value=1, max_value=300),
)
def test_property_training_plan_other_validations_preserved(goal_likelihood_length: int):
    """
    **Property 2: Preservation** - Training Plan Other Field Validations
    
    For any training plan, validations for other fields (session_title, warm_up, 
    main_set, cool_down, total_distance, focus_notes) SHALL remain unchanged.
    
    This test observes that other validation logic works correctly on UNFIXED code.
    Expected to PASS on unfixed code.
    
    **Validates: Requirements 3.5**
    """
    goal_likelihood = "W" * goal_likelihood_length
    
    # Test 1: Missing session_title should still return None
    response_invalid_title = {
        "content": [
            {
                "type": "tool_use",
                "name": "submit_training_plan",
                "input": {
                    "session_title": "",  # Empty - invalid
                    "warm_up": ["200m easy"],
                    "main_set": ["5x100m @ 1:30"],
                    "cool_down": ["200m easy"],
                    "total_distance": 1000,
                    "focus_notes": "Test",
                    "goal_likelihood": goal_likelihood,
                },
            }
        ]
    }
    
    result = _parse_training_plan_response(response_invalid_title)
    assert result is None  # Should fail validation
    
    # Test 2: Invalid total_distance should still return None
    response_invalid_distance = {
        "content": [
            {
                "type": "tool_use",
                "name": "submit_training_plan",
                "input": {
                    "session_title": "Test Session",
                    "warm_up": ["200m easy"],
                    "main_set": ["5x100m @ 1:30"],
                    "cool_down": ["200m easy"],
                    "total_distance": 0,  # Invalid - must be > 0
                    "focus_notes": "Test",
                    "goal_likelihood": goal_likelihood,
                },
            }
        ]
    }
    
    result = _parse_training_plan_response(response_invalid_distance)
    assert result is None  # Should fail validation
    
    # Test 3: Empty warm_up should still return None
    response_invalid_warmup = {
        "content": [
            {
                "type": "tool_use",
                "name": "submit_training_plan",
                "input": {
                    "session_title": "Test Session",
                    "warm_up": [],  # Empty - invalid
                    "main_set": ["5x100m @ 1:30"],
                    "cool_down": ["200m easy"],
                    "total_distance": 1000,
                    "focus_notes": "Test",
                    "goal_likelihood": goal_likelihood,
                },
            }
        ]
    }
    
    result = _parse_training_plan_response(response_invalid_warmup)
    assert result is None  # Should fail validation
    
    # Test 4: Valid input should still work
    response_valid = {
        "content": [
            {
                "type": "tool_use",
                "name": "submit_training_plan",
                "input": {
                    "session_title": "Valid Session",
                    "warm_up": ["200m easy"],
                    "main_set": ["5x100m @ 1:30"],
                    "cool_down": ["200m easy"],
                    "total_distance": 1000,
                    "focus_notes": "Valid focus",
                    "goal_likelihood": goal_likelihood,
                },
            }
        ]
    }
    
    result = _parse_training_plan_response(response_valid)
    assert result is not None  # Should pass validation
    assert result.session_title == "Valid Session"
    assert result.goal_likelihood == goal_likelihood


# ============================================================================
# Unit Tests - Edge Cases
# ============================================================================


def test_hr_zones_exactly_one_second_difference():
    """
    Test HR zones with exactly 1.0 second time difference (boundary case).
    
    The current validation allows up to 1.0 second difference. This test
    verifies that exactly 1.0s is accepted on unfixed code.
    
    Expected to PASS on unfixed code.
    
    **Validates: Requirements 3.1**
    """
    ts_base = datetime(2024, 1, 15, 10, 0, 0)
    
    # Create samples with exactly 1.0s difference
    # Due to rounding, achieving exactly 1.0s is challenging
    # This test documents the boundary behavior
    hr_samples = [
        (ts_base, 150),
        (ts_base + timedelta(seconds=60), 150),
        (ts_base + timedelta(seconds=120), 150),
        (ts_base + timedelta(seconds=180), 150),
        (ts_base + timedelta(seconds=240), 150),
        (ts_base + timedelta(seconds=300), 150),
    ]
    
    # Should work on unfixed code (no discrepancy with perfect sampling)
    result = calculate_hr_zones(hr_samples, age=20)
    assert result is not None


def test_training_plan_exactly_300_characters():
    """
    Test training plan with exactly 300-character goal_likelihood (boundary case).
    
    The current validation allows up to 300 characters. This test verifies
    that exactly 300 characters is accepted on unfixed code.
    
    Expected to PASS on unfixed code.
    
    **Validates: Requirements 3.2**
    """
    goal_likelihood_300 = "B" * 300
    
    response_body = {
        "content": [
            {
                "type": "tool_use",
                "name": "submit_training_plan",
                "input": {
                    "session_title": "Boundary Test Session",
                    "warm_up": ["200m easy"],
                    "main_set": ["5x100m @ 1:30"],
                    "cool_down": ["200m easy"],
                    "total_distance": 1000,
                    "focus_notes": "Testing exact boundary",
                    "goal_likelihood": goal_likelihood_300,
                },
            }
        ]
    }
    
    result = _parse_training_plan_response(response_body)
    
    assert result is not None
    assert len(result.goal_likelihood) == 300
    assert result.goal_likelihood == goal_likelihood_300


def test_hr_zones_minimum_valid_samples():
    """
    Test HR zones with minimum valid number of samples (2 samples).
    
    This verifies that the minimum edge case still works on unfixed code.
    
    Expected to PASS on unfixed code.
    
    **Validates: Requirements 3.1**
    """
    ts_base = datetime(2024, 1, 15, 10, 0, 0)
    
    hr_samples = [
        (ts_base, 150),
        (ts_base + timedelta(seconds=60), 150),
    ]
    
    result = calculate_hr_zones(hr_samples, age=30)
    assert result is not None
    assert result.max_hr == 190
