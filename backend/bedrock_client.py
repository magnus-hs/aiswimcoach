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

from models import CoachingResponse, Metrics, TrainingGoal, TrainingPlan, AbilityAssessment, UserProfile

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
            "goal_likelihood": {
                "type": "string",
                "description": "Assessment of likelihood of reaching stated goal (achievable/challenging/unrealistic)",
                "maxLength": 300,
            },
        },
        "required": ["session_title", "warm_up", "main_set", "cool_down", "total_distance", "focus_notes", "goal_likelihood"],
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
    "When profile information is provided (age, ability level, locality), tailor the plan accordingly.\n"
    "Evaluate the likelihood of the swimmer reaching their stated goal based on current pace, "
    "the time difference from their goal, and their timeframe.\n"
    "For interval targets in the main set, adjust targets by at least 5% based on the difference "
    "between current pace and goal pace to create progressive training stimuli.\n"
    "Respond by calling the submit_training_plan tool with the session details.\n"
    "Do not add any other fields or commentary outside the tool call."
)

# ---------------------------------------------------------------------------
# Training Plan — Public interface
# ---------------------------------------------------------------------------


def generate_training_plan(
    metrics: Metrics,
    goal: TrainingGoal,
    profile: UserProfile | None = None,
    competitive_analysis: str | None = None,
) -> TrainingPlan:
    """Generate a structured training session plan using Bedrock.

    Args:
        metrics: Current swim performance metrics.
        goal: The swimmer's training goal (event, target_time, volume, timeframe).
        profile: Optional user profile with age, ability_level, locality.
        competitive_analysis: Optional competitive analysis from ability assessment.

    Returns:
        A validated TrainingPlan with goal_likelihood assessment.

    Raises:
        BedrockError: On invocation failure or invalid response after retry.
    
    Requirements: 10.1-10.8, 11.1-11.6
    """
    region = os.environ.get("AWS_REGION", "us-east-1")
    client = boto3.client("bedrock-runtime", region_name=region)

    request_body = _build_training_plan_request(metrics, goal, profile, competitive_analysis)

    raw_response = _call_bedrock(client, request_body)
    plan = _parse_training_plan_response(raw_response)

    if plan is None:
        logger.warning("Training plan response failed validation; retrying once")
        raw_response = _call_bedrock(client, request_body)
        plan = _parse_training_plan_response(raw_response)

    if plan is None:
        raise BedrockError("AI coach returned an invalid training plan")

    return plan


