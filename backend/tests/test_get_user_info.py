"""
Tests for get_user_info function in auth module.

Validates: Requirements 24.1-24.6
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest
from moto import mock_aws


@pytest.fixture
def setup_dynamodb():
    """Set up mock DynamoDB with Users table."""
    with mock_aws():
        import boto3
        import backend.auth as auth_module
        
        # Create Users table
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName="test-users-table",
            KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "email", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "email-index",
                    "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 5,
                        "WriteCapacityUnits": 5,
                    },
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        
        # Set environment variables
        os.environ["USERS_TABLE"] = "test-users-table"
        os.environ["JWT_SECRET"] = "test-secret-key-for-jwt-tokens-minimum-256-bits"
        
        # Reload dynamodb resource in auth module
        auth_module.dynamodb = dynamodb
        
        yield table


def test_get_user_info_returns_user_data(setup_dynamodb):
    """Test get_user_info returns correct user data including profile picture URL."""
    from backend.auth import register_user, get_user_info
    
    # Register a user
    user = register_user("test@example.com", "password123")
    user_id = user["user_id"]
    
    # Add profile picture URL to user record
    table = setup_dynamodb
    table.update_item(
        Key={"user_id": user_id},
        UpdateExpression="SET profile_picture_url = :url",
        ExpressionAttributeValues={
            ":url": "https://bucket.s3.amazonaws.com/user_123.jpg"
        },
    )
    
    # Get user info
    user_info = get_user_info(user_id)
    
    assert user_info["user_id"] == user_id
    assert user_info["email"] == "test@example.com"
    assert user_info["profile_picture_url"] == "https://bucket.s3.amazonaws.com/user_123.jpg"
    assert "created_at" in user_info


def test_get_user_info_returns_none_for_missing_profile_picture(setup_dynamodb):
    """Test get_user_info returns None for profile_picture_url when not set."""
    from backend.auth import register_user, get_user_info
    
    # Register a user (no profile picture)
    user = register_user("test@example.com", "password123")
    user_id = user["user_id"]
    
    # Get user info
    user_info = get_user_info(user_id)
    
    assert user_info["user_id"] == user_id
    assert user_info["email"] == "test@example.com"
    assert user_info["profile_picture_url"] is None
    assert "created_at" in user_info


def test_get_user_info_raises_error_for_nonexistent_user(setup_dynamodb):
    """Test get_user_info raises AuthenticationError for nonexistent user."""
    from backend.auth import get_user_info, AuthenticationError
    
    fake_user_id = str(uuid.uuid4())
    
    with pytest.raises(AuthenticationError, match="User not found"):
        get_user_info(fake_user_id)


def test_get_user_info_requires_users_table_env_var():
    """Test get_user_info raises ValueError when USERS_TABLE not configured."""
    from backend.auth import get_user_info
    
    # Remove USERS_TABLE env var
    original = os.environ.pop("USERS_TABLE", None)
    
    try:
        with pytest.raises(ValueError, match="USERS_TABLE"):
            get_user_info("some-user-id")
    finally:
        if original:
            os.environ["USERS_TABLE"] = original
