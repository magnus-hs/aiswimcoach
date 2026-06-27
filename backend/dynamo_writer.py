"""
DynamoDB writer for AI Swim Coach.

Persists a coaching session record to the `coaching-sessions` table.
The table name is read from the ``DYNAMODB_TABLE`` environment variable.

Schema
------
Partition key : ``file_key``  (String) – the S3 object key
Sort key      : ``created_at`` (String) – ISO 8601 UTC, millisecond precision
                e.g. ``2024-06-15T10:30:00.123Z``
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal

import boto3

from backend.models import CoachingResponse, Metrics

# Module-level placeholder; lazily initialised on first call so that:
#   1. Lambda warm-path reuses the connection across invocations.
#   2. Tests that import the module before patching boto3 (e.g. with moto)
#      do not trigger a real AWS connection at import time.
_dynamodb_resource = None


def _get_dynamodb() -> "boto3.resources.base.ServiceResource":
    """Return the (cached) DynamoDB resource, creating it if necessary."""
    global _dynamodb_resource  # noqa: PLW0603
    if _dynamodb_resource is None:
        _dynamodb_resource = boto3.resource("dynamodb")
    return _dynamodb_resource


def save_to_dynamodb(
    s3_key: str,
    metrics: Metrics,
    coaching: CoachingResponse,
) -> None:
    """Persist a coaching session to DynamoDB.

    Composes and writes a single item containing the S3 key, a UTC
    millisecond-precision timestamp, all three swim metrics, and the
    AI-generated coaching response.

    The table name is resolved from the ``DYNAMODB_TABLE`` environment
    variable at call time so that it can be overridden in tests without
    monkeypatching the module.

    Args:
        s3_key:   S3 object key used as the DynamoDB partition key.
        metrics:  Swim metrics extracted from the FIT file.
        coaching: AI-generated coaching response.

    Raises:
        Exception: Any exception raised by the DynamoDB ``put_item`` call
            is re-raised unmodified.  The Lambda handler wraps this call in
            a ``try/except`` block and logs the failure as best-effort.
    """
    table_name = os.environ["DYNAMODB_TABLE"]

    # Build ISO 8601 UTC timestamp with millisecond precision.
    now = datetime.now(tz=timezone.utc)
    ms = now.microsecond // 1000
    created_at = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ms:03d}Z"

    item = {
        "file_key": s3_key,
        "created_at": created_at,
        # DynamoDB Number type requires Decimal; float is not supported.
        "pace": Decimal(str(metrics.pace)),
        "swolf": Decimal(str(metrics.swolf)),
        "stroke_rate": Decimal(str(metrics.stroke_rate)),
        # List of Strings
        "tips": coaching.tips,
        # Single String
        "drill": coaching.drill,
    }

    table = _get_dynamodb().Table(table_name)
    try:
        table.put_item(Item=item)
    except Exception:
        raise
