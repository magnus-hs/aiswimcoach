"""
Account service for AI Swim Coach — GDPR data export and account deletion.

Provides two capabilities:

* ``export_user_data`` — gather ALL of a user's data across DynamoDB tables and
  S3 buckets into a single JSON-serializable dict (excluding secrets like the
  password hash).
* ``delete_user_data`` — permanently and irreversibly delete ALL of a user's
  data across every backing store, returning a summary of what was removed.

Both functions read the same environment variables used elsewhere in the
codebase so they operate against the correct tables/buckets in every stage.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key


# ---------------------------------------------------------------------------
# Lazy client/resource helpers
# ---------------------------------------------------------------------------

_dynamodb_resource = None
_s3_client = None


def _get_dynamodb():
    """Return the (cached) DynamoDB resource, creating it if necessary."""
    global _dynamodb_resource  # noqa: PLW0603
    if _dynamodb_resource is None:
        _dynamodb_resource = boto3.resource("dynamodb", region_name="us-east-1")
    return _dynamodb_resource


def _get_s3_client():
    """Return the (cached) S3 client, creating it if necessary."""
    global _s3_client  # noqa: PLW0603
    if _s3_client is None:
        _s3_client = boto3.client("s3")
    return _s3_client


def _users_table():
    return _get_dynamodb().Table(os.environ.get("USERS_TABLE", "ai-swim-coach-users"))


def _profiles_table():
    return _get_dynamodb().Table(
        os.environ.get("PROFILES_TABLE", "ai-swim-coach-user-profiles")
    )


def _sessions_table():
    return _get_dynamodb().Table(os.environ.get("SESSIONS_TABLE", "ai-swim-coach-sessions"))


def _notes_table():
    return _get_dynamodb().Table(os.environ.get("NOTES_TABLE", "ai-swim-coach-notes"))


def _friends_table():
    return _get_dynamodb().Table(os.environ.get("FRIENDS_TABLE", "ai-swim-coach-friends"))


def _s3_bucket() -> str:
    return os.environ["S3_BUCKET"]


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# JSON serialization helpers
# ---------------------------------------------------------------------------


def _decimal_to_number(value: Decimal) -> Any:
    """Convert a Decimal to an int when it has no fractional part, else float."""
    if value == value.to_integral_value():
        return int(value)
    return float(value)


def _make_serializable(obj: Any) -> Any:
    """Recursively convert DynamoDB/Decimal structures into JSON-native types."""
    if isinstance(obj, Decimal):
        return _decimal_to_number(obj)
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_serializable(v) for v in obj]
    if isinstance(obj, set):
        return [_make_serializable(v) for v in obj]
    return obj


# Prefixes on session_date that represent internal marker rows rather than
# real swim sessions (dedup markers, single-plan rows, multi-week plan rows).
_MARKER_PREFIXES = ("DEDUP#", "PLAN#", "MPLAN#")


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def export_user_data(user_id: str) -> dict:
    """Gather ALL of a user's data into a JSON-serializable dict.

    Args:
        user_id: The authenticated user's ID.

    Returns:
        A dict with keys: ``exported_at``, ``account``, ``profile``,
        ``sessions``, ``notes``, ``chat_history`` and ``friends``. All values
        are JSON-serializable (Decimals converted to int/float).
    """
    account = _export_account(user_id)
    profile = _export_profile(user_id)
    sessions = _export_sessions(user_id)
    notes = _export_notes(user_id)
    chat_history = _export_chat_history(user_id)
    friends = _export_friends(user_id)

    return {
        "exported_at": _now_iso(),
        "account": account,
        "profile": profile,
        "sessions": sessions,
        "notes": notes,
        "chat_history": chat_history,
        "friends": friends,
    }


def _export_account(user_id: str) -> dict:
    """Fetch the user's account record, excluding the password hash."""
    response = _users_table().get_item(Key={"user_id": user_id})
    item = response.get("Item") or {}
    item.pop("password_hash", None)
    return _make_serializable(item)


def _export_profile(user_id: str) -> dict:
    """Fetch the user's full profile record."""
    response = _profiles_table().get_item(Key={"user_id": user_id})
    item = response.get("Item") or {}
    return _make_serializable(item)


