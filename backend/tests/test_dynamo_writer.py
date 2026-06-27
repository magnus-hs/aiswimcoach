"""
Unit tests for dynamo_writer.save_to_dynamodb.

Uses moto to intercept DynamoDB calls — no real AWS credentials required.
"""
from __future__ import annotations

import os
import re

import boto3
import pytest
from moto import mock_aws

from backend.models import CoachingResponse, Metrics

TABLE_NAME = "coaching-sessions"
ISO_8601_MS_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$"
)


@pytest.fixture(autouse=True)
def _aws_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set required environment variables for every test."""
    monkeypatch.setenv("DYNAMODB_TABLE", TABLE_NAME)
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    # Dummy credentials so boto3 doesn't look for real ones
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")


def _create_table() -> None:
    """Create the coaching-sessions table in the moto fake DynamoDB."""
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    ddb.create_table(
        TableName=TABLE_NAME,
        KeySchema=[
            {"AttributeName": "file_key", "KeyType": "HASH"},
            {"AttributeName": "created_at", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "file_key", "AttributeType": "S"},
            {"AttributeName": "created_at", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

@mock_aws
def test_save_writes_item_to_table() -> None:
    """A successful call should persist an item with the correct keys."""
    import backend.dynamo_writer as dynamo_writer  # noqa: PLC0415 — imported inside mock context
    dynamo_writer._dynamodb_resource = None  # reset cached resource

    _create_table()

    metrics = Metrics(pace=90.0, swolf=35.0, stroke_rate=30.0)
    coaching = CoachingResponse(
        tips=["Tip one", "Tip two", "Tip three"],
        drill="Pull buoy drill",
    )
    s3_key = "uploads/abc123.fit"

    dynamo_writer.save_to_dynamodb(s3_key, metrics, coaching)

    table = boto3.resource("dynamodb", region_name="us-east-1").Table(TABLE_NAME)
    items = table.scan()["Items"]
    assert len(items) == 1

    item = items[0]
    assert item["file_key"] == s3_key
    assert item["tips"] == ["Tip one", "Tip two", "Tip three"]
    assert item["drill"] == "Pull buoy drill"


@mock_aws
def test_save_stores_metrics_as_decimal() -> None:
    """Metric fields must be stored as Decimal (DynamoDB Number type)."""
    from decimal import Decimal

    import backend.dynamo_writer as dynamo_writer  # noqa: PLC0415
    dynamo_writer._dynamodb_resource = None

    _create_table()

    metrics = Metrics(pace=95.5, swolf=38.25, stroke_rate=28.75)
    coaching = CoachingResponse(tips=["A", "B", "C"], drill="Catch drill")

    dynamo_writer.save_to_dynamodb("uploads/x.fit", metrics, coaching)

    table = boto3.resource("dynamodb", region_name="us-east-1").Table(TABLE_NAME)
    item = table.scan()["Items"][0]

    assert item["pace"] == Decimal("95.5")
    assert item["swolf"] == Decimal("38.25")
    assert item["stroke_rate"] == Decimal("28.75")


@mock_aws
def test_created_at_matches_iso8601_ms_format() -> None:
    """The created_at sort key must match ISO 8601 UTC millisecond format."""
    import backend.dynamo_writer as dynamo_writer  # noqa: PLC0415
    dynamo_writer._dynamodb_resource = None

    _create_table()

    metrics = Metrics(pace=85.0, swolf=32.0, stroke_rate=35.0)
    coaching = CoachingResponse(tips=["X", "Y", "Z"], drill="Kick drill")

    dynamo_writer.save_to_dynamodb("uploads/ts.fit", metrics, coaching)

    table = boto3.resource("dynamodb", region_name="us-east-1").Table(TABLE_NAME)
    item = table.scan()["Items"][0]
    assert ISO_8601_MS_RE.match(item["created_at"]), (
        f"created_at '{item['created_at']}' does not match ISO 8601 ms format"
    )


# ---------------------------------------------------------------------------
# Failure / error-propagation tests
# ---------------------------------------------------------------------------

@mock_aws
def test_exception_is_reraised_on_failure() -> None:
    """If DynamoDB raises an exception it must propagate to the caller."""
    import backend.dynamo_writer as dynamo_writer  # noqa: PLC0415
    dynamo_writer._dynamodb_resource = None

    # Do NOT create the table — put_item will raise a ClientError.

    metrics = Metrics(pace=90.0, swolf=35.0, stroke_rate=30.0)
    coaching = CoachingResponse(tips=["A", "B", "C"], drill="Drill")

    with pytest.raises(Exception):
        dynamo_writer.save_to_dynamodb("uploads/fail.fit", metrics, coaching)
