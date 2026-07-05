"""
Unit tests for backend/chat_history_store.py.

Tests cover:
  - QAEntry dataclass creation
  - get_history returns empty list on missing key
  - get_history returns empty list on read failure
  - get_history returns parsed entries on valid JSON
  - save_history enforces 50-entry cap
  - save_history writes valid JSON to S3
  - append_entry appends and persists
  - append_entry enforces 50-entry cap via read-modify-write
"""
from __future__ import annotations

import json
import os

import boto3
import pytest
from moto import mock_aws

from backend.chat_history_store import (
    MAX_ENTRIES,
    QAEntry,
    append_entry,
    get_history,
    save_history,
)

BUCKET_NAME = "test-swim-bucket"


@pytest.fixture(autouse=True)
def aws_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set required environment variables for all tests."""
    monkeypatch.setenv("S3_BUCKET", BUCKET_NAME)
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")


def _make_entry(i: int) -> QAEntry:
    """Create a test QAEntry with a given index."""
    return QAEntry(
        user_prompt=f"Question {i}",
        ai_response=f"Answer {i}",
        timestamp=f"2025-01-{i:02d}T10:00:00.000Z",
    )


@mock_aws
def test_get_history_returns_empty_on_missing_key() -> None:
    """get_history returns [] when the history file doesn't exist."""
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET_NAME)

    result = get_history("user-123")
    assert result == []


@mock_aws
def test_get_history_returns_empty_on_invalid_json() -> None:
    """get_history returns [] when the file contains invalid JSON."""
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET_NAME)
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key="chat-history/user-123/history.json",
        Body=b"not valid json",
    )

    result = get_history("user-123")
    assert result == []


@mock_aws
def test_get_history_returns_parsed_entries() -> None:
    """get_history correctly parses valid history JSON."""
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET_NAME)

    entries_data = {
        "entries": [
            {
                "user_prompt": "How is my pace?",
                "ai_response": "Your pace has improved.",
                "timestamp": "2025-01-15T10:30:00.000Z",
            }
        ]
    }
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key="chat-history/user-123/history.json",
        Body=json.dumps(entries_data).encode(),
    )

    result = get_history("user-123")
    assert len(result) == 1
    assert result[0].user_prompt == "How is my pace?"
    assert result[0].ai_response == "Your pace has improved."
    assert result[0].timestamp == "2025-01-15T10:30:00.000Z"


@mock_aws
def test_save_history_writes_json_to_s3() -> None:
    """save_history writes correctly formatted JSON to the expected key."""
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET_NAME)

    entries = [_make_entry(1), _make_entry(2)]
    save_history("user-456", entries)

    obj = s3.get_object(
        Bucket=BUCKET_NAME, Key="chat-history/user-456/history.json"
    )
    data = json.loads(obj["Body"].read().decode())
    assert len(data["entries"]) == 2
    assert data["entries"][0]["user_prompt"] == "Question 1"
    assert data["entries"][1]["user_prompt"] == "Question 2"


@mock_aws
def test_save_history_enforces_50_entry_cap() -> None:
    """save_history drops oldest entries when history exceeds 50."""
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET_NAME)

    entries = [_make_entry(i) for i in range(1, 61)]  # 60 entries
    save_history("user-789", entries)

    obj = s3.get_object(
        Bucket=BUCKET_NAME, Key="chat-history/user-789/history.json"
    )
    data = json.loads(obj["Body"].read().decode())
    assert len(data["entries"]) == MAX_ENTRIES
    # Should keep the last 50 (entries 11-60)
    assert data["entries"][0]["user_prompt"] == "Question 11"
    assert data["entries"][-1]["user_prompt"] == "Question 60"


@mock_aws
def test_append_entry_adds_to_empty_history() -> None:
    """append_entry works when no prior history exists."""
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET_NAME)

    entry = QAEntry(
        user_prompt="First question",
        ai_response="First answer",
        timestamp="2025-01-15T10:30:00.000Z",
    )
    append_entry("user-new", entry)

    result = get_history("user-new")
    assert len(result) == 1
    assert result[0].user_prompt == "First question"


@mock_aws
def test_append_entry_adds_to_existing_history() -> None:
    """append_entry appends to existing entries."""
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET_NAME)

    # Pre-populate with 2 entries
    initial = [_make_entry(1), _make_entry(2)]
    save_history("user-existing", initial)

    new_entry = QAEntry(
        user_prompt="New question",
        ai_response="New answer",
        timestamp="2025-02-01T10:00:00.000Z",
    )
    append_entry("user-existing", new_entry)

    result = get_history("user-existing")
    assert len(result) == 3
    assert result[-1].user_prompt == "New question"


@mock_aws
def test_append_entry_enforces_cap_on_overflow() -> None:
    """append_entry drops oldest entry when appending would exceed 50."""
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET_NAME)

    # Pre-populate with exactly 50 entries
    initial = [_make_entry(i) for i in range(1, 51)]
    save_history("user-full", initial)

    new_entry = QAEntry(
        user_prompt="Entry 51",
        ai_response="Answer 51",
        timestamp="2025-03-01T10:00:00.000Z",
    )
    append_entry("user-full", new_entry)

    result = get_history("user-full")
    assert len(result) == MAX_ENTRIES
    # Oldest (entry 1) should be gone, entry 2 should be first
    assert result[0].user_prompt == "Question 2"
    assert result[-1].user_prompt == "Entry 51"


@mock_aws
def test_qa_entry_user_prompt_stored_up_to_2000_chars() -> None:
    """QAEntry can store a user_prompt at the max 2000 character limit."""
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET_NAME)

    long_prompt = "x" * 2000
    entry = QAEntry(
        user_prompt=long_prompt,
        ai_response="Response",
        timestamp="2025-01-15T10:30:00.000Z",
    )
    save_history("user-long", [entry])

    result = get_history("user-long")
    assert len(result) == 1
    assert len(result[0].user_prompt) == 2000
