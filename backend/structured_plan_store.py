"""
Structured training plan persistence module for AI Swim Coach.

Provides functions for saving and retrieving multi-week structured training plans.
Plans are stored in the same DynamoDB Sessions table using a sort key prefix of
"MPLAN#" to distinguish them from single-session plans ("PLAN#") and session records.

Schema:
    Partition key: user_id (same as sessions)
    Sort key: MPLAN#<created_at_iso> (prefix differentiates from single-session plans)
    Attributes: plan_id, user_id, created_at, status, status_updated_at,
                goal, duration_weeks, sessions_per_week, weeks
"""
from __future__ import annotations

import logging
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Module-level placeholder for DynamoDB resource (lazy initialization)
_dynamodb_resource = None


def _get_dynamodb() -> "boto3.resources.base.ServiceResource":
    """Return the (cached) DynamoDB resource, creating it if necessary."""
    global _dynamodb_resource  # noqa: PLW0603
    if _dynamodb_resource is None:
        _dynamodb_resource = boto3.resource("dynamodb")
    return _dynamodb_resource


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class SessionTemplate:
    """A single training session within a week block."""

    session_title: str
    session_type: str  # "endurance" | "speed" | "technique" | "threshold"
    warm_up: list[str] = field(default_factory=list)
    main_set: list[str] = field(default_factory=list)
    cool_down: list[str] = field(default_factory=list)
    total_distance: int = 0
    focus_notes: str = ""


@dataclass
class WeekBlock:
    """A grouping of sessions within a single week of a training plan."""

    week_number: int
    sessions: list[SessionTemplate] = field(default_factory=list)


@dataclass
class StructuredTrainingPlan:
    """A complete multi-week structured training plan."""

    plan_id: str
    user_id: str
    created_at: str
    status: str  # "draft" | "active" | "archived"
    status_updated_at: str
    goal: dict  # {event, target_time, personal_best_seconds}
    duration_weeks: int
    sessions_per_week: int
    weeks: list[WeekBlock] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Persistence Functions
# ---------------------------------------------------------------------------


def save_structured_plan(user_id: str, plan: dict) -> str:
    """Save a complete multi-week training plan to DynamoDB.

    Generates a unique plan_id (UUID v4) and persists the plan with metadata.

    Args:
        user_id: User identifier (UUID v4)
        plan: Plan dict containing goal, duration_weeks, sessions_per_week,
              weeks (list of week blocks with sessions), and optionally status.

    Returns:
        plan_id (UUID v4 string)

    Raises:
        Exception: Any exception raised by DynamoDB put_item operation
    """
    plan_id = str(uuid.uuid4())
    now = datetime.now(tz=timezone.utc)
    created_at = now.isoformat()

    # Sort key uses MPLAN# prefix to distinguish from single-session plans
    sort_key = f"MPLAN#{created_at}"

    status = plan.get("status", "draft")

    # Build DynamoDB item
    item = {
        "user_id": user_id,
        "session_date": sort_key,  # sort key column name in existing table
        "plan_id": plan_id,
        "created_at": created_at,
        "status": status,
        "status_updated_at": created_at,
        "goal": _convert_to_dynamodb_types(plan.get("goal", {})),
        "duration_weeks": plan.get("duration_weeks", 0),
        "sessions_per_week": plan.get("sessions_per_week", 3),
        "weeks": _convert_to_dynamodb_types(plan.get("weeks", [])),
        "item_type": "MPLAN",  # explicit type marker for clarity
    }

    table_name = os.environ.get("SESSIONS_TABLE", "Sessions")
    table = _get_dynamodb().Table(table_name)
    table.put_item(Item=item)

    logger.info("Saved structured plan %s for user %s", plan_id, user_id)
    return plan_id


