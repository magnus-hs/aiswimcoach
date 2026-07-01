"""
Social interactions service for AI Swim Coach.

Manages comments and kudos on swim sessions. Authorized users (session owners
and mutual friends with shared visibility) can add/delete comments and
toggle kudos.

Data is stored as list attributes (`comments`, `kudos`) directly on the session
item in the `ai-swim-coach-sessions` DynamoDB table.

Requirements: 1.2, 1.4, 2.2, 2.4, 3.1, 4.3, 4.5, 5.2, 5.5, 5.7, 6.1, 6.4, 9.1, 9.2, 9.3
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

import friends_service


# Module-level placeholders; lazily initialized on first call
_dynamodb_resource = None


def _get_dynamodb() -> "boto3.resources.base.ServiceResource":
    """Return the (cached) DynamoDB resource, creating it if necessary."""
    global _dynamodb_resource  # noqa: PLW0603
    if _dynamodb_resource is None:
        _dynamodb_resource = boto3.resource("dynamodb", region_name="us-east-1")
    return _dynamodb_resource


def _get_sessions_table():
    """Get the sessions DynamoDB table."""
    table_name = os.environ.get("SESSIONS_TABLE", "ai-swim-coach-sessions")
    return _get_dynamodb().Table(table_name)


def _get_profiles_table():
    """Get the user profiles DynamoDB table."""
    table_name = os.environ.get("PROFILES_TABLE", "ai-swim-coach-user-profiles")
    return _get_dynamodb().Table(table_name)


def _now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(tz=timezone.utc).isoformat()


def _push_notification(target_user_id: str, notif: dict) -> None:
    """Append a notification to the target user's profile (max 50 kept)."""
    try:
        table = _get_profiles_table()
        table.update_item(
            Key={"user_id": target_user_id},
            UpdateExpression="SET notifications = list_append(if_not_exists(notifications, :empty), :n)",
            ExpressionAttributeValues={":empty": [], ":n": [notif]},
        )
    except Exception:
        pass  # Non-critical — notification delivery is best-effort


def _authorize_interaction(session_id: str, current_user_id: str) -> tuple[dict, bool]:
    """Verify the user is authorized to interact with the session.

    Authorization rules:
    - Session owner always has access (is_owner=True)
    - Mutual friends have access if the session owner has activity_visibility="shared"

    Args:
        session_id: The target session UUID
        current_user_id: The user attempting to interact

    Returns:
        Tuple of (session_item, is_owner)

    Raises:
        PermissionError: If user is not authorized
        ValueError: If session not found
    """
    table = _get_sessions_table()

    # Load session via session_id-index GSI
    response = table.query(
        IndexName="session_id-index",
        KeyConditionExpression=Key("session_id").eq(session_id),
    )

    items = response.get("Items", [])
    if not items:
        raise ValueError(f"Session not found: {session_id}")

    session_item = items[0]
    session_owner_id = session_item["user_id"]

    # Check if current user is the session owner
    if current_user_id == session_owner_id:
        return (session_item, True)

    # Check if current user is an authorized friend
    # 1. Must be a mutual friend of the session owner
    friends_list = friends_service.get_friends(session_owner_id)
    friend_ids = [f["user_id"] for f in friends_list]

    if current_user_id not in friend_ids:
        raise PermissionError("You do not have permission to interact with this session")

    # 2. Session owner must have activity_visibility set to "shared"
    if not friends_service.get_activity_visibility(session_owner_id):
        raise PermissionError("You do not have permission to interact with this session")

    return (session_item, False)


def get_interactions(session_id: str, current_user_id: str) -> dict:
    """Retrieve comments and kudos for a session.

    Args:
        session_id: Target session UUID
        current_user_id: The requesting user's ID

    Returns:
        {
            "comments": [...] sorted ascending by created_at,
            "kudos_count": int,
            "user_has_kudos": bool
        }

    Raises:
        PermissionError: User not authorized
        ValueError: Session not found
    """
    session_item, _is_owner = _authorize_interaction(session_id, current_user_id)

    comments = session_item.get("comments", [])
    kudos = session_item.get("kudos", [])

    # Sort comments by created_at ascending
    sorted_comments = sorted(comments, key=lambda c: c.get("created_at", ""))

    # Determine if current user has given kudos
    user_has_kudos = any(k.get("user_id") == current_user_id for k in kudos)

    return {
        "comments": sorted_comments,
        "kudos_count": len(kudos),
        "user_has_kudos": user_has_kudos,
    }


