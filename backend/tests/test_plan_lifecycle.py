"""Unit tests for plan_lifecycle module.

Tests state transition logic, single-active-plan invariant enforcement,
and error handling for invalid transitions.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from backend import plan_lifecycle


def _make_plan(plan_id: str, status: str = "draft") -> dict:
    """Helper to create a minimal plan dict for mocking."""
    return {
        "plan_id": plan_id,
        "user_id": "user-1",
        "status": status,
        "created_at": "2024-01-01T00:00:00+00:00",
        "status_updated_at": "2024-01-01T00:00:00+00:00",
        "goal": {"event": "100m Freestyle", "target_time": "1:00.0"},
        "duration_weeks": 8,
        "sessions_per_week": 3,
        "weeks": [],
    }


class TestGetPlanStatus:
    """Tests for get_plan_status."""

    @patch("backend.plan_lifecycle.structured_plan_store.get_plan_by_id")
    def test_returns_status_for_existing_plan(self, mock_get):
        mock_get.return_value = _make_plan("plan-1", status="active")
        assert plan_lifecycle.get_plan_status("user-1", "plan-1") == "active"

    @patch("backend.plan_lifecycle.structured_plan_store.get_plan_by_id")
    def test_raises_value_error_for_missing_plan(self, mock_get):
        mock_get.return_value = None
        with pytest.raises(ValueError, match="not found"):
            plan_lifecycle.get_plan_status("user-1", "nonexistent")


class TestActivatePlan:
    """Tests for activate_plan."""

    @patch("backend.plan_lifecycle.structured_plan_store.update_plan_status")
    @patch("backend.plan_lifecycle.structured_plan_store.get_user_structured_plans")
    @patch("backend.plan_lifecycle.structured_plan_store.get_plan_by_id")
    def test_activates_draft_plan(self, mock_get, mock_list, mock_update):
        mock_get.return_value = _make_plan("plan-1", status="draft")
        mock_list.return_value = []

        plan_lifecycle.activate_plan("user-1", "plan-1")

        mock_update.assert_called_once_with("user-1", "plan-1", "active")

    @patch("backend.plan_lifecycle.structured_plan_store.update_plan_status")
    @patch("backend.plan_lifecycle.structured_plan_store.get_user_structured_plans")
    @patch("backend.plan_lifecycle.structured_plan_store.get_plan_by_id")
    def test_archives_previously_active_plan(self, mock_get, mock_list, mock_update):
        mock_get.return_value = _make_plan("plan-2", status="draft")
        mock_list.return_value = [
            {"plan_id": "plan-1", "status": "active"},
            {"plan_id": "plan-2", "status": "draft"},
        ]

        plan_lifecycle.activate_plan("user-1", "plan-2")

        # Should archive plan-1, then activate plan-2
        calls = mock_update.call_args_list
        assert len(calls) == 2
        assert calls[0] == (("user-1", "plan-1", "archived"),)
        assert calls[1] == (("user-1", "plan-2", "active"),)

    @patch("backend.plan_lifecycle.structured_plan_store.get_plan_by_id")
    def test_raises_for_activating_archived_plan(self, mock_get):
        mock_get.return_value = _make_plan("plan-1", status="archived")

        with pytest.raises(ValueError, match="Invalid transition"):
            plan_lifecycle.activate_plan("user-1", "plan-1")

    @patch("backend.plan_lifecycle.structured_plan_store.get_plan_by_id")
    def test_raises_for_activating_already_active_plan(self, mock_get):
        mock_get.return_value = _make_plan("plan-1", status="active")

        with pytest.raises(ValueError, match="Invalid transition"):
            plan_lifecycle.activate_plan("user-1", "plan-1")

    @patch("backend.plan_lifecycle.structured_plan_store.get_plan_by_id")
    def test_raises_for_nonexistent_plan(self, mock_get):
        mock_get.return_value = None

        with pytest.raises(ValueError, match="not found"):
            plan_lifecycle.activate_plan("user-1", "nonexistent")


class TestArchivePlan:
    """Tests for archive_plan."""

    @patch("backend.plan_lifecycle.structured_plan_store.update_plan_status")
    @patch("backend.plan_lifecycle.structured_plan_store.get_plan_by_id")
    def test_archives_active_plan(self, mock_get, mock_update):
        mock_get.return_value = _make_plan("plan-1", status="active")

        plan_lifecycle.archive_plan("user-1", "plan-1")

        mock_update.assert_called_once_with("user-1", "plan-1", "archived")

    @patch("backend.plan_lifecycle.structured_plan_store.get_plan_by_id")
    def test_raises_for_archiving_draft_plan(self, mock_get):
        mock_get.return_value = _make_plan("plan-1", status="draft")

        with pytest.raises(ValueError, match="Invalid transition"):
            plan_lifecycle.archive_plan("user-1", "plan-1")

    @patch("backend.plan_lifecycle.structured_plan_store.get_plan_by_id")
    def test_raises_for_archiving_already_archived_plan(self, mock_get):
        mock_get.return_value = _make_plan("plan-1", status="archived")

        with pytest.raises(ValueError, match="Invalid transition"):
            plan_lifecycle.archive_plan("user-1", "plan-1")

    @patch("backend.plan_lifecycle.structured_plan_store.get_plan_by_id")
    def test_raises_for_nonexistent_plan(self, mock_get):
        mock_get.return_value = None

        with pytest.raises(ValueError, match="not found"):
            plan_lifecycle.archive_plan("user-1", "nonexistent")
