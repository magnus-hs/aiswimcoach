"""
Unit tests for profile endpoint handlers in backend/handler.py

Tests cover:
  - POST /profile → Save user profile (requires auth)
  - GET /profile → Retrieve user profile (requires auth)
  - POST /profile/picture → Upload profile picture (requires auth)

Requirements: 4.7, 23.4, 23.11
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from backend.handler import (
    _handle_save_profile,
    _handle_get_profile,
    _handle_upload_profile_picture,
)
from backend.models import UserProfile


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

MOCK_CONTEXT = MagicMock()


def _create_auth_event(body: str | dict, headers: dict | None = None) -> dict:
    """Create an event with Authorization header for testing authenticated endpoints."""
    if isinstance(body, dict):
        body = json.dumps(body)
    
    default_headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer fake-jwt-token-for-testing",
    }
    if headers:
        default_headers.update(headers)
    
    event = {
        "body": body,
        "isBase64Encoded": False,
        "headers": default_headers,
    }
    return event


# ---------------------------------------------------------------------------
# POST /profile tests
# ---------------------------------------------------------------------------


class TestHandleSaveProfile:
    """Tests for POST /profile endpoint."""

    @patch("backend.middleware.verify_token")
    @patch("backend.handler.save_profile")
    def test_saves_valid_profile(self, mock_save: MagicMock, mock_verify: MagicMock) -> None:
        """Valid profile data should save successfully."""
        # Mock authentication
        mock_verify.return_value = {"user_id": "test-user-123", "email": "test@example.com"}
        
        payload = {
            "age": 30,
            "nationality": "USA",
            "locality": "California",
            "ability_level": "intermediate",
        }
        event = _create_auth_event(payload)

        response = _handle_save_profile(event, MOCK_CONTEXT)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["message"] == "Profile saved successfully"
        
        # Verify save_profile was called with correct arguments
        mock_save.assert_called_once()
        call_args = mock_save.call_args
        assert call_args[0][0] == "test-user-123"
        profile = call_args[0][1]
        assert isinstance(profile, UserProfile)
        assert profile.age == 30
        assert profile.nationality == "USA"
        assert profile.locality == "California"
        assert profile.ability_level == "intermediate"

    @patch("backend.middleware.verify_token")
    @patch("backend.handler.save_profile")
    def test_saves_profile_with_optional_fields_empty(self, mock_save: MagicMock, mock_verify: MagicMock) -> None:
        """Profile with empty optional fields should be rejected by validation."""
        mock_verify.return_value = {"user_id": "test-user-123", "email": "test@example.com"}
        
        payload = {
            "age": 25,
            "nationality": "",  # Empty string - will be rejected
            "locality": "",     # Empty string - will be rejected
            "ability_level": "beginner",
        }
        event = _create_auth_event(payload)

        response = _handle_save_profile(event, MOCK_CONTEXT)

        # Empty strings should be rejected by UserProfile validation
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body

    @patch("backend.middleware.verify_token")
    @patch("backend.handler.save_profile")
    def test_rejects_missing_age(self, mock_save: MagicMock, mock_verify: MagicMock) -> None:
        """Missing age field should return 400."""
        mock_verify.return_value = {"user_id": "test-user-123", "email": "test@example.com"}
        
        payload = {
            "nationality": "USA",
            "locality": "California",
            "ability_level": "intermediate",
        }
        event = _create_auth_event(payload)

        response = _handle_save_profile(event, MOCK_CONTEXT)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body
        assert "age" in body["error"].lower()
        mock_save.assert_not_called()

    @patch("backend.middleware.verify_token")
    @patch("backend.handler.save_profile")
    def test_rejects_missing_ability_level(self, mock_save: MagicMock, mock_verify: MagicMock) -> None:
        """Missing ability_level field should return 400."""
        mock_verify.return_value = {"user_id": "test-user-123", "email": "test@example.com"}
        
        payload = {
            "age": 30,
            "nationality": "USA",
            "locality": "California",
        }
        event = _create_auth_event(payload)

        response = _handle_save_profile(event, MOCK_CONTEXT)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body
        assert "ability_level" in body["error"].lower()
        mock_save.assert_not_called()

    @patch("backend.middleware.verify_token")
    @patch("backend.handler.save_profile")
    def test_rejects_invalid_age(self, mock_save: MagicMock, mock_verify: MagicMock) -> None:
        """Age outside valid range should return 400."""
        mock_verify.return_value = {"user_id": "test-user-123", "email": "test@example.com"}
        
        payload = {
            "age": 5,  # Too young (< 10)
            "nationality": "USA",
            "locality": "California",
            "ability_level": "beginner",
        }
        event = _create_auth_event(payload)

        response = _handle_save_profile(event, MOCK_CONTEXT)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body
        mock_save.assert_not_called()

    @patch("backend.middleware.verify_token")
    @patch("backend.handler.save_profile")
    def test_rejects_invalid_ability_level(self, mock_save: MagicMock, mock_verify: MagicMock) -> None:
        """Invalid ability_level should return 400."""
        mock_verify.return_value = {"user_id": "test-user-123", "email": "test@example.com"}
        
        payload = {
            "age": 30,
            "nationality": "USA",
            "locality": "California",
            "ability_level": "invalid_level",
        }
        event = _create_auth_event(payload)

        response = _handle_save_profile(event, MOCK_CONTEXT)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body
        mock_save.assert_not_called()

    @patch("backend.middleware.verify_token")
    @patch("backend.handler.save_profile")
    def test_handles_storage_error(self, mock_save: MagicMock, mock_verify: MagicMock) -> None:
        """Storage error should return 500."""
        from backend.profile_manager import StorageError as ProfileStorageError
        
        mock_verify.return_value = {"user_id": "test-user-123", "email": "test@example.com"}
        
        payload = {
            "age": 30,
            "nationality": "USA",
            "locality": "California",
            "ability_level": "intermediate",
        }
        event = _create_auth_event(payload)
        mock_save.side_effect = ProfileStorageError("DynamoDB connection failed")

        response = _handle_save_profile(event, MOCK_CONTEXT)

        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert "error" in body


# ---------------------------------------------------------------------------
# GET /profile tests
# ---------------------------------------------------------------------------


class TestHandleGetProfile:
    """Tests for GET /profile endpoint."""

    @patch("backend.middleware.verify_token")
    @patch("backend.handler.get_profile")
    def test_retrieves_existing_profile(self, mock_get: MagicMock, mock_verify: MagicMock) -> None:
        """Existing profile should be returned successfully."""
        mock_verify.return_value = {"user_id": "test-user-123", "email": "test@example.com"}
        
        mock_profile = UserProfile(
            age=30,
            nationality="USA",
            locality="California",
            ability_level="intermediate",
        )
        mock_get.return_value = mock_profile
        
        event = _create_auth_event("")
        response = _handle_get_profile(event, MOCK_CONTEXT)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["age"] == 30
        assert body["nationality"] == "USA"
        assert body["locality"] == "California"
        assert body["ability_level"] == "intermediate"
        
        mock_get.assert_called_once_with("test-user-123")

    @patch("backend.middleware.verify_token")
    @patch("backend.handler.get_profile")
    def test_returns_404_when_profile_not_found(self, mock_get: MagicMock, mock_verify: MagicMock) -> None:
        """Non-existent profile should return 404."""
        mock_verify.return_value = {"user_id": "test-user-123", "email": "test@example.com"}
        mock_get.return_value = None
        
        event = _create_auth_event("")
        response = _handle_get_profile(event, MOCK_CONTEXT)

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert "error" in body
        assert "not found" in body["error"].lower()

    @patch("backend.middleware.verify_token")
    @patch("backend.handler.get_profile")
    def test_handles_storage_error(self, mock_get: MagicMock, mock_verify: MagicMock) -> None:
        """Storage error should return 500."""
        from backend.profile_manager import StorageError as ProfileStorageError
        
        mock_verify.return_value = {"user_id": "test-user-123", "email": "test@example.com"}
        mock_get.side_effect = ProfileStorageError("DynamoDB connection failed")
        
        event = _create_auth_event("")
        response = _handle_get_profile(event, MOCK_CONTEXT)

        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert "error" in body


# ---------------------------------------------------------------------------
# POST /profile/picture tests
# ---------------------------------------------------------------------------


class TestHandleUploadProfilePicture:
    """Tests for POST /profile/picture endpoint."""

    @patch("backend.middleware.verify_token")
    @patch("backend.handler.upload_profile_picture")
    @patch("backend.handler.parse_multipart")
    def test_uploads_valid_image(
        self, mock_parse: MagicMock, mock_upload: MagicMock, mock_verify: MagicMock
    ) -> None:
        """Valid image should upload successfully."""
        mock_verify.return_value = {"user_id": "test-user-123", "email": "test@example.com"}
        mock_parse.return_value = b"\xff\xd8\xff\xe0..."  # JPEG magic bytes
        mock_upload.return_value = "https://bucket.s3.amazonaws.com/user_123.jpg"
        
        event = _create_auth_event(
            "image_data",
            headers={"Content-Type": "image/jpeg"}
        )
        response = _handle_upload_profile_picture(event, MOCK_CONTEXT)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "url" in body
        assert "s3.amazonaws.com" in body["url"]
        
        mock_upload.assert_called_once()

    @patch("backend.middleware.verify_token")
    @patch("backend.handler.upload_profile_picture")
    @patch("backend.handler.parse_multipart")
    def test_rejects_file_too_large(
        self, mock_parse: MagicMock, mock_upload: MagicMock, mock_verify: MagicMock
    ) -> None:
        """File exceeding 2 MB should return 413."""
        mock_verify.return_value = {"user_id": "test-user-123", "email": "test@example.com"}
        mock_parse.return_value = b"large_image_data"
        mock_upload.side_effect = ValueError("Image file size exceeds 2 MB limit")
        
        event = _create_auth_event(
            "large_image_data",
            headers={"Content-Type": "image/jpeg"}
        )
        response = _handle_upload_profile_picture(event, MOCK_CONTEXT)

        assert response["statusCode"] == 413
        body = json.loads(response["body"])
        assert "error" in body
        assert "2 MB" in body["error"]

    @patch("backend.middleware.verify_token")
    @patch("backend.handler.upload_profile_picture")
    @patch("backend.handler.parse_multipart")
    def test_rejects_invalid_format(
        self, mock_parse: MagicMock, mock_upload: MagicMock, mock_verify: MagicMock
    ) -> None:
        """Invalid image format should return 400."""
        mock_verify.return_value = {"user_id": "test-user-123", "email": "test@example.com"}
        mock_parse.return_value = b"not_an_image"
        mock_upload.side_effect = ValueError("Invalid image file format")
        
        event = _create_auth_event(
            "not_an_image",
            headers={"Content-Type": "image/jpeg"}
        )
        response = _handle_upload_profile_picture(event, MOCK_CONTEXT)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body

    @patch("backend.middleware.verify_token")
    @patch("backend.handler.parse_multipart")
    def test_handles_multipart_parse_error(self, mock_parse: MagicMock, mock_verify: MagicMock) -> None:
        """Multipart parse error should return 400."""
        from backend.multipart_parser import ParseError as MultipartParseError
        
        mock_verify.return_value = {"user_id": "test-user-123", "email": "test@example.com"}
        mock_parse.side_effect = MultipartParseError("Invalid multipart data")
        
        event = _create_auth_event("invalid_data")
        response = _handle_upload_profile_picture(event, MOCK_CONTEXT)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body

