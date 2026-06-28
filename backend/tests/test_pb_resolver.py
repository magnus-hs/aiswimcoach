"""
Unit tests for PB resolver module.

Tests: save_personal_best, get_personal_bests, resolve_personal_best,
derive_pb_from_history, and _scale_pace_to_distance.

Requirements: 3.1, 3.2, 3.3, 3.4, 7.1, 7.2, 7.4
"""
from __future__ import annotations

import os
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

# Set env vars before importing pb_resolver
os.environ.setdefault("PROFILES_TABLE", "UserProfiles")
os.environ.setdefault("SESSIONS_TABLE", "Sessions")

from pb_resolver import (
    PACE_DEGRADATION_FACTORS,
    PBResolverError,
    _parse_event,
    _scale_pace_to_distance,
    derive_pb_from_history,
    get_personal_bests,
    resolve_personal_best,
    save_personal_best,
)


class TestParseEvent:
    """Tests for _parse_event helper."""

    def test_standard_event(self):
        result = _parse_event("100m Freestyle")
        assert result == (100, "Freestyle")

    def test_longer_distance(self):
        result = _parse_event("200m Backstroke")
        assert result == (200, "Backstroke")

    def test_1500m_event(self):
        result = _parse_event("1500m Freestyle")
        assert result == (1500, "Freestyle")

    def test_invalid_format(self):
        result = _parse_event("invalid")
        assert result is None

    def test_missing_m(self):
        result = _parse_event("100 Freestyle")
        assert result is None

    def test_case_insensitive(self):
        result = _parse_event("100M Freestyle")
        assert result == (100, "Freestyle")


class TestScalePaceToDistance:
    """Tests for pace degradation scaling logic."""

    def test_100m_is_identity(self):
        """100m factor is 1.0, so time equals pace."""
        result = _scale_pace_to_distance(60.0, 100)
        assert result == 60.0

    def test_200m_has_fatigue_factor(self):
        """200m should be slightly more than 2x the 100m pace."""
        result = _scale_pace_to_distance(60.0, 200)
        # 60 * 2.05 = 123.0
        assert result == pytest.approx(123.0)

    def test_400m_scaling(self):
        """400m uses factor 4.20."""
        result = _scale_pace_to_distance(60.0, 400)
        assert result == pytest.approx(252.0)

    def test_monotonically_increasing(self):
        """Longer distances should always result in larger times."""
        pace = 65.0
        distances = sorted(PACE_DEGRADATION_FACTORS.keys())
        times = [_scale_pace_to_distance(pace, d) for d in distances]
        for i in range(len(times) - 1):
            assert times[i] < times[i + 1], (
                f"Time at {distances[i]}m ({times[i]}) should be less than "
                f"time at {distances[i+1]}m ({times[i+1]})"
            )

    def test_interpolation_between_distances(self):
        """Non-standard distances should interpolate between known points."""
        pace = 60.0
        # 150m is between 100m (factor 1.0) and 200m (factor 2.05)
        result = _scale_pace_to_distance(pace, 150)
        time_100 = _scale_pace_to_distance(pace, 100)
        time_200 = _scale_pace_to_distance(pace, 200)
        assert time_100 < result < time_200

    def test_50m_is_less_than_100m(self):
        """50m should be faster than 100m."""
        pace = 60.0
        result_50 = _scale_pace_to_distance(pace, 50)
        result_100 = _scale_pace_to_distance(pace, 100)
        assert result_50 < result_100


