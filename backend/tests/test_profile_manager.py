"""
Unit tests for backend/profile_manager.py

Tests cover profile picture validation functions:
  - Image file validation using magic bytes (JPEG, PNG, GIF)
  - File size validation (max 2 MB)
  - Edge cases (empty files, truncated headers, invalid formats)
"""
import pytest

from backend.profile_manager import (
    validate_image_file,
    validate_file_size,
    MAX_FILE_SIZE,
)


class TestValidateImageFile:
    """Tests for validate_image_file() function."""

    def test_valid_jpeg_file(self):
        """Valid JPEG file should be accepted and return 'jpg' extension."""
        # JPEG magic bytes: FF D8 FF
        jpeg_bytes = bytes([0xFF, 0xD8, 0xFF, 0xE0]) + b'\x00' * 100
        is_valid, extension = validate_image_file(jpeg_bytes)
        assert is_valid is True
        assert extension == 'jpg'

    def test_valid_png_file(self):
        """Valid PNG file should be accepted and return 'png' extension."""
        # PNG magic bytes: 89 50 4E 47 0D 0A 1A 0A
        png_bytes = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]) + b'\x00' * 100
        is_valid, extension = validate_image_file(png_bytes)
        assert is_valid is True
        assert extension == 'png'

    def test_valid_gif87a_file(self):
        """Valid GIF87a file should be accepted and return 'gif' extension."""
        # GIF87a magic bytes: 47 49 46 38 37 61
        gif_bytes = bytes([0x47, 0x49, 0x46, 0x38, 0x37, 0x61]) + b'\x00' * 100
        is_valid, extension = validate_image_file(gif_bytes)
        assert is_valid is True
        assert extension == 'gif'

    def test_valid_gif89a_file(self):
        """Valid GIF89a file should be accepted and return 'gif' extension."""
        # GIF89a magic bytes: 47 49 46 38 39 61
        gif_bytes = bytes([0x47, 0x49, 0x46, 0x38, 0x39, 0x61]) + b'\x00' * 100
        is_valid, extension = validate_image_file(gif_bytes)
        assert is_valid is True
        assert extension == 'gif'

    def test_invalid_file_format(self):
        """File with invalid magic bytes should be rejected."""
        # Random bytes that don't match any image format
        invalid_bytes = b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09'
        is_valid, extension = validate_image_file(invalid_bytes)
        assert is_valid is False
        assert extension is None

    def test_text_file_rejected(self):
        """Text file should be rejected."""
        text_bytes = b'This is a text file, not an image'
        is_valid, extension = validate_image_file(text_bytes)
        assert is_valid is False
        assert extension is None

    def test_empty_file_rejected(self):
        """Empty file should be rejected."""
        empty_bytes = b''
        is_valid, extension = validate_image_file(empty_bytes)
        assert is_valid is False
        assert extension is None

    def test_file_with_less_than_8_bytes_rejected(self):
        """File with less than 8 bytes should be rejected."""
        short_bytes = b'\xFF\xD8\xFF'  # Only 3 bytes
        is_valid, extension = validate_image_file(short_bytes)
        assert is_valid is False
        assert extension is None

    def test_file_with_partial_jpeg_magic_bytes(self):
        """File with partial JPEG magic bytes should be rejected."""
        # Only FF D8, missing the third FF byte
        partial_jpeg = bytes([0xFF, 0xD8, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        is_valid, extension = validate_image_file(partial_jpeg)
        assert is_valid is False
        assert extension is None

    def test_file_with_jpeg_extension_but_wrong_magic_bytes(self):
        """File claiming to be JPEG but with wrong magic bytes should be rejected."""
        # This simulates a file renamed to .jpg but actually containing different data
        fake_jpeg = b'FAKE_IMAGE_DATA_NOT_JPEG'
        is_valid, extension = validate_image_file(fake_jpeg)
        assert is_valid is False
        assert extension is None


class TestValidateFileSize:
    """Tests for validate_file_size() function."""

    def test_file_within_size_limit(self):
        """File smaller than 2 MB should be accepted."""
        # 1 MB file
        file_bytes = b'\x00' * (1 * 1024 * 1024)
        assert validate_file_size(file_bytes) is True

    def test_file_exactly_at_size_limit(self):
        """File exactly at 2 MB should be accepted."""
        # Exactly 2 MB (2,097,152 bytes)
        file_bytes = b'\x00' * MAX_FILE_SIZE
        assert validate_file_size(file_bytes) is True

    def test_file_exceeds_size_limit(self):
        """File exceeding 2 MB should be rejected."""
        # 2 MB + 1 byte
        file_bytes = b'\x00' * (MAX_FILE_SIZE + 1)
        assert validate_file_size(file_bytes) is False

    def test_file_significantly_exceeds_size_limit(self):
        """File significantly exceeding 2 MB should be rejected."""
        # 5 MB file
        file_bytes = b'\x00' * (5 * 1024 * 1024)
        assert validate_file_size(file_bytes) is False

    def test_empty_file_rejected(self):
        """Empty file should be rejected."""
        empty_bytes = b''
        assert validate_file_size(empty_bytes) is False

    def test_very_small_file_accepted(self):
        """Very small file (1 KB) should be accepted."""
        small_file = b'\x00' * 1024
        assert validate_file_size(small_file) is True

    def test_custom_size_limit(self):
        """Custom size limit should be respected."""
        # Test with custom limit of 1 MB
        file_bytes = b'\x00' * (1 * 1024 * 1024 + 1)  # 1 MB + 1 byte
        custom_limit = 1 * 1024 * 1024  # 1 MB
        assert validate_file_size(file_bytes, max_size=custom_limit) is False
        
        # File exactly at custom limit should pass
        file_at_limit = b'\x00' * custom_limit
        assert validate_file_size(file_at_limit, max_size=custom_limit) is True

    def test_none_file_rejected(self):
        """None as file bytes should be rejected."""
        assert validate_file_size(None) is False


class TestImageValidationIntegration:
    """Integration tests combining file size and image format validation."""

    def test_valid_jpeg_within_size_limit(self):
        """Valid JPEG file within size limit should pass both validations."""
        # 1 MB JPEG file
        jpeg_bytes = bytes([0xFF, 0xD8, 0xFF, 0xE0]) + b'\x00' * (1024 * 1024)
        
        # Check image format
        is_valid_format, extension = validate_image_file(jpeg_bytes)
        assert is_valid_format is True
        assert extension == 'jpg'
        
        # Check file size
        assert validate_file_size(jpeg_bytes) is True

    def test_valid_png_exceeds_size_limit(self):
        """Valid PNG file exceeding size limit should fail size validation."""
        # 3 MB PNG file
        png_bytes = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]) + b'\x00' * (3 * 1024 * 1024)
        
        # Check image format (should pass)
        is_valid_format, extension = validate_image_file(png_bytes)
        assert is_valid_format is True
        assert extension == 'png'
        
        # Check file size (should fail)
        assert validate_file_size(png_bytes) is False

    def test_invalid_format_within_size_limit(self):
        """Invalid file format within size limit should fail format validation."""
        # 1 MB text file
        text_bytes = b'Not an image file' * (1024 * 64)  # ~1 MB
        
        # Check image format (should fail)
        is_valid_format, extension = validate_image_file(text_bytes)
        assert is_valid_format is False
        assert extension is None
        
        # Check file size (should pass)
        assert validate_file_size(text_bytes) is True
