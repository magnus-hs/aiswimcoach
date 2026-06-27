"""
Heart rate zone analysis module for AI Swim Coach.

Extracts heart rate data from FIT files and calculates time distribution
across five intensity zones based on maximum heart rate.
"""
from __future__ import annotations

import math
from datetime import datetime

from fitparse import FitFile


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class HRDataError(Exception):
    """Raised when heart rate data cannot be extracted or processed."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


# ---------------------------------------------------------------------------
# Heart Rate Data Extraction
# ---------------------------------------------------------------------------

def extract_heart_rate_data(fit_bytes: bytes) -> list[tuple[datetime, int]]:
    """Extract heart rate samples from FIT file record messages.

    Parses FIT file record messages and extracts all valid heart rate
    values with their associated timestamps. Filters out invalid values
    (zero, negative, >= 221 bpm) and non-finite values (NaN, Inf).

    Args:
        fit_bytes: Raw bytes of a Garmin FIT file.

    Returns:
        List of (timestamp, heart_rate_bpm) tuples, filtered for valid values.
        Returns empty list if no valid heart rate data is found.

    Raises:
        HRDataError: If FIT file cannot be parsed.

    Requirements:
        - Validates: Requirements 1.1, 1.2, 1.4, 1.5
    """
    try:
        fitfile = FitFile(fit_bytes)
    except Exception as exc:
        raise HRDataError(f"Malformed FIT file: {exc}") from exc

    hr_samples: list[tuple[datetime, int]] = []

    # Extract heart rate data from record messages
    for record in fitfile.get_messages("record"):
        # Convert record fields to dict
        data = {f.name: f.value for f in record}

        # Get timestamp
        timestamp = data.get("timestamp")
        if timestamp is None:
            continue

        # Get heart rate value
        hr_value = data.get("heart_rate")
        if hr_value is None:
            continue

        # Filter out non-numeric and non-finite values (NaN, Inf)
        # Requirement 1.5
        try:
            hr_float = float(hr_value)
            if not math.isfinite(hr_float):
                continue
        except (ValueError, TypeError):
            continue

        # Convert to integer for validation
        try:
            hr_bpm = int(hr_float)
        except (ValueError, TypeError):
            continue

        # Filter out invalid values: zero, negative, or >= 221 bpm
        # Requirement 1.4
        if hr_bpm <= 0 or hr_bpm >= 221:
            continue

        # Add valid sample
        hr_samples.append((timestamp, hr_bpm))

    # Requirement 1.3: Return empty list if no heart rate data found
    return hr_samples


# ---------------------------------------------------------------------------
# Heart Rate Sample Validation
# ---------------------------------------------------------------------------

def is_valid_hr_sample(hr: int) -> bool:
    """Validate a heart rate sample value.

    A heart rate sample is considered valid if it is greater than 0
    and less than or equal to 300 beats per minute.

    Args:
        hr: Heart rate value in beats per minute.

    Returns:
        True if the heart rate is valid (0 < hr <= 300), False otherwise.

    Requirements:
        - Validates: Requirement 2.8
    """
    return 0 < hr <= 300


# ---------------------------------------------------------------------------
# Maximum Heart Rate Calculation
# ---------------------------------------------------------------------------

def calculate_max_hr(age: int) -> int:
    """Calculate maximum heart rate from age.

    Uses the standard formula: 220 - age.

    Args:
        age: User age (1-120 inclusive).

    Returns:
        Maximum heart rate in beats per minute.

    Raises:
        ValueError: If age is outside valid range (1-120).

    Requirements:
        - Validates: Requirements 2.1, 2.2
    """
    # Requirement 2.1: Validate age range
    if age < 1 or age > 120:
        raise ValueError("age must be between 1 and 120")

    # Requirement 2.2: Calculate max HR as 220 - age
    return 220 - age


# ---------------------------------------------------------------------------
# Heart Rate Zone Boundary Calculation
# ---------------------------------------------------------------------------

def calculate_zone_boundaries(max_hr: int) -> dict[int, tuple[int, int]]:
    """Calculate heart rate zone boundaries.

    Calculates five zone boundaries based on percentages of maximum heart rate.
    Zone boundaries are rounded to the nearest whole number.

    Args:
        max_hr: Maximum heart rate in beats per minute.

    Returns:
        Dictionary mapping zone number (1-5) to (lower_bound, upper_bound) tuples.
        Zone 1: 50-60% of max HR
        Zone 2: 60-70% of max HR
        Zone 3: 70-80% of max HR
        Zone 4: 80-90% of max HR
        Zone 5: 90-100% of max HR

    Requirements:
        - Validates: Requirements 2.3, 2.4, 2.5, 2.6, 2.7
    """
    # Calculate zone boundaries rounded to nearest whole number
    # Zone 1: 50-60% (inclusive-exclusive)
    zone_1_lower = round(0.50 * max_hr)
    zone_1_upper = round(0.60 * max_hr)

    # Zone 2: 60-70% (inclusive-exclusive)
    zone_2_lower = round(0.60 * max_hr)
    zone_2_upper = round(0.70 * max_hr)

    # Zone 3: 70-80% (inclusive-exclusive)
    zone_3_lower = round(0.70 * max_hr)
    zone_3_upper = round(0.80 * max_hr)

    # Zone 4: 80-90% (inclusive-exclusive)
    zone_4_lower = round(0.80 * max_hr)
    zone_4_upper = round(0.90 * max_hr)

    # Zone 5: 90-100% (inclusive-inclusive)
    zone_5_lower = round(0.90 * max_hr)
    zone_5_upper = round(1.00 * max_hr)

    return {
        1: (zone_1_lower, zone_1_upper),
        2: (zone_2_lower, zone_2_upper),
        3: (zone_3_lower, zone_3_upper),
        4: (zone_4_lower, zone_4_upper),
        5: (zone_5_lower, zone_5_upper),
    }


# ---------------------------------------------------------------------------
# Heart Rate Zone Time Calculation
# ---------------------------------------------------------------------------

def calculate_hr_zones(
    hr_samples: list[tuple[datetime, int]],
    age: int
) -> "HRZonesData":
    """Calculate time and percentage spent in each heart rate zone.

    Processes heart rate samples to determine how much time was spent in each
    of the five intensity zones. Calculates both absolute time (seconds) and
    relative percentages.

    Args:
        hr_samples: List of (timestamp, heart_rate_bpm) tuples from FIT file.
        age: User age for maximum heart rate calculation (1-120 inclusive).

    Returns:
        HRZonesData object with time (seconds) and percentage for each zone,
        plus max_hr and zone_boundaries used for calculations.

    Raises:
        ValueError: If hr_samples is empty or contains no valid samples,
                   or if age is outside valid range (1-120),
                   or if there are fewer than 2 valid samples.

    Requirements:
        - Validates: Requirements 2.9, 2.10, 2.11, 2.12
    """
    # Import HRZonesData here to avoid circular import
    from backend.models import HRZonesData

    # Requirement 2.10: Validate we have heart rate data
    if not hr_samples:
        raise ValueError("no valid heart rate samples found")

    # Filter for valid HR samples (0 < hr <= 300)
    valid_samples = [(ts, hr) for ts, hr in hr_samples if is_valid_hr_sample(hr)]

    # Requirement 2.10: Ensure we have valid samples after filtering
    if not valid_samples:
        raise ValueError("no valid heart rate samples found")
    
    # Need at least 2 samples to calculate time intervals
    if len(valid_samples) < 2:
        raise ValueError("need at least 2 valid heart rate samples to calculate zones")

    # Calculate max HR and zone boundaries
    max_hr = calculate_max_hr(age)  # This validates age range (Requirement 2.1)
    zone_boundaries = calculate_zone_boundaries(max_hr)

    # Initialize zone time counters
    zone_times = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0}

    # Calculate time spent in each zone
    # Process consecutive samples to calculate time intervals
    for i in range(len(valid_samples) - 1):
        current_ts, current_hr = valid_samples[i]
        next_ts, _ = valid_samples[i + 1]

        # Calculate time interval between samples (in seconds)
        time_delta = (next_ts - current_ts).total_seconds()

        # Determine which zone the current HR falls into
        # Zone boundaries are inclusive on lower bound, exclusive on upper bound
        # except Zone 5 which is inclusive on both bounds
        zone = None
        for zone_num in range(1, 6):
            lower, upper = zone_boundaries[zone_num]
            if zone_num < 5:
                # Zones 1-4: [lower, upper)
                if lower <= current_hr < upper:
                    zone = zone_num
                    break
            else:
                # Zone 5: [lower, upper]
                if lower <= current_hr <= upper:
                    zone = zone_num
                    break

        # If HR falls within a zone, add the time interval
        if zone is not None:
            zone_times[zone] += time_delta

    # Calculate total session time
    # Total time is from first to last timestamp
    total_time = (valid_samples[-1][0] - valid_samples[0][0]).total_seconds()

    # Requirement 2.12: Ensure sum of zone times equals total time (within 1 second)
    sum_zone_times = sum(zone_times.values())
    if abs(sum_zone_times - total_time) > 1.0:
        # This shouldn't happen with proper logic, but validate anyway
        raise ValueError(
            f"Zone time sum ({sum_zone_times:.1f}s) does not equal "
            f"total session time ({total_time:.1f}s)"
        )

    # Calculate percentages (Requirement 2.11)
    # Percentages are rounded to one decimal place
    zone_percentages = {}
    if total_time > 0:
        for zone_num in range(1, 6):
            percentage = (zone_times[zone_num] / total_time) * 100.0
            zone_percentages[zone_num] = round(percentage, 1)
    else:
        # Edge case: if total time is 0 (shouldn't happen with 2+ samples), all percentages are 0
        zone_percentages = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0}

    # Create HRZonesData object
    return HRZonesData(
        zone_1_seconds=int(round(zone_times[1])),
        zone_2_seconds=int(round(zone_times[2])),
        zone_3_seconds=int(round(zone_times[3])),
        zone_4_seconds=int(round(zone_times[4])),
        zone_5_seconds=int(round(zone_times[5])),
        zone_1_percent=zone_percentages[1],
        zone_2_percent=zone_percentages[2],
        zone_3_percent=zone_percentages[3],
        zone_4_percent=zone_percentages[4],
        zone_5_percent=zone_percentages[5],
        max_hr=max_hr,
        zone_boundaries=zone_boundaries,
    )
