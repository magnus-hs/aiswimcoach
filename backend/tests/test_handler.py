"""
Unit tests for backend/handler.py

Tests cover the handler pipeline wiring and error mapping:
  - MultipartParseError → HTTP 400
  - StorageError → HTTP 500
  - FitParseError → HTTP 422
  - MetricsMissingError → HTTP 422
  - BedrockError → HTTP 502
  - DynamoDB failure → logged, HTTP 200 still returned
  - Full success pipeline → HTTP 200 with coaching JSON

Also tests authentication endpoint routing:
  - POST /auth/register → User registration
  - POST /auth/login → User login
  - GET /auth/verify → Token verification

Requirements: 2.2, 2.3, 3.1, 3.3, 3.4, 4.1, 5.1, 6.1, 6.3, 7.1, 21.5-21.22
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from backend.handler import handler, http_200
from backend.models import CoachingResponse, Metrics


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

MOCK_EVENT = {
    "body": "base64data",
    "isBase64Encoded": True,
    "headers": {
        "Content-Type": "multipart/form-data; boundary=----abc",
        "Authorization": "Bearer mock-jwt-token"  # Add auth header for protected routes
    },
}

MOCK_CONTEXT = MagicMock()

SAMPLE_METRICS = Metrics(pace=95.0, swolf=38.0, stroke_rate=30.0)
SAMPLE_COACHING = CoachingResponse(
    tips=["Tip one", "Tip two", "Tip three"],
    drill="Catch-up drill",
)

# Sample SessionInfo for mocking extract_session_info
from backend.models import SessionInfo, LengthSplit

SAMPLE_SESSION_INFO = SessionInfo(
    start_time="2024-01-01T10:00:00Z",
    pool_length_m=25.0,
    stroke="freestyle",
    total_distance_m=1000.0,
    total_time_seconds=900.0,
    num_lengths=40
)

SAMPLE_SPLITS = [
    LengthSplit(length_number=1, time_seconds=22.5, stroke="freestyle", strokes=15)
]


def _assert_error_response(response: dict, status_code: int, error_substring: str) -> None:
    """Assert the response is an error with the expected status and message."""
    assert response["statusCode"] == status_code
    assert response["headers"]["Content-Type"] == "application/json"
    assert response["headers"]["Access-Control-Allow-Origin"] == "https://main.d3qbayea55l8tl.amplifyapp.com"
    body = json.loads(response["body"])
    assert "error" in body
    assert error_substring in body["error"]


# ---------------------------------------------------------------------------
# Error mapping tests
# ---------------------------------------------------------------------------


class TestMultipartParseError:
    """MultipartParseError from parse_multipart → HTTP 400."""

    @patch("backend.middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    @patch("backend.handler.parse_multipart")
    def test_returns_400(self, mock_parse: MagicMock, mock_verify: MagicMock) -> None:
        from backend.multipart_parser import ParseError as MultipartParseError
        mock_parse.side_effect = MultipartParseError("No FIT file found in request")

        response = handler(MOCK_EVENT, MOCK_CONTEXT)

        _assert_error_response(response, 400, "No FIT file found in request")

    @patch("backend.middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    @patch("backend.handler.parse_multipart")
    def test_does_not_call_downstream(self, mock_parse: MagicMock, mock_verify: MagicMock) -> None:
        from backend.multipart_parser import ParseError as MultipartParseError
        mock_parse.side_effect = MultipartParseError("missing")

        with patch("backend.handler.store_in_s3") as mock_s3:
            handler(MOCK_EVENT, MOCK_CONTEXT)
            mock_s3.assert_not_called()


class TestStorageError:
    """StorageError from store_in_s3 → HTTP 500."""

    @patch("backend.middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    @patch("backend.handler.parse_multipart", return_value=b"fitbytes")
    @patch("backend.handler.store_in_s3")
    def test_returns_500(self, mock_s3: MagicMock, mock_parse: MagicMock, mock_verify: MagicMock) -> None:
        from backend.s3_store import StorageError
        mock_s3.side_effect = StorageError("Failed to store file")

        response = handler(MOCK_EVENT, MOCK_CONTEXT)

        _assert_error_response(response, 500, "Failed to store file")


class TestFitParseError:
    """FitParseError from parse_fit → HTTP 422."""

    @patch("backend.middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    @patch("backend.handler.parse_multipart", return_value=b"fitbytes")
    @patch("backend.handler.store_in_s3", return_value="uploads/uuid.fit")
    @patch("backend.handler.parse_fit")
    def test_malformed_file_returns_422(
        self, mock_fit: MagicMock, mock_s3: MagicMock, mock_parse: MagicMock, mock_verify: MagicMock
    ) -> None:
        from backend.fit_parser import ParseError as FitParseError
        mock_fit.side_effect = FitParseError("Malformed FIT file: bad header")

        response = handler(MOCK_EVENT, MOCK_CONTEXT)

        _assert_error_response(response, 422, "Malformed FIT file")


class TestMetricsMissingError:
    """MetricsMissingError from parse_fit → HTTP 422 listing missing metrics."""

    @patch("backend.middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    @patch("backend.handler.parse_multipart", return_value=b"fitbytes")
    @patch("backend.handler.store_in_s3", return_value="uploads/uuid.fit")
    @patch("backend.handler.parse_fit")
    def test_missing_metrics_returns_422(
        self, mock_fit: MagicMock, mock_s3: MagicMock, mock_parse: MagicMock, mock_verify: MagicMock
    ) -> None:
        from backend.fit_parser import MetricsMissingError
        mock_fit.side_effect = MetricsMissingError(["pace", "SWOLF"])

        response = handler(MOCK_EVENT, MOCK_CONTEXT)

        _assert_error_response(response, 422, "Missing metrics: pace, SWOLF")


class TestBedrockError:
    """BedrockError from invoke_bedrock → HTTP 502."""

    @patch("backend.middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    @patch("backend.handler.parse_multipart", return_value=b"fitbytes")
    @patch("backend.handler.store_in_s3", return_value="uploads/uuid.fit")
    @patch("backend.handler.parse_fit", return_value=SAMPLE_METRICS)
    @patch("backend.handler.extract_session_info", return_value=(SAMPLE_SESSION_INFO, SAMPLE_SPLITS))  # Use proper objects
    @patch("backend.handler.invoke_bedrock")
    def test_returns_502(
        self, mock_bedrock: MagicMock, mock_extract_session: MagicMock, mock_fit: MagicMock,
        mock_s3: MagicMock, mock_parse: MagicMock, mock_verify: MagicMock
    ) -> None:
        from backend.bedrock_client import BedrockError
        mock_bedrock.side_effect = BedrockError("AI coach unavailable")

        response = handler(MOCK_EVENT, MOCK_CONTEXT)

        _assert_error_response(response, 502, "AI coach unavailable")


class TestDynamoDBBestEffort:
    """DynamoDB failure is logged but does not block HTTP 200."""

    @patch("backend.middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    @patch("backend.handler.parse_multipart", return_value=b"fitbytes")
    @patch("backend.handler.store_in_s3", return_value="uploads/uuid.fit")
    @patch("backend.handler.parse_fit", return_value=SAMPLE_METRICS)
    @patch("backend.handler.extract_session_info", return_value=(SAMPLE_SESSION_INFO, SAMPLE_SPLITS))  # Use proper objects
    @patch("backend.handler.invoke_bedrock", return_value=SAMPLE_COACHING)
    @patch("backend.handler.save_to_dynamodb")
    def test_dynamo_error_still_returns_200(
        self, mock_dynamo: MagicMock, mock_bedrock: MagicMock, mock_extract_session: MagicMock,
        mock_fit: MagicMock, mock_s3: MagicMock, mock_parse: MagicMock, mock_verify: MagicMock
    ) -> None:
        mock_dynamo.side_effect = RuntimeError("DynamoDB unreachable")

        response = handler(MOCK_EVENT, MOCK_CONTEXT)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["coaching"]["tips"] == ["Tip one", "Tip two", "Tip three"]
        assert body["coaching"]["drill"] == "Catch-up drill"


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


class TestSuccessPipeline:
    """Full pipeline success → HTTP 200 with coaching JSON."""

    @patch("backend.middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    @patch("backend.handler.parse_multipart", return_value=b"fitbytes")
    @patch("backend.handler.store_in_s3", return_value="uploads/uuid.fit")
    @patch("backend.handler.parse_fit", return_value=SAMPLE_METRICS)
    @patch("backend.handler.extract_session_info", return_value=(SAMPLE_SESSION_INFO, SAMPLE_SPLITS))  # Use proper objects
    @patch("backend.handler.invoke_bedrock", return_value=SAMPLE_COACHING)
    @patch("backend.handler.save_to_dynamodb")
    def test_returns_200_with_coaching(
        self, mock_dynamo: MagicMock, mock_bedrock: MagicMock, mock_extract_session: MagicMock,
        mock_fit: MagicMock, mock_s3: MagicMock, mock_parse: MagicMock, mock_verify: MagicMock
    ) -> None:
        response = handler(MOCK_EVENT, MOCK_CONTEXT)

        assert response["statusCode"] == 200
        assert response["headers"]["Content-Type"] == "application/json"
        assert response["headers"]["Access-Control-Allow-Origin"] == "https://main.d3qbayea55l8tl.amplifyapp.com"

        body = json.loads(response["body"])
        assert body["coaching"]["tips"] == ["Tip one", "Tip two", "Tip three"]
        assert body["coaching"]["drill"] == "Catch-up drill"

    @patch("backend.middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    @patch("backend.handler.parse_multipart", return_value=b"fitbytes")
    @patch("backend.handler.store_in_s3", return_value="uploads/uuid.fit")
    @patch("backend.handler.parse_fit", return_value=SAMPLE_METRICS)
    @patch("backend.handler.extract_session_info", return_value=(SAMPLE_SESSION_INFO, SAMPLE_SPLITS))  # Use proper objects
    @patch("backend.handler.invoke_bedrock", return_value=SAMPLE_COACHING)
    @patch("backend.handler.save_to_dynamodb")
    def test_pipeline_calls_in_order(
        self, mock_dynamo: MagicMock, mock_bedrock: MagicMock, mock_extract_session: MagicMock,
        mock_fit: MagicMock, mock_s3: MagicMock, mock_parse: MagicMock, mock_verify: MagicMock
    ) -> None:
        handler(MOCK_EVENT, MOCK_CONTEXT)

        # Verify each stage was called with the expected arguments
        mock_parse.assert_called_once_with(MOCK_EVENT)
        mock_s3.assert_called_once_with(b"fitbytes")
        mock_fit.assert_called_once_with(b"fitbytes")
        mock_bedrock.assert_called_once()
        # Verify metrics is the first argument
        call_args = mock_bedrock.call_args
        assert call_args[0][0] == SAMPLE_METRICS
        mock_dynamo.assert_called_once_with("uploads/uuid.fit", SAMPLE_METRICS, SAMPLE_COACHING)


# ---------------------------------------------------------------------------
# http_200 helper
# ---------------------------------------------------------------------------


class TestHttp200Helper:
    """The http_200 helper returns a correctly-shaped proxy response."""

    def test_response_shape(self) -> None:
        response = http_200(SAMPLE_COACHING)

        assert response["statusCode"] == 200
        assert response["headers"]["Content-Type"] == "application/json"
        assert response["headers"]["Access-Control-Allow-Origin"] == "https://main.d3qbayea55l8tl.amplifyapp.com"

        body = json.loads(response["body"])
        assert body == {"tips": ["Tip one", "Tip two", "Tip three"], "drill": "Catch-up drill"}


# ---------------------------------------------------------------------------
# Authentication endpoint tests
# ---------------------------------------------------------------------------


class TestAuthRegisterEndpoint:
    """POST /auth/register endpoint tests."""

    @patch.dict("os.environ", {"JWT_SECRET": "test-secret-key", "USERS_TABLE": "test-users-table"})
    @patch("backend.handler.register_user")
    def test_successful_registration(self, mock_register: MagicMock) -> None:
        """Successful registration returns 201 with user_id and email."""
        mock_register.return_value = {
            "user_id": "test-uuid-123",
            "email": "test@example.com",
        }

        event = {
            "httpMethod": "POST",
            "path": "/auth/register",
            "body": json.dumps({"email": "test@example.com", "password": "password123"}),
            "headers": {"Content-Type": "application/json"},
        }

        response = handler(event, MOCK_CONTEXT)

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["user_id"] == "test-uuid-123"
        assert body["email"] == "test@example.com"
        mock_register.assert_called_once_with("test@example.com", "password123")

    @patch.dict("os.environ", {"JWT_SECRET": "test-secret-key", "USERS_TABLE": "test-users-table"})
    @patch("backend.handler.register_user")
    def test_invalid_email_returns_400(self, mock_register: MagicMock) -> None:
        """Invalid email returns 400 with error message."""
        mock_register.side_effect = ValueError("email must be a valid email address")

        event = {
            "httpMethod": "POST",
            "path": "/auth/register",
            "body": json.dumps({"email": "invalid-email", "password": "password123"}),
            "headers": {"Content-Type": "application/json"},
        }

        response = handler(event, MOCK_CONTEXT)

        _assert_error_response(response, 400, "email must be a valid email address")

    @patch.dict("os.environ", {"JWT_SECRET": "test-secret-key", "USERS_TABLE": "test-users-table"})
    @patch("backend.handler.register_user")
    def test_duplicate_email_returns_409(self, mock_register: MagicMock) -> None:
        """Duplicate email returns 409 with conflict error."""
        from backend.auth import ConflictError
        mock_register.side_effect = ConflictError("Email already registered")

        event = {
            "httpMethod": "POST",
            "path": "/auth/register",
            "body": json.dumps({"email": "existing@example.com", "password": "password123"}),
            "headers": {"Content-Type": "application/json"},
        }

        response = handler(event, MOCK_CONTEXT)

        _assert_error_response(response, 409, "Email already registered")

    @patch.dict("os.environ", {"JWT_SECRET": "test-secret-key", "USERS_TABLE": "test-users-table"})
    def test_missing_email_returns_400(self) -> None:
        """Missing email field returns 400."""
        event = {
            "httpMethod": "POST",
            "path": "/auth/register",
            "body": json.dumps({"password": "password123"}),
            "headers": {"Content-Type": "application/json"},
        }

        response = handler(event, MOCK_CONTEXT)

        _assert_error_response(response, 400, "Missing 'email' or 'password'")

    @patch.dict("os.environ", {"JWT_SECRET": "test-secret-key", "USERS_TABLE": "test-users-table"})
    def test_missing_password_returns_400(self) -> None:
        """Missing password field returns 400."""
        event = {
            "httpMethod": "POST",
            "path": "/auth/register",
            "body": json.dumps({"email": "test@example.com"}),
            "headers": {"Content-Type": "application/json"},
        }

        response = handler(event, MOCK_CONTEXT)

        _assert_error_response(response, 400, "Missing 'email' or 'password'")


class TestAuthLoginEndpoint:
    """POST /auth/login endpoint tests."""

    @patch.dict("os.environ", {"JWT_SECRET": "test-secret-key", "USERS_TABLE": "test-users-table"})
    @patch("backend.handler.login_user")
    def test_successful_login(self, mock_login: MagicMock) -> None:
        """Successful login returns 200 with token, user_id, and email."""
        mock_login.return_value = {
            "token": "jwt-token-string",
            "user_id": "test-uuid-123",
            "email": "test@example.com",
        }

        event = {
            "httpMethod": "POST",
            "path": "/auth/login",
            "body": json.dumps({"email": "test@example.com", "password": "password123"}),
            "headers": {"Content-Type": "application/json"},
        }

        response = handler(event, MOCK_CONTEXT)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["token"] == "jwt-token-string"
        assert body["user_id"] == "test-uuid-123"
        assert body["email"] == "test@example.com"
        mock_login.assert_called_once_with("test@example.com", "password123")

    @patch.dict("os.environ", {"JWT_SECRET": "test-secret-key", "USERS_TABLE": "test-users-table"})
    @patch("backend.handler.login_user")
    def test_invalid_credentials_returns_401(self, mock_login: MagicMock) -> None:
        """Invalid credentials return 401."""
        from backend.auth import AuthenticationError
        mock_login.side_effect = AuthenticationError("Invalid credentials")

        event = {
            "httpMethod": "POST",
            "path": "/auth/login",
            "body": json.dumps({"email": "test@example.com", "password": "wrongpassword"}),
            "headers": {"Content-Type": "application/json"},
        }

        response = handler(event, MOCK_CONTEXT)

        _assert_error_response(response, 401, "Invalid credentials")

    @patch.dict("os.environ", {"JWT_SECRET": "test-secret-key", "USERS_TABLE": "test-users-table"})
    def test_missing_credentials_returns_400(self) -> None:
        """Missing email or password returns 400."""
        event = {
            "httpMethod": "POST",
            "path": "/auth/login",
            "body": json.dumps({"email": "test@example.com"}),
            "headers": {"Content-Type": "application/json"},
        }

        response = handler(event, MOCK_CONTEXT)

        _assert_error_response(response, 400, "Missing 'email' or 'password'")


class TestAuthVerifyEndpoint:
    """GET /auth/verify endpoint tests."""

    @patch.dict("os.environ", {"JWT_SECRET": "test-secret-key", "USERS_TABLE": "test-users-table"})
    @patch("backend.handler.verify_token")
    def test_successful_verification(self, mock_verify: MagicMock) -> None:
        """Successful token verification returns 200 with claims."""
        mock_verify.return_value = {
            "user_id": "test-uuid-123",
            "email": "test@example.com",
        }

        event = {
            "httpMethod": "GET",
            "path": "/auth/verify",
            "headers": {"Authorization": "Bearer jwt-token-string"},
        }

        response = handler(event, MOCK_CONTEXT)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["user_id"] == "test-uuid-123"
        assert body["email"] == "test@example.com"
        mock_verify.assert_called_once_with("jwt-token-string")

    @patch.dict("os.environ", {"JWT_SECRET": "test-secret-key", "USERS_TABLE": "test-users-table"})
    def test_missing_authorization_header_returns_401(self) -> None:
        """Missing Authorization header returns 401."""
        event = {
            "httpMethod": "GET",
            "path": "/auth/verify",
            "headers": {},
        }

        response = handler(event, MOCK_CONTEXT)

        _assert_error_response(response, 401, "Missing Authorization header")

    @patch.dict("os.environ", {"JWT_SECRET": "test-secret-key", "USERS_TABLE": "test-users-table"})
    def test_invalid_authorization_format_returns_401(self) -> None:
        """Invalid Authorization header format returns 401."""
        event = {
            "httpMethod": "GET",
            "path": "/auth/verify",
            "headers": {"Authorization": "InvalidFormat"},
        }

        response = handler(event, MOCK_CONTEXT)

        _assert_error_response(response, 401, "Invalid Authorization header format")

    @patch.dict("os.environ", {"JWT_SECRET": "test-secret-key", "USERS_TABLE": "test-users-table"})
    @patch("backend.handler.verify_token")
    def test_expired_token_returns_401(self, mock_verify: MagicMock) -> None:
        """Expired token returns 401."""
        from backend.auth import AuthenticationError
        mock_verify.side_effect = AuthenticationError("Token has expired")

        event = {
            "httpMethod": "GET",
            "path": "/auth/verify",
            "headers": {"Authorization": "Bearer expired-token"},
        }

        response = handler(event, MOCK_CONTEXT)

        _assert_error_response(response, 401, "Token has expired")

    @patch.dict("os.environ", {"JWT_SECRET": "test-secret-key", "USERS_TABLE": "test-users-table"})
    @patch("backend.handler.verify_token")
    def test_invalid_token_returns_401(self, mock_verify: MagicMock) -> None:
        """Invalid token returns 401."""
        from backend.auth import AuthenticationError
        mock_verify.side_effect = AuthenticationError("Invalid token")

        event = {
            "httpMethod": "GET",
            "path": "/auth/verify",
            "headers": {"Authorization": "Bearer invalid-token"},
        }

        response = handler(event, MOCK_CONTEXT)

        _assert_error_response(response, 401, "Invalid token")



# ---------------------------------------------------------------------------
# HR Zones Integration Tests
# ---------------------------------------------------------------------------


class TestHRZonesIntegration:
    """Test HR zones integration in upload handler.
    
    Requirements: 12.1-12.7
    """

    @patch("backend.middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    @patch("backend.handler.parse_multipart", return_value=b"fitbytes")
    @patch("backend.handler.store_in_s3", return_value="uploads/uuid.fit")
    @patch("backend.handler.parse_fit", return_value=SAMPLE_METRICS)
    @patch("backend.handler.extract_session_info")
    @patch("backend.handler.invoke_bedrock", return_value=SAMPLE_COACHING)
    @patch("backend.handler.save_to_dynamodb")
    @patch("backend.handler.get_profile")
    @patch("backend.handler.extract_heart_rate_data")
    @patch("backend.handler.calculate_hr_zones")
    def test_includes_hr_zones_with_authenticated_user_and_profile(
        self, 
        mock_calc_zones: MagicMock,
        mock_extract_hr: MagicMock,
        mock_get_profile: MagicMock,
        mock_dynamo: MagicMock,
        mock_bedrock: MagicMock,
        mock_extract_session: MagicMock,
        mock_fit: MagicMock,
        mock_s3: MagicMock,
        mock_parse: MagicMock,
        mock_verify: MagicMock
    ) -> None:
        """HR zones included when user authenticated and has profile with age."""
        from backend.models import UserProfile, HRZonesData, SessionInfo, LengthSplit
        from datetime import datetime
        
        # Mock session info and splits
        mock_extract_session.return_value = (
            SessionInfo(
                start_time="2024-01-01T10:00:00Z",
                pool_length_m=25.0,
                stroke="freestyle",
                total_distance_m=1000.0,
                total_time_seconds=900.0,
                num_lengths=40
            ),
            [LengthSplit(length_number=1, time_seconds=22.5, stroke="freestyle", strokes=15)]
        )
        
        # Mock user profile with age
        mock_profile = UserProfile(
            age=30,
            nationality="USA",
            locality="California",
            ability_level="intermediate"
        )
        mock_get_profile.return_value = mock_profile
        
        # Mock heart rate data
        mock_hr_samples = [
            (datetime(2024, 1, 1, 10, 0, 0), 120),
            (datetime(2024, 1, 1, 10, 0, 30), 140),
        ]
        mock_extract_hr.return_value = mock_hr_samples
        
        # Mock HR zones data
        mock_hr_zones = HRZonesData(
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
        )
        mock_calc_zones.return_value = mock_hr_zones
        
        # Create event with auth context
        event = {
            **MOCK_EVENT,
            "auth_context": {
                "user_id": "test-user-123",
                "email": "test@example.com"
            }
        }
        
        response = handler(event, MOCK_CONTEXT)
        
        # Verify HR zones are included in response
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "hr_zones" in body
        assert body["hr_zones"] is not None
        assert body["hr_zones"]["zone_1_seconds"] == 100
        assert body["hr_zones"]["zone_3_percent"] == 33.3
        assert body["hr_zones"]["max_hr"] == 190
        
        # Verify function calls
        mock_get_profile.assert_called_with("test-user")  # Changed from assert_called_once_with
        mock_extract_hr.assert_called_once_with(b"fitbytes")
        mock_calc_zones.assert_called_once_with(mock_hr_samples, 30)

    @patch("backend.middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    @patch("backend.handler.parse_multipart", return_value=b"fitbytes")
    @patch("backend.handler.store_in_s3", return_value="uploads/uuid.fit")
    @patch("backend.handler.parse_fit", return_value=SAMPLE_METRICS)
    @patch("backend.handler.extract_session_info")
    @patch("backend.handler.invoke_bedrock", return_value=SAMPLE_COACHING)
    @patch("backend.handler.save_to_dynamodb")
    def test_omits_hr_zones_without_auth_context(
        self,
        mock_dynamo: MagicMock,
        mock_bedrock: MagicMock,
        mock_extract_session: MagicMock,
        mock_fit: MagicMock,
        mock_s3: MagicMock,
        mock_parse: MagicMock,
        mock_verify: MagicMock
    ) -> None:
        """HR zones omitted when user not authenticated (no auth_context)."""
        from backend.models import SessionInfo, LengthSplit
        
        # Mock session info and splits
        mock_extract_session.return_value = (
            SessionInfo(
                start_time="2024-01-01T10:00:00Z",
                pool_length_m=25.0,
                stroke="freestyle",
                total_distance_m=1000.0,
                total_time_seconds=900.0,
                num_lengths=40
            ),
            [LengthSplit(length_number=1, time_seconds=22.5, stroke="freestyle", strokes=15)]
        )
        
        # Event without auth_context
        event = MOCK_EVENT.copy()
        
        response = handler(event, MOCK_CONTEXT)
        
        # Verify HR zones are null/omitted
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body.get("hr_zones") is None

    @patch("backend.middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    @patch("backend.handler.parse_multipart", return_value=b"fitbytes")
    @patch("backend.handler.store_in_s3", return_value="uploads/uuid.fit")
    @patch("backend.handler.parse_fit", return_value=SAMPLE_METRICS)
    @patch("backend.handler.extract_session_info")
    @patch("backend.handler.invoke_bedrock", return_value=SAMPLE_COACHING)
    @patch("backend.handler.save_to_dynamodb")
    @patch("backend.handler.get_profile")
    def test_omits_hr_zones_when_no_profile(
        self,
        mock_get_profile: MagicMock,
        mock_dynamo: MagicMock,
        mock_bedrock: MagicMock,
        mock_extract_session: MagicMock,
        mock_fit: MagicMock,
        mock_s3: MagicMock,
        mock_parse: MagicMock,
        mock_verify: MagicMock
    ) -> None:
        """HR zones omitted when user has no profile."""
        from backend.models import SessionInfo, LengthSplit
        
        # Mock session info and splits
        mock_extract_session.return_value = (
            SessionInfo(
                start_time="2024-01-01T10:00:00Z",
                pool_length_m=25.0,
                stroke="freestyle",
                total_distance_m=1000.0,
                total_time_seconds=900.0,
                num_lengths=40
            ),
            [LengthSplit(length_number=1, time_seconds=22.5, stroke="freestyle", strokes=15)]
        )
        
        # Mock get_profile returning None
        mock_get_profile.return_value = None
        
        # Create event with auth context
        event = {
            **MOCK_EVENT,
            "auth_context": {
                "user_id": "test-user-123",
                "email": "test@example.com"
            }
        }
        
        response = handler(event, MOCK_CONTEXT)
        
        # Verify HR zones are null/omitted
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body.get("hr_zones") is None
        
        # Verify get_profile was called
        mock_get_profile.assert_called_with("test-user")  # Changed to test-user to match mock verify_token

    @patch("backend.middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    @patch("backend.handler.parse_multipart", return_value=b"fitbytes")
    @patch("backend.handler.store_in_s3", return_value="uploads/uuid.fit")
    @patch("backend.handler.parse_fit", return_value=SAMPLE_METRICS)
    @patch("backend.handler.extract_session_info")
    @patch("backend.handler.invoke_bedrock", return_value=SAMPLE_COACHING)
    @patch("backend.handler.save_to_dynamodb")
    @patch("backend.handler.get_profile")
    @patch("backend.handler.extract_heart_rate_data")
    def test_omits_hr_zones_when_no_hr_data(
        self,
        mock_extract_hr: MagicMock,
        mock_get_profile: MagicMock,
        mock_dynamo: MagicMock,
        mock_bedrock: MagicMock,
        mock_extract_session: MagicMock,
        mock_fit: MagicMock,
        mock_s3: MagicMock,
        mock_parse: MagicMock,
        mock_verify: MagicMock
    ) -> None:
        """HR zones omitted when FIT file has no heart rate data."""
        from backend.models import UserProfile, SessionInfo, LengthSplit
        
        # Mock session info and splits
        mock_extract_session.return_value = (
            SessionInfo(
                start_time="2024-01-01T10:00:00Z",
                pool_length_m=25.0,
                stroke="freestyle",
                total_distance_m=1000.0,
                total_time_seconds=900.0,
                num_lengths=40
            ),
            [LengthSplit(length_number=1, time_seconds=22.5, stroke="freestyle", strokes=15)]
        )
        
        # Mock user profile with age
        mock_profile = UserProfile(
            age=30,
            nationality="USA",
            locality="California",
            ability_level="intermediate"
        )
        mock_get_profile.return_value = mock_profile
        
        # Mock empty heart rate data
        mock_extract_hr.return_value = []
        
        # Create event with auth context
        event = {
            **MOCK_EVENT,
            "auth_context": {
                "user_id": "test-user-123",
                "email": "test@example.com"
            }
        }
        
        response = handler(event, MOCK_CONTEXT)
        
        # Verify HR zones are null/omitted
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body.get("hr_zones") is None
        
        # Verify functions were called
        mock_get_profile.assert_called_with("test-user")  # Changed to test-user to match mock verify_token
        mock_extract_hr.assert_called_once_with(b"fitbytes")

    @patch("backend.middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    @patch("backend.handler.parse_multipart", return_value=b"fitbytes")
    @patch("backend.handler.store_in_s3", return_value="uploads/uuid.fit")
    @patch("backend.handler.parse_fit", return_value=SAMPLE_METRICS)
    @patch("backend.handler.extract_session_info")
    @patch("backend.handler.invoke_bedrock", return_value=SAMPLE_COACHING)
    @patch("backend.handler.save_to_dynamodb")
    @patch("backend.handler.get_profile")
    @patch("backend.handler.extract_heart_rate_data")
    @patch("backend.handler.calculate_hr_zones")
    def test_handles_hr_zone_calculation_failure_gracefully(
        self,
        mock_calc_zones: MagicMock,
        mock_extract_hr: MagicMock,
        mock_get_profile: MagicMock,
        mock_dynamo: MagicMock,
        mock_bedrock: MagicMock,
        mock_extract_session: MagicMock,
        mock_fit: MagicMock,
        mock_s3: MagicMock,
        mock_parse: MagicMock,
        mock_verify: MagicMock
    ) -> None:
        """HR zones omitted when calculation fails, but response still succeeds."""
        from backend.models import UserProfile, SessionInfo, LengthSplit
        from datetime import datetime
        
        # Mock session info and splits
        mock_extract_session.return_value = (
            SessionInfo(
                start_time="2024-01-01T10:00:00Z",
                pool_length_m=25.0,
                stroke="freestyle",
                total_distance_m=1000.0,
                total_time_seconds=900.0,
                num_lengths=40
            ),
            [LengthSplit(length_number=1, time_seconds=22.5, stroke="freestyle", strokes=15)]
        )
        
        # Mock user profile with age
        mock_profile = UserProfile(
            age=30,
            nationality="USA",
            locality="California",
            ability_level="intermediate"
        )
        mock_get_profile.return_value = mock_profile
        
        # Mock heart rate data
        mock_hr_samples = [
            (datetime(2024, 1, 1, 10, 0, 0), 120),
        ]
        mock_extract_hr.return_value = mock_hr_samples
        
        # Mock calculation failure
        mock_calc_zones.side_effect = ValueError("need at least 2 valid heart rate samples")
        
        # Create event with auth context
        event = {
            **MOCK_EVENT,
            "auth_context": {
                "user_id": "test-user-123",
                "email": "test@example.com"
            }
        }
        
        response = handler(event, MOCK_CONTEXT)
        
        # Verify response is still successful but without HR zones
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body.get("hr_zones") is None
        assert body["coaching"]["tips"] == ["Tip one", "Tip two", "Tip three"]
        
        # Verify functions were called
        mock_get_profile.assert_called_with("test-user")  # Changed to test-user to match mock verify_token
        mock_extract_hr.assert_called_once_with(b"fitbytes")
        mock_calc_zones.assert_called_once()

    @patch("backend.middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    @patch("backend.handler.parse_multipart", return_value=b"fitbytes")
    @patch("backend.handler.store_in_s3", return_value="uploads/uuid.fit")
    @patch("backend.handler.parse_fit", return_value=SAMPLE_METRICS)
    @patch("backend.handler.extract_session_info")
    @patch("backend.handler.invoke_bedrock", return_value=SAMPLE_COACHING)
    @patch("backend.handler.save_to_dynamodb")
    @patch("backend.handler.get_profile")
    def test_handles_profile_retrieval_failure_gracefully(
        self,
        mock_get_profile: MagicMock,
        mock_dynamo: MagicMock,
        mock_bedrock: MagicMock,
        mock_extract_session: MagicMock,
        mock_fit: MagicMock,
        mock_s3: MagicMock,
        mock_parse: MagicMock,
        mock_verify: MagicMock
    ) -> None:
        """HR zones omitted when profile retrieval fails, but response still succeeds."""
        from backend.models import SessionInfo, LengthSplit
        from backend.profile_manager import StorageError as ProfileStorageError
        
        # Mock session info and splits
        mock_extract_session.return_value = (
            SessionInfo(
                start_time="2024-01-01T10:00:00Z",
                pool_length_m=25.0,
                stroke="freestyle",
                total_distance_m=1000.0,
                total_time_seconds=900.0,
                num_lengths=40
            ),
            [LengthSplit(length_number=1, time_seconds=22.5, stroke="freestyle", strokes=15)]
        )
        
        # Mock profile retrieval failure
        mock_get_profile.side_effect = ProfileStorageError("DynamoDB connection failed")
        
        # Create event with auth context
        event = {
            **MOCK_EVENT,
            "auth_context": {
                "user_id": "test-user-123",
                "email": "test@example.com"
            }
        }
        
        response = handler(event, MOCK_CONTEXT)
        
        # Verify response is still successful but without HR zones
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body.get("hr_zones") is None
        assert body["coaching"]["tips"] == ["Tip one", "Tip two", "Tip three"]
        
        # Verify get_profile was called
        mock_get_profile.assert_called_with("test-user")  # Changed to test-user to match mock verify_token
