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
  - Property 1: Chat history round-trip
  - Property 2: History size bounded at 50
"""
from __future__ import annotations

import json
import os

import boto3
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
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



# ──────────────────────────────────────────────────────────────────────────────
# Feature: ai-coach-context, Property 1: Chat history round-trip
# For any list of valid QAEntry objects, serialize to JSON and deserialize back,
# assert equivalence.
# Validates: Requirements 1.2, 1.8
# ──────────────────────────────────────────────────────────────────────────────


def _iso8601_timestamp_strategy() -> st.SearchStrategy[str]:
    """Generate valid ISO 8601 UTC timestamps."""
    return st.builds(
        lambda y, mo, d, h, mi, s: f"{y:04d}-{mo:02d}-{d:02d}T{h:02d}:{mi:02d}:{s:02d}.000Z",
        y=st.integers(min_value=2020, max_value=2030),
        mo=st.integers(min_value=1, max_value=12),
        d=st.integers(min_value=1, max_value=28),
        h=st.integers(min_value=0, max_value=23),
        mi=st.integers(min_value=0, max_value=59),
        s=st.integers(min_value=0, max_value=59),
    )


def _qa_entry_strategy() -> st.SearchStrategy[QAEntry]:
    """Generate valid QAEntry objects with non-empty fields and max 2000-char prompt."""
    return st.builds(
        QAEntry,
        user_prompt=st.text(min_size=1, max_size=2000, alphabet=st.characters(blacklist_categories=("Cs",))),
        ai_response=st.text(min_size=1, alphabet=st.characters(blacklist_categories=("Cs",))),
        timestamp=_iso8601_timestamp_strategy(),
    )


@mock_aws
@settings(max_examples=100, deadline=None)
@given(entries=st.lists(_qa_entry_strategy(), min_size=0, max_size=50))
def test_property_chat_history_round_trip(entries: list[QAEntry]) -> None:
    """
    Property 1: Chat history round-trip.

    For any list of valid QAEntry objects (each with a non-empty user prompt
    ≤ 2000 chars, a non-empty AI response, and a valid ISO 8601 timestamp),
    serializing to S3 JSON format and then deserializing SHALL produce an
    equivalent list of entries.

    **Validates: Requirements 1.2, 1.8**
    """
    # Set up mocked S3
    os.environ["S3_BUCKET"] = BUCKET_NAME
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET_NAME)

    user_id = "property-test-user"

    # Serialize (save) to S3
    save_history(user_id, entries)

    # Deserialize (read) from S3
    result = get_history(user_id)

    # Assert equivalence
    assert len(result) == len(entries)
    for original, restored in zip(entries, result):
        assert restored.user_prompt == original.user_prompt
        assert restored.ai_response == original.ai_response
        assert restored.timestamp == original.timestamp


# ──────────────────────────────────────────────────────────────────────────────
# Feature: ai-coach-context, Property 2: History size bounded at 50
# For any sequence of N appends (N ≥ 1), assert stored history ≤ 50 entries,
# and when N > 50, oldest N-50 entries are discarded.
# Validates: Requirements 1.7, 6.1, 6.2
# ──────────────────────────────────────────────────────────────────────────────


@settings(max_examples=100, deadline=None)
@given(entries=st.lists(_qa_entry_strategy(), min_size=1, max_size=120))
def test_property_history_size_bounded_at_50(entries: list[QAEntry]) -> None:
    """
    Property 2: History size bounded at 50.

    For any sequence of N append operations (N ≥ 1) on a user's chat history,
    the resulting stored history SHALL contain at most 50 entries, and when
    N > 50 the oldest N − 50 entries SHALL have been discarded.

    **Validates: Requirements 1.7, 6.1, 6.2**
    """
    with mock_aws():
        # Set up fresh mocked S3 for each iteration
        os.environ["S3_BUCKET"] = BUCKET_NAME
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=BUCKET_NAME)

        user_id = "property2-user"
        n = len(entries)

        # Perform N sequential appends
        for entry in entries:
            append_entry(user_id, entry)

        # Read back the stored history
        result = get_history(user_id)

        # Assert: stored history never exceeds 50 entries
        assert len(result) <= MAX_ENTRIES

        # Assert: when N > 50, exactly 50 entries are kept (the most recent ones)
        if n > MAX_ENTRIES:
            assert len(result) == MAX_ENTRIES
            # The kept entries should be the last 50 that were appended
            expected_entries = entries[-MAX_ENTRIES:]
            for stored, expected in zip(result, expected_entries):
                assert stored.user_prompt == expected.user_prompt
                assert stored.ai_response == expected.ai_response
                assert stored.timestamp == expected.timestamp
        else:
            # When N <= 50, all entries should be present
            assert len(result) == n
            for stored, expected in zip(result, entries):
                assert stored.user_prompt == expected.user_prompt
                assert stored.ai_response == expected.ai_response
                assert stored.timestamp == expected.timestamp
