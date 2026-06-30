"""
Personal Best (PB) resolver for AI Swim Coach.

Resolves personal bests by priority: manual entry first, then derived from
session history. PBs are stored as a map attribute `personal_bests` on the
existing UserProfiles DynamoDB table.

Format:
    personal_bests: {
        "100m Freestyle": {
            "time_seconds": 65.5,
            "source": "manual",
            "updated_at": "2024-..."
        }
    }

Requirements: 3.1, 3.2, 3.3, 3.4, 7.1, 7.2, 7.3, 7.4
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError


# Module-level placeholder; lazily initialized on first call
_dynamodb_resource = None

# Pace degradation factors: how much slower per-100m pace becomes at longer distances.
# Key is target distance in meters, value is the scaling factor applied to the
# fastest 100m pace to estimate the time for that distance.
# For example, 200m uses factor 2.05 (not 2.0) to account for fatigue.
PACE_DEGRADATION_FACTORS = {
    50: 0.48,    # 50m is slightly faster than half of 100m pace
    100: 1.0,    # baseline
    200: 2.05,   # ~2.5% fatigue penalty
    400: 4.20,   # ~5% fatigue penalty
    800: 8.60,   # ~7.5% fatigue penalty
    1500: 16.50, # ~10% fatigue penalty
}


def _get_dynamodb() -> "boto3.resources.base.ServiceResource":
    """Return the (cached) DynamoDB resource, creating it if necessary."""
    global _dynamodb_resource  # noqa: PLW0603
    if _dynamodb_resource is None:
        _dynamodb_resource = boto3.resource("dynamodb")
    return _dynamodb_resource


class PBResolverError(Exception):
    """Exception raised when PB resolution operations fail."""
    pass


def _get_profiles_table():
    """Get the UserProfiles DynamoDB table."""
    table_name = os.environ.get("PROFILES_TABLE", "UserProfiles")
    return _get_dynamodb().Table(table_name)


def _get_sessions_table():
    """Get the Sessions DynamoDB table."""
    table_name = os.environ.get("SESSIONS_TABLE", "Sessions")
    return _get_dynamodb().Table(table_name)


def _now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format with millisecond precision."""
    now = datetime.now(tz=timezone.utc)
    ms = now.microsecond // 1000
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ms:03d}Z"


def _parse_event(event: str) -> tuple[int, str] | None:
    """Parse an event string like '100m Freestyle' into (distance_m, stroke_type).

    Returns None if the event string doesn't match the expected format.
    """
    match = re.match(r"(\d+)m\s+(.+)", event, re.IGNORECASE)
    if not match:
        return None
    distance_m = int(match.group(1))
    stroke_type = match.group(2).strip()
    return distance_m, stroke_type


def save_personal_best(user_id: str, event: str, time_seconds: float) -> None:
    """Persist a manually entered personal best.

    Stores the PB as part of the `personal_bests` map attribute on the
    UserProfiles table item. If the attribute doesn't exist yet, it is created.

    Args:
        user_id: User identifier (UUID v4)
        event: Event name (e.g., "100m Freestyle")
        time_seconds: Time in seconds (must be positive)

    Raises:
        ValueError: If time_seconds is not positive or event is empty
        PBResolverError: If DynamoDB operation fails

    Requirements: 3.1, 3.2
    """
    if not event or not event.strip():
        raise ValueError("Event name must be non-empty")
    if not isinstance(time_seconds, (int, float)) or time_seconds <= 0:
        raise ValueError("time_seconds must be a positive number")

    table = _get_profiles_table()
    updated_at = _now_iso()

    # Use DynamoDB update expression to set the PB within the map
    # First ensure the personal_bests map exists, then set the event entry
    try:
        table.update_item(
            Key={"user_id": user_id},
            UpdateExpression=(
                "SET personal_bests.#event = :pb_entry"
            ),
            ExpressionAttributeNames={
                "#event": event,
            },
            ExpressionAttributeValues={
                ":pb_entry": {
                    "time_seconds": Decimal(str(time_seconds)),
                    "source": "manual",
                    "updated_at": updated_at,
                },
            },
        )
    except ClientError as e:
        # If personal_bests attribute doesn't exist yet, create it
        if e.response["Error"]["Code"] == "ValidationException":
            try:
                table.update_item(
                    Key={"user_id": user_id},
                    UpdateExpression="SET personal_bests = :pb_map",
                    ExpressionAttributeValues={
                        ":pb_map": {
                            event: {
                                "time_seconds": Decimal(str(time_seconds)),
                                "source": "manual",
                                "updated_at": updated_at,
                            }
                        },
                    },
                )
            except ClientError as e2:
                raise PBResolverError(
                    f"Failed to save personal best: {e2}"
                ) from e2
        else:
            raise PBResolverError(
                f"Failed to save personal best: {e}"
            ) from e


