"""Property-based tests for notes_service.py."""
from __future__ import annotations

import os
import sys

import boto3
import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
from moto import mock_aws

# Ensure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import notes_service  # noqa: E402


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TABLE_NAME = "ai-swim-coach-notes"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_notes_table():
    """Create the mocked DynamoDB notes table (idempotent)."""
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    try:
        dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "note_id", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "note_id", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
    except dynamodb.meta.client.exceptions.ResourceInUseException:
        pass  # Table already exists in this mock context


# ---------------------------------------------------------------------------
# Feature: ai-coach-context, Property 6: Note text validation
# ---------------------------------------------------------------------------


@mock_aws
@settings(max_examples=100, deadline=None)
@given(text=st.text(min_size=0, max_size=600))
def test_property_note_text_accepted_iff_valid_length(text: str) -> None:
    """
    Property 6: Note text validation.

    For any string input, the notes validation function SHALL accept the input
    if and only if the trimmed string length is between 1 and 500 characters
    inclusive.

    **Validates: Requirements 3.2, 3.3**
    """
    # Set up mocked DynamoDB
    os.environ["NOTES_TABLE"] = TABLE_NAME
    notes_service._dynamodb_resource = None
    _create_notes_table()

    trimmed = text.strip()
    trimmed_len = len(trimmed)

    if 1 <= trimmed_len <= 500:
        # Should succeed — note is accepted
        note = notes_service.create_note("test-user", text)
        assert note.text == trimmed
        assert note.user_id == "test-user"
        assert len(note.note_id) > 0
        assert len(note.timestamp) > 0
    else:
        # Should raise ValueError — note is rejected
        with pytest.raises(ValueError):
            notes_service.create_note("test-user", text)


# ---------------------------------------------------------------------------
# Feature: ai-coach-context, Property 8: Notes retrieval ordering and bound
# For any set of notes for a user, assert response ordered by timestamp
# descending and contains ≤ 200 entries.
# Validates: Requirements 3.4
# ---------------------------------------------------------------------------


@mock_aws
@settings(max_examples=100, deadline=None)
@given(
    num_notes=st.integers(min_value=0, max_value=250),
)
def test_property_notes_retrieval_ordering_and_bound(num_notes: int) -> None:
    """
    Property 8: Notes retrieval ordering and bound.

    For any set of notes stored for a user, the get_notes response SHALL
    return notes ordered by timestamp descending, containing at most 200
    entries.

    **Validates: Requirements 3.4**
    """
    import uuid
    from datetime import datetime, timezone, timedelta

    # Set up mocked DynamoDB
    os.environ["NOTES_TABLE"] = TABLE_NAME
    notes_service._dynamodb_resource = None
    _create_notes_table()

    user_id = f"property8-user-{uuid.uuid4()}"
    table = boto3.resource("dynamodb", region_name="us-east-1").Table(TABLE_NAME)

    # Insert notes with distinct timestamps
    base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)

    for i in range(num_notes):
        note_id = str(uuid.uuid4())
        ts = (base_time + timedelta(seconds=i)).isoformat()
        table.put_item(
            Item={
                "user_id": user_id,
                "note_id": note_id,
                "text": f"Note {i}",
                "timestamp": ts,
            }
        )

    # Retrieve notes
    result = notes_service.get_notes(user_id)

    # Assert: at most 200 entries
    assert len(result) <= 200

    # Assert: correct count (min of inserted notes and 200)
    expected_count = min(num_notes, 200)
    assert len(result) == expected_count

    # Assert: ordered by timestamp descending
    if len(result) > 1:
        for i in range(len(result) - 1):
            assert result[i].timestamp >= result[i + 1].timestamp, (
                f"Notes not in descending order at index {i}: "
                f"{result[i].timestamp} should be >= {result[i + 1].timestamp}"
            )


# ---------------------------------------------------------------------------
# Feature: ai-coach-context, Property 7: Note deletion ownership
# For any note belonging to user A and delete request from user B,
# assert success iff A == B.
# Validates: Requirements 3.5, 3.6
# ---------------------------------------------------------------------------


def _user_id_strategy() -> st.SearchStrategy[str]:
    """Generate valid user ID strings (non-empty, alphanumeric with - and _)."""
    return st.from_regex(r"[a-zA-Z0-9_\-]{1,20}", fullmatch=True)


def _note_text_strategy() -> st.SearchStrategy[str]:
    """Generate valid note text (1-100 chars, non-whitespace-only)."""
    return st.from_regex(r"[a-zA-Z0-9 ]{1,100}", fullmatch=True).filter(
        lambda t: len(t.strip()) >= 1
    )


@mock_aws
@settings(max_examples=100, deadline=None)
@given(
    owner=_user_id_strategy(),
    requester=_user_id_strategy(),
    note_text=_note_text_strategy(),
)
def test_property_note_deletion_ownership(owner: str, requester: str, note_text: str) -> None:
    """
    Property 7: Note deletion ownership.

    For any note belonging to user A (owner) and any delete request from
    user B (requester), the deletion SHALL succeed if and only if A equals B.

    **Validates: Requirements 3.5, 3.6**
    """
    # Set up mocked DynamoDB
    os.environ["NOTES_TABLE"] = TABLE_NAME
    notes_service._dynamodb_resource = None
    _create_notes_table()

    # Create a note owned by 'owner'
    note = notes_service.create_note(owner, note_text)

    if owner == requester:
        # Same user: deletion should succeed
        result = notes_service.delete_note(requester, note.note_id)
        assert result is True
    else:
        # Different user: deletion should raise NotFoundError
        with pytest.raises(notes_service.NotFoundError):
            notes_service.delete_note(requester, note.note_id)
