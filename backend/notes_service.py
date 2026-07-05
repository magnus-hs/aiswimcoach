"""
Training notes service for AI Swim Coach.

Manages personal training notes (create/list/delete) stored in the
`ai-swim-coach-notes` DynamoDB table.

Users record short observations (injuries, group changes, illness) that the
AI coach reads when generating responses to explain anomalies.

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class NotFoundError(Exception):
    """Raised when a note is not found or does not belong to the requesting user."""

    pass


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class TrainingNote:
    """A single user training note."""

    user_id: str
    note_id: str  # UUID v4
    text: str  # 1–500 chars (trimmed)
    timestamp: str  # ISO 8601 UTC
    session_id: str | None = None  # Optional: links note to a specific swim session


# ---------------------------------------------------------------------------
# DynamoDB access (lazy-initialized, matches friends_service.py pattern)
# ---------------------------------------------------------------------------

_dynamodb_resource = None


def _get_dynamodb() -> "boto3.resources.base.ServiceResource":
    """Return the (cached) DynamoDB resource, creating it if necessary."""
    global _dynamodb_resource  # noqa: PLW0603
    if _dynamodb_resource is None:
        _dynamodb_resource = boto3.resource("dynamodb", region_name="us-east-1")
    return _dynamodb_resource


def _get_notes_table():
    """Get the notes DynamoDB table."""
    table_name = os.environ.get("NOTES_TABLE", "ai-swim-coach-notes")
    return _get_dynamodb().Table(table_name)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_note(user_id: str, text: str, session_id: str | None = None) -> TrainingNote:
    """Create a new training note for a user.

    Validates the text (1-500 chars after trimming), generates a UUID v4 and
    ISO 8601 UTC timestamp, persists to DynamoDB, and returns the note.

    Args:
        user_id: The authenticated user's ID.
        text: The note text (will be trimmed).
        session_id: Optional session ID to associate the note with a specific swim.

    Returns:
        The created TrainingNote.

    Raises:
        ValueError: If text is empty, whitespace-only, or exceeds 500 chars
                    after trimming.
    """
    trimmed = text.strip()

    if len(trimmed) < 1:
        raise ValueError("Note text must not be empty")
    if len(trimmed) > 500:
        raise ValueError("Note text must not exceed 500 characters")

    note_id = str(uuid.uuid4())
    timestamp = datetime.now(tz=timezone.utc).isoformat()

    note = TrainingNote(
        user_id=user_id,
        note_id=note_id,
        text=trimmed,
        timestamp=timestamp,
        session_id=session_id,
    )

    item: dict = {
        "user_id": note.user_id,
        "note_id": note.note_id,
        "text": note.text,
        "timestamp": note.timestamp,
    }
    if session_id:
        item["session_id"] = session_id

    table = _get_notes_table()
    table.put_item(Item=item)

    return note


def get_notes(user_id: str, session_id: str | None = None, limit: int = 200) -> list[TrainingNote]:
    """Retrieve training notes for a user, ordered by timestamp descending.

    Queries all notes for the user from DynamoDB and sorts by timestamp
    descending in Python (since the sort key is note_id, not timestamp).

    Args:
        user_id: The user whose notes to retrieve.
        session_id: If provided, return only notes with this session_id.
                    If None, return only notes without a session_id (global notes).
        limit: Maximum number of notes to return (default 200).

    Returns:
        List of TrainingNote objects, ordered by timestamp descending,
        capped at limit.
    """
    table = _get_notes_table()

    response = table.query(
        KeyConditionExpression=Key("user_id").eq(user_id),
    )

    items = response.get("Items", [])

    # Handle pagination if there are more items
    while "LastEvaluatedKey" in response:
        response = table.query(
            KeyConditionExpression=Key("user_id").eq(user_id),
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response.get("Items", []))

    # Filter by session_id
    if session_id is not None:
        items = [item for item in items if item.get("session_id") == session_id]
    else:
        items = [item for item in items if not item.get("session_id")]

    # Sort by timestamp descending in Python
    items.sort(key=lambda item: item.get("timestamp", ""), reverse=True)

    # Cap at limit
    items = items[:limit]

    return [
        TrainingNote(
            user_id=item["user_id"],
            note_id=item["note_id"],
            text=item["text"],
            timestamp=item["timestamp"],
            session_id=item.get("session_id"),
        )
        for item in items
    ]


def delete_note(user_id: str, note_id: str) -> bool:
    """Delete a note if it belongs to the specified user.

    First verifies the note exists and belongs to the user via GetItem,
    then deletes it.

    Args:
        user_id: The authenticated user's ID.
        note_id: The UUID of the note to delete.

    Returns:
        True on successful deletion.

    Raises:
        NotFoundError: If the note does not exist or belongs to another user.
    """
    table = _get_notes_table()

    # Check note exists and belongs to user
    try:
        response = table.get_item(
            Key={"user_id": user_id, "note_id": note_id}
        )
    except ClientError:
        raise NotFoundError("Note not found")

    if "Item" not in response:
        raise NotFoundError("Note not found")

    # Delete the note
    table.delete_item(
        Key={"user_id": user_id, "note_id": note_id}
    )

    return True
