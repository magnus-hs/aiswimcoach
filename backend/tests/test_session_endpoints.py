"""
Unit tests for session history endpoints in backend/handler.py

Tests cover the session endpoints with authentication:
  - GET /sessions → Get user session history
  - GET /sessions/:id → Get session by ID

Requirements: 16.3, 19.3
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from backend.handler import handler


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

MOCK_CONTEXT = MagicMock()


def _assert_error_response(response: dict, status_code: int, error_substring: str) -> None:
    """Assert the response is an error with the expected status and message."""
    assert response["statusCode"] == status_code
    assert response["headers"]["Content-Type"] == "application/json"
    body = json.loads(response["body"])
    assert "error" in body
    assert error_substring in body["error"]


# ---------------------------------------------------------------------------
# GET /sessions endpoint tests
# ---------------------------------------------------------------------------


class TestGetSessionsEndpoint:
    """GET /sessions endpoint tests."""

    @patch("backend.middleware.verify_token")
    @patch("backend.handler.get_user_sessions")
    def test_successful_retrieval(
        self, mock_get_sessions: MagicMock, mock_verify: MagicMock
    ) -> None:
        """Successfully retrieves user sessions with authentication."""
        from backend.models import Session
        
        # Mock token verification
        mock_verify.return_value = {
            "user_id": "test-user-123",
            "email": "test@example.com",
        }
        
        # Mock session data
        mock_sessions = [
            Session(
                session_id="session-1",
                user_id="test-user-123",
                session_date="2024-01-15T10:00:00Z",
                pool_length_meters=25,
                total_distance_meters=2000,
                total_time_seconds=2400,
                stroke_type="freestyle",
                average_pace_per_100m=120.0,
                swolf_score=45,
                stroke_rate=30.0,
                uploaded_at="2024-01-15T11:00:00Z",
                s3_key="uploads/file1.fit",
            ),
            Session(
                session_id="session-2",
                user_id="test-user-123",
                session_date="2024-01-16T10:00:00Z",
                pool_length_meters=25,
                total_distance_meters=1500,
                total_time_seconds=1800,
                stroke_type="freestyle",
                average_pace_per_100m=115.0,
                swolf_score=42,
                stroke_rate=32.0,
                uploaded_at="2024-01-16T11:00:00Z",
                s3_key="uploads/file2.fit",
            ),
        ]
        mock_get_sessions.return_value = mock_sessions
        
        event = {
            "httpMethod": "GET",
            "path": "/sessions",
            "headers": {"Authorization": "Bearer valid-token"},
            "queryStringParameters": None,
        }
        
        response = handler(event, MOCK_CONTEXT)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "sessions" in body
        assert len(body["sessions"]) == 2
        assert body["sessions"][0]["session_id"] == "session-1"
        assert body["sessions"][0]["total_distance_meters"] == 2000
        assert body["sessions"][1]["session_id"] == "session-2"
        
        # Verify get_user_sessions was called with user_id
        mock_get_sessions.assert_called_once_with("test-user-123", None, None)

    @patch("backend.middleware.verify_token")
    @patch("backend.handler.get_user_sessions")
    def test_retrieval_with_date_filters(
        self, mock_get_sessions: MagicMock, mock_verify: MagicMock
    ) -> None:
        """Successfully retrieves sessions with date range filters."""
        mock_verify.return_value = {
            "user_id": "test-user-123",
            "email": "test@example.com",
        }
        
        mock_get_sessions.return_value = []
        
        event = {
            "httpMethod": "GET",
            "path": "/sessions",
            "headers": {"Authorization": "Bearer valid-token"},
            "queryStringParameters": {
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-01-31T23:59:59Z",
            },
        }
        
        response = handler(event, MOCK_CONTEXT)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "sessions" in body
        assert len(body["sessions"]) == 0
        
        # Verify get_user_sessions was called with date filters
        mock_get_sessions.assert_called_once_with(
            "test-user-123",
            "2024-01-01T00:00:00Z",
            "2024-01-31T23:59:59Z"
        )

    def test_missing_authentication_returns_401(self) -> None:
        """Missing authentication returns 401."""
        event = {
            "httpMethod": "GET",
            "path": "/sessions",
            "headers": {},
            "queryStringParameters": None,
        }
        
        response = handler(event, MOCK_CONTEXT)
        
        _assert_error_response(response, 401, "Authorization header required")

    @patch("backend.middleware.verify_token")
    @patch("backend.handler.get_user_sessions")
    def test_storage_error_returns_500(
        self, mock_get_sessions: MagicMock, mock_verify: MagicMock
    ) -> None:
        """Storage error returns 500."""
        mock_verify.return_value = {
            "user_id": "test-user-123",
            "email": "test@example.com",
        }
        
        mock_get_sessions.side_effect = Exception("DynamoDB error")
        
        event = {
            "httpMethod": "GET",
            "path": "/sessions",
            "headers": {"Authorization": "Bearer valid-token"},
            "queryStringParameters": None,
        }
        
        response = handler(event, MOCK_CONTEXT)
        
        _assert_error_response(response, 500, "Session retrieval failure")


# ---------------------------------------------------------------------------
# GET /sessions/:id endpoint tests
# ---------------------------------------------------------------------------


class TestGetSessionByIdEndpoint:
    """GET /sessions/:id endpoint tests."""

    @patch("backend.middleware.verify_token")
    @patch("backend.handler.get_session_by_id")
    def test_successful_retrieval(
        self, mock_get_session: MagicMock, mock_verify: MagicMock
    ) -> None:
        """Successfully retrieves session by ID with authentication."""
        from backend.models import Session, HRZonesData
        
        # Mock token verification
        mock_verify.return_value = {
            "user_id": "test-user-123",
            "email": "test@example.com",
        }
        
        # Mock session data with HR zones
        mock_session = Session(
            session_id="session-123",
            user_id="test-user-123",
            session_date="2024-01-15T10:00:00Z",
            pool_length_meters=25,
            total_distance_meters=2000,
            total_time_seconds=2400,
            stroke_type="freestyle",
            average_pace_per_100m=120.0,
            swolf_score=45,
            stroke_rate=30.0,
            uploaded_at="2024-01-15T11:00:00Z",
            s3_key="uploads/file1.fit",
            hr_zones=HRZonesData(
                zone_1_seconds=100,
                zone_2_seconds=200,
                zone_3_seconds=300,
                zone_4_seconds=200,
                zone_5_seconds=100,
                zone_1_percent=11.1,
                zone_2_percent=22.2,
                zone_3_percent=33.3,
                zone_4_percent=22.2,
                zone_5_percent=11.1,
                max_hr=190,
                zone_boundaries={
                    1: (95, 114),
                    2: (114, 133),
                    3: (133, 152),
                    4: (152, 171),
                    5: (171, 190),
                }
            ),
        )
        mock_get_session.return_value = mock_session
        
        event = {
            "httpMethod": "GET",
            "path": "/sessions/session-123",
            "headers": {"Authorization": "Bearer valid-token"},
        }
        
        response = handler(event, MOCK_CONTEXT)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["session_id"] == "session-123"
        assert body["user_id"] == "test-user-123"
        assert body["total_distance_meters"] == 2000
        assert "hr_zones" in body
        assert body["hr_zones"]["zone_1_seconds"] == 100
        
        # Verify get_session_by_id was called
        mock_get_session.assert_called_once_with("session-123")

    @patch("backend.middleware.verify_token")
    @patch("backend.handler.get_session_by_id")
    def test_session_not_found_returns_404(
        self, mock_get_session: MagicMock, mock_verify: MagicMock
    ) -> None:
        """Session not found returns 404."""
        mock_verify.return_value = {
            "user_id": "test-user-123",
            "email": "test@example.com",
        }
        
        mock_get_session.side_effect = ValueError("Session not found: session-999")
        
        event = {
            "httpMethod": "GET",
            "path": "/sessions/session-999",
            "headers": {"Authorization": "Bearer valid-token"},
        }
        
        response = handler(event, MOCK_CONTEXT)
        
        _assert_error_response(response, 404, "Session not found")

    @patch("backend.middleware.verify_token")
    @patch("backend.handler.get_session_by_id")
    def test_wrong_user_returns_404(
        self, mock_get_session: MagicMock, mock_verify: MagicMock
    ) -> None:
        """Accessing another user's session returns 404."""
        from backend.models import Session
        
        mock_verify.return_value = {
            "user_id": "test-user-123",
            "email": "test@example.com",
        }
        
        # Mock session belonging to a different user
        mock_session = Session(
            session_id="session-123",
            user_id="other-user-456",
            session_date="2024-01-15T10:00:00Z",
            pool_length_meters=25,
            total_distance_meters=2000,
            total_time_seconds=2400,
            stroke_type="freestyle",
            average_pace_per_100m=120.0,
            swolf_score=45,
            stroke_rate=30.0,
            uploaded_at="2024-01-15T11:00:00Z",
            s3_key="uploads/file1.fit",
        )
        mock_get_session.return_value = mock_session
        
        event = {
            "httpMethod": "GET",
            "path": "/sessions/session-123",
            "headers": {"Authorization": "Bearer valid-token"},
        }
        
        response = handler(event, MOCK_CONTEXT)
        
        _assert_error_response(response, 404, "Session not found")

    def test_missing_authentication_returns_401(self) -> None:
        """Missing authentication returns 401."""
        event = {
            "httpMethod": "GET",
            "path": "/sessions/session-123",
            "headers": {},
        }
        
        response = handler(event, MOCK_CONTEXT)
        
        _assert_error_response(response, 401, "Authorization header required")

    @patch("backend.middleware.verify_token")
    @patch("backend.handler.get_session_by_id")
    def test_storage_error_returns_500(
        self, mock_get_session: MagicMock, mock_verify: MagicMock
    ) -> None:
        """Storage error returns 500."""
        mock_verify.return_value = {
            "user_id": "test-user-123",
            "email": "test@example.com",
        }
        
        mock_get_session.side_effect = Exception("DynamoDB error")
        
        event = {
            "httpMethod": "GET",
            "path": "/sessions/session-123",
            "headers": {"Authorization": "Bearer valid-token"},
        }
        
        response = handler(event, MOCK_CONTEXT)
        
        _assert_error_response(response, 500, "Session retrieval failure")
