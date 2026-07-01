"""
Simple fixed-window rate limiter backed by DynamoDB.

Used to throttle abuse-prone endpoints (login, registration, password reset,
Google auth). Keyed by action + identifier (usually the client IP).

The limiter FAILS OPEN: if the backing store errors, requests are allowed so a
DynamoDB hiccup never locks legitimate users out.
"""
from __future__ import annotations

import os
import time

import boto3

_table = None


def _get_table():
    global _table  # noqa: PLW0603
    if _table is None:
        name = os.environ.get("RATE_LIMIT_TABLE", "ai-swim-coach-rate-limits")
        _table = boto3.resource("dynamodb").Table(name)
    return _table


def check_rate_limit(action: str, identifier: str, limit: int, window_seconds: int) -> bool:
    """Return True if the request is allowed, False if the limit is exceeded.

    Fixed-window algorithm: the first request in a window sets the counter and
    an expiry; subsequent requests within the window increment it. Once the
    counter reaches ``limit`` the window is blocked until it expires.

    Args:
        action:         Logical action name (e.g. "login").
        identifier:     Caller identity, typically the source IP.
        limit:          Max requests allowed per window.
        window_seconds: Window length in seconds.
    """
    key = f"{action}#{identifier}"
    now = int(time.time())
    try:
        table = _get_table()
        item = table.get_item(Key={"rl_key": key}).get("Item")
        if item and int(item.get("window_end", 0)) > now:
            if int(item.get("attempts", 0)) >= limit:
                return False
            table.update_item(
                Key={"rl_key": key},
                UpdateExpression="ADD attempts :one",
                ExpressionAttributeValues={":one": 1},
            )
            return True
        # New window (or previous one expired).
        window_end = now + window_seconds
        table.put_item(
            Item={
                "rl_key": key,
                "attempts": 1,
                "window_end": window_end,
                "ttl": window_end + 300,
            }
        )
        return True
    except Exception:
        # Fail open — never block legitimate traffic on infra errors.
        return True
