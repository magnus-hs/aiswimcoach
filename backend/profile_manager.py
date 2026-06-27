"""
Profile manager for AI Swim Coach.

Manages user profile persistence and retrieval from DynamoDB UserProfiles table,
and profile picture management in S3.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from models import UserProfile  # type: ignore


# Module-level placeholders; lazily initialized on first call
_dynamodb_resource = None
_s3_client = None


# Magic bytes for image file format validation
JPEG_MAGIC_BYTES = [
    bytes([0xFF, 0xD8, 0xFF]),  # JPEG (all variants start with FF D8 FF)
]

PNG_MAGIC_BYTES = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])  # PNG

GIF_MAGIC_BYTES = [
    bytes([0x47, 0x49, 0x46, 0x38, 0x37, 0x61]),  # GIF87a
    bytes([0x47, 0x49, 0x46, 0x38, 0x39, 0x61]),  # GIF89a
]

MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB in bytes (2,097,152)


def _get_dynamodb() -> "boto3.resources.base.ServiceResource":
    """Return the (cached) DynamoDB resource, creating it if necessary."""
    global _dynamodb_resource  # noqa: PLW0603
    if _dynamodb_resource is None:
        _dynamodb_resource = boto3.resource("dynamodb")
    return _dynamodb_resource


def _get_s3_client() -> "boto3.client":
    """Return the (cached) S3 client, creating it if necessary."""
    global _s3_client  # noqa: PLW0603
    if _s3_client is None:
        _s3_client = boto3.client("s3")
    return _s3_client


class StorageError(Exception):
    """Exception raised when DynamoDB or S3 operations fail."""
    pass


def save_profile(user_id: str, profile: UserProfile) -> None:
    """Persist or update user profile in UserProfiles table.
    
    Stores the user profile with all fields from the UserProfile dataclass
    plus an updated_at timestamp in ISO 8601 format with UTC timezone and
    millisecond precision.
    
    The table name is resolved from the PROFILES_TABLE environment variable.
    
    Args:
        user_id: User identifier (UUID v4)
        profile: UserProfile object with validated data
    
    Raises:
        StorageError: If DynamoDB write fails
    
    Requirements: 5.1-5.6
    """
    table_name = os.environ["PROFILES_TABLE"]
    
    # Build ISO 8601 UTC timestamp with millisecond precision
    now = datetime.now(tz=timezone.utc)
    ms = now.microsecond // 1000
    updated_at = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ms:03d}Z"
    
    item = {
        "user_id": user_id,
        "age": profile.age,
        "nationality": profile.nationality,
        "locality": profile.locality,
        "ability_level": profile.ability_level,
        "updated_at": updated_at,
    }
    
    table = _get_dynamodb().Table(table_name)
    try:
        table.put_item(Item=item)
    except ClientError as e:
        raise StorageError(f"Failed to save profile to DynamoDB: {e}") from e


def get_profile(user_id: str) -> Optional[UserProfile]:
    """Retrieve user profile from DynamoDB.
    
    Args:
        user_id: User identifier (UUID v4)
    
    Returns:
        UserProfile object if profile exists, None otherwise
    
    Raises:
        StorageError: If DynamoDB query fails
    
    Requirements: 5.9
    """
    table_name = os.environ["PROFILES_TABLE"]
    table = _get_dynamodb().Table(table_name)
    
    try:
        response = table.get_item(Key={"user_id": user_id})
    except ClientError as e:
        raise StorageError(f"Failed to retrieve profile from DynamoDB: {e}") from e
    
    # Profile doesn't exist
    if "Item" not in response:
        return None
    
    item = response["Item"]
    
    # Construct UserProfile from DynamoDB item
    try:
        profile = UserProfile(
            age=int(item["age"]),
            nationality=item["nationality"],
            locality=item["locality"],
            ability_level=item["ability_level"]
        )
        return profile
    except (KeyError, ValueError, TypeError) as e:
        raise StorageError(f"Failed to parse profile data: {e}") from e


def validate_image_file(file_bytes: bytes) -> tuple[bool, Optional[str]]:
    """Validate image file format by checking magic bytes for JPEG/PNG/GIF.
    
    This function validates that the file is a valid image format by examining
    the file header magic bytes rather than relying on file extensions.
    
    Args:
        file_bytes: Raw file bytes to validate
    
    Returns:
        Tuple of (is_valid, file_extension):
        - is_valid: True if file is a valid JPEG, PNG, or GIF
        - file_extension: File extension string ('jpg', 'png', 'gif') or None if invalid
    
    Requirements: 23.2, 23.5
    """
    if not file_bytes or len(file_bytes) < 8:
        return False, None
    
    # Check PNG (8 bytes)
    if file_bytes[:8] == PNG_MAGIC_BYTES:
        return True, 'png'
    
    # Check JPEG (3 bytes - FF D8 FF)
    for jpeg_magic in JPEG_MAGIC_BYTES:
        if file_bytes[:len(jpeg_magic)] == jpeg_magic:
            return True, 'jpg'
    
    # Check GIF (6 bytes)
    for gif_magic in GIF_MAGIC_BYTES:
        if file_bytes[:6] == gif_magic:
            return True, 'gif'
    
    return False, None


def validate_file_size(file_bytes: bytes, max_size: int = MAX_FILE_SIZE) -> bool:
    """Validate that file size does not exceed the maximum allowed size.
    
    Args:
        file_bytes: Raw file bytes to validate
        max_size: Maximum allowed file size in bytes (default: 2 MB = 2,097,152 bytes)
    
    Returns:
        True if file size is within limit, False otherwise
    
    Requirements: 23.2, 23.7
    """
    if not file_bytes:
        return False
    
    return len(file_bytes) <= max_size


def upload_profile_picture(
    user_id: str,
    image_bytes: bytes,
    content_type: str
) -> str:
    """Upload profile picture to S3 and update user record.
    
    Generates a unique filename using the format {user_id}_{timestamp}.{extension},
    uploads the image to S3 bucket specified by PROFILE_PICTURES_BUCKET environment
    variable, and updates the Users table with the profile_picture_url.
    
    Args:
        user_id: User identifier (UUID v4)
        image_bytes: Image file bytes
        content_type: MIME type (image/jpeg, image/png, image/gif)
    
    Returns:
        S3 URL of uploaded image
    
    Raises:
        ValueError: If image invalid or too large
        StorageError: If S3 upload or DynamoDB update fails
    
    Requirements: 23.8-23.11
    """
    # Validate file size (2 MB max per requirement 23.7)
    if not validate_file_size(image_bytes):
        raise ValueError(f"Image file size exceeds 2 MB limit (size: {len(image_bytes)} bytes)")
    
    # Validate image format using magic bytes (requirement 23.5)
    is_valid, extension = validate_image_file(image_bytes)
    if not is_valid:
        raise ValueError("Invalid image file format. Supported formats: JPEG, PNG, GIF")
    
    # Generate unique filename: {user_id}_{timestamp}.{extension} (requirement 23.8)
    timestamp = int(time.time() * 1000)  # milliseconds since epoch
    filename = f"{user_id}_{timestamp}.{extension}"
    
    # Get S3 bucket from environment
    bucket_name = os.environ["PROFILE_PICTURES_BUCKET"]
    
    # Upload to S3 (requirement 23.9)
    s3_client = _get_s3_client()
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=filename,
            Body=image_bytes,
            ContentType=content_type,
            ACL='public-read'  # Public read access per requirement 23.15
        )
    except ClientError as e:
        raise StorageError(f"Failed to upload image to S3: {e}") from e
    
    # Construct S3 URL
    s3_url = f"https://{bucket_name}.s3.amazonaws.com/{filename}"
    
    # Update Users table with profile_picture_url (requirement 23.10)
    users_table_name = os.environ["USERS_TABLE"]
    users_table = _get_dynamodb().Table(users_table_name)
    
    try:
        users_table.update_item(
            Key={"user_id": user_id},
            UpdateExpression="SET profile_picture_url = :url",
            ExpressionAttributeValues={":url": s3_url},
            ConditionExpression="attribute_exists(user_id)"
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise StorageError(f"User not found: {user_id}") from e
        raise StorageError(f"Failed to update user record with profile picture URL: {e}") from e
    
    return s3_url