class TestSavePersonalBest:
    """Tests for save_personal_best."""

    def test_rejects_empty_event(self):
        with pytest.raises(ValueError, match="Event name must be non-empty"):
            save_personal_best("user1", "", 60.0)

    def test_rejects_whitespace_event(self):
        with pytest.raises(ValueError, match="Event name must be non-empty"):
            save_personal_best("user1", "   ", 60.0)

    def test_rejects_zero_time(self):
        with pytest.raises(ValueError, match="time_seconds must be a positive number"):
            save_personal_best("user1", "100m Freestyle", 0)

    def test_rejects_negative_time(self):
        with pytest.raises(ValueError, match="time_seconds must be a positive number"):
            save_personal_best("user1", "100m Freestyle", -5.0)

    @patch("pb_resolver._get_profiles_table")
    def test_saves_to_dynamodb(self, mock_get_table):
        """Test successful save calls update_item with correct params."""
        mock_table = MagicMock()
        mock_get_table.return_value = mock_table

        save_personal_best("user123", "100m Freestyle", 65.5)

        mock_table.update_item.assert_called_once()
        call_kwargs = mock_table.update_item.call_args[1]
        assert call_kwargs["Key"] == {"user_id": "user123"}
        assert "#event" in call_kwargs["ExpressionAttributeNames"]
        assert call_kwargs["ExpressionAttributeNames"]["#event"] == "100m Freestyle"

    @patch("pb_resolver._get_profiles_table")
    def test_creates_map_on_first_save(self, mock_get_table):
        """If personal_bests map doesn't exist, creates it."""
        mock_table = MagicMock()
        mock_get_table.return_value = mock_table

        # First call fails with ValidationException (map doesn't exist)
        from botocore.exceptions import ClientError

        error_response = {"Error": {"Code": "ValidationException", "Message": "path does not exist"}}
        mock_table.update_item.side_effect = [
            ClientError(error_response, "UpdateItem"),
            None,  # Second call succeeds
        ]

        save_personal_best("user123", "100m Freestyle", 65.5)

        assert mock_table.update_item.call_count == 2


class TestResolvePersonalBest:
    """Tests for resolve_personal_best."""

    @patch("pb_resolver._get_sessions_table")
    @patch("pb_resolver._get_profiles_table")
    def test_returns_manual_pb_when_present(self, mock_profiles, mock_sessions):
        """Manual PB takes priority over derived."""
        mock_table = MagicMock()
        mock_profiles.return_value = mock_table
        mock_table.get_item.return_value = {
            "Item": {
                "personal_bests": {
                    "100m Freestyle": {
                        "time_seconds": Decimal("65.5"),
                        "source": "manual",
                        "updated_at": "2024-01-01T00:00:00.000Z",
                    }
                }
            }
        }

        result = resolve_personal_best("user1", "100m Freestyle")
        assert result == 65.5

    @patch("pb_resolver._get_sessions_table")
    @patch("pb_resolver._get_profiles_table")
    def test_derives_from_history_when_no_manual(self, mock_profiles, mock_sessions):
        """Derives PB from session history when no manual entry exists."""
        mock_profile_table = MagicMock()
        mock_profiles.return_value = mock_profile_table
        mock_profile_table.get_item.return_value = {"Item": {}}

        mock_session_table = MagicMock()
        mock_sessions.return_value = mock_session_table
        mock_session_table.query.return_value = {
            "Items": [
                {
                    "stroke_type": "Freestyle",
                    "average_pace_per_100m": Decimal("65.0"),
                    "session_date": "2024-01-15T10:00:00Z",
                },
                {
                    "stroke_type": "Freestyle",
                    "average_pace_per_100m": Decimal("68.0"),
                    "session_date": "2024-01-10T10:00:00Z",
                },
            ]
        }

        result = resolve_personal_best("user1", "100m Freestyle")
        # Should use fastest pace (65.0) * factor for 100m (1.0) = 65.0
        assert result == 65.0

    @patch("pb_resolver._get_sessions_table")
    @patch("pb_resolver._get_profiles_table")
    def test_returns_none_when_no_data(self, mock_profiles, mock_sessions):
        """Returns None when no manual PB and no session history."""
        mock_profile_table = MagicMock()
        mock_profiles.return_value = mock_profile_table
        mock_profile_table.get_item.return_value = {"Item": {}}

        mock_session_table = MagicMock()
        mock_sessions.return_value = mock_session_table
        mock_session_table.query.return_value = {"Items": []}

        result = resolve_personal_best("user1", "100m Freestyle")
        assert result is None

    @patch("pb_resolver._get_sessions_table")
    @patch("pb_resolver._get_profiles_table")
    def test_returns_none_for_invalid_event_format(self, mock_profiles, mock_sessions):
        """Returns None for event strings that can't be parsed."""
        mock_profile_table = MagicMock()
        mock_profiles.return_value = mock_profile_table
        mock_profile_table.get_item.return_value = {"Item": {}}

        result = resolve_personal_best("user1", "invalid_event")
        assert result is None