def add_comment(session_id: str, user_id: str, text: str) -> dict:
    """Add a comment to a session.

    Args:
        session_id: Target session UUID
        user_id: Author's user_id (from auth_context)
        text: Comment text (1-500 characters)

    Returns:
        The new comment dict with comment_id, user_id, display_name, text, created_at

    Raises:
        ValueError: Empty or >500 char text
        PermissionError: User is not owner or authorized friend
    """
    # Validate text
    stripped_text = text.strip() if text else ""
    if not stripped_text:
        raise ValueError("Comment text must be 1-500 characters")
    if len(stripped_text) > 500:
        raise ValueError("Comment text must be 1-500 characters")

    # Authorize
    _authorize_interaction(session_id, user_id)

    # Build comment record
    comment_id = str(uuid.uuid4())
    created_at = _now_iso()
    display_name = friends_service._get_display_name(user_id)

    new_comment = {
        "comment_id": comment_id,
        "user_id": user_id,
        "display_name": display_name,
        "text": stripped_text,
        "created_at": created_at,
    }

    # Append to session's comments list using DynamoDB UpdateItem
    table = _get_sessions_table()

    # We need the primary key (user_id + session_date) for the update
    # Re-query to get the full key
    response = table.query(
        IndexName="session_id-index",
        KeyConditionExpression=Key("session_id").eq(session_id),
    )
    items = response.get("Items", [])
    if not items:
        raise ValueError(f"Session not found: {session_id}")

    session_item = items[0]
    pk_user_id = session_item["user_id"]
    pk_session_date = session_item["session_date"]

    table.update_item(
        Key={"user_id": pk_user_id, "session_date": pk_session_date},
        UpdateExpression="SET comments = list_append(if_not_exists(comments, :empty), :new_comment)",
        ExpressionAttributeValues={
            ":empty": [],
            ":new_comment": [new_comment],
        },
    )

    # Notify session owner (if commenter is not the owner)
    if user_id != pk_user_id:
        _push_notification(pk_user_id, {
            "type": "comment",
            "from_display_name": display_name,
            "session_id": session_id,
            "text": stripped_text[:80],
            "created_at": created_at,
        })

    return new_comment


def delete_comment(session_id: str, comment_id: str, user_id: str) -> None:
    """Delete a comment by ID.

    Args:
        session_id: Target session UUID
        comment_id: The comment to delete
        user_id: The user requesting deletion

    Raises:
        PermissionError: user_id does not match comment author
        ValueError: Comment not found
    """
    table = _get_sessions_table()

    # Load session
    response = table.query(
        IndexName="session_id-index",
        KeyConditionExpression=Key("session_id").eq(session_id),
    )
    items = response.get("Items", [])
    if not items:
        raise ValueError(f"Session not found: {session_id}")

    session_item = items[0]
    comments = session_item.get("comments", [])

    # Find the comment by comment_id
    target_index = None
    target_comment = None
    for i, comment in enumerate(comments):
        if comment.get("comment_id") == comment_id:
            target_index = i
            target_comment = comment
            break

    if target_index is None:
        raise ValueError("Comment not found")

    # Verify the requesting user is the comment author
    if target_comment.get("user_id") != user_id:
        raise PermissionError("You can only delete your own comments")

    # Remove the comment using DynamoDB REMOVE expression
    pk_user_id = session_item["user_id"]
    pk_session_date = session_item["session_date"]

    table.update_item(
        Key={"user_id": pk_user_id, "session_date": pk_session_date},
        UpdateExpression=f"REMOVE comments[{target_index}]",
    )


def toggle_kudos(session_id: str, user_id: str) -> dict:
    """Add or remove kudos for a user on a session.

    Args:
        session_id: Target session UUID
        user_id: The user toggling kudos

    Returns:
        {"action": "added"|"removed", "kudos_count": int}

    Raises:
        PermissionError: User is session owner, or not an authorized friend
    """
    session_item, is_owner = _authorize_interaction(session_id, user_id)

    # Session owner cannot give kudos to their own session
    if is_owner:
        raise PermissionError("Cannot give kudos to your own session")

    kudos = session_item.get("kudos", [])
    pk_user_id = session_item["user_id"]
    pk_session_date = session_item["session_date"]

    table = _get_sessions_table()

    # Check if user already has kudos on this session
    existing_index = None
    for i, k in enumerate(kudos):
        if k.get("user_id") == user_id:
            existing_index = i
            break

    if existing_index is not None:
        # Remove kudos
        table.update_item(
            Key={"user_id": pk_user_id, "session_date": pk_session_date},
            UpdateExpression=f"REMOVE kudos[{existing_index}]",
        )
        new_count = len(kudos) - 1
        return {"action": "removed", "kudos_count": new_count}
    else:
        # Add kudos
        new_kudos = {
            "user_id": user_id,
            "created_at": _now_iso(),
        }
        table.update_item(
            Key={"user_id": pk_user_id, "session_date": pk_session_date},
            UpdateExpression="SET kudos = list_append(if_not_exists(kudos, :empty), :new_kudos)",
            ExpressionAttributeValues={
                ":empty": [],
                ":new_kudos": [new_kudos],
            },
        )
        new_count = len(kudos) + 1

        # Notify session owner
        giver_name = friends_service._get_display_name(user_id)
        _push_notification(pk_user_id, {
            "type": "kudos",
            "from_display_name": giver_name,
            "session_id": session_id,
            "created_at": new_kudos["created_at"],
        })

        return {"action": "added", "kudos_count": new_count}


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


def get_notifications(user_id: str) -> list[dict]:
    """Get all notifications for a user (most recent first, max 50)."""
    table = _get_profiles_table()
    try:
        response = table.get_item(
            Key={"user_id": user_id},
            ProjectionExpression="notifications",
        )
        items = response.get("Item", {}).get("notifications", [])
        # Return most recent first, capped at 50
        return list(reversed(items[-50:]))
    except ClientError:
        return []


def clear_notifications(user_id: str) -> None:
    """Clear all notifications for a user."""
    table = _get_profiles_table()
    try:
        table.update_item(
            Key={"user_id": user_id},
            UpdateExpression="SET notifications = :empty",
            ExpressionAttributeValues={":empty": []},
        )
    except ClientError:
        pass
