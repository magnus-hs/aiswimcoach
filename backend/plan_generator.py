"""
Plan Generator for AI Swim Coach.

Orchestrates multi-week plan creation by:
1. Validating input parameters
2. Resolving personal best via pb_resolver
3. Building the prompt via periodization_engine
4. Calling Bedrock with tool-use schema
5. Parsing and validating the response
6. Saving to structured_plan_store
7. Returning the complete plan dict

Requirements: 1.1-1.6, 2.1-2.4, 3.5, 3.6, 8.1
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError

from periodization_engine import (
    MULTI_WEEK_PLAN_TOOL_SCHEMA,
    build_plan_prompt,
    validate_plan_structure,
)
from pb_resolver import resolve_personal_best, PBResolverError
from structured_plan_store import save_structured_plan

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Model configuration (same as bedrock_client.py)
# ---------------------------------------------------------------------------

_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class PlanGenerationError(Exception):
    """Raised when plan generation fails."""

    def __init__(self, message: str, http_status: int = 502) -> None:
        super().__init__(message)
        self.http_status = http_status


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def generate_multi_week_plan(
    user_id: str,
    event: str,
    target_time: str,
    weeks: int,
    sessions_per_week: int = 3,
) -> dict:
    """Generate a complete multi-week training plan.

    Orchestrates the full plan generation pipeline: validation, PB resolution,
    prompt building, Bedrock invocation, response validation, and persistence.

    Args:
        user_id: Authenticated user ID
        event: Target event (e.g., "100m Freestyle")
        target_time: Goal time string (e.g., "0:58.5")
        weeks: Plan duration (4-12)
        sessions_per_week: Sessions per week (3-5, default 3)

    Returns:
        Complete plan dict with plan_id, goal, weeks, sessions, and metadata.

    Raises:
        ValueError: If weeks or sessions_per_week are outside valid ranges.
        PlanGenerationError: If Bedrock invocation or response validation fails.
    """
    # 1. Validate inputs
    if not isinstance(weeks, int) or weeks < 4 or weeks > 12:
        raise ValueError(
            f"weeks must be an integer between 4 and 12, got {weeks}"
        )
    if not isinstance(sessions_per_week, int) or sessions_per_week < 3 or sessions_per_week > 5:
        raise ValueError(
            f"sessions_per_week must be an integer between 3 and 5, got {sessions_per_week}"
        )
    if not event or not event.strip():
        raise ValueError("event must be a non-empty string")
    if not target_time or not target_time.strip():
        raise ValueError("target_time must be a non-empty string")

    # 2. Resolve personal best (best-effort, None if unavailable)
    personal_best_seconds: float | None = None
    try:
        personal_best_seconds = resolve_personal_best(user_id, event)
    except PBResolverError as exc:
        logger.warning(
            "PB resolution failed for user %s, event %s: %s",
            user_id,
            event,
            exc,
        )
    except Exception as exc:
        logger.warning(
            "Unexpected error resolving PB for user %s: %s", user_id, exc
        )

    # 3. Build prompt via periodization_engine
    system_prompt = build_plan_prompt(
        event=event,
        target_time=target_time,
        personal_best_seconds=personal_best_seconds,
        weeks=weeks,
        sessions_per_week=sessions_per_week,
    )

    # 4. Call Bedrock with tool-use schema
    request_body = _build_bedrock_request(system_prompt, event, target_time)

    plan_data = _invoke_bedrock_with_retry(request_body, weeks, sessions_per_week)

    # 7. Save plan via structured_plan_store with status "draft"
    plan_to_save = {
        "goal": {
            "event": event,
            "target_time": target_time,
            "personal_best_seconds": personal_best_seconds,
        },
        "duration_weeks": weeks,
        "sessions_per_week": sessions_per_week,
        "weeks": plan_data["weeks"],
        "status": "draft",
    }

    plan_id = save_structured_plan(user_id, plan_to_save)

    # 8. Return complete plan dict
    return {
        "plan_id": plan_id,
        "status": "draft",
        "goal": {
            "event": event,
            "target_time": target_time,
            "personal_best_seconds": personal_best_seconds,
        },
        "duration_weeks": weeks,
        "sessions_per_week": sessions_per_week,
        "weeks": plan_data["weeks"],
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _build_bedrock_request(
    system_prompt: str,
    event: str,
    target_time: str,
) -> dict[str, Any]:
    """Construct the Bedrock invoke_model request body for multi-week plan."""
    user_message = (
        f"Please generate a multi-week training plan for the following goal:\n"
        f"- Event: {event}\n"
        f"- Target time: {target_time}\n\n"
        "Generate the plan following the constraints in the system prompt."
    )

    return {
        "anthropic_version": "bedrock-2023-05-31",
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": user_message},
        ],
        "tools": [MULTI_WEEK_PLAN_TOOL_SCHEMA],
        "tool_choice": {"type": "tool", "name": "submit_multi_week_plan"},
        "max_tokens": 8192,
    }


def _invoke_bedrock_with_retry(
    request_body: dict[str, Any],
    weeks: int,
    sessions_per_week: int,
) -> dict[str, Any]:
    """Call Bedrock and validate response; retry once on validation failure.

    Args:
        request_body: The full Bedrock request body
        weeks: Expected number of weeks for validation
        sessions_per_week: Expected sessions per week for validation

    Returns:
        Validated plan_data dict with 'weeks' key

    Raises:
        PlanGenerationError: On Bedrock failure or invalid response after retry
    """
    region = os.environ.get("AWS_REGION", "us-east-1")
    client = boto3.client("bedrock-runtime", region_name=region)

    # First attempt
    raw_response = _call_bedrock(client, request_body)
    plan_data = _parse_plan_response(raw_response)

    if plan_data is not None and validate_plan_structure(plan_data, weeks, sessions_per_week):
        return plan_data

    # Retry once
    logger.warning("Multi-week plan response failed validation; retrying once")
    raw_response = _call_bedrock(client, request_body)
    plan_data = _parse_plan_response(raw_response)

    if plan_data is not None and validate_plan_structure(plan_data, weeks, sessions_per_week):
        return plan_data

    raise PlanGenerationError("Plan generation failed: AI returned an invalid plan structure")


def _call_bedrock(client: Any, request_body: dict[str, Any]) -> dict[str, Any]:
    """Call bedrock-runtime invoke_model and return the parsed response body.

    Raises:
        PlanGenerationError: On ClientError or any other network/HTTP exception.
    """
    try:
        response = client.invoke_model(
            modelId=_MODEL_ID,
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json",
        )
    except ClientError as exc:
        logger.error("Bedrock ClientError: %s", exc)
        raise PlanGenerationError("Plan generation unavailable") from exc
    except Exception as exc:
        logger.error("Bedrock network/unknown error: %s", exc)
        raise PlanGenerationError("Plan generation unavailable") from exc

    http_status = response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)
    if http_status != 200:
        logger.error("Bedrock returned HTTP %s", http_status)
        raise PlanGenerationError("Plan generation unavailable")

    raw_body = response["body"].read()
    return json.loads(raw_body)


def _parse_plan_response(response_body: dict[str, Any]) -> dict[str, Any] | None:
    """Extract plan data from a Bedrock tool-use response.

    Returns the plan data dict (with 'weeks' key) on success, or None if invalid.
    """
    try:
        content = response_body.get("content", [])

        tool_use_block = next(
            (block for block in content if block.get("type") == "tool_use"),
            None,
        )
        if tool_use_block is None:
            logger.warning("No tool_use block found in multi-week plan response")
            return None

        tool_input = tool_use_block.get("input", {})

        if "weeks" not in tool_input:
            logger.warning("tool_input missing 'weeks' key")
            return None

        return tool_input

    except (ValueError, TypeError, KeyError) as exc:
        logger.warning("Failed to parse multi-week plan response: %s", exc)
        return None