class TestDeriveFromHistory:
    """Tests for derive_pb_from_history."""

    @patch("pb_resolver._get_sessions_table")
    def test_uses_fastest_pace(self, mock_sessions):
        """Should pick the fastest (lowest) pace from matching sessions."""
        mock_table = MagicMock()
        mock_sessions.return_value = mock_table
        mock_table.query.return_value = {
            "Items": [
                {
                    "stroke_type": "Freestyle",
                    "average_pace_per_100m": Decimal("70.0"),
                    "session_date": "2024-01-10T10:00:00Z",
                },
                {
                    "stroke_type": "Freestyle",
                    "average_pace_per_100m": Decimal("65.0"),
                    "session_date": "2024-01-15T10:00:00Z",
                },
                {
                    "stroke_type": "Backstroke",
                    "average_pace_per_100m": Decimal("60.0"),
                    "session_date": "2024-01-12T10:00:00Z",
                },
            ]
        }

        # For 100m Freestyle, should use 65.0 (fastest Freestyle pace)
        result = derive_pb_from_history("user1", "Freestyle", 100)
        assert result == 65.0

    @patch("pb_resolver._get_sessions_table")
    def test_scales_pace_for_200m(self, mock_sessions):
        """Derives 200m PB with degradation factor."""
        mock_table = MagicMock()
        mock_sessions.return_value = mock_table
        mock_table.query.return_value = {
            "Items": [
                {
                    "stroke_type": "Freestyle",
                    "average_pace_per_100m": Decimal("60.0"),
                    "session_date": "2024-01-15T10:00:00Z",
                },
            ]
        }

        result = derive_pb_from_history("user1", "Freestyle", 200)
        # 60.0 * 2.05 = 123.0
        assert result == pytest.approx(123.0)

    @patch("pb_resolver._get_sessions_table")
    def test_returns_none_no_matching_stroke(self, mock_sessions):
        """Returns None when no sessions match the stroke type."""
        mock_table = MagicMock()
        mock_sessions.return_value = mock_table
        mock_table.query.return_value = {
            "Items": [
                {
                    "stroke_type": "Backstroke",
                    "average_pace_per_100m": Decimal("65.0"),
                    "session_date": "2024-01-15T10:00:00Z",
                },
            ]
        }

        result = derive_pb_from_history("user1", "Freestyle", 100)
        assert result is None

    @patch("pb_resolver._get_sessions_table")
    def test_skips_plan_items(self, mock_sessions):
        """Skips items with PLAN# or MPLAN# sort keys."""
        mock_table = MagicMock()
        mock_sessions.return_value = mock_table
        mock_table.query.return_value = {
            "Items": [
                {
                    "stroke_type": "Freestyle",
                    "average_pace_per_100m": Decimal("50.0"),
                    "session_date": "PLAN#2024-01-15",
                },
                {
                    "stroke_type": "Freestyle",
                    "average_pace_per_100m": Decimal("65.0"),
                    "session_date": "2024-01-15T10:00:00Z",
                },
            ]
        }

        result = derive_pb_from_history("user1", "Freestyle", 100)
        assert result == 65.0

    @patch("pb_resolver._get_sessions_table")
    def test_case_insensitive_stroke_matching(self, mock_sessions):
        """Stroke type matching should be case-insensitive."""
        mock_table = MagicMock()
        mock_sessions.return_value = mock_table
        mock_table.query.return_value = {
            "Items": [
                {
                    "stroke_type": "freestyle",
                    "average_pace_per_100m": Decimal("65.0"),
                    "session_date": "2024-01-15T10:00:00Z",
                },
            ]
        }

        result = derive_pb_from_history("user1", "Freestyle", 100)
        assert result == 65.0