def delete_personal_best(user_id: str, event: str) -> None:
    """Delete a manually entered personal best.

    Removes the PB entry from the `personal_bests` map attribute on the
    UserProfiles table item.

    Args:
        user_id: User identifier (UUID v4)
        event: Event name (e.g., "100m Freestyle")

    Raises:
        ValueError: If event is empty
        PBResolverError: If DynamoDB operation fails
    """
    if not event or not event.strip():
        raise ValueError("Event name must be non-empty")

    table = _get_profiles_table()

    try:
        table.update_item(
            Key={"user_id": user_id},
            UpdateExpression="REMOVE personal_bests.#event",
            ExpressionAttributeNames={
                "#event": event,
            },
        )
    except ClientError as e:
        raise PBResolverError(
            f"Failed to delete personal best: {e}"
        ) from e


def get_personal_bests(user_id: str) -> list[dict]:
    """Return all PBs (manual + derived) for a user.

    Retrieves manually entered PBs from the UserProfiles table, then
    derives PBs from session history. Returns BOTH manual and derived
    entries even when they exist for the same event, enabling side-by-side
    comparison in the frontend.

    Args:
        user_id: User identifier (UUID v4)

    Returns:
        List of dicts, each with:
            - event: str (event name)
            - time_seconds: float
            - source: str ("manual" or "derived")
            - updated_at: str (ISO 8601)
        Note: Multiple entries may exist for the same event (one manual,
        one derived).

    Raises:
        PBResolverError: If DynamoDB operation fails

    Requirements: 3.2, 4.3, 4.8, 8.7
    """
    table = _get_profiles_table()

    try:
        response = table.get_item(
            Key={"user_id": user_id},
            ProjectionExpression="personal_bests",
        )
    except ClientError as e:
        raise PBResolverError(
            f"Failed to retrieve personal bests: {e}"
        ) from e

    # Gather manual PBs
    manual_pbs: dict[str, dict] = {}
    item = response.get("Item", {})
    pb_map = item.get("personal_bests", {})

    for event_name, pb_data in pb_map.items():
        manual_pbs[event_name] = {
            "event": event_name,
            "time_seconds": float(pb_data["time_seconds"]),
            "source": pb_data["source"],
            "updated_at": pb_data["updated_at"],
        }

    # Derive PBs from session history
    derived_pbs = _derive_all_pbs_from_history(user_id)

    # Return ALL PBs — both manual and derived (even for same event)
    all_pbs = list(manual_pbs.values()) + list(derived_pbs.values())
    return all_pbs


def resolve_personal_best(user_id: str, event: str) -> float | None:
    """Resolve PB for an event. Returns time in seconds or None.

    Priority: manual entry > derived from session history.

    Args:
        user_id: User identifier (UUID v4)
        event: Event name (e.g., "100m Freestyle")

    Returns:
        Time in seconds if a PB is found, None otherwise.

    Raises:
        PBResolverError: If DynamoDB operation fails

    Requirements: 3.3, 3.4, 7.4
    """
    # First check for manual PB
    table = _get_profiles_table()

    try:
        response = table.get_item(
            Key={"user_id": user_id},
            ProjectionExpression="personal_bests.#event",
            ExpressionAttributeNames={"#event": event},
        )
    except ClientError as e:
        raise PBResolverError(
            f"Failed to resolve personal best: {e}"
        ) from e

    item = response.get("Item", {})
    pb_map = item.get("personal_bests", {})

    if event in pb_map:
        pb_entry = pb_map[event]
        return float(pb_entry["time_seconds"])

    # No manual PB; try to derive from history
    parsed = _parse_event(event)
    if parsed is None:
        return None

    distance_m, stroke_type = parsed
    return derive_pb_from_history(user_id, stroke_type, distance_m)


def derive_pb_from_history(
    user_id: str, stroke_type: str, distance_m: int
) -> float | None:
    """Derive PB from session history using pace degradation scaling.

    Finds the fastest average_pace_per_100m for sessions matching the given
    stroke_type, then scales using the pace degradation factor for the target
    distance.

    Args:
        user_id: User identifier (UUID v4)
        stroke_type: Stroke type to filter sessions by (e.g., "Freestyle")
        distance_m: Target event distance in meters

    Returns:
        Estimated time in seconds for the target distance, or None if no
        matching sessions found.

    Requirements: 3.4, 7.1, 7.2, 7.3
    """
    # Query sessions for this user
    sessions_table = _get_sessions_table()

    try:
        response = sessions_table.query(
            KeyConditionExpression=Key("user_id").eq(user_id),
            ProjectionExpression="stroke_type, average_pace_per_100m, session_date",
        )
    except ClientError as e:
        raise PBResolverError(
            f"Failed to query session history: {e}"
        ) from e

    items = response.get("Items", [])

    # Filter for matching stroke type (case-insensitive) and skip non-session items
    fastest_pace: float | None = None
    for item in items:
        # Skip plan items or items without expected fields
        session_date = item.get("session_date", "")
        if session_date.startswith("PLAN#") or session_date.startswith("MPLAN#"):
            continue

        item_stroke = item.get("stroke_type", "")
        if item_stroke.lower() != stroke_type.lower():
            continue

        pace = item.get("average_pace_per_100m")
        if pace is None:
            continue

        pace_float = float(pace)
        if pace_float <= 0:
            continue

        if fastest_pace is None or pace_float < fastest_pace:
            fastest_pace = pace_float

    if fastest_pace is None:
        return None

    # Scale the fastest 100m pace to the target distance using degradation factors
    return _scale_pace_to_distance(fastest_pace, distance_m)


