"""
Bedrock client for AI Swim Coach.

Invokes Amazon Bedrock (Claude 3.5 Sonnet) using the Tool Use API to produce
a structured CoachingResponse from swim Metrics.

Error handling:
  - Non-2xx HTTP status or network/ClientError  → BedrockError (HTTP 502) immediately
  - HTTP 200 but invalid schema                → retry once; HTTP 502 if still invalid
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError

from models import CoachingResponse, Metrics, TrainingGoal, TrainingPlan

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------

_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

# ---------------------------------------------------------------------------
# Tool schema — enforces structured output
# ---------------------------------------------------------------------------

TOOL_SCHEMA: dict[str, Any] = {
    "name": "submit_coaching_response",
    "description": "Submit three swim improvement tips and one drill",
    "input_schema": {
        "type": "object",
        "properties": {
            "tips": {
                "type": "array",
                "items": {"type": "string", "maxLength": 300},
                "minItems": 3,
                "maxItems": 3,
            },
            "drill": {"type": "string", "maxLength": 500},
        },
        "required": ["tips", "drill"],
    },
}

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are an elite competitive swim coach with decades of experience at national and Olympic level.\n"
    "Analyse the swimmer's metrics and respond by calling the submit_coaching_response tool with:\n"
    "- tips: exactly three concise, actionable improvement tips (each ≤ 300 characters) based on the metrics\n"
    "- drill: exactly one specific drill recommendation (≤ 500 characters) that targets the swimmer's weakest area\n"
    "Do not add any other fields or commentary outside the tool call."
)

# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class BedrockError(Exception):
    """Raised when the Bedrock invocation fails or returns an invalid response.

    The Lambda handler should map this to HTTP 502.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.http_status = 502


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def invoke_bedrock(metrics: Metrics) -> CoachingResponse:
    """Invoke Amazon Bedrock and return a structured CoachingResponse.

    Args:
        metrics: Swim metrics extracted from the uploaded FIT file.

    Returns:
        A validated CoachingResponse with exactly 3 tips and 1 drill.

    Raises:
        BedrockError: On non-2xx / network failure (immediately), or on schema
                      validation failure after one retry.
    """
    region = os.environ.get("AWS_REGION", "us-east-1")
    client = boto3.client("bedrock-runtime", region_name=region)

    request_body = _build_request_body(metrics)

    # First attempt
    raw_response = _call_bedrock(client, request_body)
    coaching = _parse_response(raw_response)

    if coaching is None:
        logger.warning("Bedrock response failed schema validation; retrying once")
        raw_response = _call_bedrock(client, request_body)
        coaching = _parse_response(raw_response)

    if coaching is None:
        raise BedrockError("AI coach returned an invalid response")

    return coaching


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _build_request_body(metrics: Metrics) -> dict[str, Any]:
    """Construct the Bedrock invoke_model request body."""
    user_message = (
        f"Here are my swim session metrics:\n"
        f"- Pace: {metrics.pace:.1f} seconds per 100 m\n"
        f"- SWOLF: {metrics.swolf:.1f}\n"
        f"- Stroke rate: {metrics.stroke_rate:.1f} strokes per minute\n\n"
        "Please analyse these metrics and provide coaching feedback."
    )

    return {
        "anthropic_version": "bedrock-2023-05-31",
        "system": SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": user_message},
        ],
        "tools": [TOOL_SCHEMA],
        "tool_choice": {"type": "tool", "name": "submit_coaching_response"},
        "max_tokens": 1024,
    }


