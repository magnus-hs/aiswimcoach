"""
Tests for the heart rate zones module (hr_zones.py).

Tests cover:
  - Heart rate data extraction from FIT files
  - Filtering of invalid values (zero, negative, >= 221 bpm)
  - Handling of NaN and Inf values
  - Empty HR data handling
"""
from __future__ import annotations

import math
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from backend.hr_zones import (
    extract_heart_rate_data,
    calculate_max_hr,
    calculate_zone_boundaries,
    is_valid_hr_sample,
    HRDataError,
)


def create_mock_record(**fields):
    """Helper to create mock FIT record with specified fields.
    
    Args:
        **fields: field_name=value pairs
    
    Returns:
        Mock record object that can be iterated to get fields
    """
    mock_record = MagicMock()
    mock_fields = []
    for name, value in fields.items():
        field = MagicMock()
        field.name = name
        field.value = value
        mock_fields.append(field)
    # Store fields list to avoid closure issues
    mock_record._fields = mock_fields
    mock_record.__iter__ = lambda self: iter(self._fields)
    return mock_record


class TestExtractHeartRateData:
    """Tests for extract_heart_rate_data() function."""

    @patch("backend.hr_zones.FitFile")
    def test_extracts_valid_hr_data(self, mock_fitfile_class: MagicMock) -> None:
        """Valid heart rate data should be extracted as (timestamp, hr_bpm) tuples."""
        mock_fitfile = MagicMock()
        mock_fitfile_class.return_value = mock_fitfile

        ts1 = datetime(2024, 1, 15, 10, 0, 0)
        ts2 = datetime(2024, 1, 15, 10, 0, 5)
        ts3 = datetime(2024, 1, 15, 10, 0, 10)

        mock_record1 = create_mock_record(timestamp=ts1, heart_rate=150)
        mock_record2 = create_mock_record(timestamp=ts2, heart_rate=165)
        mock_record3 = create_mock_record(timestamp=ts3, heart_rate=142)

        mock_fitfile.get_messages.return_value = [mock_record1, mock_record2, mock_record3]

        result = extract_heart_rate_data(b"fake_fit_bytes")

        assert len(result) == 3
        assert result[0] == (ts1, 150)
        assert result[1] == (ts2, 165)
        assert result[2] == (ts3, 142)
        mock_fitfile.get_messages.assert_called_once_with("record")

    @patch("backend.hr_zones.FitFile")
    def test_filters_out_zero_values(self, mock_fitfile_class: MagicMock) -> None:
        """Zero heart rate values should be filtered out."""
        mock_fitfile = MagicMock()
        mock_fitfile_class.return_value = mock_fitfile

        ts1 = datetime(2024, 1, 15, 10, 0, 0)
        ts2 = datetime(2024, 1, 15, 10, 0, 5)

        mock_record1 = create_mock_record(timestamp=ts1, heart_rate=0)
        mock_record2 = create_mock_record(timestamp=ts2, heart_rate=150)

        mock_fitfile.get_messages.return_value = [mock_record1, mock_record2]

        result = extract_heart_rate_data(b"fake_fit_bytes")

        assert len(result) == 1
        assert result[0] == (ts2, 150)

    @patch("backend.hr_zones.FitFile")
    def test_filters_out_negative_values(self, mock_fitfile_class: MagicMock) -> None:
        """Negative heart rate values should be filtered out."""
        mock_fitfile = MagicMock()
        mock_fitfile_class.return_value = mock_fitfile

        ts1 = datetime(2024, 1, 15, 10, 0, 0)
        ts2 = datetime(2024, 1, 15, 10, 0, 5)

        mock_record1 = create_mock_record(timestamp=ts1, heart_rate=-10)
        mock_record2 = create_mock_record(timestamp=ts2, heart_rate=160)

        mock_fitfile.get_messages.return_value = [mock_record1, mock_record2]

        result = extract_heart_rate_data(b"fake_fit_bytes")

        assert len(result) == 1
        assert result[0] == (ts2, 160)

    @patch("backend.hr_zones.FitFile")
    def test_filters_out_values_above_threshold(self, mock_fitfile_class: MagicMock) -> None:
        """Heart rate values >= 221 bpm should be filtered out."""
        mock_fitfile = MagicMock()
        mock_fitfile_class.return_value = mock_fitfile

        ts1 = datetime(2024, 1, 15, 10, 0, 0)
        ts2 = datetime(2024, 1, 15, 10, 0, 5)
        ts3 = datetime(2024, 1, 15, 10, 0, 10)
        ts4 = datetime(2024, 1, 15, 10, 0, 15)

        mock_record1 = create_mock_record(timestamp=ts1, heart_rate=220)
        mock_record2 = create_mock_record(timestamp=ts2, heart_rate=221)
        mock_record3 = create_mock_record(timestamp=ts3, heart_rate=250)
        mock_record4 = create_mock_record(timestamp=ts4, heart_rate=180)

        mock_fitfile.get_messages.return_value = [
            mock_record1, mock_record2, mock_record3, mock_record4
        ]

        result = extract_heart_rate_data(b"fake_fit_bytes")

        assert len(result) == 2
        assert result[0] == (ts1, 220)
        assert result[1] == (ts4, 180)

    @patch("backend.hr_zones.FitFile")
    def test_filters_out_nan_values(self, mock_fitfile_class: MagicMock) -> None:
        """NaN heart rate values should be filtered out."""
        mock_fitfile = MagicMock()
        mock_fitfile_class.return_value = mock_fitfile

        ts1 = datetime(2024, 1, 15, 10, 0, 0)
        ts2 = datetime(2024, 1, 15, 10, 0, 5)

        mock_record1 = create_mock_record(timestamp=ts1, heart_rate=float('nan'))
        mock_record2 = create_mock_record(timestamp=ts2, heart_rate=155)

        mock_fitfile.get_messages.return_value = [mock_record1, mock_record2]

        result = extract_heart_rate_data(b"fake_fit_bytes")

        assert len(result) == 1
        assert result[0] == (ts2, 155)

    @patch("backend.hr_zones.FitFile")
    def test_filters_out_inf_values(self, mock_fitfile_class: MagicMock) -> None:
        """Inf heart rate values should be filtered out."""
        mock_fitfile = MagicMock()
        mock_fitfile_class.return_value = mock_fitfile

        ts1 = datetime(2024, 1, 15, 10, 0, 0)
        ts2 = datetime(2024, 1, 15, 10, 0, 5)
        ts3 = datetime(2024, 1, 15, 10, 0, 10)

        mock_record1 = create_mock_record(timestamp=ts1, heart_rate=float('inf'))
        mock_record2 = create_mock_record(timestamp=ts2, heart_rate=float('-inf'))
        mock_record3 = create_mock_record(timestamp=ts3, heart_rate=145)

        mock_fitfile.get_messages.return_value = [mock_record1, mock_record2, mock_record3]

        result = extract_heart_rate_data(b"fake_fit_bytes")

        assert len(result) == 1
        assert result[0] == (ts3, 145)

    @patch("backend.hr_zones.FitFile")
    def test_returns_empty_list_when_no_hr_data(self, mock_fitfile_class: MagicMock) -> None:
        """Should return empty list when no heart rate data is present."""
        mock_fitfile = MagicMock()
        mock_fitfile_class.return_value = mock_fitfile

        ts1 = datetime(2024, 1, 15, 10, 0, 0)
        mock_record1 = create_mock_record(timestamp=ts1, speed=1.5)

        mock_fitfile.get_messages.return_value = [mock_record1]

        result = extract_heart_rate_data(b"fake_fit_bytes")

        assert result == []

    @patch("backend.hr_zones.FitFile")
    def test_returns_empty_list_when_no_records(self, mock_fitfile_class: MagicMock) -> None:
        """Should return empty list when no record messages are found."""
        mock_fitfile = MagicMock()
        mock_fitfile_class.return_value = mock_fitfile
        mock_fitfile.get_messages.return_value = []

        result = extract_heart_rate_data(b"fake_fit_bytes")

        assert result == []

    @patch("backend.hr_zones.FitFile")
    def test_skips_records_with_missing_timestamp(self, mock_fitfile_class: MagicMock) -> None:
        """Should skip records that have heart rate but no timestamp."""
        mock_fitfile = MagicMock()
        mock_fitfile_class.return_value = mock_fitfile

        ts1 = datetime(2024, 1, 15, 10, 0, 0)

        mock_record1 = create_mock_record(heart_rate=150)
        mock_record2 = create_mock_record(timestamp=ts1, heart_rate=160)

        mock_fitfile.get_messages.return_value = [mock_record1, mock_record2]

        result = extract_heart_rate_data(b"fake_fit_bytes")

        assert len(result) == 1
        assert result[0] == (ts1, 160)

    @patch("backend.hr_zones.FitFile")
    def test_raises_error_on_malformed_fit_file(self, mock_fitfile_class: MagicMock) -> None:
        """Should raise HRDataError when FIT file cannot be parsed."""
        mock_fitfile_class.side_effect = Exception("Invalid FIT file header")

        with pytest.raises(HRDataError, match="Malformed FIT file"):
            extract_heart_rate_data(b"invalid_fit_bytes")

    @patch("backend.hr_zones.FitFile")
    def test_handles_non_numeric_hr_values(self, mock_fitfile_class: MagicMock) -> None:
        """Should skip non-numeric heart rate values."""
        mock_fitfile = MagicMock()
        mock_fitfile_class.return_value = mock_fitfile

        ts1 = datetime(2024, 1, 15, 10, 0, 0)
        ts2 = datetime(2024, 1, 15, 10, 0, 5)

        mock_record1 = create_mock_record(timestamp=ts1, heart_rate="invalid")
        mock_record2 = create_mock_record(timestamp=ts2, heart_rate=150)

        mock_fitfile.get_messages.return_value = [mock_record1, mock_record2]

        result = extract_heart_rate_data(b"fake_fit_bytes")

        assert len(result) == 1
        assert result[0] == (ts2, 150)

    @patch("backend.hr_zones.FitFile")
    def test_converts_float_hr_to_int(self, mock_fitfile_class: MagicMock) -> None:
        """Should convert float heart rate values to integers."""
        mock_fitfile = MagicMock()
        mock_fitfile_class.return_value = mock_fitfile

        ts1 = datetime(2024, 1, 15, 10, 0, 0)

        mock_record1 = create_mock_record(timestamp=ts1, heart_rate=150.7)

        mock_fitfile.get_messages.return_value = [mock_record1]

        result = extract_heart_rate_data(b"fake_fit_bytes")

        assert len(result) == 1
        assert result[0] == (ts1, 150)
        assert isinstance(result[0][1], int)



