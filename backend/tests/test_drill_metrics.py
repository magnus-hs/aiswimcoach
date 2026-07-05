"""
Tests for drill metrics exclusion in parse_fit.

Validates Requirements 8.1, 8.2, 8.3, 8.4:
  - Drill lengths excluded from average pace calculation
  - Drill lengths excluded from average SWOLF calculation
  - Drill lengths excluded from average stroke rate calculation
  - All-drill sessions compute metrics from drill data without error
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from fit_parser import parse_fit, compute_swolf, speed_to_pace, MetricsMissingError


def _make_field(name: str, value):
    """Create a mock field object with .name and .value attributes."""
    field = MagicMock()
    field.name = name
    field.value = value
    return field


def _make_record(**fields):
    """Create a mock FIT record whose iteration yields field objects."""
    mock_record = MagicMock()
    mock_fields = [_make_field(name, value) for name, value in fields.items()]
    mock_record.fields = mock_fields
    mock_record.__iter__ = lambda self: iter(self.fields)
    return mock_record


class TestMixedSessionDrillExclusion:
    """Test that drill lengths are excluded from session averages in mixed sessions."""

    @patch("fit_parser.FitFile")
    def test_pace_excludes_drill_lengths(self, mock_fitfile_class: MagicMock) -> None:
        """Req 8.1: Drill lengths with no valid avg_speed excluded from pace."""
        mock_fitfile = MagicMock()
        mock_fitfile_class.return_value = mock_fitfile

        # Two freestyle records with known speed, one drill with different speed
        freestyle_1 = _make_record(
            swim_stroke=0, avg_speed=1.0, avg_swimming_cadence=30,
            total_strokes=10, total_elapsed_time=25.0,
        )
        freestyle_2 = _make_record(
            swim_stroke=0, avg_speed=2.0, avg_swimming_cadence=40,
            total_strokes=12, total_elapsed_time=20.0,
        )
        drill = _make_record(
            swim_stroke=4, avg_speed=0.5, avg_swimming_cadence=0,
            total_strokes=0, total_elapsed_time=30.0,
        )

        # Session record for pool length
        session_record = _make_record(pool_length=25.0)

        def get_messages(msg_type):
            if msg_type == "session":
                return [session_record]
            elif msg_type == "length":
                return [freestyle_1, drill, freestyle_2]
            return []

        mock_fitfile.get_messages.side_effect = get_messages

        result = parse_fit(b"fake_fit_bytes")

        # Pace should be computed from only freestyle records (speeds 1.0 and 2.0)
        # speed_to_pace(1.0) = 100.0, speed_to_pace(2.0) = 50.0
        # Average = (100.0 + 50.0) / 2 = 75.0
        expected_pace = (speed_to_pace(1.0) + speed_to_pace(2.0)) / 2
        assert result.pace == pytest.approx(expected_pace)

    @patch("fit_parser.FitFile")
    def test_swolf_excludes_drill_lengths(self, mock_fitfile_class: MagicMock) -> None:
        """Req 8.2: Drill lengths excluded from SWOLF calculation."""
        mock_fitfile = MagicMock()
        mock_fitfile_class.return_value = mock_fitfile

        # Freestyle with SWOLF components: strokes=10, elapsed=25 → SWOLF=35
        freestyle = _make_record(
            swim_stroke=0, avg_speed=1.5, avg_swimming_cadence=30,
            total_strokes=10, total_elapsed_time=25.0,
        )
        # Drill with different SWOLF components: strokes=5, elapsed=30 → SWOLF=35
        # Even though SWOLF happens to be same, drill should be excluded
        drill = _make_record(
            swim_stroke=4, avg_speed=0.8, avg_swimming_cadence=0,
            total_strokes=5, total_elapsed_time=40.0,
        )

        session_record = _make_record(pool_length=25.0)

        def get_messages(msg_type):
            if msg_type == "session":
                return [session_record]
            elif msg_type == "length":
                return [freestyle, drill]
            return []

        mock_fitfile.get_messages.side_effect = get_messages

        result = parse_fit(b"fake_fit_bytes")

        # SWOLF from freestyle only: total_strokes(10) + total_elapsed_time(25) = 35
        expected_swolf = 35.0
        assert result.swolf == pytest.approx(expected_swolf)

    @patch("fit_parser.FitFile")
    def test_stroke_rate_excludes_drill_lengths(self, mock_fitfile_class: MagicMock) -> None:
        """Req 8.3: Drill lengths with cadence 0 or null excluded from stroke rate."""
        mock_fitfile = MagicMock()
        mock_fitfile_class.return_value = mock_fitfile

        freestyle_1 = _make_record(
            swim_stroke=0, avg_speed=1.5, avg_swimming_cadence=30,
            total_strokes=10, total_elapsed_time=25.0,
        )
        freestyle_2 = _make_record(
            swim_stroke=0, avg_speed=1.8, avg_swimming_cadence=40,
            total_strokes=12, total_elapsed_time=22.0,
        )
        # Drill with cadence=0 (should be excluded)
        drill = _make_record(
            swim_stroke=4, avg_speed=0.8, avg_swimming_cadence=0,
            total_strokes=0, total_elapsed_time=30.0,
        )

        session_record = _make_record(pool_length=25.0)

        def get_messages(msg_type):
            if msg_type == "session":
                return [session_record]
            elif msg_type == "length":
                return [freestyle_1, drill, freestyle_2]
            return []

        mock_fitfile.get_messages.side_effect = get_messages

        result = parse_fit(b"fake_fit_bytes")

        # Stroke rate from only freestyle records: (30 + 40) / 2 = 35
        expected_stroke_rate = (30.0 + 40.0) / 2
        assert result.stroke_rate == pytest.approx(expected_stroke_rate)

    @patch("fit_parser.FitFile")
    def test_drill_with_valid_cadence_still_excluded(self, mock_fitfile_class: MagicMock) -> None:
        """Even a drill with valid cadence > 0 is excluded from stroke rate when non-drills exist."""
        mock_fitfile = MagicMock()
        mock_fitfile_class.return_value = mock_fitfile

        freestyle = _make_record(
            swim_stroke=0, avg_speed=1.5, avg_swimming_cadence=32,
            total_strokes=10, total_elapsed_time=25.0,
        )
        # Drill that has cadence > 0 — still excluded from averages
        drill = _make_record(
            swim_stroke=4, avg_speed=1.0, avg_swimming_cadence=20,
            total_strokes=5, total_elapsed_time=28.0,
        )

        session_record = _make_record(pool_length=25.0)

        def get_messages(msg_type):
            if msg_type == "session":
                return [session_record]
            elif msg_type == "length":
                return [freestyle, drill]
            return []

        mock_fitfile.get_messages.side_effect = get_messages

        result = parse_fit(b"fake_fit_bytes")

        # Only freestyle cadence used: 32
        assert result.stroke_rate == pytest.approx(32.0)


class TestAllDrillSession:
    """Test that all-drill sessions compute metrics from drill data without error."""

    @patch("fit_parser.FitFile")
    def test_all_drill_session_no_error(self, mock_fitfile_class: MagicMock) -> None:
        """Req 8.4: All-drill session should NOT raise MetricsMissingError."""
        mock_fitfile = MagicMock()
        mock_fitfile_class.return_value = mock_fitfile

        drill_1 = _make_record(
            swim_stroke=4, avg_speed=0.8, avg_swimming_cadence=15,
            total_strokes=5, total_elapsed_time=30.0,
        )
        drill_2 = _make_record(
            swim_stroke=4, avg_speed=0.9, avg_swimming_cadence=18,
            total_strokes=6, total_elapsed_time=28.0,
        )

        session_record = _make_record(pool_length=25.0)

        def get_messages(msg_type):
            if msg_type == "session":
                return [session_record]
            elif msg_type == "length":
                return [drill_1, drill_2]
            return []

        mock_fitfile.get_messages.side_effect = get_messages

        # Should not raise
        result = parse_fit(b"fake_fit_bytes")

        # Metrics should use drill data as fallback
        expected_pace = (speed_to_pace(0.8) + speed_to_pace(0.9)) / 2
        assert result.pace == pytest.approx(expected_pace)

        expected_stroke_rate = (15.0 + 18.0) / 2
        assert result.stroke_rate == pytest.approx(expected_stroke_rate)

        # SWOLF from total_strokes + total_elapsed_time: (5+30)=35, (6+28)=34
        expected_swolf = (35.0 + 34.0) / 2
        assert result.swolf == pytest.approx(expected_swolf)

    @patch("fit_parser.FitFile")
    def test_all_drill_session_no_speed_raises_error(self, mock_fitfile_class: MagicMock) -> None:
        """All-drill session with no valid metrics at all raises MetricsMissingError."""
        mock_fitfile = MagicMock()
        mock_fitfile_class.return_value = mock_fitfile

        # Drills with no valid data
        drill = _make_record(
            swim_stroke=4, avg_speed=None, avg_swimming_cadence=0,
            total_strokes=0, total_elapsed_time=0,
        )

        session_record = _make_record(pool_length=25.0)

        def get_messages(msg_type):
            if msg_type == "session":
                return [session_record]
            elif msg_type == "length":
                return [drill]
            return []

        mock_fitfile.get_messages.side_effect = get_messages

        with pytest.raises(MetricsMissingError):
            parse_fit(b"fake_fit_bytes")


class TestNoDrillSession:
    """Test that sessions with no drill lengths have unchanged behavior."""

    @patch("fit_parser.FitFile")
    def test_no_drills_uses_all_lengths(self, mock_fitfile_class: MagicMock) -> None:
        """Session with no drills: all lengths contribute to averages."""
        mock_fitfile = MagicMock()
        mock_fitfile_class.return_value = mock_fitfile

        freestyle_1 = _make_record(
            swim_stroke=0, avg_speed=1.5, avg_swimming_cadence=30,
            total_strokes=10, total_elapsed_time=25.0,
        )
        freestyle_2 = _make_record(
            swim_stroke=0, avg_speed=1.8, avg_swimming_cadence=36,
            total_strokes=12, total_elapsed_time=22.0,
        )
        backstroke = _make_record(
            swim_stroke=1, avg_speed=1.2, avg_swimming_cadence=28,
            total_strokes=8, total_elapsed_time=28.0,
        )

        session_record = _make_record(pool_length=25.0)

        def get_messages(msg_type):
            if msg_type == "session":
                return [session_record]
            elif msg_type == "length":
                return [freestyle_1, freestyle_2, backstroke]
            return []

        mock_fitfile.get_messages.side_effect = get_messages

        result = parse_fit(b"fake_fit_bytes")

        # All three lengths contribute to averages
        expected_pace = (speed_to_pace(1.5) + speed_to_pace(1.8) + speed_to_pace(1.2)) / 3
        assert result.pace == pytest.approx(expected_pace)

        expected_stroke_rate = (30.0 + 36.0 + 28.0) / 3
        assert result.stroke_rate == pytest.approx(expected_stroke_rate)

        # SWOLF: (10+25)=35, (12+22)=34, (8+28)=36 → avg=35
        expected_swolf = (35.0 + 34.0 + 36.0) / 3
        assert result.swolf == pytest.approx(expected_swolf)

    @patch("fit_parser.FitFile")
    def test_no_data_raises_metrics_missing(self, mock_fitfile_class: MagicMock) -> None:
        """Session with no lengths at all raises MetricsMissingError."""
        mock_fitfile = MagicMock()
        mock_fitfile_class.return_value = mock_fitfile

        session_record = _make_record(pool_length=25.0)

        def get_messages(msg_type):
            if msg_type == "session":
                return [session_record]
            elif msg_type == "length":
                return []
            elif msg_type == "lap":
                return []
            return []

        mock_fitfile.get_messages.side_effect = get_messages

        with pytest.raises(MetricsMissingError):
            parse_fit(b"fake_fit_bytes")
