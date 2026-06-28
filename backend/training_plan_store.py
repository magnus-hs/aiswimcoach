"""
Training plan persistence module for AI Swim Coach.

Provides functions for saving and retrieving generated training plans.
Plans are stored in the same DynamoDB Sessions table using a sort key
prefix of "PLAN#" to distinguish them from swim session records.

Schema:
    Partition key: user_id (same as sessions)
    Sort key: PLAN#<created_at_iso> (prefix differentiates from session dates)
    Attributes: plan_id, user_id, created_at, goal, plan
"""
from __future__ import annotations

import json
import logging
import os
import uuid
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


def save_training_plan(user_id: str, goal: dict, plan: dict) -> str:
    """Save a training plan to DynamoDB.

    Generates a unique plan_id (UUID v4) and persists the plan with metadata.

    Args:
        user_id: User identifier (UUID v4)
        goal: Training goal dict with event, target_time, volume_meters, timeframe
        plan: Generated plan dict with session_title, warm_up, main_set,
              cool_down, total_distance, focus_notes, goal_likelihood

    Returns:
        plan_id (UUID v4 string)

    Raises:
        Exception: Any exception raised by DynamoDB put_item operation
    """
    plan_id = str(uuid.uuid4())
    now = datetime.now(tz=timezone.utc)
    created_at = now.isoformat()

    # Sort key uses PLAN# prefix to distinguish from session records
    sort_key = f"PLAN#{created_at}"

    # Build DynamoDB item - convert numeric values to Decimal for DynamoDB
    item = {
        "user_id": user_id,
        "session_date": sort_key,  # sort key column name in existing table
        "plan_id": plan_id,
        "created_at": created_at,
        "goal": {
            "event": goal.get("event", ""),
            "target_time": goal.get("target_time", ""),
            "volume_meters": int(goal.get("volume_meters", 0)),
            "timeframe": goal.get("timeframe", ""),
        },
        "plan": {
            "session_title": plan.get("session_title", ""),
            "warm_up": plan.get("warm_up", []),
            "main_set": plan.get("main_set", []),
            "cool_down": plan.get("cool_down", []),
            "total_distance": int(plan.get("total_distance", 0)),
            "focus_notes": plan.get("focus_notes", ""),
            "goal_likelihood": plan.get("goal_likelihood", ""),
        },
        "item_type": "PLAN",  # explicit type marker for clarity
    }

    table_name = os.environ.get("SESSIONS_TABLE", "Sessions")
    table = _get_dynamodb().Table(table_name)
    table.put_item(Item=item)

    logger.info("Saved training plan %s for user %s", plan_id, user_id)
    return plan_id


def get_user_plans(user_id: str) -> list[dict]:
    """Get all training plans for a user, ordered by created_at descending.

    Queries the Sessions table for items with sort key beginning with "PLAN#".

    Args:
        user_id: User identifier (UUID v4)

    Returns:
        List of plan dicts ordered by created_at descending, each containing:
        plan_id, created_at, goal, plan

    Raises:
        Exception: Any exception raised by DynamoDB query operation
    """
    table_name = os.environ.get("SESSIONS_TABLE", "Sessions")
    table = _get_dynamodb().Table(table_name)

    response = table.query(
        KeyConditionExpression=(
            Key("user_id").eq(user_id) & Key("session_date").begins_with("PLAN#")
        ),
        ScanIndexForward=False,  # Descending order (most recent first)
    )

    items = response.get("Items", [])

    plans = []
    for item in items:
        plan_data = {
            "plan_id": item.get("plan_id", ""),
            "created_at": item.get("created_at", ""),
            "goal": _convert_decimals(item.get("goal", {})),
            "plan": _convert_decimals(item.get("plan", {})),
        }
        plans.append(plan_data)

    return plans


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
