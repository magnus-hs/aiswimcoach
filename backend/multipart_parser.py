"""
Multipart body parser for the AI Swim Coach Lambda function.

API Gateway base64-encodes binary bodies (isBase64Encoded: true) when the
Content-Type is registered as a binary media type.  This module handles
decoding and extraction of the ``file`` part from a multipart/form-data body.
"""
from __future__ import annotations

import base64
import email
import email.parser
import email.policy
from typing import Any


class ParseError(Exception):
    """Raised when the multipart body cannot be parsed or the file part is missing.

    The Lambda handler should catch this and return HTTP 400.
    """


def parse_multipart(event: dict[str, Any]) -> bytes:
    """Extract the raw bytes of the ``file`` field from a multipart/form-data event.

    Args:
        event: AWS Lambda proxy integration event from API Gateway.
               Expected keys:
               - ``body``           – raw (or base64-encoded) request body string
               - ``isBase64Encoded``– bool; when ``True`` the body is base64-encoded
               - ``headers``        – dict containing ``Content-Type`` (case-insensitive)

    Returns:
        Raw bytes of the ``file`` form-data part.

    Raises:
        ParseError: If the body is absent, cannot be decoded, or does not contain
                    a part named ``file``.
    """
    # ------------------------------------------------------------------ #
    # 1. Obtain raw body bytes                                             #
    # ------------------------------------------------------------------ #
    raw_body = event.get("body")
    if not raw_body:
        raise ParseError("Request body is empty or missing")

    if event.get("isBase64Encoded"):
        try:
            body_bytes: bytes = base64.b64decode(raw_body)
        except Exception as exc:
            raise ParseError(f"Failed to base64-decode request body: {exc}") from exc
    else:
        body_bytes = raw_body.encode("latin-1") if isinstance(raw_body, str) else raw_body

    # ------------------------------------------------------------------ #
    # 2. Extract Content-Type header (case-insensitive)                   #
    # ------------------------------------------------------------------ #
    headers: dict[str, str] = event.get("headers") or {}
    # API Gateway may send headers with different casing; normalise to lowercase.
    headers_lower = {k.lower(): v for k, v in headers.items()}
    content_type = headers_lower.get("content-type")
    if not content_type:
        raise ParseError("Content-Type header is missing")

    # ------------------------------------------------------------------ #
    # 3. Parse multipart using email stdlib                               #
    # ------------------------------------------------------------------ #
    # Build a minimal RFC 2822-style message so email.parser can handle it.
    # We prepend the Content-Type header and a blank line (header/body sep).
    header_block = f"Content-Type: {content_type}\r\n\r\n"
    raw_message: bytes = header_block.encode("ascii") + body_bytes

    parser = email.parser.BytesParser(policy=email.policy.compat32)
    msg = parser.parsebytes(raw_message)

    # ------------------------------------------------------------------ #
    # 4. Walk parts and find the one with name="file"                     #
    # ------------------------------------------------------------------ #
    for part in msg.walk():
        # get_param looks at Content-Disposition for the 'name' parameter
        disposition = part.get("Content-Disposition", "")
        if not disposition:
            continue
        name = part.get_param("name", header="Content-Disposition")
        if name == "file":
            payload = part.get_payload(decode=True)
            if payload is None:
                raise ParseError("The 'file' part has no payload")
            return payload  # type: ignore[return-value]

    raise ParseError("No FIT file found in request")