def _scale_pace_to_distance(pace_per_100m: float, distance_m: int) -> float:
    """Scale a 100m pace to a target distance using pace degradation factors.

    Uses predefined degradation factors for standard distances. For non-standard
    distances, interpolates linearly between the two nearest standard distances.

    Args:
        pace_per_100m: Fastest pace per 100m in seconds
        distance_m: Target distance in meters

    Returns:
        Estimated time in seconds for the target distance
    """
    # If exact match in our table, use it directly
    if distance_m in PACE_DEGRADATION_FACTORS:
        return pace_per_100m * PACE_DEGRADATION_FACTORS[distance_m]

    # Interpolate between nearest standard distances
    distances = sorted(PACE_DEGRADATION_FACTORS.keys())

    # If below minimum, extrapolate from smallest
    if distance_m <= distances[0]:
        factor = PACE_DEGRADATION_FACTORS[distances[0]]
        ratio = distance_m / distances[0]
        return pace_per_100m * factor * ratio

    # If above maximum, extrapolate with degradation
    if distance_m >= distances[-1]:
        # Use the degradation rate from the last two known points
        d1, d2 = distances[-2], distances[-1]
        f1, f2 = PACE_DEGRADATION_FACTORS[d1], PACE_DEGRADATION_FACTORS[d2]
        rate = (f2 - f1) / (d2 - d1)
        extra_distance = distance_m - d2
        return pace_per_100m * (f2 + rate * extra_distance)

    # Find bracketing distances and interpolate
    for i in range(len(distances) - 1):
        d_low, d_high = distances[i], distances[i + 1]
        if d_low <= distance_m <= d_high:
            f_low = PACE_DEGRADATION_FACTORS[d_low]
            f_high = PACE_DEGRADATION_FACTORS[d_high]
            # Linear interpolation
            t = (distance_m - d_low) / (d_high - d_low)
            factor = f_low + t * (f_high - f_low)
            return pace_per_100m * factor

    # Fallback: simple scaling (shouldn't reach here)
    return pace_per_100m * (distance_m / 100.0)


def _derive_all_pbs_from_history(user_id: str) -> dict[str, dict]:
    """Derive PBs for all stroke types found in session history.

    Scans all sessions for the user, groups by stroke type, finds the
    fastest pace per stroke, and derives a 100m PB for each.

    Args:
        user_id: User identifier

    Returns:
        Dict mapping event name to PB data dict
    """
    sessions_table = _get_sessions_table()

    try:
        response = sessions_table.query(
            KeyConditionExpression=Key("user_id").eq(user_id),
            ProjectionExpression="stroke_type, average_pace_per_100m, session_date",
        )
    except ClientError as e:
        # Non-fatal: return empty if we can't query history
        return {}

    items = response.get("Items", [])

    # Group fastest pace by stroke type
    fastest_by_stroke: dict[str, float] = {}
    for item in items:
        session_date = item.get("session_date", "")
        if session_date.startswith("PLAN#") or session_date.startswith("MPLAN#"):
            continue

        stroke = item.get("stroke_type", "")
        if not stroke:
            continue

        pace = item.get("average_pace_per_100m")
        if pace is None:
            continue

        pace_float = float(pace)
        if pace_float <= 0:
            continue

        if stroke not in fastest_by_stroke or pace_float < fastest_by_stroke[stroke]:
            fastest_by_stroke[stroke] = pace_float

    # Build derived PB entries for multiple distances
    # Standard distances to derive: 50m, 100m, 400m, 750m, 2000m
    derive_distances = [50, 100, 400, 750, 2000]
    
    derived: dict[str, dict] = {}
    for stroke, fastest_pace in fastest_by_stroke.items():
        for distance in derive_distances:
            event_name = f"{distance}m {stroke}"
            time_seconds = _scale_pace_to_distance(fastest_pace, distance)
            derived[event_name] = {
                "event": event_name,
                "time_seconds": round(time_seconds, 3),
                "source": "derived",
                "updated_at": _now_iso(),
            }

    return derived
