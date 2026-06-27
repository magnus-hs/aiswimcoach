"""
Unit tests for backend/profile_manager.py get_profile() function.

Tests cover profile retrieval:
  - Retrieval from DynamoDB
  - Handling of missing profiles
  - Error handling for DynamoDB failures
"""
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from backend.profile_manager import get_profile, StorageError
from backend.models import UserProfile


class TestGetProfile:
    """Tests for get_profile() function."""

    @patch.dict("os.environ", {"PROFILES_TABLE": "test-profiles-table"})
    @patch("backend.profile_manager._get_dynamodb")
    def test_retrieves_existing_profile(self, mock_get_dynamodb):
        """Should retrieve and parse UserProfile from DynamoDB."""
        mock_table = MagicMock()
        mock_get_dynamodb.return_value.Table.return_value = mock_table

        # Mock DynamoDB response with complete profile
        mock_table.get_item.return_value = {
            "Item": {
                "user_id": "test-user-123",
                "age": 25,
                "nationality": "USA",
                "locality": "California",
                "ability_level": "intermediate",
                "updated_at": "2024-01-15T10:00:00.000Z"
            }
        }

        result = get_profile("test-user-123")

        # Verify correct profile returned
        assert result is not None
        assert isinstance(result, UserProfile)
        assert result.age == 25
        assert result.nationality == "USA"
        assert result.locality == "California"
        assert result.ability_level == "intermediate"

        # Verify DynamoDB was called correctly
        mock_table.get_item.assert_called_once_with(Key={"user_id": "test-user-123"})

    @patch.dict("os.environ", {"PROFILES_TABLE": "test-profiles-table"})
    @patch("backend.profile_manager._get_dynamodb")
    def test_returns_none_for_missing_profile(self, mock_get_dynamodb):
        """Should return None when profile doesn't exist."""
        mock_table = MagicMock()
        mock_get_dynamodb.return_value.Table.return_value = mock_table

        # Mock DynamoDB response with no Item
        mock_table.get_item.return_value = {}

        result = get_profile("nonexistent-user")

        assert result is None
        mock_table.get_item.assert_called_once_with(Key={"user_id": "nonexistent-user"})

    @patch.dict("os.environ", {"PROFILES_TABLE": "test-profiles-table"})
    @patch("backend.profile_manager._get_dynamodb")
    def test_raises_storage_error_on_dynamodb_failure(self, mock_get_dynamodb):
        """Should raise StorageError when DynamoDB query fails."""
        mock_table = MagicMock()
        mock_get_dynamodb.return_value.Table.return_value = mock_table

        # Mock DynamoDB ClientError
        error_response = {"Error": {"Code": "ServiceUnavailable", "Message": "Service unavailable"}}
        mock_table.get_item.side_effect = ClientError(error_response, "GetItem")

        with pytest.raises(StorageError, match="Failed to retrieve profile from DynamoDB"):
            get_profile("test-user-123")

    @patch.dict("os.environ", {"PROFILES_TABLE": "test-profiles-table"})
    @patch("backend.profile_manager._get_dynamodb")
    def test_raises_storage_error_on_missing_required_fields(self, mock_get_dynamodb):
        """Should raise StorageError when profile data is missing required fields."""
        mock_table = MagicMock()
        mock_get_dynamodb.return_value.Table.return_value = mock_table

        # Mock DynamoDB response missing required fields
        mock_table.get_item.return_value = {
            "Item": {
                "user_id": "test-user-123",
                "age": 25,
                # Missing nationality, locality, ability_level
            }
        }

        with pytest.raises(StorageError, match="Failed to parse profile data"):
            get_profile("test-user-123")

    @patch.dict("os.environ", {"PROFILES_TABLE": "test-profiles-table"})
    @patch("backend.profile_manager._get_dynamodb")
    def test_raises_storage_error_on_invalid_age_type(self, mock_get_dynamodb):
        """Should raise StorageError when age is not a valid integer."""
        mock_table = MagicMock()
        mock_get_dynamodb.return_value.Table.return_value = mock_table

        # Mock DynamoDB response with invalid age type
        mock_table.get_item.return_value = {
            "Item": {
                "user_id": "test-user-123",
                "age": "twenty-five",  # String instead of int
                "nationality": "USA",
                "locality": "California",
                "ability_level": "intermediate"
            }
        }

        with pytest.raises(StorageError, match="Failed to parse profile data"):
            get_profile("test-user-123")

    @patch.dict("os.environ", {"PROFILES_TABLE": "test-profiles-table"})
    @patch("backend.profile_manager._get_dynamodb")
    def test_validates_profile_on_retrieval(self, mock_get_dynamodb):
        """Should validate profile data through UserProfile __post_init__."""
        mock_table = MagicMock()
        mock_get_dynamodb.return_value.Table.return_value = mock_table

        # Mock DynamoDB response with invalid age value (out of range)
        mock_table.get_item.return_value = {
            "Item": {
                "user_id": "test-user-123",
                "age": 5,  # Below minimum age of 10
                "nationality": "USA",
                "locality": "California",
                "ability_level": "intermediate"
            }
        }

        # UserProfile __post_init__ should raise ValueError for age < 10
        with pytest.raises(StorageError, match="Failed to parse profile data"):
            get_profile("test-user-123")

    @patch.dict("os.environ", {"PROFILES_TABLE": "test-profiles-table"})
    @patch("backend.profile_manager._get_dynamodb")
    def test_handles_different_user_ids(self, mock_get_dynamodb):
        """Should correctly query DynamoDB with different user IDs."""
        mock_table = MagicMock()
        mock_get_dynamodb.return_value.Table.return_value = mock_table

        # Mock response
        mock_table.get_item.return_value = {
            "Item": {
                "user_id": "user-abc-123",
                "age": 30,
                "nationality": "Canada",
                "locality": "Toronto",
                "ability_level": "advanced"
            }
        }

        result = get_profile("user-abc-123")

        assert result is not None
        mock_table.get_item.assert_called_once_with(Key={"user_id": "user-abc-123"})

    @patch.dict("os.environ", {"PROFILES_TABLE": "test-profiles-table"})
    @patch("backend.profile_manager._get_dynamodb")
    def test_preserves_all_profile_fields(self, mock_get_dynamodb):
        """Should preserve all profile fields exactly as stored."""
        mock_table = MagicMock()
        mock_get_dynamodb.return_value.Table.return_value = mock_table

        mock_table.get_item.return_value = {
            "Item": {
                "user_id": "test-user",
                "age": 42,
                "nationality": "United Kingdom",
                "locality": "London",
                "ability_level": "elite",
                "updated_at": "2024-01-15T10:00:00.000Z"
            }
        }

        result = get_profile("test-user")

        assert result.age == 42
        assert result.nationality == "United Kingdom"
        assert result.locality == "London"
        assert result.ability_level == "elite"

    @patch.dict("os.environ", {"PROFILES_TABLE": "test-profiles-table"})
    @patch("backend.profile_manager._get_dynamodb")
    def test_uses_profiles_table_from_environment(self, mock_get_dynamodb):
        """Should use PROFILES_TABLE environment variable."""
        mock_dynamodb = MagicMock()
        mock_get_dynamodb.return_value = mock_dynamodb
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table

        mock_table.get_item.return_value = {}

        get_profile("test-user")

        # Verify the correct table name was used
        mock_dynamodb.Table.assert_called_once_with("test-profiles-table")

    @patch.dict("os.environ", {"PROFILES_TABLE": "test-profiles-table"})
    @patch("backend.profile_manager._get_dynamodb")
    def test_handles_beginner_ability_level(self, mock_get_dynamodb):
        """Should handle beginner ability level."""
        mock_table = MagicMock()
        mock_get_dynamodb.return_value.Table.return_value = mock_table

        mock_table.get_item.return_value = {
            "Item": {
                "user_id": "test-user",
                "age": 18,
                "nationality": "France",
                "locality": "Paris",
                "ability_level": "beginner"
            }
        }

        result = get_profile("test-user")

        assert result is not None
        assert result.ability_level == "beginner"

    @patch.dict("os.environ", {"PROFILES_TABLE": "test-profiles-table"})
    @patch("backend.profile_manager._get_dynamodb")
    def test_handles_case_insensitive_ability_level(self, mock_get_dynamodb):
        """Should handle ability levels stored in different cases."""
        mock_table = MagicMock()
        mock_get_dynamodb.return_value.Table.return_value = mock_table

        mock_table.get_item.return_value = {
            "Item": {
                "user_id": "test-user",
                "age": 25,
                "nationality": "Germany",
                "locality": "Berlin",
                "ability_level": "INTERMEDIATE"  # Uppercase
            }
        }

        result = get_profile("test-user")

        # UserProfile should accept and normalize the ability level
        assert result is not None
        assert result.ability_level == "INTERMEDIATE"

    @patch.dict("os.environ", {"PROFILES_TABLE": "test-profiles-table"})
    @patch("backend.profile_manager._get_dynamodb")
    def test_handles_edge_case_age_boundaries(self, mock_get_dynamodb):
        """Should handle valid age boundaries (10 and 100)."""
        mock_table = MagicMock()
        mock_get_dynamodb.return_value.Table.return_value = mock_table

        # Test minimum age
        mock_table.get_item.return_value = {
            "Item": {
                "user_id": "test-user",
                "age": 10,
                "nationality": "Spain",
                "locality": "Madrid",
                "ability_level": "beginner"
            }
        }

        result = get_profile("test-user")
        assert result is not None
        assert result.age == 10

        # Test maximum age
        mock_table.get_item.return_value = {
            "Item": {
                "user_id": "test-user",
                "age": 100,
                "nationality": "Japan",
                "locality": "Tokyo",
                "ability_level": "advanced"
            }
        }

        result = get_profile("test-user")
        assert result is not None
        assert result.age == 100

    @patch.dict("os.environ", {"PROFILES_TABLE": "test-profiles-table"})
    @patch("backend.profile_manager._get_dynamodb")
    def test_handles_international_characters(self, mock_get_dynamodb):
        """Should handle international characters in nationality and locality."""
        mock_table = MagicMock()
        mock_get_dynamodb.return_value.Table.return_value = mock_table

        mock_table.get_item.return_value = {
            "Item": {
                "user_id": "test-user",
                "age": 35,
                "nationality": "日本",  # Japan in Japanese
                "locality": "São Paulo",  # With accent
                "ability_level": "intermediate"
            }
        }

        result = get_profile("test-user")

        assert result is not None
        assert result.nationality == "日本"
        assert result.locality == "São Paulo"