def _call_bedrock(client: Any, request_body: dict[str, Any]) -> dict[str, Any]:
    """Call bedrock-runtime invoke_model and return the parsed response body.

    Raises:
        BedrockError: On ClientError or any other network/HTTP exception.
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
        raise BedrockError("AI coach unavailable") from exc
    except Exception as exc:
        logger.error("Bedrock network/unknown error: %s", exc)
        raise BedrockError("AI coach unavailable") from exc

    # boto3 invoke_model raises on non-2xx, but guard explicitly for safety
    http_status = response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)
    if http_status != 200:
        logger.error("Bedrock returned HTTP %s", http_status)
        raise BedrockError("AI coach unavailable")

    raw_body = response["body"].read()
    return json.loads(raw_body)


def _parse_response(response_body: dict[str, Any]) -> CoachingResponse | None:
    """Extract and validate the tool-use input from a Bedrock response.

    Returns a CoachingResponse on success, or None if the response is invalid.
    """
    try:
        content = response_body.get("content", [])

        # Find the first tool_use block
        tool_use_block = next(
            (block for block in content if block.get("type") == "tool_use"),
            None,
        )
        if tool_use_block is None:
            logger.warning("No tool_use block found in Bedrock response")
            return None

        tool_input = tool_use_block.get("input", {})
        tips = tool_input.get("tips")
        drill = tool_input.get("drill")

        # Basic structural checks before handing off to CoachingResponse
        if not isinstance(tips, list) or len(tips) != 3:
            logger.warning("Invalid tips in Bedrock response: %r", tips)
            return None
        if not isinstance(drill, str):
            logger.warning("Invalid drill in Bedrock response: %r", drill)
            return None

        # CoachingResponse.__post_init__ enforces full invariants
        return CoachingResponse(tips=tips, drill=drill)

    except (ValueError, TypeError) as exc:
        logger.warning("Failed to construct CoachingResponse: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Training Plan — Tool schema
# ---------------------------------------------------------------------------

TRAINING_PLAN_TOOL_SCHEMA: dict[str, Any] = {
    "name": "submit_training_plan",
    "description": "Submit a structured swim training session plan",
    "input_schema": {
        "type": "object",
        "properties": {
            "session_title": {
                "type": "string",
                "description": "A descriptive title for the training session",
            },
            "warm_up": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of warm-up activities with distances",
            },
            "main_set": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of main set activities with intervals and targets",
            },
            "cool_down": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of cool-down activities",
            },
            "total_distance": {
                "type": "integer",
                "description": "Total session distance in metres",
            },
            "focus_notes": {
                "type": "string",
                "description": "Explanation of what this session targets and why",
            },
        },
        "required": ["session_title", "warm_up", "main_set", "cool_down", "total_distance", "focus_notes"],
    },
}

# ---------------------------------------------------------------------------
# Training Plan — System prompt
# ---------------------------------------------------------------------------

TRAINING_PLAN_SYSTEM_PROMPT = (
    "You are an elite competitive swim coach designing a single training session.\n"
    "Based on the swimmer's current metrics and their stated goal, create a structured "
    "training session plan that is realistic, progressive, and targets their weaknesses.\n"
    "The session should total approximately the requested volume in metres.\n"
    "Respond by calling the submit_training_plan tool with the session details.\n"
    "Do not add any other fields or commentary outside the tool call."
)

# ---------------------------------------------------------------------------
# Training Plan — Public interface
# ---------------------------------------------------------------------------


def generate_training_plan(metrics: Metrics, goal: TrainingGoal) -> TrainingPlan:
    """Generate a structured training session plan using Bedrock.

    Args:
        metrics: Current swim performance metrics.
        goal: The swimmer's training goal (event, target_time, volume, timeframe).

    Returns:
        A validated TrainingPlan.

    Raises:
        BedrockError: On invocation failure or invalid response after retry.
    """
    region = os.environ.get("AWS_REGION", "us-east-1")
    client = boto3.client("bedrock-runtime", region_name=region)

    request_body = _build_training_plan_request(metrics, goal)

    raw_response = _call_bedrock(client, request_body)
    plan = _parse_training_plan_response(raw_response)

    if plan is None:
        logger.warning("Training plan response failed validation; retrying once")
        raw_response = _call_bedrock(client, request_body)
        plan = _parse_training_plan_response(raw_response)

    if plan is None:
        raise BedrockError("AI coach returned an invalid training plan")

    return plan


def _build_training_plan_request(metrics: Metrics, goal: TrainingGoal) -> dict[str, Any]:
    """Construct the Bedrock request body for training plan generation."""
    user_message = (
        f"Here are my current swim metrics:\n"
        f"- Pace: {metrics.pace:.1f} seconds per 100 m\n"
        f"- SWOLF: {metrics.swolf:.1f}\n"
        f"- Stroke rate: {metrics.stroke_rate:.1f} strokes per minute\n\n"
        f"My training goal:\n"
        f"- Target event: {goal.event}\n"
        f"- Target time: {goal.target_time}\n"
        f"- Session volume: {goal.volume_meters} metres\n"
        f"- Timeframe: {goal.timeframe}\n\n"
        "Please design a single training session that helps me work towards this goal."
    )

    return {
        "anthropic_version": "bedrock-2023-05-31",
        "system": TRAINING_PLAN_SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": user_message},
        ],
        "tools": [TRAINING_PLAN_TOOL_SCHEMA],
        "tool_choice": {"type": "tool", "name": "submit_training_plan"},
        "max_tokens": 2048,
    }


def _parse_training_plan_response(response_body: dict[str, Any]) -> TrainingPlan | None:
    """Extract and validate the training plan from a Bedrock response.

    Returns a TrainingPlan on success, or None if the response is invalid.
    """
    try:
        content = response_body.get("content", [])

        tool_use_block = next(
            (block for block in content if block.get("type") == "tool_use"),
            None,
        )
        if tool_use_block is None:
            logger.warning("No tool_use block found in training plan response")
            return None

        tool_input = tool_use_block.get("input", {})

        session_title = tool_input.get("session_title")
        warm_up = tool_input.get("warm_up")
        main_set = tool_input.get("main_set")
        cool_down = tool_input.get("cool_down")
        total_distance = tool_input.get("total_distance")
        focus_notes = tool_input.get("focus_notes")

        # Basic validation
        if not isinstance(session_title, str) or not session_title:
            return None
        if not isinstance(warm_up, list) or not warm_up:
            return None
        if not isinstance(main_set, list) or not main_set:
            return None
        if not isinstance(cool_down, list) or not cool_down:
            return None
        if not isinstance(total_distance, (int, float)) or total_distance <= 0:
            return None
        if not isinstance(focus_notes, str) or not focus_notes:
            return None

        return TrainingPlan(
            session_title=session_title,
            warm_up=warm_up,
            main_set=main_set,
            cool_down=cool_down,
            total_distance=int(total_distance),
            focus_notes=focus_notes,
        )

    except (ValueError, TypeError) as exc:
        logger.warning("Failed to construct TrainingPlan: %s", exc)
        return None