class TestCalculateMaxHR:
    """Tests for calculate_max_hr() function."""

    def test_calculates_max_hr_for_valid_age(self) -> None:
        """Max HR should be 220 - age for valid ages."""
        assert calculate_max_hr(25) == 195
        assert calculate_max_hr(30) == 190
        assert calculate_max_hr(40) == 180
        assert calculate_max_hr(50) == 170
        assert calculate_max_hr(60) == 160

    def test_calculates_max_hr_at_lower_boundary(self) -> None:
        """Max HR calculation should work at age 1 (lower boundary)."""
        assert calculate_max_hr(1) == 219

    def test_calculates_max_hr_at_upper_boundary(self) -> None:
        """Max HR calculation should work at age 120 (upper boundary)."""
        assert calculate_max_hr(120) == 100

    def test_raises_error_for_age_zero(self) -> None:
        """Should raise ValueError for age 0."""
        with pytest.raises(ValueError, match="age must be between 1 and 120"):
            calculate_max_hr(0)

    def test_raises_error_for_negative_age(self) -> None:
        """Should raise ValueError for negative age."""
        with pytest.raises(ValueError, match="age must be between 1 and 120"):
            calculate_max_hr(-5)

    def test_raises_error_for_age_above_120(self) -> None:
        """Should raise ValueError for age > 120."""
        with pytest.raises(ValueError, match="age must be between 1 and 120"):
            calculate_max_hr(121)
        with pytest.raises(ValueError, match="age must be between 1 and 120"):
            calculate_max_hr(150)

    def test_returns_integer(self) -> None:
        """Max HR should always be an integer."""
        result = calculate_max_hr(35)
        assert isinstance(result, int)
        assert result == 185