def _export_sessions(user_id: str) -> list:
    """Fetch all real swim sessions (skipping internal marker rows)."""
    table = _sessions_table()
    sessions: list = []

    response = table.query(KeyConditionExpression=Key("user_id").eq(user_id))
    items = response.get("Items", [])
    while "LastEvaluatedKey" in response:
        response = table.query(
            KeyConditionExpression=Key("user_id").eq(user_id),
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response.get("Items", []))

    for item in items:
        session_date = str(item.get("session_date", ""))
        if session_date.startswith(_MARKER_PREFIXES):
            continue
        sessions.append(_make_serializable(item))

    return sessions


def _export_notes(user_id: str) -> list:
    """Fetch all of the user's training notes."""
    table = _notes_table()

    response = table.query(KeyConditionExpression=Key("user_id").eq(user_id))
    items = response.get("Items", [])
    while "LastEvaluatedKey" in response:
        response = table.query(
            KeyConditionExpression=Key("user_id").eq(user_id),
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response.get("Items", []))

    return [_make_serializable(item) for item in items]


def _export_chat_history(user_id: str) -> list:
    """Read and parse the user's chat history from S3, or [] if absent."""
    key = f"chat-history/{user_id}/history.json"
    try:
        response = _get_s3_client().get_object(Bucket=_s3_bucket(), Key=key)
    except Exception:
        return []

    try:
        body = response["Body"].read().decode("utf-8")
        data = json.loads(body)
    except Exception:
        return []

    return _make_serializable(data) if isinstance(data, list) else _make_serializable(data)


def _export_friends(user_id: str) -> list:
    """Fetch all friendship and request items belonging to the user."""
    table = _friends_table()

    response = table.query(KeyConditionExpression=Key("pk").eq(f"USER#{user_id}"))
    items = response.get("Items", [])
    while "LastEvaluatedKey" in response:
        response = table.query(
            KeyConditionExpression=Key("pk").eq(f"USER#{user_id}"),
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response.get("Items", []))

    return [_make_serializable(item) for item in items]


# ---------------------------------------------------------------------------
# Deletion
# ---------------------------------------------------------------------------


def delete_user_data(user_id: str) -> dict:
    """Permanently delete ALL of a user's data across every backing store.

    Each step is wrapped in its own try/except so a single failure does not
    abort the remaining cleanup. Errors are collected and returned alongside a
    per-category count of deleted items.

    Args:
        user_id: The authenticated user's ID.

    Returns:
        A dict of the form ``{"deleted": {...counts...}, "errors": [...]}``.
    """
    counts: dict[str, int] = {
        "sessions": 0,
        "session_s3_objects": 0,
        "notes": 0,
        "friends": 0,
        "s3_objects": 0,
        "profile_pictures": 0,
        "profile": 0,
        "account": 0,
    }
    errors: list[str] = []

    _delete_sessions(user_id, counts, errors)
    _delete_notes(user_id, counts, errors)
    _delete_friends(user_id, counts, errors)
    _delete_s3_prefixes(user_id, counts, errors)
    _delete_profile_pictures(user_id, counts, errors)
    _delete_profile(user_id, counts, errors)
    _delete_account(user_id, counts, errors)

    return {"deleted": counts, "errors": errors}


def _delete_sessions(user_id: str, counts: dict, errors: list) -> None:
    """Delete every session item (including markers) and any linked S3 objects."""
    try:
        table = _sessions_table()

        response = table.query(KeyConditionExpression=Key("user_id").eq(user_id))
        items = response.get("Items", [])
        while "LastEvaluatedKey" in response:
            response = table.query(
                KeyConditionExpression=Key("user_id").eq(user_id),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response.get("Items", []))

        # Delete linked S3 objects (raw FIT files) best-effort.
        s3 = _get_s3_client()
        bucket = _s3_bucket()
        for item in items:
            s3_key = item.get("s3_key")
            if s3_key:
                try:
                    s3.delete_object(Bucket=bucket, Key=s3_key)
                    counts["session_s3_objects"] += 1
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"sessions: failed to delete S3 object {s3_key}: {exc}")

        with table.batch_writer() as batch:
            for item in items:
                batch.delete_item(
                    Key={
                        "user_id": item["user_id"],
                        "session_date": item["session_date"],
                    }
                )
                counts["sessions"] += 1
    except Exception as exc:  # noqa: BLE001
        errors.append(f"sessions: {exc}")


