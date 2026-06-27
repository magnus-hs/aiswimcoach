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
from typing import Any

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
from session_history import get_user_sessions, get_session_by_id, save_session

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
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
                "Access-Control-Max-Age": "86400"
            },
            "body": ""
        }
    
    # Authentication routes (no auth required)
    if path == "/auth/register" and http_method == "POST":
        return _handle_register(event)
    elif path == "/auth/login" and http_method == "POST":
        return _handle_login(event)
    elif path == "/auth/verify" and http_method == "GET":
        return _handle_verify(event)
    elif path == "/auth/user" and http_method == "GET":
        return _handle_get_user_info(event, context)
    
    # Profile routes (auth required)
    elif path == "/profile" and http_method == "POST":
        return _handle_save_profile(event, context)
    elif path == "/profile" and http_method == "GET":
        return _handle_get_profile(event, context)
    elif path == "/profile/picture" and http_method == "POST":
        return _handle_upload_profile_picture(event, context)
    
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
        # 5. Invoke Bedrock
        coaching = invoke_bedrock(metrics)
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
                        # Extract heart rate data from FIT file
                        hr_samples = extract_heart_rate_data(fit_bytes)
                        
                        # Calculate HR zones if we have heart rate data
                        if hr_samples:
                            hr_zones = calculate_hr_zones(hr_samples, profile.age)
                            logger.info("HR zones calculated successfully for user %s", user_id)
                        else:
                            logger.info("No heart rate data found in FIT file for user %s", user_id)
                    
                    except (HRDataError, ValueError) as exc:
                        # HR zone calculation failed - log and continue without HR zones
                        # Requirement 12.1: Handle calculation failure gracefully
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
                    # Requirement 7.3: Skip if metrics contain non-finite values
                    import math
                    if (math.isfinite(metrics.pace) and 
                        math.isfinite(metrics.swolf) and 
                        math.isfinite(metrics.stroke_rate)):
                        
                        try:
                            # Generate ability assessment
                            ability_assessment = generate_ability_assessment(
                                metrics=metrics,
                                age=profile.age,
                                nationality=profile.nationality,
                                locality=profile.locality,
                                ability_level=profile.ability_level,
                            )
                            logger.info("Ability assessment generated successfully for user %s", user_id)
                        
                        except BedrockError as exc:
                            # Bedrock invocation failed - log and continue without ability assessment
                            # Requirement 7.11: Handle Bedrock failure gracefully
                            logger.warning("Ability assessment generation failed for user %s: %s", user_id, exc)
                    
                    else:
                        logger.info("Metrics contain non-finite values - skipping ability assessment for user %s", user_id)
                
                else:
                    # Requirement 7.2: Skip if profile incomplete
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
        return http_200_dict(profile_dict)
    except ProfileStorageError as exc:
        logger.error("Profile retrieval failed for user %s: %s", user_id, exc)
        return _error_response(500, "Profile retrieval failure")
    except Exception as exc:
        logger.error("Profile retrieval failed for user %s: %s", user_id, exc)
        return _error_response(500, "Internal server error")


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


def _error_response(status_code: int, message: str) -> dict[str, Any]:
    """Build an error response in the documented JSON format."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps({"error": message}),
    }


def http_200(response: Any) -> dict[str, Any]:
    """Return a successful response as a Lambda proxy response."""
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(dataclasses.asdict(response)),
    }


def http_200_dict(response: dict[str, Any]) -> dict[str, Any]:
    """Return a successful response from a dictionary as a Lambda proxy response."""
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(response),
    }
