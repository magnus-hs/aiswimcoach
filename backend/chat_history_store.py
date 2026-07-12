"""
Chat history storage module for AI Swim Coach.

Persists per-user Q&A conversation history to S3 as a single JSON file
at `chat-history/{user_id}/history.json`. Enforces a 20-entry cap per user,
dropping oldest entries on overflow.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

MAX_ENTRIES = 20


@dataclass
class QAEntry:
    """A single Q&A exchange between the user and the AI coach."""

    user_prompt: str  # max 2000 chars
    ai_response: str
    timestamp: str  # ISO 8601 UTC


def _s3_key(user_id: str) -> str:
    """Build the S3 object key for a user's chat history."""
    return f"chat-history/{user_id}/history.json"


def _get_bucket() -> str:
    """Read the S3 bucket name from environment."""
    return os.environ["S3_BUCKET"]


def _get_s3_client():
    """Create a boto3 S3 client."""
    return boto3.client("s3")


def get_history(user_id: str) -> list[QAEntry]:
    """Read chat history from S3.

    Returns an empty list on missing key or any read failure.
    """
    try:
        s3 = _get_s3_client()
        response = s3.get_object(Bucket=_get_bucket(), Key=_s3_key(user_id))
        body = response["Body"].read().decode("utf-8")
        data = json.loads(body)
        entries = data.get("entries", [])
        return [
            QAEntry(
                user_prompt=e["user_prompt"],
                ai_response=e["ai_response"],
                timestamp=e["timestamp"],
            )
            for e in entries
        ]
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code", "")
        if error_code == "NoSuchKey":
            logger.info("No chat history found for user %s", user_id)
        else:
            logger.error(
                "Failed to read chat history for user %s: %s", user_id, exc
            )
        return []
    except Exception as exc:
        logger.error(
            "Unexpected error reading chat history for user %s: %s",
            user_id,
            exc,
        )
        return []


def save_history(user_id: str, history: list[QAEntry]) -> None:
    """Write the full history list to S3, enforcing a 50-entry cap.

    Drops the oldest entries if the list exceeds MAX_ENTRIES.
    On write failure, logs the error without raising.
    """
    # Enforce 20-entry cap by keeping only the most recent entries
    capped = history[-MAX_ENTRIES:] if len(history) > MAX_ENTRIES else history

    payload = json.dumps(
        {"entries": [asdict(e) for e in capped]},
        ensure_ascii=False,
    )

    try:
        s3 = _get_s3_client()
        s3.put_object(
            Bucket=_get_bucket(),
            Key=_s3_key(user_id),
            Body=payload.encode("utf-8"),
            ContentType="application/json",
        )
    except Exception as exc:
        logger.error(
            "Failed to save chat history for user %s: %s", user_id, exc
        )


def append_entry(user_id: str, entry: QAEntry) -> None:
    """Append a new Q&A entry to the user's history (read-modify-write).

    Reads the current history, appends the new entry, enforces the 50-entry
    cap, and persists the result. Failures are logged but not raised.
    """
    history = get_history(user_id)
    history.append(entry)
    save_history(user_id, history)
