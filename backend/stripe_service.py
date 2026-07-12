"""
Stripe subscription service for AI Swim Coach.

Handles checkout session creation, billing portal access, and webhook
processing for the £3/month AI Coach Premium subscription.

Environment variables:
    STRIPE_SECRET_KEY: Stripe secret API key
    STRIPE_PRICE_ID: Price ID for the monthly subscription
    STRIPE_WEBHOOK_SECRET: Webhook endpoint signing secret
    PROFILES_TABLE: DynamoDB table name for user profiles
"""
from __future__ import annotations

import logging
import os
from typing import Any

import stripe

logger = logging.getLogger(__name__)

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

PRICE_ID = os.environ.get("STRIPE_PRICE_ID")


def create_checkout_session(
    user_id: str, user_email: str, success_url: str, cancel_url: str
) -> str:
    """Create a Stripe Checkout session for the monthly subscription.

    Args:
        user_id: Internal user ID to attach as client_reference_id.
        user_email: Pre-fills the customer email on the checkout page.
        success_url: Redirect URL after successful payment.
        cancel_url: Redirect URL if the user cancels.

    Returns:
        The checkout session URL to redirect the user to.

    Raises:
        stripe.error.StripeError: On Stripe API failure.
    """
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": PRICE_ID, "quantity": 1}],
        customer_email=user_email,
        client_reference_id=user_id,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"user_id": user_id},
    )
    return session.url


def create_portal_session(customer_id: str, return_url: str) -> str:
    """Create a Stripe Billing Portal session for managing the subscription.

    Args:
        customer_id: The Stripe customer ID.
        return_url: URL to return to after the portal session.

    Returns:
        The billing portal URL.

    Raises:
        stripe.error.StripeError: On Stripe API failure.
    """
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    return session.url


def handle_webhook_event(payload: bytes, sig_header: str) -> dict[str, Any] | None:
    """Verify and process a Stripe webhook event.

    Args:
        payload: Raw request body bytes.
        sig_header: Value of the Stripe-Signature header.

    Returns:
        A dict with {"user_id": ..., "action": "activate"|"deactivate"} if the
        event is subscription-relevant, or None if it should be ignored.

    Raises:
        Exception: If signature is invalid or parsing fails.
    """
    endpoint_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)

    event_type = event.type if hasattr(event, "type") else event.get("type", "")
    data_object = event.data.object if hasattr(event, "data") else event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        # data_object is the checkout Session
        user_id = getattr(data_object, "client_reference_id", None) or (data_object.get("client_reference_id") if isinstance(data_object, dict) else None)
        customer_id = getattr(data_object, "customer", None) or (data_object.get("customer") if isinstance(data_object, dict) else None)
        # Also check metadata
        if not user_id:
            metadata = getattr(data_object, "metadata", None) or (data_object.get("metadata", {}) if isinstance(data_object, dict) else {})
            user_id = metadata.get("user_id") if isinstance(metadata, dict) else getattr(metadata, "user_id", None)
        if user_id and customer_id:
            _store_customer_id(user_id, str(customer_id))
            return {"user_id": str(user_id), "action": "activate"}

    elif event_type in (
        "customer.subscription.deleted",
        "customer.subscription.updated",
    ):
        customer_id = getattr(data_object, "customer", None) or (data_object.get("customer") if isinstance(data_object, dict) else None)
        status = getattr(data_object, "status", None) or (data_object.get("status") if isinstance(data_object, dict) else None)
        if customer_id:
            user_id = _find_user_by_customer_id(str(customer_id))
            if user_id:
                if status in ("canceled", "unpaid", "past_due", "incomplete_expired"):
                    return {"user_id": user_id, "action": "deactivate"}
                elif status == "active":
                    return {"user_id": user_id, "action": "activate"}

    return None


def set_user_tier(user_id: str, tier: str) -> None:
    """Set a user's subscription tier to 'paid' or 'free'.

    Args:
        user_id: The user to update.
        tier: Either "paid" or "free".
    """
    import boto3

    table_name = os.environ.get("PROFILES_TABLE", "UserProfiles")
    table = boto3.resource("dynamodb").Table(table_name)
    table.update_item(
        Key={"user_id": user_id},
        UpdateExpression="SET tier = :t",
        ExpressionAttributeValues={":t": tier},
    )


def _store_customer_id(user_id: str, customer_id: str) -> None:
    """Store Stripe customer ID on the user's profile and activate their tier."""
    import boto3

    table_name = os.environ.get("PROFILES_TABLE", "UserProfiles")
    table = boto3.resource("dynamodb").Table(table_name)
    table.update_item(
        Key={"user_id": user_id},
        UpdateExpression="SET stripe_customer_id = :cid, tier = :t",
        ExpressionAttributeValues={":cid": customer_id, ":t": "paid"},
    )


def _find_user_by_customer_id(customer_id: str) -> str | None:
    """Find user_id by their Stripe customer ID.

    Uses a table scan — acceptable at low subscriber volume. For scale,
    add a GSI on stripe_customer_id.
    """
    import boto3

    table_name = os.environ.get("PROFILES_TABLE", "UserProfiles")
    table = boto3.resource("dynamodb").Table(table_name)
    resp = table.scan(
        FilterExpression="stripe_customer_id = :cid",
        ExpressionAttributeValues={":cid": customer_id},
        ProjectionExpression="user_id",
    )
    items = resp.get("Items", [])
    return items[0]["user_id"] if items else None
