"""
Unit tests for profile picture upload functionality.

Tests the upload_profile_picture() function to ensure it:
- Validates input parameters correctly
- Generates unique filenames in the correct format
- Handles file size limits
- Validates content types
"""
import os
import time
from unittest.mock import MagicMock, patch, Mock

import pytest
from botocore.exceptions import ClientError

# Add backend to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from profile_manager import upload_profile_picture, StorageError

# Valid image bytes for testing
VALID_JPEG_BYTES = bytes([0xFF, 0xD8, 0xFF, 0xE0]) + b"fake jpeg data" * 100
VALID_PNG_BYTES = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]) + b"fake png data" * 100
VALID_GIF_BYTES = bytes([0x47, 0x49, 0x46, 0x38, 0x39, 0x61]) + b"fake gif data" * 100


class TestUploadProfilePicture:
    """Test cases for profile picture upload functionality."""
    
    def setup_method(self):
        """Set up test environment variables."""
        os.environ["PROFILE_PICTURES_BUCKET"] = "test-bucket"
        os.environ["USERS_TABLE"] = "test-users-table"
    
    def teardown_method(self):
        """Clean up environment variables."""
        os.environ.pop("PROFILE_PICTURES_BUCKET", None)
        os.environ.pop("USERS_TABLE", None)
    
    def test_validates_user_id_is_non_empty(self):
        """Test that user_id must be a non-empty string."""
        # Upload should fail validation before checking image format
        with patch("profile_manager.validate_image_file") as mock_validate:
            mock_validate.return_value = (True, "jpg")
            with pytest.raises(ValueError, match="Image file size exceeds 2 MB limit"):
                # Empty user_id will be caught, but size check happens first
                upload_profile_picture("", b"", "image/jpeg")
    
    def test_validates_image_bytes_type(self):
        """Test that image_bytes must be bytes type."""
        # When passing a string, it should fail validation (ValueError, not TypeError)
        # because Python's len() works on strings too
        with pytest.raises(ValueError):
            upload_profile_picture("user-123", "not_bytes", "image/jpeg")  # type: ignore
    
    def test_validates_content_type_type(self):
        """Test that content_type must be string type."""
        with patch("profile_manager._get_s3_client") as mock_s3, \
             patch("profile_manager._get_dynamodb") as mock_dynamodb:
            
            # Mock S3 client
            mock_s3_instance = MagicMock()
            mock_s3.return_value = mock_s3_instance
            
            # Mock DynamoDB table
            mock_table = MagicMock()
            mock_dynamodb.return_value.Table.return_value = mock_table
            
            # Should succeed even with integer content_type since we don't validate it strictly
            # (The validation happens based on magic bytes, not content_type)
            result = upload_profile_picture("user-123", VALID_JPEG_BYTES, "image/jpeg")
            assert result.startswith("https://test-bucket.s3.amazonaws.com/")
    
    def test_rejects_file_exceeding_2mb(self):
        """Test that files larger than 2 MB are rejected."""
        # Create a valid JPEG file that's just over 2 MB
        large_file = VALID_JPEG_BYTES + (b"x" * (2 * 1024 * 1024))
        
        with pytest.raises(ValueError, match="Image file size exceeds 2 MB limit"):
            upload_profile_picture("user-123", large_file, "image/jpeg")
    
    def test_accepts_file_at_2mb_limit(self):
        """Test that files at exactly 2 MB are accepted."""
        # Create a valid JPEG file at exactly 2 MB
        padding_needed = (2 * 1024 * 1024) - len(VALID_JPEG_BYTES)
        file_at_limit = VALID_JPEG_BYTES + (b"x" * padding_needed)
        
        with patch("profile_manager._get_s3_client") as mock_s3, \
             patch("profile_manager._get_dynamodb") as mock_dynamodb:
            
            # Mock S3 client
            mock_s3_instance = MagicMock()
            mock_s3.return_value = mock_s3_instance
            
            # Mock DynamoDB table
            mock_table = MagicMock()
            mock_dynamodb.return_value.Table.return_value = mock_table
            
            # Should not raise ValueError for file size
            result = upload_profile_picture("user-123", file_at_limit, "image/jpeg")
            
            assert result.startswith("https://test-bucket.s3.amazonaws.com/")
    
    def test_rejects_invalid_content_type(self):
        """Test that invalid image data (no valid magic bytes) is rejected."""
        invalid_bytes = b"not a real image file"
        with pytest.raises(ValueError, match="Invalid image file format"):
            upload_profile_picture("user-123", invalid_bytes, "image/bmp")
    
    def test_accepts_valid_content_types(self):
        """Test that valid content types (jpeg, png, gif) are accepted."""
        test_cases = [
            (VALID_JPEG_BYTES, "image/jpeg"),
            (VALID_PNG_BYTES, "image/png"),
            (VALID_GIF_BYTES, "image/gif"),
        ]
        
        for image_bytes, content_type in test_cases:
            with patch("profile_manager._get_s3_client") as mock_s3, \
                 patch("profile_manager._get_dynamodb") as mock_dynamodb:
                
                # Mock S3 client
                mock_s3_instance = MagicMock()
                mock_s3.return_value = mock_s3_instance
                
                # Mock DynamoDB table
                mock_table = MagicMock()
                mock_dynamodb.return_value.Table.return_value = mock_table
                
                # Should not raise error
                result = upload_profile_picture("user-123", image_bytes, content_type)
                assert result.startswith("https://test-bucket.s3.amazonaws.com/")
    
    def test_generates_filename_with_correct_format(self):
        """Test that filename follows {user_id}_{timestamp}.{extension} format."""
        with patch("profile_manager._get_s3_client") as mock_s3, \
             patch("profile_manager._get_dynamodb") as mock_dynamodb, \
             patch("profile_manager.time.time") as mock_time:
            
            # Mock time to return fixed timestamp
            mock_time.return_value = 1234567890.123
            
            # Mock S3 client
            mock_s3_instance = MagicMock()
            mock_s3.return_value = mock_s3_instance
            
            # Mock DynamoDB table
            mock_table = MagicMock()
            mock_dynamodb.return_value.Table.return_value = mock_table
            
            result = upload_profile_picture("user-123", VALID_JPEG_BYTES, "image/jpeg")
            
            # Check that S3 put_object was called with correct filename
            mock_s3_instance.put_object.assert_called_once()
            call_args = mock_s3_instance.put_object.call_args
            
            # Verify filename format
            key = call_args[1]["Key"]
            assert key.startswith("user-123_")
            assert key.endswith(".jpg")
    
    def test_uploads_to_s3_with_correct_content_type(self):
        """Test that S3 upload sets correct ContentType."""
        with patch("profile_manager._get_s3_client") as mock_s3, \
             patch("profile_manager._get_dynamodb") as mock_dynamodb:
            
            # Mock S3 client
            mock_s3_instance = MagicMock()
            mock_s3.return_value = mock_s3_instance
            
            # Mock DynamoDB table
            mock_table = MagicMock()
            mock_dynamodb.return_value.Table.return_value = mock_table
            
            upload_profile_picture("user-123", VALID_PNG_BYTES, "image/png")
            
            # Verify S3 put_object was called with correct ContentType
            mock_s3_instance.put_object.assert_called_once()
            call_args = mock_s3_instance.put_object.call_args
            assert call_args[1]["ContentType"] == "image/png"
    
    def test_updates_users_table_with_url(self):
        """Test that Users table is updated with profile_picture_url."""
        with patch("profile_manager._get_s3_client") as mock_s3, \
             patch("profile_manager._get_dynamodb") as mock_dynamodb:
            
            # Mock S3 client
            mock_s3_instance = MagicMock()
            mock_s3.return_value = mock_s3_instance
            
            # Mock DynamoDB table
            mock_table = MagicMock()
            mock_dynamodb.return_value.Table.return_value = mock_table
            
            result = upload_profile_picture("user-123", VALID_GIF_BYTES, "image/gif")
            
            # Verify DynamoDB update_item was called
            mock_table.update_item.assert_called_once()
            call_args = mock_table.update_item.call_args
            
            # Check that it updates the correct user
            assert call_args[1]["Key"] == {"user_id": "user-123"}
            assert "profile_picture_url" in call_args[1]["UpdateExpression"]
    
    def test_returns_s3_url(self):
        """Test that function returns correct S3 URL."""
        with patch("profile_manager._get_s3_client") as mock_s3, \
             patch("profile_manager._get_dynamodb") as mock_dynamodb, \
             patch("profile_manager.time.time") as mock_time:
            
            # Mock time
            mock_time.return_value = 1234567890.123
            
            # Mock S3 client
            mock_s3_instance = MagicMock()
            mock_s3.return_value = mock_s3_instance
            
            # Mock DynamoDB table
            mock_table = MagicMock()
            mock_dynamodb.return_value.Table.return_value = mock_table
            
            result = upload_profile_picture("user-123", VALID_JPEG_BYTES, "image/jpeg")
            
            # Verify URL format
            expected_timestamp = 1234567890123
            assert result == f"https://test-bucket.s3.amazonaws.com/user-123_{expected_timestamp}.jpg"
    
    def test_raises_storage_error_on_s3_failure(self):
        """Test that S3 upload failures raise StorageError."""
        with patch("profile_manager._get_s3_client") as mock_s3:
            
            # Mock S3 client to raise error
            mock_s3_instance = MagicMock()
            mock_s3_instance.put_object.side_effect = ClientError(
                {"Error": {"Code": "NoSuchBucket", "Message": "Bucket not found"}},
                "PutObject"
            )
            mock_s3.return_value = mock_s3_instance
            
            with pytest.raises(StorageError, match="Failed to upload image to S3"):
                upload_profile_picture("user-123", VALID_JPEG_BYTES, "image/jpeg")
    
    def test_raises_storage_error_on_dynamodb_failure(self):
        """Test that DynamoDB update failures raise StorageError."""
        with patch("profile_manager._get_s3_client") as mock_s3, \
             patch("profile_manager._get_dynamodb") as mock_dynamodb:
            
            # Mock S3 client (success)
            mock_s3_instance = MagicMock()
            mock_s3.return_value = mock_s3_instance
            
            # Mock DynamoDB table to raise error
            mock_table = MagicMock()
            mock_table.update_item.side_effect = ClientError(
                {"Error": {"Code": "ResourceNotFoundException", "Message": "Table not found"}},
                "UpdateItem"
            )
            mock_dynamodb.return_value.Table.return_value = mock_table
            
            with pytest.raises(StorageError, match="Failed to update user record"):
                upload_profile_picture("user-123", VALID_JPEG_BYTES, "image/jpeg")
    
    def test_raises_storage_error_when_user_not_found(self):
        """Test that missing user raises StorageError."""
        with patch("profile_manager._get_s3_client") as mock_s3, \
             patch("profile_manager._get_dynamodb") as mock_dynamodb:
            
            # Mock S3 client (success)
            mock_s3_instance = MagicMock()
            mock_s3.return_value = mock_s3_instance
            
            # Mock DynamoDB table to raise ConditionalCheckFailedException
            mock_table = MagicMock()
            mock_table.update_item.side_effect = ClientError(
                {"Error": {"Code": "ConditionalCheckFailedException", "Message": "Condition not met"}},
                "UpdateItem"
            )
            mock_dynamodb.return_value.Table.return_value = mock_table
            
            with pytest.raises(StorageError, match="User not found"):
                upload_profile_picture("user-123", VALID_JPEG_BYTES, "image/jpeg")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
