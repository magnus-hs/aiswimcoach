"""
Plan Lifecycle Manager for AI Swim Coach.

Manages state transitions for structured training plans with validation.
Enforces the single-active-plan invariant: at most one plan per user can
have "active" status at any time.

Valid transitions:
    draft  → active
    active → archived

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
"""
from __future__ import annotations

import logging

try:
    import structured_plan_store
except ImportError:
    from backend import structured_plan_store

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Valid state transitions: current_status → set of allowed next statuses
VALID_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"active"},
    "active": {"archived"},
}


def get_plan_status(user_id: str, plan_id: str) -> str:
    """Get the current status of a plan.

    Args:
        user_id: User identifier
        plan_id: Plan identifier

    Returns:
        Current status string ("draft", "active", or "archived")

    Raises:
        ValueError: If the plan is not found
    """
    plan = structured_plan_store.get_plan_by_id(user_id, plan_id)
    if plan is None:
        raise ValueError(f"Plan {plan_id} not found for user {user_id}")
    return plan["status"]


def activate_plan(user_id: str, plan_id: str) -> None:
    """Activate a draft plan. Archives any currently active plan first.

    This enforces the single-active-plan invariant: at most one plan per user
    can be active at any time. If another plan is already active, it will be
    archived before the target plan is activated.

    Args:
        user_id: User identifier
        plan_id: Plan identifier

    Raises:
        ValueError: If the plan is not found or is not in "draft" status
    """
    # Get the target plan and validate its current status
    plan = structured_plan_store.get_plan_by_id(user_id, plan_id)
    if plan is None:
        raise ValueError(f"Plan {plan_id} not found for user {user_id}")

    current_status = plan["status"]
    if "active" not in VALID_TRANSITIONS.get(current_status, set()):
        raise ValueError(
            f"Invalid transition: cannot move from '{current_status}' to 'active'. "
            f"Only plans in 'draft' status can be activated."
        )

    # Archive any currently active plan to enforce single-active invariant
    user_plans = structured_plan_store.get_user_structured_plans(user_id)
    for existing_plan in user_plans:
        if existing_plan["status"] == "active" and existing_plan["plan_id"] != plan_id:
            structured_plan_store.update_plan_status(
                user_id, existing_plan["plan_id"], "archived"
            )
            logger.info(
                "Archived previously active plan %s for user %s",
                existing_plan["plan_id"],
                user_id,
            )

    # Activate the target plan
    structured_plan_store.update_plan_status(user_id, plan_id, "active")
    logger.info("Activated plan %s for user %s", plan_id, user_id)


def archive_plan(user_id: str, plan_id: str) -> None:
    """Archive an active plan.

    Args:
        user_id: User identifier
        plan_id: Plan identifier

    Raises:
        ValueError: If the plan is not found or is not in "active" status
    """
    plan = structured_plan_store.get_plan_by_id(user_id, plan_id)
    if plan is None:
        raise ValueError(f"Plan {plan_id} not found for user {user_id}")

    current_status = plan["status"]
    if "archived" not in VALID_TRANSITIONS.get(current_status, set()):
        raise ValueError(
            f"Invalid transition: cannot move from '{current_status}' to 'archived'. "
            f"Only plans in 'active' status can be archived."
        )

    structured_plan_store.update_plan_status(user_id, plan_id, "archived")
    logger.info("Archived plan %s for user %s", plan_id, user_id)
