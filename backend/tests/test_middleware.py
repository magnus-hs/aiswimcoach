"""
Unit tests for backend/middleware.py

Tests cover the require_auth decorator:
  - Valid JWT token allows handler execution
  - Missing Authorization header returns 401
  - Invalid Authorization header format returns 401
  - Expired JWT token returns 401
  - Invalid JWT token returns 401
  - Auth context is injected into event with user_id and email
"""
import json
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import jwt
import pytest

from backend.middleware import require_auth
from backend.auth import AuthenticationError


# Test JWT secret - using a fixed secret for testing
TEST_JWT_SECRET = "test_secret_key_for_middleware_tests_at_least_256_bits_long_to_be_secure"


@pytest.fixture(autouse=True)
def setup_environment(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("JWT_SECRET", TEST_JWT_SECRET)


def generate_test_token(user_id: str, email: str, expired: bool = False) -> str:
    """Generate a test JWT token.
    
    Args:
        user_id: User identifier
        email: User email
        expired: If True, generate an expired token
    
    Returns:
        JWT token string
    """
    now = datetime.now(timezone.utc)
    
    if expired:
        expiration = now - timedelta(days=1)  # Expired yesterday
    else:
        expiration = now + timedelta(days=7)
    
    payload = {
        "user_id": user_id,
        "email": email,
        "iat": now,
        "exp": expiration,
    }
    
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")


class TestRequireAuthDecorator:
    """Tests for the require_auth decorator."""
    
    def test_valid_token_allows_handler_execution(self):
        """Valid JWT token should allow handler execution and inject auth_context."""
        # Create a mock handler that returns the auth_context
        @require_auth
        def mock_handler(event, context):
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "user_id": event["auth_context"]["user_id"],
                    "email": event["auth_context"]["email"],
                }),
            }
        
        # Generate valid token
        token = generate_test_token("test-user-123", "test@example.com")
        
        # Create event with Authorization header
        event = {
            "headers": {
                "Authorization": f"Bearer {token}"
            }
        }
        context = MagicMock()
        
        # Call handler
        response = mock_handler(event, context)
        
        # Verify response
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["user_id"] == "test-user-123"
        assert body["email"] == "test@example.com"
    
    def test_missing_authorization_header_returns_401(self):
        """Missing Authorization header should return 401."""
        @require_auth
        def mock_handler(event, context):
            return {"statusCode": 200, "body": "should not reach here"}
        
        event = {"headers": {}}
        context = MagicMock()
        
        response = mock_handler(event, context)
        
        assert response["statusCode"] == 401
        body = json.loads(response["body"])
        assert "error" in body
        assert "Authorization header required" in body["error"]
    
    def test_missing_headers_dict_returns_401(self):
        """Event with no headers dict should return 401."""
        @require_auth
        def mock_handler(event, context):
            return {"statusCode": 200, "body": "should not reach here"}
        
        event = {}
        context = MagicMock()
        
        response = mock_handler(event, context)
        
        assert response["statusCode"] == 401
        body = json.loads(response["body"])
        assert "error" in body
        assert "Authorization header required" in body["error"]
    
    def test_invalid_header_format_no_bearer_returns_401(self):
        """Authorization header without 'Bearer' prefix should return 401."""
        @require_auth
        def mock_handler(event, context):
            return {"statusCode": 200, "body": "should not reach here"}
        
        token = generate_test_token("test-user-123", "test@example.com")
        
        event = {
            "headers": {
                "Authorization": token  # Missing "Bearer " prefix
            }
        }
        context = MagicMock()
        
        response = mock_handler(event, context)
        
        assert response["statusCode"] == 401
        body = json.loads(response["body"])
        assert "error" in body
        assert "Invalid Authorization header format" in body["error"]
    
    def test_invalid_header_format_wrong_scheme_returns_401(self):
        """Authorization header with wrong scheme (not 'Bearer') should return 401."""
        @require_auth
        def mock_handler(event, context):
            return {"statusCode": 200, "body": "should not reach here"}
        
        token = generate_test_token("test-user-123", "test@example.com")
        
        event = {
            "headers": {
                "Authorization": f"Basic {token}"  # Wrong scheme
            }
        }
        context = MagicMock()
        
        response = mock_handler(event, context)
        
        assert response["statusCode"] == 401
        body = json.loads(response["body"])
        assert "error" in body
        assert "Invalid Authorization header format" in body["error"]
    
    def test_expired_token_returns_401(self):
        """Expired JWT token should return 401."""
        @require_auth
        def mock_handler(event, context):
            return {"statusCode": 200, "body": "should not reach here"}
        
        # Generate expired token
        token = generate_test_token("test-user-123", "test@example.com", expired=True)
        
        event = {
            "headers": {
                "Authorization": f"Bearer {token}"
            }
        }
        context = MagicMock()
        
        response = mock_handler(event, context)
        
        assert response["statusCode"] == 401
        body = json.loads(response["body"])
        assert "error" in body
        assert "expired" in body["error"].lower()
    
    def test_invalid_token_returns_401(self):
        """Invalid JWT token (bad signature) should return 401."""
        @require_auth
        def mock_handler(event, context):
            return {"statusCode": 200, "body": "should not reach here"}
        
        # Generate token with wrong secret
        token = jwt.encode(
            {"user_id": "test-user-123", "email": "test@example.com"},
            "wrong_secret",
            algorithm="HS256"
        )
        
        event = {
            "headers": {
                "Authorization": f"Bearer {token}"
            }
        }
        context = MagicMock()
        
        response = mock_handler(event, context)
        
        assert response["statusCode"] == 401
        body = json.loads(response["body"])
        assert "error" in body
        assert "Invalid token" in body["error"]
    
    def test_malformed_token_returns_401(self):
        """Malformed JWT token should return 401."""
        @require_auth
        def mock_handler(event, context):
            return {"statusCode": 200, "body": "should not reach here"}
        
        event = {
            "headers": {
                "Authorization": "Bearer not-a-valid-jwt-token"
            }
        }
        context = MagicMock()
        
        response = mock_handler(event, context)
        
        assert response["statusCode"] == 401
        body = json.loads(response["body"])
        assert "error" in body
        assert "Invalid token" in body["error"]
    
    def test_case_insensitive_authorization_header(self):
        """Authorization header should be case-insensitive (lowercase 'authorization')."""
        @require_auth
        def mock_handler(event, context):
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "user_id": event["auth_context"]["user_id"],
                }),
            }
        
        token = generate_test_token("test-user-123", "test@example.com")
        
        event = {
            "headers": {
                "authorization": f"Bearer {token}"  # lowercase
            }
        }
        context = MagicMock()
        
        response = mock_handler(event, context)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["user_id"] == "test-user-123"
    
    def test_auth_context_contains_user_id_and_email(self):
        """Auth context should contain both user_id and email from token."""
        @require_auth
        def mock_handler(event, context):
            assert "auth_context" in event
            assert "user_id" in event["auth_context"]
            assert "email" in event["auth_context"]
            return {
                "statusCode": 200,
                "body": json.dumps(event["auth_context"]),
            }
        
        token = generate_test_token("user-456", "another@example.com")
        
        event = {
            "headers": {
                "Authorization": f"Bearer {token}"
            }
        }
        context = MagicMock()
        
        response = mock_handler(event, context)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["user_id"] == "user-456"
        assert body["email"] == "another@example.com"
    
    def test_handler_not_called_when_auth_fails(self):
        """Handler should not be called when authentication fails."""
        handler_called = False
        
        @require_auth
        def mock_handler(event, context):
            nonlocal handler_called
            handler_called = True
            return {"statusCode": 200}
        
        event = {"headers": {}}  # Missing Authorization
        context = MagicMock()
        
        response = mock_handler(event, context)
        
        assert response["statusCode"] == 401
        assert not handler_called, "Handler should not be called when auth fails"