def _build_training_plan_request(
    metrics: Metrics,
    goal: TrainingGoal,
    profile: UserProfile | None = None,
    competitive_analysis: str | None = None,
) -> dict[str, Any]:
    """Construct the Bedrock request body for training plan generation.
    
    Requirements: 10.1-10.7
    """
    user_message = (
        f"Here are my current swim metrics:\n"
        f"- Pace: {metrics.pace:.1f} seconds per 100 m\n"
        f"- SWOLF: {metrics.swolf:.1f}\n"
        f"- Stroke rate: {metrics.stroke_rate:.1f} strokes per minute\n\n"
    )
    
    # Include profile context if available (Requirement 10.1-10.3)
    if profile:
        user_message += (
            f"My profile:\n"
            f"- Age: {profile.age} years\n"
            f"- Ability level: {profile.ability_level}\n"
            f"- Locality: {profile.locality}\n\n"
        )
    
    # Include competitive analysis if available (Requirement 10.4)
    if competitive_analysis:
        user_message += (
            f"My competitive analysis:\n"
            f"{competitive_analysis}\n\n"
        )
    
    user_message += (
        f"My training goal:\n"
        f"- Target event: {goal.event}\n"
        f"- Target time: {goal.target_time}\n"
        f"- Session volume: {goal.volume_meters} metres\n"
        f"- Timeframe: {goal.timeframe}\n\n"
        "Please design a single training session that helps me work towards this goal. "
        "Evaluate the likelihood of me reaching my goal based on my current pace and timeframe. "
        "Adjust interval targets by at least 5% based on the difference between my current pace and goal pace."
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
    
    Requirements: 11.1-11.5
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
        goal_likelihood = tool_input.get("goal_likelihood")

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
        
        # Validate goal_likelihood (Requirement 11.4)
        if not isinstance(goal_likelihood, str) or not goal_likelihood:
            logger.warning("goal_likelihood missing or empty in training plan response")
            return None
        
        # Truncate field if it exceeds max length (defensive coding against AI over-generation)
        goal_likelihood = goal_likelihood[:300]

        return TrainingPlan(
            session_title=session_title,
            warm_up=warm_up,
            main_set=main_set,
            cool_down=cool_down,
            total_distance=int(total_distance),
            focus_notes=focus_notes,
            goal_likelihood=goal_likelihood,
        )

    except (ValueError, TypeError) as exc:
        logger.warning("Failed to construct TrainingPlan: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Ability Assessment — Tool schema
# ---------------------------------------------------------------------------

ABILITY_ASSESSMENT_TOOL_SCHEMA: dict[str, Any] = {
    "name": "submit_ability_assessment",
    "description": "Submit a competitive ability assessment for the swimmer",
    "input_schema": {
        "type": "object",
        "properties": {
            "percentile_estimate": {
                "type": "string",
                "description": "Estimated percentile ranking within age group (e.g., 'top 25%')",
                "maxLength": 100,
            },
            "local_ranking": {
                "type": "string",
                "description": "Estimated local competition ranking in the specified locality",
                "maxLength": 200,
            },
            "national_ranking": {
                "type": "string",
                "description": "Estimated national competition ranking in the specified nationality",
                "maxLength": 200,
            },
            "competitive_analysis": {
                "type": "string",
                "description": "Assessment of how competitive the swimmer is for their age and population context",
                "maxLength": 800,
            },
        },
        "required": ["percentile_estimate", "local_ranking", "national_ranking", "competitive_analysis"],
    },
}

# ---------------------------------------------------------------------------
# Ability Assessment — System prompt
# ---------------------------------------------------------------------------

ABILITY_ASSESSMENT_SYSTEM_PROMPT = (
    "You are an elite competitive swim coach with decades of experience analyzing swimmer performance.\n"
    "Based on the swimmer's profile (age, nationality, locality, ability level) and current metrics "
    "(pace, SWOLF, stroke rate), provide a competitive ability assessment.\n"
    "Respond by calling the submit_ability_assessment tool with:\n"
    "- percentile_estimate: estimated percentile ranking within their age group (≤ 100 chars)\n"
    "- local_ranking: estimated local competition ranking in their locality (≤ 200 chars)\n"
    "- national_ranking: estimated national competition ranking in their country (≤ 200 chars)\n"
    "- competitive_analysis: assessment of competitiveness for their age and population (≤ 800 chars)\n"
    "Do not add any other fields or commentary outside the tool call."
)

# ---------------------------------------------------------------------------
# Ability Assessment — Public interface
# ---------------------------------------------------------------------------


def generate_ability_assessment(
    metrics: Metrics,
    age: int,
    nationality: str,
    locality: str,
    ability_level: str,
) -> AbilityAssessment:
    """Generate a competitive ability assessment using Bedrock.

    Args:
        metrics: Current swim performance metrics.
        age: Swimmer's age.
        nationality: Swimmer's nationality.
        locality: Swimmer's locality/region.
        ability_level: Swimmer's self-assessed ability level.

    Returns:
        A validated AbilityAssessment.

    Raises:
        BedrockError: On invocation failure or invalid response after retry.
    
    Requirements: 7.1, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10, 7.11
    """
    region = os.environ.get("AWS_REGION", "us-east-1")
    client = boto3.client("bedrock-runtime", region_name=region)

    request_body = _build_ability_assessment_request(
        metrics, age, nationality, locality, ability_level
    )

    raw_response = _call_bedrock(client, request_body)
    assessment = _parse_ability_assessment_response(raw_response)

    if assessment is None:
        logger.warning("Ability assessment response failed validation; retrying once")
        raw_response = _call_bedrock(client, request_body)
        assessment = _parse_ability_assessment_response(raw_response)

    if assessment is None:
        raise BedrockError("AI coach unavailable for ability assessment")

    return assessment


def _build_ability_assessment_request(
    metrics: Metrics,
    age: int,
    nationality: str,
    locality: str,
    ability_level: str,
) -> dict[str, Any]:
    """Construct the Bedrock request body for ability assessment generation."""
    user_message = (
        f"Here is my swimmer profile and current metrics:\n\n"
        f"Profile:\n"
        f"- Age: {age} years\n"
        f"- Nationality: {nationality}\n"
        f"- Locality: {locality}\n"
        f"- Ability level: {ability_level}\n\n"
        f"Current metrics:\n"
        f"- Pace: {metrics.pace:.1f} seconds per 100 m\n"
        f"- SWOLF: {metrics.swolf:.1f}\n"
        f"- Stroke rate: {metrics.stroke_rate:.1f} strokes per minute\n\n"
        "Please assess my competitive ability considering my age group and location."
    )

    return {
        "anthropic_version": "bedrock-2023-05-31",
        "system": ABILITY_ASSESSMENT_SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": user_message},
        ],
        "tools": [ABILITY_ASSESSMENT_TOOL_SCHEMA],
        "tool_choice": {"type": "tool", "name": "submit_ability_assessment"},
        "max_tokens": 2048,
    }


def _parse_ability_assessment_response(response_body: dict[str, Any]) -> AbilityAssessment | None:
    """Extract and validate the ability assessment from a Bedrock response.

    Returns an AbilityAssessment on success, or None if the response is invalid.
    
    Requirements: 8.2, 8.3
    """
    try:
        content = response_body.get("content", [])

        tool_use_block = next(
            (block for block in content if block.get("type") == "tool_use"),
            None,
        )
        if tool_use_block is None:
            logger.warning("No tool_use block found in ability assessment response")
            return None

        tool_input = tool_use_block.get("input", {})

        percentile_estimate = tool_input.get("percentile_estimate")
        local_ranking = tool_input.get("local_ranking")
        national_ranking = tool_input.get("national_ranking")
        competitive_analysis = tool_input.get("competitive_analysis")

        # Basic validation before passing to AbilityAssessment constructor
        if not isinstance(percentile_estimate, str) or not percentile_estimate:
            return None
        if not isinstance(local_ranking, str) or not local_ranking:
            return None
        if not isinstance(national_ranking, str) or not national_ranking:
            return None
        if not isinstance(competitive_analysis, str) or not competitive_analysis:
            return None

        # Truncate fields if they exceed max length (defensive coding against AI over-generation)
        percentile_estimate = percentile_estimate[:100]
        local_ranking = local_ranking[:200]
        national_ranking = national_ranking[:200]
        competitive_analysis = competitive_analysis[:800]

        # AbilityAssessment.__post_init__ enforces full invariants
        return AbilityAssessment(
            percentile_estimate=percentile_estimate,
            local_ranking=local_ranking,
            national_ranking=national_ranking,
            competitive_analysis=competitive_analysis,
        )

    except (ValueError, TypeError) as exc:
        logger.warning("Failed to construct AbilityAssessment: %s", exc)
        return None