class TestIsValidHRSample:
    """Tests for is_valid_hr_sample() function."""

    def test_valid_hr_within_range(self) -> None:
        """Heart rate values within valid range (1-300) should return True."""
        assert is_valid_hr_sample(1) is True
        assert is_valid_hr_sample(50) is True
        assert is_valid_hr_sample(120) is True
        assert is_valid_hr_sample(180) is True
        assert is_valid_hr_sample(300) is True

    def test_boundary_at_300(self) -> None:
        """Heart rate of exactly 300 bpm should be valid (upper boundary)."""
        assert is_valid_hr_sample(300) is True

    def test_boundary_at_1(self) -> None:
        """Heart rate of exactly 1 bpm should be valid (lower boundary)."""
        assert is_valid_hr_sample(1) is True

    def test_zero_is_invalid(self) -> None:
        """Heart rate of 0 bpm should be invalid."""
        assert is_valid_hr_sample(0) is False

    def test_negative_is_invalid(self) -> None:
        """Negative heart rate values should be invalid."""
        assert is_valid_hr_sample(-1) is False
        assert is_valid_hr_sample(-50) is False
        assert is_valid_hr_sample(-200) is False

    def test_above_300_is_invalid(self) -> None:
        """Heart rate values above 300 bpm should be invalid."""
        assert is_valid_hr_sample(301) is False
        assert is_valid_hr_sample(350) is False
        assert is_valid_hr_sample(500) is False

    def test_typical_exercise_hr_values(self) -> None:
        """Typical exercise heart rate values should be valid."""
        assert is_valid_hr_sample(100) is True
        assert is_valid_hr_sample(150) is True
        assert is_valid_hr_sample(180) is True
        assert is_valid_hr_sample(200) is True