def get_user_structured_plans(user_id: str) -> list[dict]:
    """Get plan summaries for a user, ordered by created_at descending.

    Returns summaries without full weeks content for the list view.

    Args:
        user_id: User identifier (UUID v4)

    Returns:
        List of plan summary dicts ordered by created_at descending, each containing:
        plan_id, created_at, status, status_updated_at, goal, duration_weeks,
        sessions_per_week (without full weeks content)

    Raises:
        Exception: Any exception raised by DynamoDB query operation
    """
    table_name = os.environ.get("SESSIONS_TABLE", "Sessions")
    table = _get_dynamodb().Table(table_name)

    response = table.query(
        KeyConditionExpression=(
            Key("user_id").eq(user_id)
            & Key("session_date").begins_with("MPLAN#")
        ),
        ScanIndexForward=False,  # Descending order (most recent first)
    )

    items = response.get("Items", [])

    plans = []
    for item in items:
        plan_summary = {
            "plan_id": item.get("plan_id", ""),
            "created_at": item.get("created_at", ""),
            "status": item.get("status", "draft"),
            "status_updated_at": item.get("status_updated_at", ""),
            "goal": _convert_decimals(item.get("goal", {})),
            "duration_weeks": _convert_decimals(item.get("duration_weeks", 0)),
            "sessions_per_week": _convert_decimals(
                item.get("sessions_per_week", 3)
            ),
        }
        plans.append(plan_summary)

    return plans


def get_plan_by_id(user_id: str, plan_id: str) -> dict | None:
    """Get a complete plan by ID including all weeks and sessions.

    Args:
        user_id: User identifier (UUID v4)
        plan_id: Plan identifier (UUID v4)

    Returns:
        Complete plan dict with all weeks and sessions, or None if not found.

    Raises:
        Exception: Any exception raised by DynamoDB query operation
    """
    table_name = os.environ.get("SESSIONS_TABLE", "Sessions")
    table = _get_dynamodb().Table(table_name)

    # Query all MPLAN# items for this user and filter by plan_id
    response = table.query(
        KeyConditionExpression=(
            Key("user_id").eq(user_id)
            & Key("session_date").begins_with("MPLAN#")
        ),
    )

    items = response.get("Items", [])

    for item in items:
        if item.get("plan_id") == plan_id:
            return {
                "plan_id": item.get("plan_id", ""),
                "user_id": item.get("user_id", ""),
                "created_at": item.get("created_at", ""),
                "status": item.get("status", "draft"),
                "status_updated_at": item.get("status_updated_at", ""),
                "goal": _convert_decimals(item.get("goal", {})),
                "duration_weeks": _convert_decimals(
                    item.get("duration_weeks", 0)
                ),
                "sessions_per_week": _convert_decimals(
                    item.get("sessions_per_week", 3)
                ),
                "weeks": _convert_decimals(item.get("weeks", [])),
            }

    return None


def update_plan_status(user_id: str, plan_id: str, new_status: str) -> None:
    """Update plan status and record transition timestamp.

    Args:
        user_id: User identifier (UUID v4)
        plan_id: Plan identifier (UUID v4)
        new_status: New status value ("draft", "active", or "archived")

    Raises:
        ValueError: If plan is not found
        Exception: Any exception raised by DynamoDB update operation
    """
    table_name = os.environ.get("SESSIONS_TABLE", "Sessions")
    table = _get_dynamodb().Table(table_name)

    # First, find the plan's sort key by querying
    response = table.query(
        KeyConditionExpression=(
            Key("user_id").eq(user_id)
            & Key("session_date").begins_with("MPLAN#")
        ),
    )

    items = response.get("Items", [])
    target_item = None
    for item in items:
        if item.get("plan_id") == plan_id:
            target_item = item
            break

    if target_item is None:
        raise ValueError(f"Plan {plan_id} not found for user {user_id}")

    # Update the status and status_updated_at
    now = datetime.now(tz=timezone.utc).isoformat()
    sort_key = target_item["session_date"]

    table.update_item(
        Key={"user_id": user_id, "session_date": sort_key},
        UpdateExpression="SET #s = :status, #su = :status_updated_at",
        ExpressionAttributeNames={
            "#s": "status",
            "#su": "status_updated_at",
        },
        ExpressionAttributeValues={
            ":status": new_status,
            ":status_updated_at": now,
        },
    )

    logger.info(
        "Updated plan %s status to %s for user %s",
        plan_id,
        new_status,
        user_id,
    )


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _convert_decimals(obj):
    """Recursively convert Decimal values to int/float for JSON serialization."""
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    elif isinstance(obj, dict):
        return {k: _convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_decimals(i) for i in obj]
    return obj


def _convert_to_dynamodb_types(obj):
    """Recursively convert float/int values to Decimal for DynamoDB storage."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, int) and not isinstance(obj, bool):
        return obj  # DynamoDB handles int natively
    elif isinstance(obj, dict):
        return {k: _convert_to_dynamodb_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_to_dynamodb_types(i) for i in obj]
    return obj
