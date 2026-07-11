"""
Authentication module for the AI Swim Coach backend.

Provides user registration, login, JWT token generation and verification,
and password hashing using bcrypt.

JWT secret resolution (in priority order):
    1. AWS Secrets Manager, if JWT_SECRET_ARN is set. The secret value may be
       either a plain string, or JSON: {"current": "...", "previous": "..."}.
       Tokens are SIGNED with `current` and VERIFIED against both `current` and
       `previous`, giving a zero-downtime rotation window (rotating the secret
       does not log existing users out until `previous` is dropped).
    2. Environment variables JWT_SECRET (+ optional JWT_SECRET_PREVIOUS).

Environment Variables:
    JWT_SECRET_ARN:      (preferred) Secrets Manager ARN/name for the JWT secret
    JWT_SECRET:          Fallback signing secret (256-bit minimum)
    JWT_SECRET_PREVIOUS: Optional previous secret accepted during rotation
    USERS_TABLE:         DynamoDB table name for user storage
"""
from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import boto3
import jwt
from botocore.exceptions import ClientError


# Initialize DynamoDB client
dynamodb = boto3.resource("dynamodb")

# --- JWT secret resolution (cached) ---
_secret_cache: dict[str, Any] = {"value": None, "ts": 0.0}
_SECRET_TTL = 300  # seconds


def _load_secrets() -> tuple[str, list[str]]:
    """Return (signing_secret, [verification_secrets]).

    Cached for _SECRET_TTL seconds so we don't call Secrets Manager per request.
    Raises ValueError if no secret can be resolved.
    """
    now = time.time()
    cached = _secret_cache["value"]
    if cached is not None and (now - _secret_cache["ts"]) < _SECRET_TTL:
        return cached

    signing: str | None = None
    verify: list[str] = []

    arn = os.environ.get("JWT_SECRET_ARN")
    if arn:
        try:
            client = boto3.client("secretsmanager")
            resp = client.get_secret_value(SecretId=arn)
            raw = resp.get("SecretString") or ""
            try:
                data = json.loads(raw)
                signing = data.get("current")
                if signing:
                    verify.append(signing)
                prev = data.get("previous")
                if prev:
                    verify.append(prev)
            except (ValueError, TypeError):
                # Plain-string secret
                signing = raw
                verify.append(raw)
        except Exception:
            signing = None  # fall through to env fallback

    if not signing:
        env_secret = os.environ.get("JWT_SECRET")
        if not env_secret:
            raise ValueError("No JWT secret configured (JWT_SECRET_ARN or JWT_SECRET)")
        signing = env_secret
        verify = [env_secret]
        prev = os.environ.get("JWT_SECRET_PREVIOUS")
        if prev:
            verify.append(prev)

    result = (signing, verify)
    _secret_cache["value"] = result
    _secret_cache["ts"] = now
    return result


class AuthenticationError(Exception):
    """Raised when authentication fails (invalid credentials, token issues)."""
    pass


class ConflictError(Exception):
    """Raised when a resource conflict occurs (e.g., email already exists)."""
    pass


