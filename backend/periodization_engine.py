"""
Periodization Engine for AI Swim Coach.

Builds the Bedrock prompt for multi-week plan generation and validates
the AI-generated plan conforms to periodization rules (progressive overload,
session type variety, recovery weeks).

Requirements: 1.1, 1.3, 1.6, 2.1, 2.2, 2.3, 2.4
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Multi-week plan tool schema for Bedrock tool-use
# ---------------------------------------------------------------------------

MULTI_WEEK_PLAN_TOOL_SCHEMA: dict[str, Any] = {
    "name": "submit_multi_week_plan",
    "description": "Submit a structured multi-week swim training plan",
    "input_schema": {
        "type": "object",
        "properties": {
            "weeks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "week_number": {"type": "integer"},
                        "sessions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "session_title": {"type": "string"},
                                    "session_type": {
                                        "type": "string",
                                        "enum": ["endurance", "speed", "technique", "threshold"],
                                    },
                                    "warm_up": {"type": "array", "items": {"type": "string"}},
                                    "main_set": {"type": "array", "items": {"type": "string"}},
                                    "cool_down": {"type": "array", "items": {"type": "string"}},
                                    "total_distance": {"type": "integer"},
                                    "focus_notes": {"type": "string"},
                                },
                                "required": [
                                    "session_title",
                                    "session_type",
                                    "warm_up",
                                    "main_set",
                                    "cool_down",
                                    "total_distance",
                                    "focus_notes",
                                ],
                            },
                        },
                    },
                    "required": ["week_number", "sessions"],
                },
            }
        },
        "required": ["weeks"],
    },
}

# ---------------------------------------------------------------------------
# Valid session types
# ---------------------------------------------------------------------------

VALID_SESSION_TYPES = {"endurance", "speed", "technique", "threshold"}


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------


def build_plan_prompt(
    event: str,
    target_time: str,
    personal_best_seconds: float | None,
    weeks: int,
    sessions_per_week: int,
) -> str:
    """Build the system prompt for multi-week plan generation.

    The prompt instructs Claude to:
    - Create progressive overload across weeks
    - Vary session types (no two consecutive same type within a week)
    - Include a recovery week for plans >= 6 weeks
    - Structure output as exactly `weeks` week blocks with
      exactly `sessions_per_week` sessions each

    Args:
        event: Target event (e.g., "100m Freestyle")
        target_time: Goal time string (e.g., "0:58.5")
        personal_best_seconds: Current PB in seconds, or None if unknown
        weeks: Number of weeks in the plan (4-12)
        sessions_per_week: Sessions per week (3-5)

    Returns:
        System prompt string for Bedrock invocation.
    """
    pb_context = ""
    if personal_best_seconds is not None:
        minutes = int(personal_best_seconds // 60)
        seconds = personal_best_seconds % 60
        if minutes > 0:
            pb_context = f"The swimmer's current personal best is {minutes}:{seconds:05.2f}."
        else:
            pb_context = f"The swimmer's current personal best is {seconds:.2f} seconds."
    else:
        pb_context = "No personal best is available for this swimmer."

    recovery_instruction = ""
    if weeks >= 6:
        recovery_instruction = (
            "Include at least one recovery week where total distance drops by 20-40% "
            "compared to the preceding week. Place recovery weeks approximately every "
            "3-4 weeks of hard training.\n"
        )

    prompt = (
        "You are an elite competitive swim coach designing a multi-week periodized training plan.\n\n"
        f"Target event: {event}\n"
        f"Target time: {target_time}\n"
        f"{pb_context}\n\n"
        f"Plan structure: {weeks} weeks, {sessions_per_week} sessions per week.\n\n"
        "CONSTRAINTS:\n"
        "1. Progressive overload: Total weekly distance should generally increase over the "
        "plan duration (trend upward), with appropriate recovery periods.\n"
        "2. Session type variety: No two consecutive sessions within the same week should "
        "have the same session_type. Use a mix of endurance, speed, technique, and threshold.\n"
        f"{recovery_instruction}"
        "3. Each session must have a non-empty warm_up, main_set, and cool_down.\n"
        "4. total_distance should be the sum of all distances in the session (warm_up + main_set + cool_down).\n"
        "5. focus_notes should explain what the session targets and how it contributes to the goal.\n\n"
        f"Generate EXACTLY {weeks} weeks, each with EXACTLY {sessions_per_week} sessions.\n"
        "Respond by calling the submit_multi_week_plan tool with the plan details.\n"
        "Do not add any other fields or commentary outside the tool call."
    )

    return prompt


# ---------------------------------------------------------------------------
# Plan structure validation
# ---------------------------------------------------------------------------


def validate_plan_structure(
    plan_data: dict[str, Any],
    weeks: int,
    sessions_per_week: int,
) -> bool:
    """Validate that AI output conforms to the requested plan structure.

    Checks:
    - Correct number of weeks
    - Correct number of sessions per week
    - All required fields present and valid in each session
    - Session types are from the valid set
    - No two consecutive sessions in a week have the same type

    Args:
        plan_data: Parsed plan data from Bedrock tool-use response
        weeks: Expected number of weeks
        sessions_per_week: Expected number of sessions per week

    Returns:
        True if structure is valid, False otherwise.
    """
    week_blocks = plan_data.get("weeks")
    if not isinstance(week_blocks, list):
        logger.warning("Plan data missing 'weeks' list")
        return False

    if len(week_blocks) != weeks:
        logger.warning(
            "Expected %d weeks, got %d", weeks, len(week_blocks)
        )
        return False

    for i, week in enumerate(week_blocks):
        if not isinstance(week, dict):
            logger.warning("Week %d is not a dict", i + 1)
            return False

        week_number = week.get("week_number")
        if not isinstance(week_number, int):
            logger.warning("Week %d has invalid week_number", i + 1)
            return False

        sessions = week.get("sessions")
        if not isinstance(sessions, list):
            logger.warning("Week %d missing 'sessions' list", i + 1)
            return False

        if len(sessions) != sessions_per_week:
            logger.warning(
                "Week %d: expected %d sessions, got %d",
                i + 1,
                sessions_per_week,
                len(sessions),
            )
            return False

        prev_type = None
        for j, session in enumerate(sessions):
            if not _validate_session(session, i + 1, j + 1):
                return False

            session_type = session.get("session_type")
            if session_type == prev_type:
                logger.warning(
                    "Week %d: sessions %d and %d have same type '%s'",
                    i + 1,
                    j,
                    j + 1,
                    session_type,
                )
                return False
            prev_type = session_type

    return True


def _validate_session(session: dict[str, Any], week_num: int, session_num: int) -> bool:
    """Validate a single session has all required fields with correct types."""
    if not isinstance(session, dict):
        logger.warning("Week %d, session %d is not a dict", week_num, session_num)
        return False

    # session_title: non-empty string
    title = session.get("session_title")
    if not isinstance(title, str) or not title.strip():
        logger.warning(
            "Week %d, session %d: invalid session_title", week_num, session_num
        )
        return False

    # session_type: valid enum value
    session_type = session.get("session_type")
    if session_type not in VALID_SESSION_TYPES:
        logger.warning(
            "Week %d, session %d: invalid session_type '%s'",
            week_num,
            session_num,
            session_type,
        )
        return False

    # warm_up: non-empty list of strings
    warm_up = session.get("warm_up")
    if not isinstance(warm_up, list) or not warm_up:
        logger.warning(
            "Week %d, session %d: invalid warm_up", week_num, session_num
        )
        return False
    if not all(isinstance(item, str) for item in warm_up):
        logger.warning(
            "Week %d, session %d: warm_up contains non-string items",
            week_num,
            session_num,
        )
        return False

    # main_set: non-empty list of strings
    main_set = session.get("main_set")
    if not isinstance(main_set, list) or not main_set:
        logger.warning(
            "Week %d, session %d: invalid main_set", week_num, session_num
        )
        return False
    if not all(isinstance(item, str) for item in main_set):
        logger.warning(
            "Week %d, session %d: main_set contains non-string items",
            week_num,
            session_num,
        )
        return False

    # cool_down: non-empty list of strings
    cool_down = session.get("cool_down")
    if not isinstance(cool_down, list) or not cool_down:
        logger.warning(
            "Week %d, session %d: invalid cool_down", week_num, session_num
        )
        return False
    if not all(isinstance(item, str) for item in cool_down):
        logger.warning(
            "Week %d, session %d: cool_down contains non-string items",
            week_num,
            session_num,
        )
        return False

    # total_distance: positive integer
    total_distance = session.get("total_distance")
    if not isinstance(total_distance, (int, float)) or total_distance <= 0:
        logger.warning(
            "Week %d, session %d: invalid total_distance", week_num, session_num
        )
        return False

    # focus_notes: non-empty string
    focus_notes = session.get("focus_notes")
    if not isinstance(focus_notes, str) or not focus_notes.strip():
        logger.warning(
            "Week %d, session %d: invalid focus_notes", week_num, session_num
        )
        return False

    return True