def _delete_notes(user_id: str, counts: dict, errors: list) -> None:
    """Delete every note belonging to the user."""
    try:
        table = _notes_table()

        response = table.query(KeyConditionExpression=Key("user_id").eq(user_id))
        items = response.get("Items", [])
        while "LastEvaluatedKey" in response:
            response = table.query(
                KeyConditionExpression=Key("user_id").eq(user_id),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response.get("Items", []))

        with table.batch_writer() as batch:
            for item in items:
                batch.delete_item(
                    Key={"user_id": item["user_id"], "note_id": item["note_id"]}
                )
                counts["notes"] += 1
    except Exception as exc:  # noqa: BLE001
        errors.append(f"notes: {exc}")


def _delete_friends(user_id: str, counts: dict, errors: list) -> None:
    """Delete the user's own friend/request items and all reciprocal items."""
    try:
        table = _friends_table()

        # Items where this user is the owner (pk = USER#{user_id}).
        response = table.query(KeyConditionExpression=Key("pk").eq(f"USER#{user_id}"))
        items = response.get("Items", [])
        while "LastEvaluatedKey" in response:
            response = table.query(
                KeyConditionExpression=Key("pk").eq(f"USER#{user_id}"),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response.get("Items", []))

        # Reciprocal items where this user is the target, found via the GSI.
        for sk_value in (f"FRIEND#{user_id}", f"REQ#{user_id}"):
            try:
                gsi_response = table.query(
                    IndexName="sk-pk-index",
                    KeyConditionExpression=Key("sk").eq(sk_value),
                )
                items.extend(gsi_response.get("Items", []))
                while "LastEvaluatedKey" in gsi_response:
                    gsi_response = table.query(
                        IndexName="sk-pk-index",
                        KeyConditionExpression=Key("sk").eq(sk_value),
                        ExclusiveStartKey=gsi_response["LastEvaluatedKey"],
                    )
                    items.extend(gsi_response.get("Items", []))
            except Exception as exc:  # noqa: BLE001
                errors.append(f"friends: GSI query for {sk_value} failed: {exc}")

        with table.batch_writer() as batch:
            for item in items:
                batch.delete_item(Key={"pk": item["pk"], "sk": item["sk"]})
                counts["friends"] += 1
    except Exception as exc:  # noqa: BLE001
        errors.append(f"friends: {exc}")


def _delete_s3_prefixes(user_id: str, counts: dict, errors: list) -> None:
    """Delete all objects under the user's chat-history and statistics prefixes."""
    bucket = _s3_bucket()
    for prefix in (f"chat-history/{user_id}/", f"statistics/{user_id}/"):
        try:
            counts["s3_objects"] += _delete_objects_by_prefix(bucket, prefix)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"s3 prefix {prefix}: {exc}")


def _delete_profile_pictures(user_id: str, counts: dict, errors: list) -> None:
    """Delete profile picture objects prefixed with the user id."""
    try:
        bucket = os.environ["PROFILE_PICTURES_BUCKET"]
    except KeyError as exc:
        errors.append(f"profile_pictures: missing PROFILE_PICTURES_BUCKET env var: {exc}")
        return

    try:
        counts["profile_pictures"] += _delete_objects_by_prefix(bucket, f"{user_id}_")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"profile_pictures: {exc}")


def _delete_objects_by_prefix(bucket: str, prefix: str) -> int:
    """List and delete every object under ``prefix`` in ``bucket``.

    Returns the number of objects deleted.
    """
    s3 = _get_s3_client()
    deleted = 0
    continuation_token = None

    while True:
        kwargs = {"Bucket": bucket, "Prefix": prefix}
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token
        response = s3.list_objects_v2(**kwargs)

        objects = [{"Key": obj["Key"]} for obj in response.get("Contents", [])]
        if objects:
            # delete_objects handles up to 1000 keys per call; list_objects_v2
            # also returns at most 1000 keys per page, so a single call suffices.
            s3.delete_objects(Bucket=bucket, Delete={"Objects": objects})
            deleted += len(objects)

        if response.get("IsTruncated"):
            continuation_token = response.get("NextContinuationToken")
        else:
            break

    return deleted


def _delete_profile(user_id: str, counts: dict, errors: list) -> None:
    """Delete the user's profile record."""
    try:
        _profiles_table().delete_item(Key={"user_id": user_id})
        counts["profile"] += 1
    except Exception as exc:  # noqa: BLE001
        errors.append(f"profile: {exc}")


def _delete_account(user_id: str, counts: dict, errors: list) -> None:
    """Delete the user's account record."""
    try:
        _users_table().delete_item(Key={"user_id": user_id})
        counts["account"] += 1
    except Exception as exc:  # noqa: BLE001
        errors.append(f"account: {exc}")
