"""
Authentication middleware for AWS Lambda handlers.

Provides a decorator to enforce JWT authentication on Lambda function handlers,
extracting and verifying tokens from the Authorization header and injecting
user context into the event object.

Environment Variables:
    JWT_SECRET: Secret key for verifying JWT tokens (256-bit minimum)
"""
from __future__ import annotations

import json
import logging
from functools import wraps
from typing import Any, Callable

from auth import AuthenticationError, verify_token


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def require_auth(handler_func: Callable) -> Callable:
    """Decorator to enforce JWT authentication on Lambda handlers.
    
    Extracts JWT token from the Authorization header (expects "Bearer <token>" format),
    verifies the token using verify_token(), and injects an auth_context dictionary
    into the event with user_id and email claims.
    
    If authentication fails (missing token, invalid format, expired, or verification
    error), returns HTTP 401 response without calling the wrapped handler.
    
    Args:
        handler_func: Lambda handler function to wrap
    
    Returns:
        Wrapped handler function that enforces authentication
    
    Usage:
        @require_auth
        def my_handler(event, context):
            user_id = event["auth_context"]["user_id"]
            email = event["auth_context"]["email"]
            # ... handler logic
    
    Requirements: 20.2-20.3, 21.20-21.22
    """
    @wraps(handler_func)
    def wrapper(event: dict[str, Any], context: Any) -> dict[str, Any]:
        """Wrapper function that checks authentication before calling handler."""
        
        # Extract Authorization header (case-insensitive)
        headers = event.get("headers") or {}
        auth_header = headers.get("Authorization") or headers.get("authorization")
        
        if not auth_header:
            logger.warning("Missing Authorization header")
            return {
                "statusCode": 401,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Authorization header required"}),
            }
        
        # Extract token from "Bearer <token>" format
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            logger.warning(f"Invalid Authorization header format: {auth_header}")
            return {
                "statusCode": 401,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Invalid Authorization header format. Expected: Bearer <token>"}),
            }
        
        token = parts[1]
        
        # Verify token and extract claims
        try:
            claims = verify_token(token)
        except AuthenticationError as e:
            logger.warning(f"Token verification failed: {e}")
            return {
                "statusCode": 401,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": str(e)}),
            }
        except ValueError as e:
            # JWT_SECRET not configured
            logger.error(f"Configuration error: {e}")
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Internal server error"}),
            }
        except Exception as e:
            logger.error(f"Unexpected error during token verification: {e}")
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Internal server error"}),
            }
        
        # Inject auth_context into event
        event["auth_context"] = {
            "user_id": claims["user_id"],
            "email": claims["email"],
        }
        
        # Call the wrapped handler with authenticated context
        return handler_func(event, context)
    
    return wrapper