class TestCalculateZoneBoundaries:
    """Tests for calculate_zone_boundaries() function."""

    def test_calculates_boundaries_for_max_hr_200(self) -> None:
        """Zone boundaries should be correctly calculated for max HR of 200."""
        result = calculate_zone_boundaries(200)

        # Zone 1: 50-60% of 200 = 100-120
        assert result[1] == (100, 120)
        # Zone 2: 60-70% of 200 = 120-140
        assert result[2] == (120, 140)
        # Zone 3: 70-80% of 200 = 140-160
        assert result[3] == (140, 160)
        # Zone 4: 80-90% of 200 = 160-180
        assert result[4] == (160, 180)
        # Zone 5: 90-100% of 200 = 180-200
        assert result[5] == (180, 200)

    def test_calculates_boundaries_for_max_hr_190(self) -> None:
        """Zone boundaries should be correctly calculated for max HR of 190."""
        result = calculate_zone_boundaries(190)

        # Zone 1: 50-60% of 190 = 95-114 (rounded)
        assert result[1] == (95, 114)
        # Zone 2: 60-70% of 190 = 114-133 (rounded)
        assert result[2] == (114, 133)
        # Zone 3: 70-80% of 190 = 133-152 (rounded)
        assert result[3] == (133, 152)
        # Zone 4: 80-90% of 190 = 152-171 (rounded)
        assert result[4] == (152, 171)
        # Zone 5: 90-100% of 190 = 171-190 (rounded)
        assert result[5] == (171, 190)

    def test_calculates_boundaries_for_max_hr_180(self) -> None:
        """Zone boundaries should be correctly calculated for max HR of 180."""
        result = calculate_zone_boundaries(180)

        # Zone 1: 50-60% of 180 = 90-108
        assert result[1] == (90, 108)
        # Zone 2: 60-70% of 180 = 108-126
        assert result[2] == (108, 126)
        # Zone 3: 70-80% of 180 = 126-144
        assert result[3] == (126, 144)
        # Zone 4: 80-90% of 180 = 144-162
        assert result[4] == (144, 162)
        # Zone 5: 90-100% of 180 = 162-180
        assert result[5] == (162, 180)

    def test_returns_all_five_zones(self) -> None:
        """Should return exactly 5 zones."""
        result = calculate_zone_boundaries(200)
        assert len(result) == 5
        assert set(result.keys()) == {1, 2, 3, 4, 5}

    def test_boundaries_are_integers(self) -> None:
        """All zone boundaries should be integers."""
        result = calculate_zone_boundaries(195)

        for zone_num, (lower, upper) in result.items():
            assert isinstance(lower, int), f"Zone {zone_num} lower bound should be int"
            assert isinstance(upper, int), f"Zone {zone_num} upper bound should be int"

    def test_zones_are_contiguous(self) -> None:
        """Upper bound of one zone should equal lower bound of next zone."""
        result = calculate_zone_boundaries(200)

        assert result[1][1] == result[2][0]  # Zone 1 upper = Zone 2 lower
        assert result[2][1] == result[3][0]  # Zone 2 upper = Zone 3 lower
        assert result[3][1] == result[4][0]  # Zone 3 upper = Zone 4 lower
        assert result[4][1] == result[5][0]  # Zone 4 upper = Zone 5 lower

    def test_zone_5_upper_equals_max_hr(self) -> None:
        """Zone 5 upper boundary should equal max HR."""
        max_hr = 185
        result = calculate_zone_boundaries(max_hr)
        assert result[5][1] == max_hr

    def test_zone_1_lower_is_50_percent(self) -> None:
        """Zone 1 lower boundary should be 50% of max HR (rounded)."""
        max_hr = 200
        result = calculate_zone_boundaries(max_hr)
        assert result[1][0] == round(0.50 * max_hr)

    def test_handles_odd_max_hr(self) -> None:
        """Should correctly round boundaries for odd max HR values."""
        result = calculate_zone_boundaries(195)

        # Zone 1: 50-60% of 195 = 97.5-117 = 98-117 (rounded)
        assert result[1] == (98, 117)
        # Zone 2: 60-70% of 195 = 117-136.5 = 117-136 (rounded)
        assert result[2] == (117, 136)
        # Zone 3: 70-80% of 195 = 136.5-156 = 136-156 (rounded)
        assert result[3] == (136, 156)
        # Zone 4: 80-90% of 195 = 156-175.5 = 156-176 (rounded)
        assert result[4] == (156, 176)
        # Zone 5: 90-100% of 195 = 175.5-195 = 176-195 (rounded)
        assert result[5] == (176, 195)

    def test_calculates_boundaries_for_young_athlete(self) -> None:
        """Zone boundaries for a 20-year-old (max HR 200)."""
        max_hr = calculate_max_hr(20)
        result = calculate_zone_boundaries(max_hr)

        assert max_hr == 200
        assert result[1] == (100, 120)
        assert result[5] == (180, 200)

    def test_calculates_boundaries_for_older_athlete(self) -> None:
        """Zone boundaries for a 60-year-old (max HR 160)."""
        max_hr = calculate_max_hr(60)
        result = calculate_zone_boundaries(max_hr)

        assert max_hr == 160
        assert result[1] == (80, 96)
        assert result[5] == (144, 160)


