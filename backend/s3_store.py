"""
S3 storage module for AI Swim Coach.

Provides store_in_s3() which persists raw FIT bytes to S3 and returns
the generated object key.
"""
from __future__ import annotations

import os
import uuid

import boto3
from botocore.exceptions import ClientError


class StorageError(Exception):
    """Raised when the S3 PutObject call fails.

    Maps to HTTP 500 in the Lambda handler pipeline.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def store_in_s3(fit_bytes: bytes) -> str:
    """Store raw FIT file bytes in S3 and return the object key.

    Generates a UUID v4-based key of the form ``uploads/{uuid4}.fit``,
    writes *fit_bytes* to the configured S3 bucket under that key, and
    returns the key string so that downstream stages (DynamoDB writer,
    log entries) can reference the stored object.

    Args:
        fit_bytes: Raw bytes of the uploaded ``.fit`` file.

    Returns:
        The S3 object key, e.g. ``"uploads/3f2504e0-4f89-11d3-9a0c-0305e82c3301.fit"``.

    Raises:
        StorageError: If the ``boto3`` S3 ``put_object`` call raises a
            :class:`botocore.exceptions.ClientError`.  The original error
            detail is preserved in ``StorageError.detail`` and the HTTP
            pipeline should map this to an HTTP 500 response.
    """
    bucket = os.environ["S3_BUCKET"]
    key = f"uploads/{uuid.uuid4()}.fit"

    s3_client = boto3.client("s3")
    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=fit_bytes,
            ContentType="application/octet-stream",
        )
    except ClientError as exc:
        raise StorageError(f"Failed to store file: {exc}") from exc

    return key
