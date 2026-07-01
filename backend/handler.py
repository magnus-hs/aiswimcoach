"""
Lambda handler for AI Swim Coach.

Pipeline: parse_multipart → store_in_s3 → parse_fit → extract_session_info
          → invoke_bedrock → save_to_dynamodb (best-effort) → http_200(full_response)

Lambda timeout: 28 seconds (configured in infrastructure — one second under
the API Gateway 29-second integration timeout limit).
"""
from __future__ import annotations

import dataclasses
import json
import logging
import os
from decimal import Decimal
from typing import Any

import boto3

from multipart_parser import ParseError as MultipartParseError  # noqa: E402
from multipart_parser import parse_multipart
from s3_store import StorageError, store_in_s3
from fit_parser import MetricsMissingError
from fit_parser import ParseError as FitParseError
from fit_parser import parse_fit, extract_session_info
from bedrock_client import BedrockError, invoke_bedrock, generate_training_plan, generate_ability_assessment
from dynamo_writer import save_to_dynamodb
from models import FullResponse, Metrics, TrainingGoal, TrainingPlan, UserProfile
from hr_zones import extract_heart_rate_data, calculate_hr_zones, HRDataError
from profile_manager import (
    get_profile,
    save_profile,
    upload_profile_picture,
    StorageError as ProfileStorageError,
)
from auth import AuthenticationError, ConflictError, register_user, login_user, verify_token, get_user_info
from middleware import require_auth
from session_history import get_user_sessions, get_session_by_id, save_session, compute_stroke_breakdown
from training_plan_store import save_training_plan, get_user_plans
from plan_generator import generate_multi_week_plan, PlanGenerationError
from pb_resolver import save_personal_best, get_personal_bests, delete_personal_best, PBResolverError
from plan_lifecycle import activate_plan, archive_plan
from structured_plan_store import get_user_structured_plans, get_plan_by_id
from http_headers import response_headers
from rate_limit import check_rate_limit

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda entry point.

    Routes requests based on httpMethod and path:
      - POST /auth/register → User registration
      - POST /auth/login → User login
      - GET /auth/verify → JWT token verification
      - GET /auth/user → Get user info including profile picture (requires auth)
      - POST /profile → Save user profile (requires auth)
      - GET /profile → Get user profile (requires auth)
      - POST /profile/picture → Upload profile picture (requires auth)
      - GET /sessions → Get user session history (requires auth)
      - GET /sessions/:id → Get session by ID (requires auth)
      - multipart/form-data → FIT file upload pipeline (requires auth)
      - application/json with action "training_plan" → AI training plan generation (requires auth)

    Args:
        event:   API Gateway proxy integration event.
        context: Lambda context object.

    Returns:
        API Gateway proxy integration response dict.
    
    Requirements: 21.5, 21.11, 22.4, 4.7, 16.3, 19.3, 24.1-24.6
    """
    # Extract HTTP method and path
    http_method = event.get("httpMethod", "")
    path = event.get("path", "")
    
    # Handle CORS preflight requests
    if http_method == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": response_headers({
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
                "Access-Control-Max-Age": "86400",
            }),
            "body": ""
        }
    
    # Authentication routes (no auth required) — throttled to resist brute force.
    if path == "/auth/register" and http_method == "POST":
        limited = _enforce_rate_limit(event, "register", 10, 900)
        return limited or _handle_register(event)
    elif path == "/auth/login" and http_method == "POST":
        limited = _enforce_rate_limit(event, "login", 10, 900)
        return limited or _handle_login(event)
    elif path == "/auth/verify" and http_method == "GET":
        return _handle_verify(event)
    elif path == "/auth/user" and http_method == "GET":
        return _handle_get_user_info(event, context)
    elif path == "/auth/reset-request" and http_method == "POST":
        limited = _enforce_rate_limit(event, "reset-request", 5, 900)
        return limited or _handle_reset_request(event)
    elif path == "/auth/reset-password" and http_method == "POST":
        limited = _enforce_rate_limit(event, "reset-password", 10, 900)
        return limited or _handle_reset_password(event)
    elif path == "/auth/google" and http_method == "POST":
        limited = _enforce_rate_limit(event, "google", 20, 900)
        return limited or _handle_google_auth(event)
    
    # Profile routes (auth required)
    elif path == "/profile" and http_method == "POST":
        return _handle_save_profile(event, context)
    elif path == "/profile" and http_method == "GET":
        return _handle_get_profile(event, context)
    elif path == "/profile/picture" and http_method == "POST":
        return _handle_upload_profile_picture(event, context)
    elif path == "/profile/css" and http_method == "POST":
        return _handle_save_css(event, context)
    elif path == "/profile/css" and http_method == "GET":
        return _handle_get_css(event, context)
    elif path == "/profile/goals" and http_method == "POST":
        return _handle_save_goals(event, context)
    elif path == "/profile/goals" and http_method == "GET":
        return _handle_get_goals(event, context)
    elif path == "/profile/assessment" and http_method == "GET":
        return _handle_get_assessment(event, context)
    
    # Structured training plans routes (auth required)
    elif path == "/plans/generate" and http_method == "POST":
        return _handle_generate_structured_plan(event, context)
    elif path == "/plans/structured" and http_method == "GET":
        return _handle_get_structured_plans(event, context)
    elif path.startswith("/plans/") and path.endswith("/status") and http_method == "PATCH":
        plan_id = path.split("/plans/")[1].split("/status")[0]
        event["plan_id"] = plan_id
        return _handle_update_plan_status(event, context)
    elif path.startswith("/plans/") and http_method == "GET" and not path.endswith("/status"):
        plan_id = path.split("/plans/")[1]
        if plan_id and plan_id != "structured" and plan_id != "generate":
            event["plan_id"] = plan_id
            return _handle_get_plan_by_id(event, context)

    # Personal bests routes (auth required)
    elif path == "/personal-bests" and http_method == "POST":
        return _handle_save_personal_best(event, context)
    elif path == "/personal-bests" and http_method == "GET":
        return _handle_get_personal_bests(event, context)
    elif path == "/personal-bests" and http_method == "DELETE":
        return _handle_delete_personal_best(event, context)
    
    # AI chat analysis (auth required)
    elif path == "/ai/chat" and http_method == "POST":
        return _handle_ai_chat(event, context)

    # Training plans route (auth required)
    elif path == "/plans" and http_method == "GET":
        return _handle_get_plans(event, context)
    
    # Session history routes (auth required)
    elif path == "/sessions" and http_method == "GET":
        return _handle_get_sessions(event, context)
    elif path.startswith("/sessions/") and http_method == "GET":
        # Extract session_id from path: /sessions/{session_id}
        session_id = path.split("/sessions/")[-1]
        event["session_id"] = session_id
        return _handle_get_session_by_id(event, context)
    
    # Legacy routes based on Content-Type for file upload and training plan
    else:
        content_type = (event.get("headers") or {}).get("content-type", "") or \
                       (event.get("headers") or {}).get("Content-Type", "")

        if "application/json" in content_type:
            return _handle_training_plan(event, context)

        return _handle_file_upload(event, context)


def _handle_register(event: dict[str, Any]) -> dict[str, Any]:
    """Handle POST /auth/register endpoint.
    
    Registers a new user with email and password.
    
    Request body (JSON):
        {
            "email": "user@example.com",
            "password": "securepassword123"
        }
    
    Response (201):
        {
            "user_id": "uuid-v4-string",
            "email": "user@example.com"
        }
    
    Errors:
        400: Invalid email or password (doesn't meet requirements)
        409: Email already registered
        500: Server error
    
    Requirements: 21.5-21.9
    """
    import base64
    
    try:
        body = event.get("body")
        if not body:
            return _error_response(400, "Request body is required")
        if event.get("isBase64Encoded"):
            body = base64.b64decode(body).decode("utf-8")
        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError) as exc:
        return _error_response(400, f"Invalid JSON body: {exc}")
    
    email = payload.get("email")
    password = payload.get("password")
    
    if not email or not password:
        return _error_response(400, "Missing 'email' or 'password' in request body")
    
    try:
        result = register_user(email, password)
        return {
            "statusCode": 201,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(result),
        }
    except ValueError as exc:
        return _error_response(400, str(exc))
    except ConflictError as exc:
        return _error_response(409, str(exc))
    except Exception as exc:
        logger.error("Registration failed: %s", exc)
        return _error_response(500, "Registration failed")


def _handle_login(event: dict[str, Any]) -> dict[str, Any]:
    """Handle POST /auth/login endpoint.
    
    Authenticates user and returns JWT token.
    
    Request body (JSON):
        {
            "email": "user@example.com",
            "password": "securepassword123"
        }
    
    Response (200):
        {
            "token": "jwt-token-string",
            "user_id": "uuid-v4-string",
            "email": "user@example.com"
        }
    
    Errors:
        400: Invalid request body
        401: Invalid credentials
        500: Server error
    
    Requirements: 21.11-21.18
    """
    import base64
    
    try:
        body = event.get("body")
        if not body:
            return _error_response(400, "Request body is required")
        if event.get("isBase64Encoded"):
            body = base64.b64decode(body).decode("utf-8")
        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError) as exc:
        return _error_response(400, f"Invalid JSON body: {exc}")
    
    email = payload.get("email")
    password = payload.get("password")
    
    if not email or not password:
        return _error_response(400, "Missing 'email' or 'password' in request body")
    
    try:
        result = login_user(email, password)
        return http_200_dict(result)
    except AuthenticationError as exc:
        return _error_response(401, str(exc))
    except Exception as exc:
        logger.error("Login failed: %s", exc)
        return _error_response(500, "Login failed")


def _handle_verify(event: dict[str, Any]) -> dict[str, Any]:
    """Handle GET /auth/verify endpoint.
    
    Verifies JWT token from Authorization header and returns user claims.
    
    Request headers:
        Authorization: Bearer <jwt-token>
    
    Response (200):
        {
            "user_id": "uuid-v4-string",
            "email": "user@example.com"
        }
    
    Errors:
        401: Missing, invalid, or expired token
        500: Server error
    
    Requirements: 21.21-21.22
    """
    # Extract token from Authorization header
    headers = event.get("headers") or {}
    auth_header = headers.get("Authorization") or headers.get("authorization")
    
    if not auth_header:
        return _error_response(401, "Missing Authorization header")
    
    # Expected format: "Bearer <token>"
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return _error_response(401, "Invalid Authorization header format. Expected: Bearer <token>")
    
    token = parts[1]
    
    try:
        claims = verify_token(token)
        return http_200_dict(claims)
    except AuthenticationError as exc:
        return _error_response(401, str(exc))
    except Exception as exc:
        logger.error("Token verification failed: %s", exc)
        return _error_response(500, "Token verification failed")


def _handle_reset_request(event: dict[str, Any]) -> dict[str, Any]:
    """Handle POST /auth/reset-request — generate a reset token for the user."""
    import secrets

    # Identical response for both existing and non-existing accounts to avoid
    # user enumeration.
    neutral_response = http_200_dict(
        {"message": "If an account exists, a reset token has been generated"}
    )

    try:
        body = json.loads(event.get("body") or "{}")
    except (json.JSONDecodeError, TypeError):
        return _error_response(400, "Invalid JSON body")
    
    email = body.get("email", "").strip().lower()
    if not email:
        return _error_response(400, "Email is required")
    
    # Look up user by email
    users_table = os.environ.get("USERS_TABLE", "ai-swim-coach-users")
    table = boto3.resource("dynamodb").Table(users_table)
    
    try:
        response = table.query(
            IndexName="email-index",
            KeyConditionExpression=boto3.dynamodb.conditions.Key("email").eq(email),
        )
        items = response.get("Items", [])
    except Exception as exc:
        logger.error("Reset request lookup failed: %s", exc)
        return neutral_response
    
    if not items:
        return neutral_response
    
    # Generate a cryptographically-random token (not the predictable `random`).
    token = secrets.token_hex(4)  # 8 hex chars ≈ 4.3 billion combinations
    
    # Store token with 15-min expiry
    from datetime import datetime, timezone, timedelta
    expiry = datetime.now(tz=timezone.utc) + timedelta(minutes=15)
    
    user_item = items[0]
    try:
        table.update_item(
            Key={"user_id": user_item["user_id"]},
            UpdateExpression="SET reset_token = :t, reset_token_expiry = :e",
            ExpressionAttributeValues={
                ":t": token,
                ":e": expiry.isoformat(),
            },
        )
    except Exception as exc:
        logger.error("Failed to store reset token: %s", exc)
        return _error_response(500, "Failed to generate reset token")
    
    # In production, this would be emailed.
    logger.info("Reset token for %s: %s (expires %s)", email, token, expiry.isoformat())
    
    return neutral_response


def _handle_reset_password(event: dict[str, Any]) -> dict[str, Any]:
    """Handle POST /auth/reset-password — verify token and set new password."""
    from auth import hash_password
    
    try:
        body = json.loads(event.get("body") or "{}")
    except (json.JSONDecodeError, TypeError):
        return _error_response(400, "Invalid JSON body")
    
    email = body.get("email", "").strip().lower()
    token = body.get("token", "").strip()
    new_password = body.get("new_password", "")
    
    if not email or not token or not new_password:
        return _error_response(400, "Email, token, and new_password are required")
    
    if len(new_password) < 8:
        return _error_response(400, "Password must be at least 8 characters")
    
    # Look up user
    users_table = os.environ.get("USERS_TABLE", "ai-swim-coach-users")
    table = boto3.resource("dynamodb").Table(users_table)
    
    try:
        response = table.query(
            IndexName="email-index",
            KeyConditionExpression=boto3.dynamodb.conditions.Key("email").eq(email),
        )
        items = response.get("Items", [])
    except Exception as exc:
        logger.error("Reset password lookup failed: %s", exc)
        return _error_response(500, "Password reset failed")
    
    if not items:
        return _error_response(400, "Invalid email or token")
    
    user_item = items[0]
    stored_token = user_item.get("reset_token")
    stored_expiry = user_item.get("reset_token_expiry")
    
    import secrets as _secrets
    if not stored_token or not _secrets.compare_digest(str(stored_token), token):
        return _error_response(400, "Invalid or expired reset token")
    
    # Check expiry
    from datetime import datetime, timezone
    if stored_expiry:
        expiry = datetime.fromisoformat(stored_expiry)
        if datetime.now(tz=timezone.utc) > expiry:
            return _error_response(400, "Reset token has expired")
    
    # Update password and clear token. NOTE: login reads `hashed_password`,
    # so the reset MUST write to that same attribute (not `password_hash`).
    hashed = hash_password(new_password)
    try:
        table.update_item(
            Key={"user_id": user_item["user_id"]},
            UpdateExpression="SET hashed_password = :p REMOVE reset_token, reset_token_expiry",
            ExpressionAttributeValues={":p": hashed},
        )
    except Exception as exc:
        logger.error("Password update failed: %s", exc)
        return _error_response(500, "Password reset failed")
    
    return http_200_dict({"message": "Password reset successfully"})


def _handle_google_auth(event: dict[str, Any]) -> dict[str, Any]:
    """Handle POST /auth/google — verify Google ID token and issue JWT.
    
    Flow:
    1. Receive Google ID token from frontend
    2. Verify token with Google's public keys
    3. Extract email from token claims
    4. Find or create user in DynamoDB
    5. Issue our app's JWT token
    """
    import urllib.request
    import urllib.parse
    import uuid
    from datetime import datetime, timezone
    from auth import generate_jwt_token
    
    try:
        body = json.loads(event.get("body") or "{}")
    except (json.JSONDecodeError, TypeError):
        return _error_response(400, "Invalid JSON body")
    
    id_token = body.get("id_token")
    if not id_token:
        return _error_response(400, "Missing id_token")
    
    # Verify the Google ID token against Google's tokeninfo endpoint. This
    # validates the cryptographic SIGNATURE, issuer and expiry server-side.
    # (Decoding the JWT payload locally without verifying the signature would
    # let anyone forge a token and take over any account.)
    expected_client_id = "315548660280-922flu5u39917s66qn51fu0u1s0gelrc.apps.googleusercontent.com"
    try:
        query = urllib.parse.urlencode({"id_token": id_token})
        req = urllib.request.Request(
            f"https://oauth2.googleapis.com/tokeninfo?{query}",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status != 200:
                return _error_response(401, "Invalid Google token")
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        logger.warning("Google token verification failed: %s", exc)
        return _error_response(401, "Invalid Google token")

    # Validate the Google-verified claims.
    iss = payload.get("iss")
    if iss not in ("accounts.google.com", "https://accounts.google.com"):
        return _error_response(401, "Invalid token issuer")

    if payload.get("aud") != expected_client_id:
        return _error_response(401, "Invalid token audience")

    import time
    try:
        if time.time() > int(payload.get("exp", 0)):
            return _error_response(401, "Token expired")
    except (ValueError, TypeError):
        return _error_response(401, "Invalid Google token")

    google_email = (payload.get("email") or "").lower()
    if not google_email:
        return _error_response(401, "No email in Google token")

    if str(payload.get("email_verified", "")).lower() != "true":
        return _error_response(401, "Email not verified by Google")
    
    # Find or create user
    users_table = os.environ.get("USERS_TABLE", "ai-swim-coach-users")
    table = boto3.resource("dynamodb").Table(users_table)
    
    try:
        response = table.query(
            IndexName="email-index",
            KeyConditionExpression=boto3.dynamodb.conditions.Key("email").eq(google_email),
        )
        items = response.get("Items", [])
        
        if items:
            # Existing user — issue token
            user_item = items[0]
            user_id = user_item["user_id"]
        else:
            # New user — create account
            user_id = str(uuid.uuid4())
            now = datetime.now(tz=timezone.utc)
            table.put_item(Item={
                "user_id": user_id,
                "email": google_email,
                "password_hash": "GOOGLE_AUTH",  # No password for Google users
                "created_at": now.isoformat(),
                "auth_provider": "google",
            })
            logger.info("Created new Google user: %s (%s)", user_id, google_email)
        
        # Generate our JWT
        token = generate_jwt_token(user_id, google_email)
        
        return http_200_dict({
            "token": token,
            "user_id": user_id,
            "email": google_email,
        })
    
    except Exception as exc:
        logger.error("Google auth user lookup/create failed: %s", exc)
        return _error_response(500, "Authentication failed")


@require_auth
def _handle_get_user_info(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle GET /auth/user endpoint.
    
    Retrieves user information including profile picture URL.
    
    Response (200):
        {
            "user_id": "uuid-v4-string",
            "email": "user@example.com",
            "profile_picture_url": "https://bucket.s3.amazonaws.com/...",
            "created_at": "2024-01-01T00:00:00.000Z"
        }
    
    Errors:
        401: Missing or invalid token
        404: User not found
        500: Server error
    
    Requirements: 24.1-24.6
    """
    user_id = event["auth_context"]["user_id"]
    
    try:
        user_info = get_user_info(user_id)
        return http_200_dict(user_info)
    except AuthenticationError as exc:
        return _error_response(404, str(exc))
    except Exception as exc:
        logger.error("Failed to retrieve user info for user %s: %s", user_id, exc)
        return _error_response(500, "Failed to retrieve user information")


@require_auth
def _handle_training_plan(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle a JSON training plan generation request.
    
    Requirements: 10.1-10.8, 11.1-11.6
    """
    import base64

    try:
        body = event.get("body")
        if not body:
            return _error_response(400, "Request body is required")
        if event.get("isBase64Encoded"):
            body = base64.b64decode(body).decode("utf-8")
        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError) as exc:
        return _error_response(400, f"Invalid JSON body: {exc}")

    action = payload.get("action")
    if action != "training_plan":
        return _error_response(400, f"Unknown action: {action}")

    metrics_data = payload.get("metrics")
    goal_data = payload.get("goal")

    if not metrics_data or not goal_data:
        return _error_response(400, "Missing 'metrics' or 'goal' in request body")

    try:
        metrics = Metrics(
            pace=float(metrics_data["pace"]),
            swolf=float(metrics_data["swolf"]),
            stroke_rate=float(metrics_data["stroke_rate"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        return _error_response(400, f"Invalid metrics: {exc}")

    try:
        goal = TrainingGoal(
            event=str(goal_data["event"]),
            target_time=str(goal_data["target_time"]),
            volume_meters=int(goal_data["volume_meters"]),
            timeframe=str(goal_data["timeframe"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        return _error_response(400, f"Invalid goal: {exc}")

    # Check if user is authenticated and retrieve profile (best-effort)
    # Requirements: 10.1-10.5
    profile = None
    ability_assessment_competitive_analysis = None
    
    auth_context = event.get("auth_context")
    if auth_context:
        user_id = auth_context.get("user_id")
        if user_id:
            try:
                profile = get_profile(user_id)
                if profile:
                    logger.info("Retrieved profile for user %s for training plan generation", user_id)
            except ProfileStorageError as exc:
                # Profile retrieval failed - log and continue without profile
                logger.warning("Profile retrieval failed for user %s: %s", user_id, exc)
            except Exception as exc:
                # Unexpected error - log and continue without profile
                logger.error("Unexpected error retrieving profile for user %s: %s", user_id, exc)

    try:
        plan = generate_training_plan(
            metrics=metrics,
            goal=goal,
            profile=profile,
            competitive_analysis=ability_assessment_competitive_analysis,
        )
    except BedrockError as exc:
        logger.error("Bedrock training plan failed: %s", exc)
        return _error_response(502, str(exc))

    # Save the plan to DynamoDB (best-effort, don't fail if save fails)
    if auth_context and auth_context.get("user_id"):
        try:
            import dataclasses as dc
            plan_dict = dc.asdict(plan)
            goal_dict = dc.asdict(goal)
            save_training_plan(auth_context["user_id"], goal_dict, plan_dict)
            logger.info("Training plan saved for user %s", auth_context["user_id"])
        except Exception as exc:
            logger.warning("Failed to save training plan for user %s: %s", auth_context["user_id"], exc)

    return http_200(plan)


@require_auth
def _handle_file_upload(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle the FIT file upload pipeline.

    Pipeline: parse_multipart → store_in_s3 → parse_fit → extract_session_info
              → invoke_bedrock → save_to_dynamodb (best-effort) → http_200(full_response)
    
    Requires authentication to save sessions to user's history.
    """
    try:
        # 1. Parse multipart body
        fit_bytes = parse_multipart(event)
    except MultipartParseError as exc:
        logger.warning("Multipart parse failed: %s", exc)
        return _error_response(400, str(exc))

    try:
        # 2. Store in S3
        s3_key = store_in_s3(fit_bytes)
    except StorageError as exc:
        logger.error("S3 storage failed: %s", exc)
        return _error_response(500, "Failed to store file")

    try:
        # 3. Parse FIT file for metrics
        metrics = parse_fit(fit_bytes)
    except FitParseError as exc:
        logger.warning("FIT parse error: %s", exc)
        return _error_response(422, exc.message)
    except MetricsMissingError as exc:
        logger.warning("Missing metrics: %s", exc.missing)
        return _error_response(422, str(exc))

    try:
        # 4. Extract session info and splits
        session_info, splits = extract_session_info(fit_bytes)
    except FitParseError as exc:
        logger.warning("FIT session parse error: %s", exc)
        return _error_response(422, exc.message)

    try:
        # 5. Build session context for richer AI coaching
        session_context: dict[str, Any] = {
            "total_distance_m": session_info.total_distance_m,
            "total_time_seconds": session_info.total_time_seconds,
            "num_lengths": session_info.num_lengths,
        }
        
        # Compute SWOLF drift and set count from splits
        if splits:
            valid_splits = [s for s in splits if s.strokes > 0 and s.time_seconds > 0]
            session_context["num_sets"] = sum(1 for s in splits if s.rest_after_seconds is not None) + 1
            
            if len(valid_splits) >= 4:
                # SWOLF for first and last quarter
                quarter = max(1, len(valid_splits) // 4)
                first_swolfs = [s.time_seconds + s.strokes for s in valid_splits[:quarter]]
                last_swolfs = [s.time_seconds + s.strokes for s in valid_splits[-quarter:]]
                avg_first = sum(first_swolfs) / len(first_swolfs)
                avg_last = sum(last_swolfs) / len(last_swolfs)
                session_context["swolf_drift"] = round(avg_last - avg_first, 1)

        # Invoke Bedrock with enriched context
        coaching = invoke_bedrock(metrics, session_context)
    except BedrockError as exc:
        logger.error("Bedrock invocation failed: %s", exc)
        return _error_response(502, str(exc))

    # 6. Persist to DynamoDB (best-effort — failure must not block the response)
    try:
        save_to_dynamodb(s3_key, metrics, coaching)
    except Exception as exc:
        logger.error("DynamoDB write failed for %s: %s", s3_key, exc)

    # 6.5. Calculate HR zones if user has profile with age (best-effort)
    # Requirements: 12.1-12.7
    hr_zones = None
    hr_timeseries = None
    
    # Extract HR time series from FIT file (independent of profile/age)
    try:
        hr_samples = extract_heart_rate_data(fit_bytes)
        if hr_samples and len(hr_samples) > 2:
            start_ts = hr_samples[0][0]
            hr_timeseries = []
            last_added_sec = -10  # force first point
            for ts, hr in hr_samples:
                elapsed_sec = (ts - start_ts).total_seconds()
                if elapsed_sec - last_added_sec >= 5:
                    hr_timeseries.append({"t": round(elapsed_sec, 0), "hr": hr})
                    last_added_sec = elapsed_sec
            # Always include last point
            last_ts, last_hr = hr_samples[-1]
            final_sec = (last_ts - start_ts).total_seconds()
            if final_sec > last_added_sec:
                hr_timeseries.append({"t": round(final_sec, 0), "hr": last_hr})
            logger.info("HR timeseries extracted: %d points", len(hr_timeseries))
    except (HRDataError, Exception) as exc:
        logger.warning("HR timeseries extraction failed: %s", exc)
        hr_samples = []
    
    # Check if user is authenticated
    auth_context = event.get("auth_context")
    if auth_context:
        user_id = auth_context.get("user_id")
        
        if user_id:
            try:
                # Retrieve user profile
                profile = get_profile(user_id)
                
                # If profile exists and has age, calculate HR zones
                if profile and profile.age:
                    try:
                        # Calculate HR zones if we have heart rate data
                        if hr_samples:
                            hr_zones = calculate_hr_zones(hr_samples, profile.age)
                            logger.info("HR zones calculated successfully for user %s", user_id)
                        else:
                            logger.info("No heart rate data found in FIT file for user %s", user_id)
                    
                    except (HRDataError, ValueError) as exc:
                        # HR zone calculation failed - log and continue without HR zones
                        logger.warning("HR zone calculation failed for user %s: %s", user_id, exc)
                    
                else:
                    logger.info("User %s has no profile or age - skipping HR zones", user_id)
            
            except ProfileStorageError as exc:
                # Profile retrieval failed - log and continue without HR zones
                logger.warning("Profile retrieval failed for user %s: %s", user_id, exc)
            
            except Exception as exc:
                # Unexpected error - log and continue without HR zones
                logger.error("Unexpected error during HR zones calculation for user %s: %s", user_id, exc)

    # 6.6. Generate ability assessment if user has complete profile (best-effort)
    # Requirements: 7.1-7.12
    ability_assessment = None
    
    if auth_context:
        user_id = auth_context.get("user_id")
        
        if user_id:
            try:
                # Retrieve user profile (may have already been fetched for HR zones)
                profile = get_profile(user_id)
                
                # Check if profile is COMPLETE: all fields populated
                # Requirement 7.1: Only generate if age, nationality, locality, ability_level all present
                if profile and profile.age and profile.nationality and profile.locality and profile.ability_level:
                    # Check if metrics are valid (finite numbers)
                    import math
                    if (math.isfinite(metrics.pace) and 
                        math.isfinite(metrics.swolf) and 
                        math.isfinite(metrics.stroke_rate)):
                        
                        try:
                            # Compute average metrics from last 3 sessions + current for form-based assessment
                            from models import Metrics as MetricsClass
                            recent_sessions = get_user_sessions(user_id)[:2]  # Last 2 + current = 3
                            
                            paces = [metrics.pace]
                            swolfs = [metrics.swolf]
                            rates = [metrics.stroke_rate]
                            for s in recent_sessions:
                                if s.average_pace_per_100m > 0:
                                    paces.append(s.average_pace_per_100m)
                                if s.swolf_score > 0:
                                    swolfs.append(float(s.swolf_score))
                                if s.stroke_rate > 0:
                                    rates.append(s.stroke_rate)
                            
                            avg_metrics = MetricsClass(
                                pace=sum(paces) / len(paces),
                                swolf=sum(swolfs) / len(swolfs),
                                stroke_rate=sum(rates) / len(rates),
                            )
                            
                            # Generate ability assessment based on recent form
                            ability_assessment = generate_ability_assessment(
                                metrics=avg_metrics,
                                age=profile.age,
                                nationality=profile.nationality,
                                locality=profile.locality,
                                ability_level=profile.ability_level,
                            )
                            logger.info("Ability assessment generated (based on %d sessions) for user %s", len(paces), user_id)
                            
                            # Persist the assessment to the profile for the Ability Assessment page
                            try:
                                import dataclasses as dc
                                table_name = os.environ.get("PROFILES_TABLE", "UserProfiles")
                                table = boto3.resource("dynamodb").Table(table_name)
                                table.update_item(
                                    Key={"user_id": user_id},
                                    UpdateExpression="SET ability_assessment = :aa",
                                    ExpressionAttributeValues={":aa": dc.asdict(ability_assessment)},
                                )
                            except Exception as exc2:
                                logger.warning("Failed to persist ability assessment: %s", exc2)
                        
                        except BedrockError as exc:
                            logger.warning("Ability assessment generation failed for user %s: %s", user_id, exc)
                    
                    else:
                        logger.info("Metrics contain non-finite values - skipping ability assessment for user %s", user_id)
                
                else:
                    logger.info("User %s has incomplete profile - skipping ability assessment", user_id)
            
            except ProfileStorageError as exc:
                # Profile retrieval failed - log and continue without ability assessment
                logger.warning("Profile retrieval failed for user %s: %s", user_id, exc)
            
            except Exception as exc:
                # Unexpected error - log and continue without ability assessment
                logger.error("Unexpected error during ability assessment generation for user %s: %s", user_id, exc)

    # 7. Save session to history (best-effort - requires auth)
    # Requirements: 20.1-20.7
    session_id = None
    
    if auth_context:
        user_id = auth_context.get("user_id")
        
        if user_id:
            try:
                # Save session with all available data
                session_id = save_session(
                    user_id=user_id,
                    session_info=session_info,
                    metrics=metrics,
                    s3_key=s3_key,
                    hr_zones=hr_zones,
                    ability_assessment=ability_assessment,
                    splits=[dataclasses.asdict(s) for s in splits] if splits else None,
                    coaching=dataclasses.asdict(coaching) if coaching else None,
                    hr_timeseries=hr_timeseries if hr_timeseries else None,
                )
                logger.info("Session saved successfully: %s for user %s", session_id, user_id)
            
            except Exception as exc:
                # Session save failure is best-effort - log but don't block response
                # Requirement 20.6: Session save failures should not prevent coaching results delivery
                logger.error("Session save failed for user %s: %s", user_id, exc)
                # Continue without session_id - user still gets coaching results

    # 8. Return full response
    full_response = FullResponse(
        session=session_info,
        splits=splits,
        metrics=metrics,
        coaching=coaching,
        hr_zones=hr_zones,
        ability_assessment=ability_assessment,
        session_id=session_id,
        hr_timeseries=hr_timeseries,
    )
    return http_200(full_response)


# ---------------------------------------------------------------------------
# Profile handlers (require authentication)
# ---------------------------------------------------------------------------


@require_auth
def _handle_save_profile(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle POST /profile endpoint.
    
    Saves user profile information.
    
    Request body (JSON):
        {
            "age": 25,
            "nationality": "USA",
            "locality": "California",
            "ability_level": "intermediate"
        }
    
    Response (200):
        {
            "message": "Profile saved successfully"
        }
    
    Errors:
        400: Invalid profile data
        500: Profile storage failure
    
    Requirements: 4.7
    """
    import base64
    
    user_id = event["auth_context"]["user_id"]
    
    try:
        body = event.get("body")
        if not body:
            return _error_response(400, "Request body is required")
        if event.get("isBase64Encoded"):
            body = base64.b64decode(body).decode("utf-8")
        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError) as exc:
        return _error_response(400, f"Invalid JSON body: {exc}")
    
    try:
        profile = UserProfile(
            age=int(payload["age"]),
            nationality=payload.get("nationality", ""),
            locality=payload.get("locality", ""),
            ability_level=payload["ability_level"],
        )
    except (KeyError, ValueError, TypeError) as exc:
        return _error_response(400, f"Invalid profile data: {exc}")
    
    try:
        save_profile(user_id, profile)
        
        # Store date_of_birth if provided (additional field not in UserProfile model)
        dob = payload.get("date_of_birth")
        if dob:
            table_name = os.environ.get("PROFILES_TABLE", "UserProfiles")
            table = boto3.resource("dynamodb").Table(table_name)
            table.update_item(
                Key={"user_id": user_id},
                UpdateExpression="SET date_of_birth = :dob",
                ExpressionAttributeValues={":dob": dob},
            )
        
        return http_200_dict({"message": "Profile saved successfully"})
    except ProfileStorageError as exc:
        logger.error("Profile save failed for user %s: %s", user_id, exc)
        return _error_response(500, "Profile storage failure")
    except Exception as exc:
        logger.error("Profile save failed for user %s: %s", user_id, exc)
        return _error_response(500, "Internal server error")


@require_auth
def _handle_get_profile(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle GET /profile endpoint.
    
    Retrieves user profile information.
    
    Response (200):
        {
            "age": 25,
            "nationality": "USA",
            "locality": "California",
            "ability_level": "intermediate"
        }
    
    Errors:
        404: Profile not found
        500: Profile retrieval failure
    
    Requirements: 4.7
    """
    user_id = event["auth_context"]["user_id"]
    
    try:
        profile = get_profile(user_id)
        if profile is None:
            return _error_response(404, "Profile not found")
        
        profile_dict = {
            "age": profile.age,
            "nationality": profile.nationality,
            "locality": profile.locality,
            "ability_level": profile.ability_level,
        }
        
        # Also fetch date_of_birth if stored
        try:
            table_name = os.environ.get("PROFILES_TABLE", "UserProfiles")
            table = boto3.resource("dynamodb").Table(table_name)
            response = table.get_item(Key={"user_id": user_id}, ProjectionExpression="date_of_birth")
            dob = response.get("Item", {}).get("date_of_birth")
            if dob:
                profile_dict["date_of_birth"] = dob
        except Exception:
            pass
        
        return http_200_dict(profile_dict)
    except ProfileStorageError as exc:
        logger.error("Profile retrieval failed for user %s: %s", user_id, exc)
        return _error_response(500, "Profile retrieval failure")
    except Exception as exc:
        logger.error("Profile retrieval failed for user %s: %s", user_id, exc)
        return _error_response(500, "Internal server error")


@require_auth
def _handle_save_css(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle POST /profile/css — save CSS pace."""
    user_id = event["auth_context"]["user_id"]
    try:
        body = json.loads(event.get("body") or "{}")
    except (json.JSONDecodeError, TypeError):
        return _error_response(400, "Invalid JSON body")

    css_pace = body.get("css_pace_per_100m")
    if css_pace is None or not isinstance(css_pace, (int, float)) or css_pace <= 0:
        return _error_response(400, "css_pace_per_100m must be a positive number")

    table_name = os.environ.get("PROFILES_TABLE", "UserProfiles")
    try:
        table = boto3.resource("dynamodb").Table(table_name)
        table.update_item(
            Key={"user_id": user_id},
            UpdateExpression="SET css_pace_per_100m = :val",
            ExpressionAttributeValues={":val": Decimal(str(round(float(css_pace), 1)))},
        )
        return http_200_dict({"message": "CSS saved", "css_pace_per_100m": float(css_pace)})
    except Exception as exc:
        logger.error("Failed to save CSS for user %s: %s", user_id, exc)
        return _error_response(500, "Failed to save CSS")


@require_auth
def _handle_get_css(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle GET /profile/css — retrieve CSS pace."""
    user_id = event["auth_context"]["user_id"]
    table_name = os.environ.get("PROFILES_TABLE", "UserProfiles")
    try:
        table = boto3.resource("dynamodb").Table(table_name)
        response = table.get_item(
            Key={"user_id": user_id},
            ProjectionExpression="css_pace_per_100m",
        )
        item = response.get("Item", {})
        css_val = item.get("css_pace_per_100m")
        css_pace = float(css_val) if css_val is not None else None
        return http_200_dict({"css_pace_per_100m": css_pace})
    except Exception as exc:
        logger.error("Failed to get CSS for user %s: %s", user_id, exc)
        return _error_response(500, "Failed to retrieve CSS")


def _goals_to_json(goals: dict | None) -> dict:
    """Convert a stored goals map (with Decimals) into JSON-friendly types."""
    if not goals:
        return {}
    out: dict[str, Any] = {}
    focus = goals.get("focus")
    if isinstance(focus, list):
        out["focus"] = [str(x) for x in focus]
    if goals.get("weekly_distance_m") is not None:
        out["weekly_distance_m"] = int(goals["weekly_distance_m"])
    if goals.get("monthly_distance_m") is not None:
        out["monthly_distance_m"] = int(goals["monthly_distance_m"])
    if goals.get("yearly_distance_m") is not None:
        out["yearly_distance_m"] = int(goals["yearly_distance_m"])
    if goals.get("target_event"):
        out["target_event"] = str(goals["target_event"])
    if goals.get("target_time_seconds") is not None:
        out["target_time_seconds"] = float(goals["target_time_seconds"])
    if goals.get("target_date"):
        out["target_date"] = str(goals["target_date"])
    if goals.get("notes"):
        out["notes"] = str(goals["notes"])
    return out


@require_auth
def _handle_save_goals(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle POST /profile/goals — save the swimmer's goals."""
    user_id = event["auth_context"]["user_id"]
    try:
        body = json.loads(event.get("body") or "{}")
    except (json.JSONDecodeError, TypeError):
        return _error_response(400, "Invalid JSON body")

    goals = body.get("goals")
    if not isinstance(goals, dict):
        return _error_response(400, "goals must be an object")

    item: dict[str, Any] = {}

    focus = goals.get("focus")
    if isinstance(focus, list):
        item["focus"] = [str(x)[:40] for x in focus][:12]

    wd = goals.get("weekly_distance_m")
    if wd is not None:
        try:
            wdf = float(wd)
            if wdf > 0:
                item["weekly_distance_m"] = Decimal(str(int(wdf)))
        except (ValueError, TypeError):
            pass

    md = goals.get("monthly_distance_m")
    if md is not None:
        try:
            mdf = float(md)
            if mdf > 0:
                item["monthly_distance_m"] = Decimal(str(int(mdf)))
        except (ValueError, TypeError):
            pass

    yd = goals.get("yearly_distance_m")
    if yd is not None:
        try:
            ydf = float(yd)
            if ydf > 0:
                item["yearly_distance_m"] = Decimal(str(int(ydf)))
        except (ValueError, TypeError):
            pass

    te = goals.get("target_event")
    if te:
        item["target_event"] = str(te)[:60]

    tt = goals.get("target_time_seconds")
    if tt is not None:
        try:
            ttf = float(tt)
            if ttf > 0:
                item["target_time_seconds"] = Decimal(str(round(ttf, 2)))
        except (ValueError, TypeError):
            pass

    td = goals.get("target_date")
    if td:
        item["target_date"] = str(td)[:20]

    notes = goals.get("notes")
    if notes:
        item["notes"] = str(notes)[:500]

    table_name = os.environ.get("PROFILES_TABLE", "UserProfiles")
    try:
        table = boto3.resource("dynamodb").Table(table_name)
        table.update_item(
            Key={"user_id": user_id},
            UpdateExpression="SET goals = :val",
            ExpressionAttributeValues={":val": item},
        )
        return http_200_dict({"message": "Goals saved", "goals": _goals_to_json(item)})
    except Exception as exc:
        logger.error("Failed to save goals for user %s: %s", user_id, exc)
        return _error_response(500, "Failed to save goals")


@require_auth
def _handle_get_goals(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle GET /profile/goals — retrieve the swimmer's goals."""
    user_id = event["auth_context"]["user_id"]
    table_name = os.environ.get("PROFILES_TABLE", "UserProfiles")
    try:
        table = boto3.resource("dynamodb").Table(table_name)
        response = table.get_item(
            Key={"user_id": user_id},
            ProjectionExpression="goals",
        )
        item = response.get("Item", {})
        return http_200_dict({"goals": _goals_to_json(item.get("goals"))})
    except Exception as exc:
        logger.error("Failed to get goals for user %s: %s", user_id, exc)
        return _error_response(500, "Failed to retrieve goals")


@require_auth
def _handle_get_assessment(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle GET /profile/assessment — retrieve ability assessment and time standards."""
    user_id = event["auth_context"]["user_id"]
    table_name = os.environ.get("PROFILES_TABLE", "UserProfiles")
    
    try:
        table = boto3.resource("dynamodb").Table(table_name)
        response = table.get_item(Key={"user_id": user_id})
        item = response.get("Item", {})
        
        assessment = item.get("ability_assessment")
        age = item.get("age")
        
        # Build time standards for the user's age group
        standards = None
        age_group = ""
        if age:
            from swim_standards import get_age_group, MASTERS_STANDARDS
            age_group = get_age_group(int(age))
            
            def fmt_time(secs: float) -> str:
                m = int(secs) // 60
                s = secs % 60
                return f"{m}:{s:04.1f}" if m > 0 else f"{s:.1f}s"
            
            british_free = MASTERS_STANDARDS.get("male", {}).get(age_group, {})
            
            # Stroke multipliers relative to freestyle
            stroke_multipliers = {
                "Freestyle": 1.0,
                "Backstroke": 1.08,
                "Breaststroke": 1.18,
                "Butterfly": 1.05,
                "IM": 1.10,
            }
            
            # Distances available per stroke
            distances_per_stroke = {
                "Freestyle": ["50m", "100m", "200m", "400m", "800m", "1500m"],
                "Backstroke": ["50m", "100m", "200m"],
                "Breaststroke": ["50m", "100m", "200m"],
                "Butterfly": ["50m", "100m", "200m"],
                "IM": ["100m", "200m", "400m"],
            }
            
            # Build British and Scottish standards for all strokes
            british_all = []
            scottish_all = []
            
            for stroke_name, mult in stroke_multipliers.items():
                for dist in distances_per_stroke.get(stroke_name, []):
                    # Find base freestyle time for this distance
                    free_key = f"{dist} Freestyle"
                    base = british_free.get(free_key)
                    if not base:
                        # Estimate 800m and 1500m from 400m
                        base_400 = british_free.get("400m Freestyle")
                        if base_400 and dist == "800m":
                            base = {k: v * 2.08 for k, v in base_400.items()}
                        elif base_400 and dist == "1500m":
                            base = {k: v * 3.95 for k, v in base_400.items()}
                        else:
                            continue
                    
                    event_name = f"{dist} {stroke_name}"
                    levels = {k: v * mult for k, v in base.items()}
                    british_all.append({
                        "event": event_name,
                        "national": fmt_time(levels["national"]),
                        "regional": fmt_time(levels["regional"]),
                        "county": fmt_time(levels["county"]),
                        "club": fmt_time(levels["club"]),
                    })
                    # Scottish ~2% slower
                    scottish_all.append({
                        "event": event_name,
                        "national": fmt_time(levels["national"] * 1.01),
                        "regional": fmt_time(levels["regional"] * 1.02),
                        "county": fmt_time(levels["county"] * 1.03),
                        "club": fmt_time(levels["club"] * 1.02),
                    })
            
            # Open water standards (estimated from pool times + 8-12% for conditions)
            ow_events = {
                "Open Water 1 mile": 1609 / 100,   # ~16 × 100m pace
                "Open Water 2km": 2000 / 100,
                "Open Water 3km": 3000 / 100,
                "Open Water 5km": 5000 / 100,
                "Open Water 10km": 10000 / 100,
            }
            ow_standards = []
            base_100 = british_free.get("100m Freestyle")
            if base_100:
                for ow_event, multiplier in ow_events.items():
                    # Open water is ~10% slower than pool pace at 100m, plus fatigue
                    fatigue = 1.0 + (multiplier / 200)  # gradual fatigue factor
                    ow_levels = {k: v * multiplier * 1.10 * fatigue for k, v in base_100.items()}
                    ow_standards.append({
                        "event": ow_event,
                        "national": fmt_time(ow_levels["national"]),
                        "regional": fmt_time(ow_levels["regional"]),
                        "county": fmt_time(ow_levels["county"]),
                        "club": fmt_time(ow_levels["club"]),
                    })
            
            standards = {
                "british": british_all,
                "scottish": scottish_all,
                "openwater": ow_standards,
            }
        
        return http_200_dict({
            "assessment": assessment,
            "standards": standards,
            "age_group": age_group,
        })
    except Exception as exc:
        logger.error("Failed to get assessment for user %s: %s", user_id, exc)
        return _error_response(500, "Failed to retrieve assessment")


@require_auth
def _handle_ai_chat(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle POST /ai/chat — interactive AI coaching chat.
    
    Accepts a user prompt and optional session context. Fetches all user sessions
    to provide trend analysis. Returns AI-generated response text.
    """
    user_id = event["auth_context"]["user_id"]
    
    try:
        body = json.loads(event.get("body") or "{}")
    except (json.JSONDecodeError, TypeError):
        return _error_response(400, "Invalid JSON body")
    
    prompt = body.get("prompt", "").strip()
    if not prompt:
        return _error_response(400, "Missing prompt")
    
    current_session = body.get("current_session")  # Optional: current session data
    intents = body.get("intents") or []  # Optional: coaching focus categories
    
    # Fetch all user sessions for trend analysis
    try:
        sessions = get_user_sessions(user_id)
    except Exception:
        sessions = []
    
    # Fetch CSS pace and profile
    css_pace = None
    profile_info = ""
    goals_data = None
    try:
        table_name = os.environ.get("PROFILES_TABLE", "UserProfiles")
        table = boto3.resource("dynamodb").Table(table_name)
        response = table.get_item(Key={"user_id": user_id})
        item = response.get("Item", {})
        css_val = item.get("css_pace_per_100m")
        if css_val is not None:
            css_pace = float(css_val)
        goals_data = item.get("goals")
        # Get profile info for age group comparisons
        age = item.get("age")
        nationality = item.get("nationality")
        ability_level = item.get("ability_level")
        if age:
            profile_info = f"\nSwimmer Profile: Age {age}"
            if nationality:
                profile_info += f", Nationality: {nationality}"
            if ability_level:
                profile_info += f", Level: {ability_level}"
            profile_info += "\n"
            
            # Add swimming time standards for their age group
            from swim_standards import get_standards_for_swimmer, classify_time
            standards_text = get_standards_for_swimmer(int(age), "male")
            if standards_text:
                profile_info += standards_text + "\n"
            
            # Pre-compute classifications from their actual session data
            if sessions:
                avg_pace = sum(s.average_pace_per_100m for s in sessions[:10]) / min(len(sessions), 10)
                # Estimate race times from training pace
                est_100m = avg_pace - 5  # Race is faster than training
                est_200m = (avg_pace - 2) * 2
                est_400m = (avg_pace + 2) * 4
                
                profile_info += f"\nPRE-COMPUTED CLASSIFICATIONS (use these, do NOT recalculate):\n"
                profile_info += f"  Average training pace: {avg_pace:.1f}s/100m ({int(avg_pace)//60}:{int(avg_pace)%60:02d}/100m)\n"
                profile_info += f"  Estimated 100m race time: {est_100m:.0f}s ({int(est_100m)//60}:{int(est_100m)%60:02d}) → {classify_time(int(age), '100m Freestyle', est_100m)}\n"
                profile_info += f"  Estimated 200m race time: {est_200m:.0f}s ({int(est_200m)//60}:{int(est_200m)%60:02d}) → {classify_time(int(age), '200m Freestyle', est_200m)}\n"
                profile_info += f"  Estimated 400m race time: {est_400m:.0f}s ({int(est_400m)//60}:{int(est_400m)%60:02d}) → {classify_time(int(age), '400m Freestyle', est_400m)}\n"
    except Exception:
        pass
    
    # Build session history summary for the AI
    history_summary = ""
    if sessions:
        history_summary = f"\n\nSession History ({len(sessions)} sessions):\n"
        for s in sessions[:20]:  # Last 20 sessions
            history_summary += (
                f"- {s.session_date[:10]}: {s.total_distance_meters}m, "
                f"pace {s.average_pace_per_100m:.1f}s/100m, "
                f"SWOLF {s.swolf_score}, "
                f"stroke rate {s.stroke_rate:.1f} spm, "
                f"{s.stroke_type}\n"
            )
    
    # Build current session context if provided
    session_detail = ""
    if current_session:
        session_detail = f"\n\nCurrent Session Details:\n"
        if current_session.get("total_distance_m"):
            session_detail += f"- Distance: {current_session['total_distance_m']}m\n"
        if current_session.get("pace"):
            session_detail += f"- Pace: {current_session['pace']:.1f}s/100m\n"
        if current_session.get("swolf"):
            session_detail += f"- SWOLF: {current_session['swolf']}\n"
        if current_session.get("stroke_rate"):
            session_detail += f"- Stroke rate: {current_session['stroke_rate']:.1f} spm\n"
    
    css_info = ""
    if css_pace:
        css_info = (
            f"\nCSS (threshold/training) pace: {css_pace:.1f}s/100m "
            f"({int(css_pace)//60}:{int(css_pace)%60:02d}/100m)\n"
            f"IMPORTANT: CSS is a TRAINING pace, not a race time. "
            f"Estimated race times from this CSS:\n"
            f"  - 100m race: ~{css_pace - 5:.0f}s ({int((css_pace-5)//60)}:{int((css_pace-5)%60):02d})\n"
            f"  - 200m race: ~{(css_pace - 2) * 2:.0f}s ({int(((css_pace-2)*2)//60)}:{int(((css_pace-2)*2)%60):02d})\n"
            f"  - 400m race: ~{(css_pace + 2) * 4:.0f}s ({int(((css_pace+2)*4)//60)}:{int(((css_pace+2)*4)%60):02d})\n"
        )

    # Build coaching-intent focus guidance from the categories the swimmer selected.
    intent_info = ""
    if intents:
        intent_guidance = {
            "technique": "Stroke technique and efficiency (distance-per-stroke, SWOLF, stroke rate).",
            "endurance": "Aerobic endurance and building a distance base.",
            "speed": "Speed and sprint development (short, fast efforts).",
            "threshold": "Threshold / CSS improvement and race-pace work.",
            "race_prep": "Race preparation, pacing strategy, and tapering.",
            "recovery": "Recovery, injury prevention, and managing training load.",
            "fitness": "General fitness, health, and weight management.",
            "open_water": "Open water swimming skills and preparation.",
        }
        lines = [intent_guidance.get(str(i), str(i)) for i in intents]
        intent_info = (
            "\n\nThe swimmer has selected these coaching focus areas. "
            "Tailor and prioritise your answer around them:\n"
            + "\n".join(f"- {line}" for line in lines)
            + "\n"
        )

    # Build goals guidance so the AI can assess how close/far the swimmer is.
    goals_info = ""
    if goals_data:
        goal_focus_labels = {
            "endurance": "Build endurance / swim further",
            "speed": "Get faster (sprint speed)",
            "technique": "Improve technique & efficiency",
            "css": "Improve CSS / threshold",
            "race": "Prepare for a race / event",
            "consistency": "Swim more consistently",
            "weight": "Fitness & weight management",
            "open_water": "Open water swimming",
        }
        parts = ["\n\nThe swimmer has set the following GOALS. Assess how close or far they are "
                 "from each goal using their session data, and give concrete steps to close the gap:\n"]
        focus = goals_data.get("focus")
        if isinstance(focus, list) and focus:
            readable = [goal_focus_labels.get(str(f), str(f)) for f in focus]
            parts.append(f"- Focus: {', '.join(readable)}\n")
        wd = goals_data.get("weekly_distance_m")
        if wd is not None:
            try:
                wdf = float(wd)
                # Compute distance swum in the current (Mon-Sun) week.
                from datetime import datetime as _dt, timezone as _tz, timedelta as _td
                now = _dt.now(tz=_tz.utc)
                week_start = (now - _td(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
                week_distance = 0
                for s in sessions:
                    try:
                        sd = _dt.fromisoformat(s.session_date.replace("Z", "+00:00"))
                        if sd.tzinfo is None:
                            sd = sd.replace(tzinfo=_tz.utc)
                        if sd >= week_start:
                            week_distance += s.total_distance_meters
                    except (ValueError, AttributeError):
                        pass
                pct = (week_distance / wdf * 100) if wdf > 0 else 0
                parts.append(
                    f"- Weekly distance goal: {int(wdf)}m ({wdf/1000:.1f} km). "
                    f"So far this week: {week_distance}m ({pct:.0f}% of goal).\n"
                )
            except (ValueError, TypeError):
                pass

        md = goals_data.get("monthly_distance_m")
        if md is not None:
            try:
                mdf = float(md)
                from datetime import datetime as _dt, timezone as _tz
                now = _dt.now(tz=_tz.utc)
                month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                month_distance = 0
                for s in sessions:
                    try:
                        sd = _dt.fromisoformat(s.session_date.replace("Z", "+00:00"))
                        if sd.tzinfo is None:
                            sd = sd.replace(tzinfo=_tz.utc)
                        if sd >= month_start:
                            month_distance += s.total_distance_meters
                    except (ValueError, AttributeError):
                        pass
                pct = (month_distance / mdf * 100) if mdf > 0 else 0
                parts.append(
                    f"- Monthly distance goal: {int(mdf)}m ({mdf/1000:.1f} km). "
                    f"So far this month: {month_distance}m ({pct:.0f}% of goal).\n"
                )
            except (ValueError, TypeError):
                pass

        yd = goals_data.get("yearly_distance_m")
        if yd is not None:
            try:
                ydf = float(yd)
                from datetime import datetime as _dt, timezone as _tz
                now = _dt.now(tz=_tz.utc)
                year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                year_distance = 0
                for s in sessions:
                    try:
                        sd = _dt.fromisoformat(s.session_date.replace("Z", "+00:00"))
                        if sd.tzinfo is None:
                            sd = sd.replace(tzinfo=_tz.utc)
                        if sd >= year_start:
                            year_distance += s.total_distance_meters
                    except (ValueError, AttributeError):
                        pass
                pct = (year_distance / ydf * 100) if ydf > 0 else 0
                parts.append(
                    f"- Yearly distance goal: {int(ydf)}m ({ydf/1000:.1f} km). "
                    f"So far this year: {year_distance}m ({pct:.0f}% of goal).\n"
                )
            except (ValueError, TypeError):
                pass
        te = goals_data.get("target_event")
        tt = goals_data.get("target_time_seconds")
        if te and tt is not None:
            try:
                ttf = float(tt)
                parts.append(
                    f"- Target event: {te} in {int(ttf)//60}:{int(ttf)%60:02d} ({ttf:.1f}s)\n"
                )
            except (ValueError, TypeError):
                parts.append(f"- Target event: {te}\n")
        elif te:
            parts.append(f"- Target event: {te}\n")
        td = goals_data.get("target_date")
        if td:
            parts.append(f"- Target date: {td}\n")
        notes = goals_data.get("notes")
        if notes:
            parts.append(f"- Additional notes: {notes}\n")
        goals_info = "".join(parts)
    
    # Call Bedrock
    system_prompt = (
        "You are an elite competitive swim coach analysing a swimmer's training data.\n"
        "You have access to their full session history, current session details, profile, CSS pace, "
        "and official Masters Swimming time standards for their age group.\n\n"
        "CRITICAL: CSS pace is a TRAINING pace (threshold), NOT a race time. "
        "Race times are typically 3-8 seconds per 100m faster than CSS depending on distance. "
        "When comparing to standards, use the ESTIMATED RACE TIMES and PRE-COMPUTED CLASSIFICATIONS provided. "
        "Do NOT do your own time arithmetic or conversions — use the pre-computed values exactly as given.\n\n"
        "When the swimmer's time standards table is provided, use THOSE EXACT NUMBERS for comparisons. "
        "Do not invent or estimate different times — reference the table directly.\n\n"
        "Provide insightful, specific analysis based on the data. Identify trends, strengths, "
        "weaknesses, and give concrete advice on how to improve and reach their targets.\n\n"
        "If the swimmer has set GOALS, explicitly assess how close or far they are from each goal "
        "using their data (e.g. weekly distance progress, gap to target race time), and give clear "
        "steps to close the gap.\n\n"
        "Keep your response concise (2-4 paragraphs) but data-driven. Reference specific numbers "
        "from their sessions and the standards table when making points.\n"
        "Do not use markdown formatting — respond in plain text with line breaks for readability."
    )
    
    user_message = f"{prompt}{intent_info}{goals_info}{profile_info}{css_info}{session_detail}{history_summary}"
    
    try:
        region = os.environ.get("AWS_REGION", "us-east-1")
        client = boto3.client("bedrock-runtime", region_name=region)
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
            "max_tokens": 1024,
        }
        
        response = client.invoke_model(
            modelId="us.anthropic.claude-haiku-4-5-20251001-v1:0",
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json",
        )
        
        result = json.loads(response["body"].read())
        content = result.get("content", [])
        text = ""
        for block in content:
            if block.get("type") == "text":
                text += block.get("text", "")
        
        return http_200_dict({"response": text})
    
    except Exception as exc:
        logger.error("AI chat failed for user %s: %s", user_id, exc)
        return _error_response(502, "AI analysis unavailable")


@require_auth
def _handle_upload_profile_picture(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle POST /profile/picture endpoint.
    
    Uploads user profile picture to S3.
    
    Request: multipart/form-data with image file
    
    Response (200):
        {
            "url": "https://bucket.s3.amazonaws.com/user_id_timestamp.jpg"
        }
    
    Errors:
        400: Invalid image format
        413: File too large (>2MB)
        500: Upload failure
    
    Requirements: 23.4, 23.11
    """
    user_id = event["auth_context"]["user_id"]
    
    try:
        # Parse multipart body to get image bytes
        image_bytes = parse_multipart(event)
    except MultipartParseError as exc:
        logger.warning("Multipart parse failed: %s", exc)
        return _error_response(400, str(exc))
    
    # Determine content type (default to image/jpeg if not specified)
    content_type = "image/jpeg"
    headers = event.get("headers") or {}
    ct = headers.get("content-type") or headers.get("Content-Type") or ""
    if "image/" in ct:
        # Extract the image type from multipart boundary
        # For simplicity, we'll infer from file magic bytes in upload_profile_picture
        content_type = ct.split(";")[0].strip()
    
    try:
        s3_url = upload_profile_picture(user_id, image_bytes, content_type)
        return http_200_dict({"url": s3_url})
    except ValueError as exc:
        # Check if it's a file size error
        if "exceeds" in str(exc):
            return _error_response(413, str(exc))
        return _error_response(400, str(exc))
    except ProfileStorageError as exc:
        logger.error("Profile picture upload failed for user %s: %s", user_id, exc)
        return _error_response(500, "Profile picture upload failure")
    except Exception as exc:
        logger.error("Profile picture upload failed for user %s: %s", user_id, exc)
        return _error_response(500, "Internal server error")


# ---------------------------------------------------------------------------
# Training plan history handler (requires authentication)
# ---------------------------------------------------------------------------


@require_auth
def _handle_get_plans(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle GET /plans endpoint.

    Retrieves user's saved training plans ordered by created_at descending.

    Response (200):
        {
            "plans": [
                {
                    "plan_id": "uuid",
                    "created_at": "2024-01-15T10:00:00+00:00",
                    "goal": {"event": "100m freestyle", "target_time": "1:00", ...},
                    "plan": {"session_title": "...", "warm_up": [...], ...}
                },
                ...
            ]
        }

    Errors:
        500: Plan retrieval failure
    """
    user_id = event["auth_context"]["user_id"]

    try:
        plans = get_user_plans(user_id)
        return http_200_dict({"plans": plans})
    except Exception as exc:
        logger.error("Plan retrieval failed for user %s: %s", user_id, exc)
        return _error_response(500, "Plan retrieval failure")


# ---------------------------------------------------------------------------
# Structured training plan handlers (require authentication)
# ---------------------------------------------------------------------------


@require_auth
def _handle_generate_structured_plan(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle POST /plans/generate endpoint.

    Generates a multi-week structured training plan.

    Request body (JSON):
        {
            "event": "100m Freestyle",
            "target_time": "0:58.5",
            "weeks": 8,
            "sessions_per_week": 3
        }

    Response (200):
        {
            "plan_id": "uuid",
            "status": "draft",
            "goal": {...},
            "duration_weeks": 8,
            "sessions_per_week": 3,
            "weeks": [...]
        }

    Errors:
        400: Invalid input parameters
        502: Plan generation failure
    """
    import base64

    user_id = event["auth_context"]["user_id"]

    try:
        body = event.get("body")
        if not body:
            return _error_response(400, "Request body is required")
        if event.get("isBase64Encoded"):
            body = base64.b64decode(body).decode("utf-8")
        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError) as exc:
        return _error_response(400, f"Invalid JSON body: {exc}")

    plan_event = payload.get("event")
    target_time = payload.get("target_time")
    weeks = payload.get("weeks")
    sessions_per_week = payload.get("sessions_per_week", 3)

    if not plan_event:
        return _error_response(400, "Missing 'event' in request body")
    if not target_time:
        return _error_response(400, "Missing 'target_time' in request body")
    if weeks is None:
        return _error_response(400, "Missing 'weeks' in request body")

    try:
        weeks = int(weeks)
        sessions_per_week = int(sessions_per_week)
    except (TypeError, ValueError) as exc:
        return _error_response(400, f"Invalid numeric parameter: {exc}")

    try:
        plan = generate_multi_week_plan(
            user_id=user_id,
            event=plan_event,
            target_time=target_time,
            weeks=weeks,
            sessions_per_week=sessions_per_week,
        )
        return http_200_dict(plan)
    except ValueError as exc:
        return _error_response(400, str(exc))
    except PlanGenerationError as exc:
        logger.error("Plan generation failed for user %s: %s", user_id, exc)
        return _error_response(exc.http_status, str(exc))
    except Exception as exc:
        logger.error("Unexpected error generating plan for user %s: %s", user_id, exc)
        return _error_response(502, "Plan generation failed")


@require_auth
def _handle_get_structured_plans(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle GET /plans/structured endpoint.

    Retrieves user's structured multi-week training plans.

    Response (200):
        {
            "plans": [
                {
                    "plan_id": "uuid",
                    "created_at": "2024-...",
                    "status": "draft",
                    "goal": {...},
                    "duration_weeks": 8,
                    "sessions_per_week": 3
                },
                ...
            ]
        }

    Errors:
        500: Plan retrieval failure
    """
    user_id = event["auth_context"]["user_id"]

    try:
        plans = get_user_structured_plans(user_id)
        return http_200_dict({"plans": plans})
    except Exception as exc:
        logger.error("Structured plan retrieval failed for user %s: %s", user_id, exc)
        return _error_response(500, "Plan retrieval failure")


@require_auth
def _handle_get_plan_by_id(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle GET /plans/<plan_id> endpoint.

    Retrieves a complete structured plan by ID.

    Response (200):
        {
            "plan_id": "uuid",
            "status": "draft",
            "goal": {...},
            "duration_weeks": 8,
            "sessions_per_week": 3,
            "weeks": [...]
        }

    Errors:
        404: Plan not found
        500: Plan retrieval failure
    """
    user_id = event["auth_context"]["user_id"]
    plan_id = event.get("plan_id")

    if not plan_id:
        return _error_response(400, "Missing plan_id")

    try:
        plan = get_plan_by_id(user_id, plan_id)
        if plan is None:
            return _error_response(404, "Plan not found")
        return http_200_dict(plan)
    except Exception as exc:
        logger.error("Plan retrieval failed for plan %s: %s", plan_id, exc)
        return _error_response(500, "Plan retrieval failure")


@require_auth
def _handle_update_plan_status(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle PATCH /plans/<plan_id>/status endpoint.

    Updates plan status (activate or archive).

    Request body (JSON):
        {
            "status": "active" | "archived"
        }

    Response (200):
        {
            "message": "Plan status updated",
            "plan_id": "uuid",
            "status": "active"
        }

    Errors:
        400: Invalid status or transition
        404: Plan not found
        500: Update failure
    """
    import base64

    user_id = event["auth_context"]["user_id"]
    plan_id = event.get("plan_id")

    if not plan_id:
        return _error_response(400, "Missing plan_id")

    try:
        body = event.get("body")
        if not body:
            return _error_response(400, "Request body is required")
        if event.get("isBase64Encoded"):
            body = base64.b64decode(body).decode("utf-8")
        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError) as exc:
        return _error_response(400, f"Invalid JSON body: {exc}")

    new_status = payload.get("status")
    if new_status not in ("active", "archived"):
        return _error_response(400, "status must be 'active' or 'archived'")

    try:
        if new_status == "active":
            activate_plan(user_id, plan_id)
        else:
            archive_plan(user_id, plan_id)

        return http_200_dict({
            "message": "Plan status updated",
            "plan_id": plan_id,
            "status": new_status,
        })
    except ValueError as exc:
        return _error_response(400, str(exc))
    except Exception as exc:
        logger.error("Plan status update failed for plan %s: %s", plan_id, exc)
        return _error_response(500, "Plan status update failure")


@require_auth
def _handle_save_personal_best(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle POST /personal-bests endpoint.

    Saves a manually entered personal best.

    Request body (JSON):
        {
            "event": "100m Freestyle",
            "time_seconds": 65.5
        }

    Response (200):
        {
            "message": "Personal best saved",
            "event": "100m Freestyle",
            "time_seconds": 65.5
        }

    Errors:
        400: Invalid input
        500: Save failure
    """
    import base64

    user_id = event["auth_context"]["user_id"]

    try:
        body = event.get("body")
        if not body:
            return _error_response(400, "Request body is required")
        if event.get("isBase64Encoded"):
            body = base64.b64decode(body).decode("utf-8")
        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError) as exc:
        return _error_response(400, f"Invalid JSON body: {exc}")

    pb_event = payload.get("event")
    time_seconds = payload.get("time_seconds")

    if not pb_event:
        return _error_response(400, "Missing 'event' in request body")
    if time_seconds is None:
        return _error_response(400, "Missing 'time_seconds' in request body")

    try:
        time_seconds = float(time_seconds)
    except (TypeError, ValueError):
        return _error_response(400, "time_seconds must be a number")

    try:
        save_personal_best(user_id, pb_event, time_seconds)
        return http_200_dict({
            "message": "Personal best saved",
            "event": pb_event,
            "time_seconds": time_seconds,
        })
    except ValueError as exc:
        return _error_response(400, str(exc))
    except PBResolverError as exc:
        logger.error("PB save failed for user %s: %s", user_id, exc)
        return _error_response(500, "Failed to save personal best")
    except Exception as exc:
        logger.error("Unexpected error saving PB for user %s: %s", user_id, exc)
        return _error_response(500, "Failed to save personal best")


@require_auth
def _handle_get_personal_bests(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle GET /personal-bests endpoint.

    Retrieves all personal bests (manual + derived) for the user.

    Response (200):
        {
            "personal_bests": [
                {
                    "event": "100m Freestyle",
                    "time_seconds": 65.5,
                    "source": "manual",
                    "updated_at": "2024-..."
                },
                ...
            ]
        }

    Errors:
        500: Retrieval failure
    """
    user_id = event["auth_context"]["user_id"]

    try:
        pbs = get_personal_bests(user_id)
        return http_200_dict({"personal_bests": pbs})
    except PBResolverError as exc:
        logger.error("PB retrieval failed for user %s: %s", user_id, exc)
        return _error_response(500, "Failed to retrieve personal bests")
    except Exception as exc:
        logger.error("Unexpected error retrieving PBs for user %s: %s", user_id, exc)
        return _error_response(500, "Failed to retrieve personal bests")


@require_auth
def _handle_delete_personal_best(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle DELETE /personal-bests endpoint.

    Deletes a manually entered personal best by event name.

    Request body:
        { "event": "100m Freestyle" }

    Errors:
        400: Missing event field
        500: Deletion failure
    """
    user_id = event["auth_context"]["user_id"]

    try:
        body = json.loads(event.get("body") or "{}")
    except (json.JSONDecodeError, TypeError):
        return _error_response(400, "Invalid JSON body")

    event_name = body.get("event", "").strip()
    if not event_name:
        return _error_response(400, "Missing required field: event")

    try:
        delete_personal_best(user_id, event_name)
        return http_200_dict({"message": "Personal best deleted"})
    except PBResolverError as exc:
        logger.error("PB deletion failed for user %s: %s", user_id, exc)
        return _error_response(500, "Failed to delete personal best")
    except Exception as exc:
        logger.error("Unexpected error deleting PB for user %s: %s", user_id, exc)
        return _error_response(500, "Failed to delete personal best")


# ---------------------------------------------------------------------------
# Session history handlers (require authentication)
# ---------------------------------------------------------------------------


@require_auth
def _handle_get_sessions(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle GET /sessions endpoint.
    
    Retrieves user's session history with optional date range filtering.
    
    Query parameters (optional):
        - start_date: ISO 8601 date (inclusive)
        - end_date: ISO 8601 date (inclusive)
    
    Response (200):
        {
            "sessions": [
                {
                    "session_id": "uuid",
                    "session_date": "2024-01-15T10:00:00Z",
                    "pool_length_meters": 25,
                    "total_distance_meters": 2000,
                    "total_time_seconds": 2400,
                    "stroke_type": "freestyle",
                    "average_pace_per_100m": 120.0,
                    "swolf_score": 45,
                    "stroke_rate": 30.0,
                    "uploaded_at": "2024-01-15T11:00:00Z",
                    "s3_key": "uploads/file.fit",
                    "hr_zones": {...},
                    "ability_assessment": {...}
                },
                ...
            ]
        }
    
    Errors:
        500: Session retrieval failure
    
    Requirements: 16.3
    """
    user_id = event["auth_context"]["user_id"]
    
    # Extract optional query parameters
    query_params = event.get("queryStringParameters") or {}
    start_date = query_params.get("start_date")
    end_date = query_params.get("end_date")
    
    try:
        sessions = get_user_sessions(user_id, start_date, end_date)
        
        # Convert Session objects to dicts
        sessions_data = [dataclasses.asdict(session) for session in sessions]

        # Add a per-stroke percentage breakdown for the activity feed.
        for session_obj, session_dict in zip(sessions, sessions_data):
            session_dict["stroke_breakdown"] = compute_stroke_breakdown(
                session_dict.get("splits"), session_obj.stroke_type
            )

        return http_200_dict({"sessions": sessions_data})
    except Exception as exc:
        logger.error("Session retrieval failed for user %s: %s", user_id, exc)
        return _error_response(500, "Session retrieval failure")


@require_auth
def _handle_get_session_by_id(
    event: dict[str, Any],
    context: Any,
) -> dict[str, Any]:
    """Handle GET /sessions/:id endpoint.
    
    Retrieves full details for a single session by ID.
    
    Response (200):
        {
            "session_id": "uuid",
            "session_date": "2024-01-15T10:00:00Z",
            "pool_length_meters": 25,
            "total_distance_meters": 2000,
            "total_time_seconds": 2400,
            "stroke_type": "freestyle",
            "average_pace_per_100m": 120.0,
            "swolf_score": 45,
            "stroke_rate": 30.0,
            "uploaded_at": "2024-01-15T11:00:00Z",
            "s3_key": "uploads/file.fit",
            "hr_zones": {...},
            "ability_assessment": {...}
        }
    
    Errors:
        404: Session not found
        500: Session retrieval failure
    
    Requirements: 19.3
    """
    # Extract session_id from event (injected by router)
    session_id = event.get("session_id")
    # Extract user_id from auth context (injected by @require_auth)
    user_id = event["auth_context"]["user_id"]
    
    try:
        session = get_session_by_id(session_id)
        
        # Verify that the session belongs to the authenticated user
        if session.user_id != user_id:
            return _error_response(404, "Session not found")
        
        session_data = dataclasses.asdict(session)
        session_data["stroke_breakdown"] = compute_stroke_breakdown(
            session_data.get("splits"), session.stroke_type
        )
        return http_200_dict(session_data)
    except ValueError as exc:
        # Session not found
        return _error_response(404, str(exc))
    except Exception as exc:
        logger.error("Session retrieval failed for session %s: %s", session_id, exc)
        return _error_response(500, "Session retrieval failure")


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------


def _client_ip(event: dict[str, Any]) -> str:
    """Best-effort client IP from the API Gateway proxy event."""
    rc = event.get("requestContext") or {}
    identity = rc.get("identity") or {}
    ip = identity.get("sourceIp")
    if ip:
        return ip
    headers = event.get("headers") or {}
    xff = headers.get("X-Forwarded-For") or headers.get("x-forwarded-for") or ""
    return (xff.split(",")[0].strip() or "unknown")


def _enforce_rate_limit(event: dict[str, Any], action: str, limit: int, window: int):
    """Return a 429 response if the caller has exceeded the limit, else None."""
    ip = _client_ip(event)
    if check_rate_limit(action, ip, limit, window):
        return None
    logger.warning("Rate limit exceeded for %s from %s", action, ip)
    return {
        "statusCode": 429,
        "headers": response_headers({"Retry-After": str(window)}),
        "body": json.dumps({"error": "Too many requests. Please try again later."}),
    }


def _error_response(status_code: int, message: str) -> dict[str, Any]:
    """Build an error response in the documented JSON format."""
    return {
        "statusCode": status_code,
        "headers": response_headers(),
        "body": json.dumps({"error": message}),
    }


def http_200(response: Any) -> dict[str, Any]:
    """Return a successful response as a Lambda proxy response."""
    return {
        "statusCode": 200,
        "headers": response_headers(),
        "body": json.dumps(dataclasses.asdict(response)),
    }


def http_200_dict(response: dict[str, Any]) -> dict[str, Any]:
    """Return a successful response from a dictionary as a Lambda proxy response."""
    return {
        "statusCode": 200,
        "headers": response_headers(),
        "body": json.dumps(response),
    }