class TestGetPersonalBests:
    """Tests for get_personal_bests."""

    @patch("pb_resolver._get_sessions_table")
    @patch("pb_resolver._get_profiles_table")
    def test_returns_manual_pbs(self, mock_profiles, mock_sessions):
        """Returns manually entered PBs."""
        mock_profile_table = MagicMock()
        mock_profiles.return_value = mock_profile_table
        mock_profile_table.get_item.return_value = {
            "Item": {
                "personal_bests": {
                    "100m Freestyle": {
                        "time_seconds": Decimal("65.5"),
                        "source": "manual",
                        "updated_at": "2024-01-01T00:00:00.000Z",
                    }
                }
            }
        }

        mock_session_table = MagicMock()
        mock_sessions.return_value = mock_session_table
        mock_session_table.query.return_value = {"Items": []}

        result = get_personal_bests("user1")
        assert len(result) == 1
        assert result[0]["event"] == "100m Freestyle"
        assert result[0]["time_seconds"] == 65.5
        assert result[0]["source"] == "manual"

    @patch("pb_resolver._get_sessions_table")
    @patch("pb_resolver._get_profiles_table")
    def test_returns_both_manual_and_derived_for_same_event(self, mock_profiles, mock_sessions):
        """Returns both manual and derived PBs for the same event."""
        mock_profile_table = MagicMock()
        mock_profiles.return_value = mock_profile_table
        mock_profile_table.get_item.return_value = {
            "Item": {
                "personal_bests": {
                    "100m Freestyle": {
                        "time_seconds": Decimal("65.5"),
                        "source": "manual",
                        "updated_at": "2024-01-01T00:00:00.000Z",
                    }
                }
            }
        }

        mock_session_table = MagicMock()
        mock_sessions.return_value = mock_session_table
        # Session history shows a faster pace — both should be returned
        mock_session_table.query.return_value = {
            "Items": [
                {
                    "stroke_type": "Freestyle",
                    "average_pace_per_100m": Decimal("60.0"),
                    "session_date": "2024-01-15T10:00:00Z",
                },
            ]
        }

        result = get_personal_bests("user1")
        # Should have both manual AND derived entries for 100m Freestyle
        freestyle_pbs = [pb for pb in result if pb["event"] == "100m Freestyle"]
        assert len(freestyle_pbs) == 2
        sources = {pb["source"] for pb in freestyle_pbs}
        assert sources == {"manual", "derived"}
        manual_pb = next(pb for pb in freestyle_pbs if pb["source"] == "manual")
        derived_pb = next(pb for pb in freestyle_pbs if pb["source"] == "derived")
        assert manual_pb["time_seconds"] == 65.5
        assert derived_pb["time_seconds"] == 60.0

    @patch("pb_resolver._get_sessions_table")
    @patch("pb_resolver._get_profiles_table")
    def test_returns_empty_list_when_no_data(self, mock_profiles, mock_sessions):
        """Returns empty list when no PBs and no history."""
        mock_profile_table = MagicMock()
        mock_profiles.return_value = mock_profile_table
        mock_profile_table.get_item.return_value = {"Item": {}}

        mock_session_table = MagicMock()
        mock_sessions.return_value = mock_session_table
        mock_session_table.query.return_value = {"Items": []}

        result = get_personal_bests("user1")
        assert result == []