def hash_password(password: str) -> str:
    """Hash password using bcrypt with cost factor 12.
    
    Args:
        password: Plain text password to hash
    
    Returns:
        Bcrypt hashed password string (UTF-8 decoded)
    
    Requirements: 21.6, 21.14
    """
    if not isinstance(password, str):
        raise TypeError(f"password must be a str, got {type(password).__name__}")
    
    # bcrypt requires bytes, returns bytes
    password_bytes = password.encode("utf-8")
    hashed_bytes = bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=12))
    
    # Return as string for storage
    return hashed_bytes.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against bcrypt hash.
    
    Args:
        password: Plain text password to verify
        hashed: Bcrypt hashed password from storage
    
    Returns:
        True if password matches hash, False otherwise
    
    Requirements: 21.6, 21.14
    """
    if not isinstance(password, str):
        raise TypeError(f"password must be a str, got {type(password).__name__}")
    if not isinstance(hashed, str):
        raise TypeError(f"hashed must be a str, got {type(hashed).__name__}")
    
    try:
        password_bytes = password.encode("utf-8")
        hashed_bytes = hashed.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        # Invalid hash format or other bcrypt error
        return False


def generate_jwt_token(user_id: str, email: str) -> str:
    """Generate JWT token with 7-day expiration.
    
    Token contains claims:
    - user_id: User identifier (UUID v4)
    - email: User email address
    - iat: Issued at timestamp
    - exp: Expiration timestamp (7 days from issuance)
    
    Args:
        user_id: User identifier
        email: User email address
    
    Returns:
        JWT token string signed with JWT_SECRET
    
    Raises:
        ValueError: If JWT_SECRET not configured
    
    Requirements: 21.16-21.17
    """
    signing, _ = _load_secrets()

    now = datetime.now(timezone.utc)
    expiration = now + timedelta(days=7)
    
    payload = {
        "user_id": user_id,
        "email": email,
        "iat": now,
        "exp": expiration,
    }
    
    token = jwt.encode(payload, signing, algorithm="HS256")
    return token


def verify_token(token: str) -> dict[str, str]:
    """Verify JWT token and extract claims.
    
    Args:
        token: JWT token string to verify
    
    Returns:
        Dictionary with user_id and email claims
    
    Raises:
        AuthenticationError: If token is invalid, expired, or malformed
        ValueError: If JWT_SECRET not configured
    
    Requirements: 21.21-21.22
    """
    _, verify_secrets = _load_secrets()

    last_err: Exception | None = None
    for secret in verify_secrets:
        try:
            payload = jwt.decode(token, secret, algorithms=["HS256"])
            return {
                "user_id": payload["user_id"],
                "email": payload["email"],
            }
        except jwt.ExpiredSignatureError:
            # Expiry is independent of which secret signed it — fail fast.
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            last_err = e
            continue  # Try the next (previous) secret during rotation

    raise AuthenticationError(f"Invalid token: {last_err}")


def _get_users_table():
    """Get DynamoDB Users table resource.
    
    Returns:
        DynamoDB Table resource
    
    Raises:
        ValueError: If USERS_TABLE not configured
    """
    table_name = os.environ.get("USERS_TABLE")
    if not table_name:
        raise ValueError("USERS_TABLE environment variable not configured")
    return dynamodb.Table(table_name)


def _validate_email(email: str) -> None:
    """Validate email format.
    
    Args:
        email: Email address to validate
    
    Raises:
        ValueError: If email is invalid
    """
    if not isinstance(email, str) or not email:
        raise ValueError("email must be a non-empty string")
    
    # Basic email validation: must contain @ and have characters before and after
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise ValueError("email must be a valid email address")
    
    if len(email) > 254:  # RFC 5321
        raise ValueError("email must not exceed 254 characters")


def _validate_password(password: str) -> None:
    """Validate password requirements.
    
    Args:
        password: Password to validate
    
    Raises:
        ValueError: If password doesn't meet requirements
    """
    if not isinstance(password, str):
        raise ValueError("password must be a string")
    
    if len(password) < 8:
        raise ValueError("password must be at least 8 characters")


def register_user(email: str, password: str) -> dict[str, str]:
    """Register a new user with email and password.
    
    Creates a new user record in the Users DynamoDB table with:
    - Unique user_id (UUID v4)
    - Email address (used for login)
    - Hashed password (bcrypt with cost factor 12)
    - Created timestamp
    
    Args:
        email: Valid email address (max 254 characters)
        password: Plain text password (min 8 characters)
    
    Returns:
        Dictionary with:
        - user_id: Unique user identifier (UUID v4 string)
        - email: User's email address
    
    Raises:
        ValueError: If email invalid or password too short
        ConflictError: If email already registered
    
    Requirements: 21.5-21.9
    """
    # Validate inputs
    _validate_email(email)
    _validate_password(password)
    
    # Check if email already exists using GSI
    table = _get_users_table()
    
    try:
        response = table.query(
            IndexName="email-index",
            KeyConditionExpression="email = :email",
            ExpressionAttributeValues={":email": email},
            Limit=1,
        )
        
        if response.get("Items"):
            raise ConflictError("Email already registered")
    except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceNotFoundException":
            raise
        # Table or index doesn't exist yet - proceed anyway for development
    
    # Generate user_id and hash password
    user_id = str(uuid.uuid4())
    hashed_password = hash_password(password)
    created_at = datetime.now(timezone.utc).isoformat()
    
    # Create user record
    try:
        table.put_item(
            Item={
                "user_id": user_id,
                "email": email,
                "hashed_password": hashed_password,
                "created_at": created_at,
            },
            ConditionExpression="attribute_not_exists(user_id)",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ConflictError("User ID conflict (UUID collision)")
        raise
    
    return {
        "user_id": user_id,
        "email": email,
    }


def get_user_info(user_id: str) -> dict[str, Any]:
    """Get user information by user_id.
    
    Retrieves user information from the Users table including
    profile picture URL if available.
    
    Args:
        user_id: User identifier (UUID v4)
    
    Returns:
        Dictionary with:
        - user_id: User identifier
        - email: User's email address
        - profile_picture_url: S3 URL of profile picture (None if not set)
        - created_at: Account creation timestamp
    
    Raises:
        AuthenticationError: If user not found
    
    Requirements: 24.1-24.6
    """
    table = _get_users_table()
    
    try:
        response = table.get_item(Key={"user_id": user_id})
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "ResourceNotFoundException":
            # Table doesn't exist
            raise AuthenticationError("User table not found")
        raise AuthenticationError(f"Failed to retrieve user: {e}")
    
    if "Item" not in response:
        raise AuthenticationError("User not found")
    
    user = response["Item"]
    
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "profile_picture_url": user.get("profile_picture_url"),
        "created_at": user["created_at"],
    }


def login_user(email: str, password: str) -> dict[str, str]:
    """Authenticate user and generate JWT token.
    
    Queries the Users table by email, verifies the password against the stored
    bcrypt hash, and generates a JWT token with 7-day expiration.
    
    Args:
        email: Registered email address
        password: Plain text password
    
    Returns:
        Dictionary with:
        - token: JWT token string (7-day expiration)
        - user_id: User identifier
        - email: User's email address
    
    Raises:
        AuthenticationError: If credentials are invalid (email not found or password incorrect)
    
    Requirements: 21.11-21.18
    """
    # Validate inputs
    if not isinstance(email, str) or not email:
        raise AuthenticationError("Invalid credentials")
    if not isinstance(password, str) or not password:
        raise AuthenticationError("Invalid credentials")
    
    # Query user by email
    table = _get_users_table()
    
    try:
        response = table.query(
            IndexName="email-index",
            KeyConditionExpression="email = :email",
            ExpressionAttributeValues={":email": email},
            Limit=1,
        )
    except ClientError as e:
        # Treat any DynamoDB error as authentication failure to avoid leaking info
        raise AuthenticationError("Invalid credentials")
    
    items = response.get("Items", [])
    if not items:
        raise AuthenticationError("Invalid credentials")
    
    user = items[0]
    
    # Verify password
    if not verify_password(password, user["hashed_password"]):
        raise AuthenticationError("Invalid credentials")
    
    # Generate JWT token
    token = generate_jwt_token(user["user_id"], user["email"])
    
    return {
        "token": token,
        "user_id": user["user_id"],
        "email": user["email"],
    }
