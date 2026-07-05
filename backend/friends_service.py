"""
Friends network service for AI Swim Coach.

Manages friend relationships (send/accept/decline/remove), user search,
activity visibility preferences, and friends' activity aggregation.

Data is stored in the `ai-swim-coach-friends` DynamoDB table using an
adjacency list pattern with two reciprocal items per friendship and
single items for pending requests.

Requirements: 2.2, 2.3, 2.4, 3.2, 3.5, 4.2, 4.4, 4.5, 5.4, 6.2, 6.3, 6.4, 8.1, 8.2, 8.3
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError


# Module-level placeholders; lazily initialized on first call
_dynamodb_resource = None


def _get_dynamodb() -> "boto3.resources.base.ServiceResource":
    """Return the (cached) DynamoDB resource, creating it if necessary."""
    global _dynamodb_resource  # noqa: PLW0603
    if _dynamodb_resource is None:
        _dynamodb_resource = boto3.resource("dynamodb", region_name="us-east-1")
    return _dynamodb_resource


def _get_friends_table():
    """Get the friends DynamoDB table."""
    table_name = os.environ.get("FRIENDS_TABLE", "ai-swim-coach-friends")
    return _get_dynamodb().Table(table_name)


def _get_users_table():
    """Get the users DynamoDB table."""
    table_name = os.environ.get("USERS_TABLE", "ai-swim-coach-users")
    return _get_dynamodb().Table(table_name)


def _get_profiles_table():
    """Get the user profiles DynamoDB table."""
    table_name = os.environ.get("PROFILES_TABLE", "ai-swim-coach-user-profiles")
    return _get_dynamodb().Table(table_name)


def _get_sessions_table():
    """Get the sessions DynamoDB table."""
    table_name = os.environ.get("SESSIONS_TABLE", "ai-swim-coach-sessions")
    return _get_dynamodb().Table(table_name)


def _now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(tz=timezone.utc).isoformat()


def _get_display_name(user_id: str) -> str:
    """Fetch display name from user-profiles table, falling back to email prefix from users table."""
    table = _get_profiles_table()
    try:
        response = table.get_item(
            Key={"user_id": user_id},
            ProjectionExpression="display_name",
        )
        item = response.get("Item", {})
        name = item.get("display_name")
        if name:
            return name
    except ClientError:
        pass

    # Fallback: get email prefix from users table
    users_table = _get_users_table()
    try:
        response = users_table.get_item(
            Key={"user_id": user_id},
            ProjectionExpression="email",
        )
        item = response.get("Item", {})
        email = item.get("email", "")
        if email and "@" in email:
            return email.split("@")[0]
    except ClientError:
        pass

    return "Unknown User"


def _get_profile_picture_url(user_id: str) -> str | None:
    """Fetch profile picture URL from the users table."""
    users_table = _get_users_table()
    try:
        response = users_table.get_item(
            Key={"user_id": user_id},
            ProjectionExpression="profile_picture_url",
        )
        item = response.get("Item", {})
        return item.get("profile_picture_url") or None
    except ClientError:
        return None# ---------------------------------------------------------------------------
# Task 2.1: Core relationship functions
# ---------------------------------------------------------------------------


def send_friend_request(from_user_id: str, to_user_id: str) -> dict:
    """Create a pending friend request from one user to another.

    Validates:
    - No self-requests
    - No duplicate pending request
    - No existing friendship

    Args:
        from_user_id: The user sending the request
        to_user_id: The user receiving the request

    Returns:
        dict with request_id and status

    Raises:
        ValueError: If self-request, duplicate request, or already friends
    """
    if from_user_id == to_user_id:
        raise ValueError("Cannot send friend request to yourself")

    table = _get_friends_table()

    # Check for existing pending request (either direction)
    try:
        response = table.get_item(
            Key={"pk": f"USER#{from_user_id}", "sk": f"REQ#{to_user_id}"}
        )
        if "Item" in response:
            raise ValueError("Friend request already exists")
    except ClientError:
        pass

    # Check reverse direction too
    try:
        response = table.get_item(
            Key={"pk": f"USER#{to_user_id}", "sk": f"REQ#{from_user_id}"}
        )
        if "Item" in response:
            raise ValueError("Friend request already exists")
    except ClientError:
        pass

    # Check if already friends
    try:
        response = table.get_item(
            Key={"pk": f"USER#{from_user_id}", "sk": f"FRIEND#{to_user_id}"}
        )
        if "Item" in response:
            raise ValueError("Already friends with this user")
    except ClientError:
        pass

    # Create the pending request
    request_id = str(uuid.uuid4())
    created_at = _now_iso()

    item = {
        "pk": f"USER#{from_user_id}",
        "sk": f"REQ#{to_user_id}",
        "status": "pending",
        "created_at": created_at,
        "request_id": request_id,
    }

    table.put_item(Item=item)

    return {"request_id": request_id, "status": "pending", "created_at": created_at}


def get_pending_requests(user_id: str) -> list[dict]:
    """Get incoming pending friend requests for a user.

    Queries the sk-pk-index GSI where sk=REQ#{user_id} to find all
    incoming requests. Enriches each result with the sender's display name.

    Args:
        user_id: The user to get pending requests for

    Returns:
        List of dicts with request_id, from_user_id, from_display_name, created_at
    """
    table = _get_friends_table()

    response = table.query(
        IndexName="sk-pk-index",
        KeyConditionExpression=Key("sk").eq(f"REQ#{user_id}"),
    )

    items = response.get("Items", [])
    requests = []

    for item in items:
        if item.get("status") != "pending":
            continue
        # Extract sender user_id from pk (format: USER#{user_id})
        from_user_id = item["pk"].replace("USER#", "")
        display_name = _get_display_name(from_user_id)

        requests.append({
            "request_id": item["request_id"],
            "from_user_id": from_user_id,
            "from_display_name": display_name,
            "created_at": item["created_at"],
        })

    return requests


def accept_friend_request(request_id: str, user_id: str) -> dict:
    """Accept a pending friend request.

    Finds the request by scanning for request_id, verifies it targets user_id,
    creates two FRIEND# items (A→B and B→A), and deletes the REQ# item.

    Args:
        request_id: The UUID of the request to accept
        user_id: The user accepting the request (must be the target)

    Returns:
        dict with status "accepted"

    Raises:
        ValueError: If request not found or not targeting this user
    """
    table = _get_friends_table()

    # Find the request by scanning for request_id
    response = table.scan(
        FilterExpression=Attr("request_id").eq(request_id),
    )

    items = response.get("Items", [])
    if not items:
        raise ValueError("Friend request not found")

    request_item = items[0]

    # Verify this request targets the accepting user
    target_user_id = request_item["sk"].replace("REQ#", "")
    if target_user_id != user_id:
        raise ValueError("Friend request not found")

    from_user_id = request_item["pk"].replace("USER#", "")
    created_at = _now_iso()

    # Create both friendship items
    table.put_item(Item={
        "pk": f"USER#{from_user_id}",
        "sk": f"FRIEND#{user_id}",
        "status": "accepted",
        "created_at": created_at,
    })

    table.put_item(Item={
        "pk": f"USER#{user_id}",
        "sk": f"FRIEND#{from_user_id}",
        "status": "accepted",
        "created_at": created_at,
    })

    # Delete the pending request item
    table.delete_item(
        Key={"pk": request_item["pk"], "sk": request_item["sk"]}
    )

    return {"status": "accepted"}


def decline_friend_request(request_id: str, user_id: str) -> dict:
    """Decline a pending friend request.

    Finds and deletes the pending REQ# item.

    Args:
        request_id: The UUID of the request to decline
        user_id: The user declining the request (must be the target)

    Returns:
        dict with status "declined"

    Raises:
        ValueError: If request not found or not targeting this user
    """
    table = _get_friends_table()

    # Find the request by scanning for request_id
    response = table.scan(
        FilterExpression=Attr("request_id").eq(request_id),
    )

    items = response.get("Items", [])
    if not items:
        raise ValueError("Friend request not found")

    request_item = items[0]

    # Verify this request targets the declining user
    target_user_id = request_item["sk"].replace("REQ#", "")
    if target_user_id != user_id:
        raise ValueError("Friend request not found")

    # Delete the pending request
    table.delete_item(
        Key={"pk": request_item["pk"], "sk": request_item["sk"]}
    )

    return {"status": "declined"}


def get_friends(user_id: str) -> list[dict]:
    """Get all confirmed friends for a user.

    Queries the main table with pk=USER#{user_id} and begins_with(sk, "FRIEND#").
    Enriches each result with the friend's display name, ability level,
    total distance this year, and member-since date.

    Args:
        user_id: The user to get friends for

    Returns:
        List of dicts with user_id, display_name, since, ability_level,
        distance_ytd_meters, member_since
    """
    table = _get_friends_table()

    response = table.query(
        KeyConditionExpression=(
            Key("pk").eq(f"USER#{user_id}")
            & Key("sk").begins_with("FRIEND#")
        ),
    )

    items = response.get("Items", [])
    friends = []

    for item in items:
        friend_user_id = item["sk"].replace("FRIEND#", "")
        display_name = _get_display_name(friend_user_id)

        # Get ability level from profile
        ability_level = ""
        try:
            prof_resp = _get_profiles_table().get_item(
                Key={"user_id": friend_user_id},
                ProjectionExpression="ability_level",
            )
            ability_level = prof_resp.get("Item", {}).get("ability_level", "")
        except ClientError:
            pass

        # Get member_since from users table
        member_since = ""
        try:
            user_resp = _get_users_table().get_item(
                Key={"user_id": friend_user_id},
                ProjectionExpression="created_at",
            )
            member_since = user_resp.get("Item", {}).get("created_at", "")
        except ClientError:
            pass

        # Get total distance this year from sessions
        distance_ytd = 0
        try:
            from datetime import datetime, timezone
            now = datetime.now(tz=timezone.utc)
            year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
            sessions_table = _get_sessions_table()
            sess_resp = sessions_table.query(
                KeyConditionExpression=(
                    Key("user_id").eq(friend_user_id)
                    & Key("session_date").gte(year_start)
                ),
                ProjectionExpression="total_distance_meters, session_date",
            )
            for s in sess_resp.get("Items", []):
                sd = s.get("session_date", "")
                if sd.startswith("PLAN") or sd.startswith("MPLAN"):
                    continue
                dist = s.get("total_distance_meters")
                if dist:
                    distance_ytd += int(dist)
        except (ClientError, Exception):
            pass

        friends.append({
            "user_id": friend_user_id,
            "display_name": display_name,
            "since": item.get("created_at", ""),
            "ability_level": ability_level,
            "distance_ytd_meters": distance_ytd,
            "member_since": member_since,
        })

    return friends


def remove_friend(user_id: str, friend_user_id: str) -> dict:
    """Remove a friend relationship (both directions).

    Deletes both USER#{A}/FRIEND#{B} and USER#{B}/FRIEND#{A} items.

    Args:
        user_id: The user initiating removal
        friend_user_id: The friend to remove

    Returns:
        dict with status "removed"
    """
    table = _get_friends_table()

    # Delete A → B
    table.delete_item(
        Key={"pk": f"USER#{user_id}", "sk": f"FRIEND#{friend_user_id}"}
    )

    # Delete B → A
    table.delete_item(
        Key={"pk": f"USER#{friend_user_id}", "sk": f"FRIEND#{user_id}"}
    )

    return {"status": "removed"}


# ---------------------------------------------------------------------------
# Task 2.2: User search
# ---------------------------------------------------------------------------


def search_users(query: str, current_user_id: str) -> list[dict]:
    """Search users by email prefix or display name.

    Searches the users table email-index with begins_with(email, query.lower())
    AND scans the user-profiles table filtering display_name (case-insensitive
    contains). Excludes the current user. Enriches each result with
    relationship_status.

    Args:
        query: Search string (minimum 2 characters)
        current_user_id: The user performing the search (excluded from results)

    Returns:
        List of dicts with user_id, display_name, email_prefix, relationship_status.
        Max 20 results.

    Raises:
        ValueError: If query is less than 2 characters
    """
    if len(query) < 2:
        raise ValueError("Search query must be at least 2 characters")

    query_lower = query.lower()
    found_users: dict[str, dict] = {}  # user_id -> {user_id, display_name, email_prefix}

    # Search users table by email (scan with contains filter — email-index is a
    # hash-only GSI so begins_with is not supported in a Query on the PK).
    users_table = _get_users_table()
    try:
        response = users_table.scan(
            FilterExpression=Attr("email").contains(query_lower),
        )
        for item in response.get("Items", []):
            uid = item.get("user_id", "")
            if uid and uid != current_user_id:
                email = item.get("email", "")
                email_prefix = email.split("@")[0] if "@" in email else email
                found_users[uid] = {
                    "user_id": uid,
                    "display_name": "",
                    "email_prefix": email_prefix,
                }
    except ClientError:
        pass

    # Scan user-profiles table for display name matches (case-insensitive contains)
    profiles_table = _get_profiles_table()
    try:
        response = profiles_table.scan(
            FilterExpression=Attr("display_name").exists(),
        )
        for item in response.get("Items", []):
            uid = item.get("user_id", "")
            display_name = item.get("display_name", "")
            if uid and uid != current_user_id and display_name:
                if query_lower in display_name.lower():
                    if uid in found_users:
                        found_users[uid]["display_name"] = display_name
                    else:
                        found_users[uid] = {
                            "user_id": uid,
                            "display_name": display_name,
                            "email_prefix": "",
                        }
    except ClientError:
        pass

    # Enrich display names for users found via email but not profiles
    for uid, user_data in found_users.items():
        if not user_data["display_name"]:
            user_data["display_name"] = _get_display_name(uid)

    # Enrich with relationship status
    results = []
    for uid, user_data in found_users.items():
        status = _get_relationship_status(current_user_id, uid)
        results.append({
            "user_id": user_data["user_id"],
            "display_name": user_data["display_name"],
            "email_prefix": user_data["email_prefix"],
            "relationship_status": status,
            "profile_picture_url": _get_profile_picture_url(uid),
        })
        if len(results) >= 20:
            break

    return results


def _get_relationship_status(current_user_id: str, other_user_id: str) -> str:
    """Determine the relationship status between two users.

    Returns one of: 'none', 'pending_sent', 'pending_received', 'friends'
    """
    table = _get_friends_table()

    # Check if friends
    try:
        response = table.get_item(
            Key={"pk": f"USER#{current_user_id}", "sk": f"FRIEND#{other_user_id}"}
        )
        if "Item" in response:
            return "friends"
    except ClientError:
        pass

    # Check if pending request sent
    try:
        response = table.get_item(
            Key={"pk": f"USER#{current_user_id}", "sk": f"REQ#{other_user_id}"}
        )
        if "Item" in response:
            return "pending_sent"
    except ClientError:
        pass

    # Check if pending request received
    try:
        response = table.get_item(
            Key={"pk": f"USER#{other_user_id}", "sk": f"REQ#{current_user_id}"}
        )
        if "Item" in response:
            return "pending_received"
    except ClientError:
        pass

    return "none"


# ---------------------------------------------------------------------------
# Task 2.3: Activity visibility and friends' activities
# ---------------------------------------------------------------------------


def update_activity_visibility(user_id: str, visible: bool) -> dict:
    """Set activity visibility for a user.

    Updates the activity_visibility attribute on the user-profiles table
    to "shared" or "not_shared".

    Args:
        user_id: The user updating their visibility
        visible: True for "shared", False for "not_shared"

    Returns:
        dict with the new visibility setting
    """
    table = _get_profiles_table()
    visibility_value = "shared" if visible else "not_shared"

    table.update_item(
        Key={"user_id": user_id},
        UpdateExpression="SET activity_visibility = :vis",
        ExpressionAttributeValues={":vis": visibility_value},
    )

    return {"activity_visibility": visibility_value}


def get_activity_visibility(user_id: str) -> bool:
    """Get activity visibility setting for a user.

    Reads activity_visibility from the profiles table. Defaults to False
    (not_shared) if not present.

    Args:
        user_id: The user to check visibility for

    Returns:
        True if visibility is "shared", False otherwise
    """
    table = _get_profiles_table()

    try:
        response = table.get_item(
            Key={"user_id": user_id},
            ProjectionExpression="activity_visibility",
        )
        item = response.get("Item", {})
        return item.get("activity_visibility", "not_shared") == "shared"
    except ClientError:
        return False


def get_friends_activities(user_id: str) -> list[dict]:
    """Get swim sessions from friends who share their activities.

    1. Gets the user's friends list
    2. Checks each friend's activity_visibility
    3. Queries sessions for friends who share
    4. Returns aggregated sessions sorted by session_date descending

    Each entry includes: session_id, session_date, total_distance_meters,
    total_time_seconds, stroke_type, average_pace_per_100m, swolf_score,
    friend_display_name, friend_user_id.

    Args:
        user_id: The user requesting friends' activities

    Returns:
        List of session dicts sorted by session_date descending
    """
    # Get user's friends
    friends = get_friends(user_id)
    if not friends:
        return []

    # Filter to friends with activity visibility set to "shared"
    sharing_friends = []
    profiles_table = _get_profiles_table()

    for friend in friends:
        friend_id = friend["user_id"]
        try:
            response = profiles_table.get_item(
                Key={"user_id": friend_id},
                ProjectionExpression="activity_visibility",
            )
            item = response.get("Item", {})
            if item.get("activity_visibility") == "shared":
                sharing_friends.append(friend)
        except ClientError:
            continue

    if not sharing_friends:
        return []

    # Query sessions for each sharing friend
    sessions_table = _get_sessions_table()
    all_sessions = []
    profile_pic_cache: dict[str, str | None] = {}

    for friend in sharing_friends:
        friend_id = friend["user_id"]
        friend_display_name = friend["display_name"]

        # Cache profile picture URL per friend to avoid repeated DynamoDB reads
        if friend_id not in profile_pic_cache:
            profile_pic_cache[friend_id] = _get_profile_picture_url(friend_id)
        profile_picture_url = profile_pic_cache[friend_id]

        try:
            response = sessions_table.query(
                KeyConditionExpression=Key("user_id").eq(friend_id),
                ScanIndexForward=False,  # Most recent first
            )
            items = response.get("Items", [])

            for item in items:
                # Skip non-session items (plans, etc.)
                session_date = item.get("session_date", "")
                if session_date.startswith("PLAN#") or session_date.startswith("MPLAN#"):
                    continue
                if "session_id" not in item:
                    continue

                all_sessions.append({
                    "session_id": item["session_id"],
                    "session_date": item["session_date"],
                    "total_distance_meters": int(item.get("total_distance_meters", 0)),
                    "total_time_seconds": int(item.get("total_time_seconds", 0)),
                    "stroke_type": item.get("stroke_type", ""),
                    "average_pace_per_100m": float(item.get("average_pace_per_100m", 0)),
                    "swolf_score": int(item.get("swolf_score", 0)),
                    "friend_display_name": friend_display_name,
                    "friend_user_id": friend_id,
                    "profile_picture_url": profile_picture_url,
                })
        except ClientError:
            continue

    # Sort by session_date descending
    all_sessions.sort(key=lambda s: s["session_date"], reverse=True)

    return all_sessions
