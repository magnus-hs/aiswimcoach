"""
Unit tests for save_profile() function in backend/profile_manager.py

Tests verify that save_profile() correctly:
  - Persists UserProfile data to DynamoDB
  - Includes updated_at timestamp in ISO 8601 format with millisecond precision
  - Handles StorageError exceptions on DynamoDB failures
"""
import os
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from models import UserProfile
from profile_manager import save_profile, StorageError


class TestSaveProfile:
    """Tests for save_profile() function."""

    @patch('profile_manager._get_dynamodb')
    @patch.dict(os.environ, {'PROFILES_TABLE': 'TestUserProfiles'})
    def test_save_profile_success(self, mock_get_dynamodb):
        """save_profile should persist UserProfile with all fields and updated_at timestamp."""
        # Setup mock DynamoDB table
        mock_table = MagicMock()
        mock_get_dynamodb.return_value.Table.return_value = mock_table
        
        # Create test profile
        user_id = "test-user-123"
        profile = UserProfile(
            age=25,
            nationality="USA",
            locality="San Francisco",
            ability_level="intermediate"
        )
        
        # Call save_profile
        save_profile(user_id, profile)
        
        # Verify put_item was called once
        mock_table.put_item.assert_called_once()
        
        # Verify the item data
        call_args = mock_table.put_item.call_args
        item = call_args.kwargs['Item']
        
        assert item['user_id'] == user_id
        assert item['age'] == 25
        assert item['nationality'] == "USA"
        assert item['locality'] == "San Francisco"
        assert item['ability_level'] == "intermediate"
        
        # Verify updated_at is in ISO 8601 format with milliseconds
        assert 'updated_at' in item
        updated_at = item['updated_at']
        
        # Check format: YYYY-MM-DDTHH:MM:SS.fffZ
        assert updated_at.endswith('Z')
        assert 'T' in updated_at
        assert '.' in updated_at  # Has milliseconds
        
        # Parse and verify it's a valid ISO 8601 datetime
        parsed = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        assert parsed.tzinfo == timezone.utc
        
        # Verify millisecond precision (3 digits after the dot)
        millisecond_part = updated_at.split('.')[1].replace('Z', '')
        assert len(millisecond_part) == 3

    @patch('profile_manager._get_dynamodb')
    @patch.dict(os.environ, {'PROFILES_TABLE': 'TestUserProfiles'})
    def test_save_profile_with_different_ability_levels(self, mock_get_dynamodb):
        """save_profile should handle all valid ability levels."""
        mock_table = MagicMock()
        mock_get_dynamodb.return_value.Table.return_value = mock_table
        
        user_id = "test-user-456"
        ability_levels = ["beginner", "intermediate", "advanced", "elite"]
        
        for ability in ability_levels:
            profile = UserProfile(
                age=30,
                nationality="Canada",
                locality="Toronto",
                ability_level=ability
            )
            
            save_profile(user_id, profile)
            
            # Verify the ability_level was saved correctly
            call_args = mock_table.put_item.call_args
            item = call_args.kwargs['Item']
            assert item['ability_level'] == ability

    @patch('profile_manager._get_dynamodb')
    @patch.dict(os.environ, {'PROFILES_TABLE': 'TestUserProfiles'})
    def test_save_profile_dynamodb_error_raises_storage_error(self, mock_get_dynamodb):
        """save_profile should raise StorageError when DynamoDB put_item fails."""
        mock_table = MagicMock()
        mock_get_dynamodb.return_value.Table.return_value = mock_table
        
        # Simulate DynamoDB error
        mock_table.put_item.side_effect = ClientError(
            {'Error': {'Code': 'InternalServerError', 'Message': 'Internal error'}},
            'PutItem'
        )
        
        user_id = "test-user-789"
        profile = UserProfile(
            age=40,
            nationality="UK",
            locality="London",
            ability_level="advanced"
        )
        
        # Verify StorageError is raised
        with pytest.raises(StorageError) as exc_info:
            save_profile(user_id, profile)
        
        assert "Failed to save profile to DynamoDB" in str(exc_info.value)

    @patch('profile_manager._get_dynamodb')
    @patch.dict(os.environ, {'PROFILES_TABLE': 'TestUserProfiles'})
    def test_save_profile_updates_existing_profile(self, mock_get_dynamodb):
        """save_profile should overwrite existing profile (update scenario)."""
        mock_table = MagicMock()
        mock_get_dynamodb.return_value.Table.return_value = mock_table
        
        user_id = "test-user-same-id"
        
        # Save initial profile
        profile1 = UserProfile(
            age=20,
            nationality="Germany",
            locality="Berlin",
            ability_level="beginner"
        )
        save_profile(user_id, profile1)
        
        # Save updated profile with same user_id
        profile2 = UserProfile(
            age=21,
            nationality="Germany",
            locality="Munich",
            ability_level="intermediate"
        )
        save_profile(user_id, profile2)
        
        # Verify put_item was called twice (both saves)
        assert mock_table.put_item.call_count == 2
        
        # Verify the second call has updated data
        second_call_args = mock_table.put_item.call_args_list[1]
        item = second_call_args.kwargs['Item']
        
        assert item['age'] == 21
        assert item['locality'] == "Munich"
        assert item['ability_level'] == "intermediate"

    @patch('profile_manager._get_dynamodb')
    @patch.dict(os.environ, {'PROFILES_TABLE': 'TestUserProfiles'})
    def test_save_profile_uses_correct_table_name(self, mock_get_dynamodb):
        """save_profile should use PROFILES_TABLE environment variable."""
        mock_resource = MagicMock()
        mock_get_dynamodb.return_value = mock_resource
        
        user_id = "test-user-env"
        profile = UserProfile(
            age=35,
            nationality="France",
            locality="Paris",
            ability_level="elite"
        )
        
        save_profile(user_id, profile)
        
        # Verify Table() was called with correct table name from environment
        mock_resource.Table.assert_called_once_with('TestUserProfiles')

    @patch('profile_manager._get_dynamodb')
    @patch.dict(os.environ, {'PROFILES_TABLE': 'TestUserProfiles'})
    def test_save_profile_timestamp_precision(self, mock_get_dynamodb):
        """save_profile should generate timestamp with exactly 3 millisecond digits."""
        mock_table = MagicMock()
        mock_get_dynamodb.return_value.Table.return_value = mock_table
        
        user_id = "test-user-timestamp"
        profile = UserProfile(
            age=28,
            nationality="Japan",
            locality="Tokyo",
            ability_level="intermediate"
        )
        
        save_profile(user_id, profile)
        
        call_args = mock_table.put_item.call_args
        item = call_args.kwargs['Item']
        updated_at = item['updated_at']
        
        # Extract milliseconds part
        # Format: 2024-01-15T10:30:45.123Z
        time_part, ms_and_z = updated_at.split('.')
        ms_part = ms_and_z.replace('Z', '')
        
        # Verify exactly 3 digits for milliseconds
        assert len(ms_part) == 3
        assert ms_part.isdigit()
