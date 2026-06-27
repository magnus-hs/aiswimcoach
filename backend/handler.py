"""
Lambda handler for AI Swim Coach.

Pipeline: parse_multipart → store_in_s3 → parse_fit → invoke_bedrock
          → save_to_dynamodb (best-effort) → http_200(coaching)

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
from fit_parser import parse_fit
from bedrock_client import BedrockError, invoke_bedrock
from dynamo_writer import save_to_dynamodb

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda entry point.

    Orchestrates the full processing pipeline for a swim FIT file upload:
      1. Parse multipart body to extract raw .fit bytes
      2. Store the file in S3
      3. Parse swim metrics from the FIT data
      4. Invoke Bedrock for AI coaching feedback
      5. Persist the result to DynamoDB (best-effort)
      6. Return the coaching response

    Args:
        event:   API Gateway proxy integration event.
        context: Lambda context object.

    Returns:
        API Gateway proxy integration response dict.
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
        # 3. Parse FIT file
        metrics = parse_fit(fit_bytes)
    except FitParseError as exc:
        logger.warning("FIT parse error: %s", exc)
        return _error_response(422, exc.message)
    except MetricsMissingError as exc:
        logger.warning("Missing metrics: %s", exc.missing)
        return _error_response(422, str(exc))

    try:
        # 4. Invoke Bedrock
        coaching = invoke_bedrock(metrics)
    except BedrockError as exc:
        logger.error("Bedrock invocation failed: %s", exc)
        return _error_response(502, str(exc))

    # 5. Persist to DynamoDB (best-effort — failure must not block the response)
    try:
        save_to_dynamodb(s3_key, metrics, coaching)
    except Exception as exc:
        logger.error("DynamoDB write failed for %s: %s", s3_key, exc)

    # 6. Return coaching response
    return http_200(coaching)


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


def http_200(coaching: Any) -> dict[str, Any]:
    """Return a successful coaching response as a Lambda proxy response."""
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(dataclasses.asdict(coaching)),
    }