class TestCalculateHRZones:
    """Tests for calculate_hr_zones() function."""

    def test_calculates_zones_for_single_zone_workout(self) -> None:
        """All HR samples in one zone should show 100% time in that zone."""
        from backend.models import HRZonesData
        from backend.hr_zones import calculate_hr_zones

        # Create samples all in Zone 3 (70-80% of max HR 200 = 140-160)
        ts_base = datetime(2024, 1, 15, 10, 0, 0)
        hr_samples = [
            (ts_base, 150),
            (datetime(2024, 1, 15, 10, 0, 10), 150),
            (datetime(2024, 1, 15, 10, 0, 20), 155),
            (datetime(2024, 1, 15, 10, 0, 30), 145),
        ]

        result = calculate_hr_zones(hr_samples, age=20)  # max HR = 200

        # Total time: 30 seconds
        # All time should be in Zone 3
        assert result.zone_1_seconds == 0
        assert result.zone_2_seconds == 0
        assert result.zone_3_seconds == 30
        assert result.zone_4_seconds == 0
        assert result.zone_5_seconds == 0

        assert result.zone_1_percent == 0.0
        assert result.zone_2_percent == 0.0
        assert result.zone_3_percent == 100.0
        assert result.zone_4_percent == 0.0
        assert result.zone_5_percent == 0.0

    def test_calculates_zones_across_multiple_zones(self) -> None:
        """Workout with HR across multiple zones should distribute time correctly."""
        from backend.models import HRZonesData
        from backend.hr_zones import calculate_hr_zones

        # Max HR for age 20 = 200
        # Zone 1: 100-120, Zone 2: 120-140, Zone 3: 140-160, Zone 4: 160-180, Zone 5: 180-200
        ts_base = datetime(2024, 1, 15, 10, 0, 0)
        hr_samples = [
            (ts_base, 110),                              # Zone 1
            (datetime(2024, 1, 15, 10, 0, 10), 130),    # Zone 2 (10s in Z1)
            (datetime(2024, 1, 15, 10, 0, 20), 150),    # Zone 3 (10s in Z2)
            (datetime(2024, 1, 15, 10, 0, 30), 170),    # Zone 4 (10s in Z3)
            (datetime(2024, 1, 15, 10, 0, 40), 190),    # Zone 5 (10s in Z4)
            (datetime(2024, 1, 15, 10, 0, 50), 195),    # Zone 5 (10s in Z5)
        ]

        result = calculate_hr_zones(hr_samples, age=20)

        # Total time: 50 seconds
        # Each zone gets 10 seconds
        assert result.zone_1_seconds == 10
        assert result.zone_2_seconds == 10
        assert result.zone_3_seconds == 10
        assert result.zone_4_seconds == 10
        assert result.zone_5_seconds == 10

        assert result.zone_1_percent == 20.0
        assert result.zone_2_percent == 20.0
        assert result.zone_3_percent == 20.0
        assert result.zone_4_percent == 20.0
        assert result.zone_5_percent == 20.0

    def test_calculates_zones_with_uneven_distribution(self) -> None:
        """Uneven time distribution across zones."""
        from backend.hr_zones import calculate_hr_zones

        # Age 30 -> max HR 190
        # Zone 1: 95-114, Zone 2: 114-133, Zone 3: 133-152, Zone 4: 152-171, Zone 5: 171-190
        ts_base = datetime(2024, 1, 15, 10, 0, 0)
        hr_samples = [
            (ts_base, 100),                              # Zone 1
            (datetime(2024, 1, 15, 10, 0, 30), 100),    # Zone 1 (30s in Z1)
            (datetime(2024, 1, 15, 10, 0, 40), 120),    # Zone 2 (10s in Z1)
            (datetime(2024, 1, 15, 10, 0, 50), 125),    # Zone 2 (10s in Z2)
            (datetime(2024, 1, 15, 10, 1, 0), 180),     # Zone 5 (10s in Z2)
        ]

        result = calculate_hr_zones(hr_samples, age=30)

        # Total time: 60 seconds
        # Zone 1: 40s, Zone 2: 20s, Zones 3-5: 0s
        assert result.zone_1_seconds == 40
        assert result.zone_2_seconds == 20
        assert result.zone_3_seconds == 0
        assert result.zone_4_seconds == 0
        assert result.zone_5_seconds == 0

        assert result.zone_1_percent == 66.7
        assert result.zone_2_percent == 33.3
        assert result.zone_3_percent == 0.0

    def test_raises_error_for_empty_samples(self) -> None:
        """Should raise ValueError when hr_samples is empty."""
        from backend.hr_zones import calculate_hr_zones

        with pytest.raises(ValueError, match="no valid heart rate samples found"):
            calculate_hr_zones([], age=30)

    def test_raises_error_for_invalid_age(self) -> None:
        """Should raise ValueError when age is invalid."""
        from backend.hr_zones import calculate_hr_zones

        ts_base = datetime(2024, 1, 15, 10, 0, 0)
        hr_samples = [
            (ts_base, 150),
            (datetime(2024, 1, 15, 10, 0, 10), 150),
        ]

        with pytest.raises(ValueError, match="age must be between 1 and 120"):
            calculate_hr_zones(hr_samples, age=0)

        with pytest.raises(ValueError, match="age must be between 1 and 120"):
            calculate_hr_zones(hr_samples, age=150)

    def test_filters_invalid_hr_samples(self) -> None:
        """Should filter out invalid HR samples before calculation."""
        from backend.hr_zones import calculate_hr_zones

        # Age 25 -> max HR 195
        # Zone 2: 117-136
        ts_base = datetime(2024, 1, 15, 10, 0, 0)
        hr_samples = [
            (ts_base, 0),                                # Invalid (zero)
            (datetime(2024, 1, 15, 10, 0, 5), 125),     # Valid - Zone 2
            (datetime(2024, 1, 15, 10, 0, 10), -10),    # Invalid (negative)
            (datetime(2024, 1, 15, 10, 0, 15), 130),    # Valid - Zone 2
            (datetime(2024, 1, 15, 10, 0, 20), 350),    # Invalid (too high)
            (datetime(2024, 1, 15, 10, 0, 25), 125),    # Valid - Zone 2
        ]

        result = calculate_hr_zones(hr_samples, age=25)

        # Should only process the 3 valid samples
        # Total time between valid samples: 25 - 5 = 20 seconds
        assert result.zone_2_seconds == 20
        assert result.zone_1_seconds == 0

    def test_raises_error_when_no_valid_samples(self) -> None:
        """Should raise error when all samples are invalid."""
        from backend.hr_zones import calculate_hr_zones

        ts_base = datetime(2024, 1, 15, 10, 0, 0)
        hr_samples = [
            (ts_base, 0),
            (datetime(2024, 1, 15, 10, 0, 10), -5),
            (datetime(2024, 1, 15, 10, 0, 20), 400),
        ]

        with pytest.raises(ValueError, match="no valid heart rate samples found"):
            calculate_hr_zones(hr_samples, age=30)

    def test_includes_max_hr_and_zone_boundaries(self) -> None:
        """Result should include max_hr and zone_boundaries."""
        from backend.hr_zones import calculate_hr_zones

        ts_base = datetime(2024, 1, 15, 10, 0, 0)
        hr_samples = [
            (ts_base, 150),
            (datetime(2024, 1, 15, 10, 0, 10), 150),
        ]

        result = calculate_hr_zones(hr_samples, age=40)  # max HR = 180

        assert result.max_hr == 180
        assert result.zone_boundaries is not None
        assert len(result.zone_boundaries) == 5
        assert result.zone_boundaries[1] == (90, 108)
        assert result.zone_boundaries[5] == (162, 180)

    def test_handles_zone_5_upper_boundary_inclusive(self) -> None:
        """Zone 5 should include max HR (upper boundary inclusive)."""
        from backend.hr_zones import calculate_hr_zones

        # Age 20 -> max HR 200, Zone 5: 180-200
        ts_base = datetime(2024, 1, 15, 10, 0, 0)
        hr_samples = [
            (ts_base, 200),                              # Exactly max HR
            (datetime(2024, 1, 15, 10, 0, 10), 200),    # Should be in Zone 5
        ]

        result = calculate_hr_zones(hr_samples, age=20)

        # Should count time in Zone 5
        assert result.zone_5_seconds == 10
        assert result.zone_5_percent == 100.0

    def test_handles_zone_boundaries_correctly(self) -> None:
        """Test HR values at zone boundaries are classified correctly."""
        from backend.hr_zones import calculate_hr_zones

        # Age 20 -> max HR 200
        # Zone 2: 120-140, Zone 3: 140-160
        ts_base = datetime(2024, 1, 15, 10, 0, 0)
        hr_samples = [
            (ts_base, 139),                              # Zone 2 (< 140) - lasts 10s
            (datetime(2024, 1, 15, 10, 0, 10), 140),    # Zone 3 (>= 140) - lasts 10s
            (datetime(2024, 1, 15, 10, 0, 20), 159),    # Zone 3 (< 160) - lasts 10s
            (datetime(2024, 1, 15, 10, 0, 30), 160),    # Zone 4 (>= 160) - no time after this
        ]

        result = calculate_hr_zones(hr_samples, age=20)

        # Zone 2: 10s (first sample)
        # Zone 3: 20s (second and third samples)
        # Zone 4: 0s (fourth sample has no time after it)
        assert result.zone_2_seconds == 10
        assert result.zone_3_seconds == 20
        assert result.zone_4_seconds == 0

    def test_sum_of_zone_times_equals_total_time(self) -> None:
        """Sum of all zone times should equal total session time (within tolerance)."""
        from backend.hr_zones import calculate_hr_zones

        ts_base = datetime(2024, 1, 15, 10, 0, 0)
        hr_samples = [
            (ts_base, 110),
            (datetime(2024, 1, 15, 10, 0, 15), 130),
            (datetime(2024, 1, 15, 10, 0, 37), 150),
            (datetime(2024, 1, 15, 10, 1, 3), 170),
        ]

        result = calculate_hr_zones(hr_samples, age=20)

        # Total time: 63 seconds
        total_zone_time = (
            result.zone_1_seconds +
            result.zone_2_seconds +
            result.zone_3_seconds +
            result.zone_4_seconds +
            result.zone_5_seconds
        )

        # Should be within 1 second tolerance (Requirement 2.12)
        assert abs(total_zone_time - 63) <= 1

    def test_percentages_rounded_to_one_decimal(self) -> None:
        """Percentages should be rounded to one decimal place."""
        from backend.hr_zones import calculate_hr_zones

        # Create scenario with non-round percentages
        ts_base = datetime(2024, 1, 15, 10, 0, 0)
        hr_samples = [
            (ts_base, 110),                              # Zone 1
            (datetime(2024, 1, 15, 10, 0, 7), 130),     # Zone 2 (7s in Z1)
            (datetime(2024, 1, 15, 10, 0, 14), 150),    # Zone 3 (7s in Z2)
            (datetime(2024, 1, 15, 10, 0, 21), 170),    # Zone 4 (7s in Z3)
        ]

        result = calculate_hr_zones(hr_samples, age=20)

        # Total time: 21 seconds
        # Each zone: 7 seconds = 7/21 = 33.333...%
        assert result.zone_1_percent == 33.3
        assert result.zone_2_percent == 33.3
        assert result.zone_3_percent == 33.3

        # All percentages should have exactly one decimal place
        for zone_num in range(1, 6):
            percent = getattr(result, f"zone_{zone_num}_percent")
            # Check that rounding to 1 decimal gives same value
            assert round(percent, 1) == percent

    def test_handles_single_sample(self) -> None:
        """Should raise error for single HR sample (need at least 2 samples)."""
        from backend.hr_zones import calculate_hr_zones

        ts_base = datetime(2024, 1, 15, 10, 0, 0)
        hr_samples = [
            (ts_base, 150),
        ]

        # Single sample should raise error - need at least 2 samples to calculate time
        with pytest.raises(ValueError, match="need at least 2 valid heart rate samples"):
            calculate_hr_zones(hr_samples, age=20)

    def test_realistic_swim_workout_zones(self) -> None:
        """Test with realistic swim workout HR pattern."""
        from backend.hr_zones import calculate_hr_zones

        # Age 35 -> max HR 185
        # Simulate warm-up -> main set -> cool-down
        ts_base = datetime(2024, 1, 15, 10, 0, 0)
        hr_samples = [
            # Warm-up: 5 minutes in Zone 2 (114-133 bpm)
            (ts_base, 120),
            (datetime(2024, 1, 15, 10, 5, 0), 120),
            # Main set: 15 minutes in Zone 4 (152-171 bpm)
            (datetime(2024, 1, 15, 10, 5, 0), 160),
            (datetime(2024, 1, 15, 10, 20, 0), 165),
            # Cool-down: 5 minutes in Zone 1 (95-114 bpm)
            (datetime(2024, 1, 15, 10, 20, 0), 100),
            (datetime(2024, 1, 15, 10, 25, 0), 105),
        ]

        result = calculate_hr_zones(hr_samples, age=35)

        # Total: 25 minutes = 1500 seconds
        # Zone 1: 5 min = 300s = 20%
        # Zone 2: 5 min = 300s = 20%
        # Zone 4: 15 min = 900s = 60%
        assert result.zone_1_seconds == 300
        assert result.zone_2_seconds == 300
        assert result.zone_3_seconds == 0
        assert result.zone_4_seconds == 900
        assert result.zone_5_seconds == 0

        assert result.zone_1_percent == 20.0
        assert result.zone_2_percent == 20.0
        assert result.zone_4_percent == 60.0
