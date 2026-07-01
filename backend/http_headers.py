"""
Shared HTTP response headers: locked-down CORS plus security headers.

The allowed origin defaults to the app's Amplify URL and can be overridden
with the ALLOWED_ORIGIN environment variable.
"""
from __future__ import annotations

import os
from typing import Any

ALLOWED_ORIGIN = os.environ.get(
    "ALLOWED_ORIGIN", "https://main.d3qbayea55l8tl.amplifyapp.com"
)

# Security headers applied to every API response.
_SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


def response_headers(extra: dict[str, Any] | None = None) -> dict[str, str]:
    """Build standard response headers (JSON content, CORS, security).

    Args:
        extra: Optional additional headers to merge in.

    Returns:
        A headers dict for an API Gateway proxy response.
    """
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
        "Vary": "Origin",
    }
    headers.update(_SECURITY_HEADERS)
    if extra:
        headers.update(extra)
    return headers
