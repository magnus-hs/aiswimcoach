"""
Unit tests for backend/s3_store.py — store_in_s3().

Tests cover:
  - Successful S3 write: returned key format matches uploads/{uuid4}.fit
  - Unique keys on repeated calls
  - StorageError raised (HTTP 500) when boto3 raises ClientError
"""
from __future__ import annotations

import os
import re
import uuid

import boto3
import pytest
from moto import mock_aws

from backend.s3_store import StorageError, store_in_s3

# Pattern for a valid UUID v4 (RFC 4122)
UUID4_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
KEY_PATTERN = re.compile(
    r"^uploads/[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\.fit$"
)

BUCKET_NAME = "test-swim-bucket"
FIT_BYTES = b"\x0e\x10\x00\x00fake fit bytes"


@pytest.fixture(autouse=True)
def aws_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set required environment variables for all tests in this module."""
    monkeypatch.setenv("S3_BUCKET", BUCKET_NAME)
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")


@mock_aws
def test_store_in_s3_returns_valid_key_format() -> None:
    """Returned key matches the pattern uploads/{uuid4}.fit."""
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET_NAME)

    key = store_in_s3(FIT_BYTES)

    assert KEY_PATTERN.match(key), f"Key '{key}' does not match expected pattern"


@mock_aws
def test_store_in_s3_object_exists_in_bucket() -> None:
    """After a successful call the object is actually present in S3."""
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET_NAME)

    key = store_in_s3(FIT_BYTES)

    obj = s3.get_object(Bucket=BUCKET_NAME, Key=key)
    assert obj["Body"].read() == FIT_BYTES


@mock_aws
def test_store_in_s3_bytes_stored_without_modification() -> None:
    """The bytes written to S3 are byte-for-byte identical to the input."""
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET_NAME)

    payload = b"\x00\xff\x0a" * 512  # arbitrary binary content
    key = store_in_s3(payload)

    obj = s3.get_object(Bucket=BUCKET_NAME, Key=key)
    assert obj["Body"].read() == payload


@mock_aws
def test_store_in_s3_keys_are_unique() -> None:
    """Two calls produce distinct keys (UUID v4 collision is astronomically unlikely)."""
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET_NAME)

    key1 = store_in_s3(FIT_BYTES)
    key2 = store_in_s3(FIT_BYTES)

    assert key1 != key2


@mock_aws
def test_store_in_s3_key_uuid_is_version_4() -> None:
    """The UUID embedded in the key is a valid version 4 UUID."""
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET_NAME)

    key = store_in_s3(FIT_BYTES)
    # Extract UUID portion from 'uploads/<uuid>.fit'
    uuid_str = key[len("uploads/") : -len(".fit")]
    parsed = uuid.UUID(uuid_str)
    assert parsed.version == 4


@mock_aws
def test_store_in_s3_raises_storage_error_on_client_error() -> None:
    """StorageError is raised (not ClientError) when S3 rejects the write.

    We deliberately do NOT create the bucket so put_object raises ClientError.
    """
    # Bucket does not exist → NoSuchBucket or similar ClientError
    with pytest.raises(StorageError) as exc_info:
        store_in_s3(FIT_BYTES)

    assert "Failed to store file" in str(exc_info.value)


@mock_aws
def test_storage_error_is_exception() -> None:
    """StorageError inherits from Exception (can be caught generically)."""
    assert issubclass(StorageError, Exception)
