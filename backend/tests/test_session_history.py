"""
Unit tests for session_history.save_session.

Uses moto to intercept DynamoDB calls — no real AWS credentials required.
"""
from __future__ import annotations

import os
import re
import uuid
from decimal import Decimal

import boto3
import pytest
from hypothesis import given, strategies as st
from moto import mock_aws

from backend.models import (
    AbilityAssessment,
    HRZonesData,
    Metrics,
    Session,
    SessionInfo,
)

TABLE_NAME = "Sessions"
ISO_8601_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
)


@pytest.fixture(autouse=True)
def _aws_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set required environment variables for every test."""
    monkeypatch.setenv("SESSIONS_TABLE", TABLE_NAME)
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    # Dummy credentials so boto3 doesn't look for real ones
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")


def _create_sessions_table() -> None:
    """Create the Sessions table in the moto fake DynamoDB."""
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    ddb.create_table(
        TableName=TABLE_NAME,
        KeySchema=[
            {"AttributeName": "user_id", "KeyType": "HASH"},
            {"AttributeName": "session_date", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "session_date", "AttributeType": "S"},
            {"AttributeName": "session_id", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "session_id-index",
                "KeySchema": [
                    {"AttributeName": "session_id", "KeyType": "HASH"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

@mock_aws
def test_save_session_generates_uuid_v4() -> None:
    """save_session should generate and return a valid UUID v4 session_id."""
    import backend.session_history as session_history  # noqa: PLC0415
    session_history._dynamodb_resource = None  # reset cached resource

    _create_sessions_table()

    user_id = str(uuid.uuid4())
    session_info = SessionInfo(
        start_time="2024-06-15T10:30:00Z",
        pool_length_m=25.0,
        stroke="freestyle",
        total_distance_m=1000.0,
        total_time_seconds=900.0,
        num_lengths=40,
    )
    metrics = Metrics(pace=90.0, swolf=35.0, stroke_rate=30.0)
    s3_key = "uploads/test.fit"

    session_id = session_history.save_session(
        user_id=user_id,
        session_info=session_info,
        metrics=metrics,
        s3_key=s3_key,
    )

    # Verify session_id is a valid UUID v4
    parsed_uuid = uuid.UUID(session_id)
    assert parsed_uuid.version == 4
    assert str(parsed_uuid) == session_id


@mock_aws
def test_save_session_persists_all_required_fields() -> None:
    """save_session should persist all required session fields to DynamoDB."""
    import backend.session_history as session_history  # noqa: PLC0415
    session_history._dynamodb_resource = None

    _create_sessions_table()

    user_id = str(uuid.uuid4())
    session_info = SessionInfo(
        start_time="2024-06-15T10:30:00Z",
        pool_length_m=25.0,
        stroke="freestyle",
        total_distance_m=1500.0,
        total_time_seconds=1350.0,
        num_lengths=60,
    )
    metrics = Metrics(pace=92.5, swolf=37.0, stroke_rate=28.5)
    s3_key = "uploads/session123.fit"

    session_id = session_history.save_session(
        user_id=user_id,
        session_info=session_info,
        metrics=metrics,
        s3_key=s3_key,
    )

    # Retrieve item from DynamoDB
    table = boto3.resource("dynamodb", region_name="us-east-1").Table(TABLE_NAME)
    response = table.get_item(
        Key={
            "user_id": user_id,
            "session_date": session_info.start_time,
        }
    )
    
    item = response["Item"]
    assert item["session_id"] == session_id
    assert item["user_id"] == user_id
    assert item["session_date"] == "2024-06-15T10:30:00Z"
    assert item["pool_length_meters"] == 25
    assert item["total_distance_meters"] == 1500
    assert item["total_time_seconds"] == 1350
    assert item["stroke_type"] == "freestyle"
    assert item["average_pace_per_100m"] == Decimal("92.5")
    assert item["swolf_score"] == 37
    assert item["stroke_rate"] == Decimal("28.5")
    assert item["s3_key"] == s3_key
    assert ISO_8601_RE.match(item["uploaded_at"])


@mock_aws
def test_save_session_stores_hr_zones_when_provided() -> None:
    """save_session should store optional hr_zones data when provided."""
    import backend.session_history as session_history  # noqa: PLC0415
    session_history._dynamodb_resource = None

    _create_sessions_table()

    user_id = str(uuid.uuid4())
    session_info = SessionInfo(
        start_time="2024-06-15T11:00:00Z",
        pool_length_m=50.0,
        stroke="butterfly",
        total_distance_m=2000.0,
        total_time_seconds=1800.0,
        num_lengths=40,
    )
    metrics = Metrics(pace=88.0, swolf=33.0, stroke_rate=32.0)
    s3_key = "uploads/hr_session.fit"
    
    hr_zones = HRZonesData(
        zone_1_seconds=300,
        zone_2_seconds=600,
        zone_3_seconds=500,
        zone_4_seconds=300,
        zone_5_seconds=100,
        zone_1_percent=16.7,
        zone_2_percent=33.3,
        zone_3_percent=27.8,
        zone_4_percent=16.7,
        zone_5_percent=5.5,
        max_hr=180,
        zone_boundaries={
            1: (90, 108),
            2: (108, 126),
            3: (126, 144),
            4: (144, 162),
            5: (162, 180),
        },
    )

    session_id = session_history.save_session(
        user_id=user_id,
        session_info=session_info,
        metrics=metrics,
        s3_key=s3_key,
        hr_zones=hr_zones,
    )

    # Retrieve and verify hr_zones data
    table = boto3.resource("dynamodb", region_name="us-east-1").Table(TABLE_NAME)
    response = table.get_item(
        Key={
            "user_id": user_id,
            "session_date": session_info.start_time,
        }
    )
    
    item = response["Item"]
    assert "hr_zones" in item
    hr_data = item["hr_zones"]
    assert hr_data["zone_1_seconds"] == 300
    assert hr_data["zone_2_seconds"] == 600
    assert hr_data["zone_3_seconds"] == 500
    assert hr_data["zone_4_seconds"] == 300
    assert hr_data["zone_5_seconds"] == 100
    assert hr_data["zone_1_percent"] == Decimal("16.7")
    assert hr_data["zone_2_percent"] == Decimal("33.3")
    assert hr_data["max_hr"] == 180
    assert hr_data["zone_boundaries"]["1"]["lower"] == 90
    assert hr_data["zone_boundaries"]["1"]["upper"] == 108


@mock_aws
def test_save_session_stores_ability_assessment_when_provided() -> None:
    """save_session should store optional ability_assessment data when provided."""
    import backend.session_history as session_history  # noqa: PLC0415
    session_history._dynamodb_resource = None

    _create_sessions_table()

    user_id = str(uuid.uuid4())
    session_info = SessionInfo(
        start_time="2024-06-15T12:00:00Z",
        pool_length_m=25.0,
        stroke="backstroke",
        total_distance_m=800.0,
        total_time_seconds=720.0,
        num_lengths=32,
    )
    metrics = Metrics(pace=95.0, swolf=40.0, stroke_rate=26.0)
    s3_key = "uploads/assessed_session.fit"
    
    ability_assessment = AbilityAssessment(
        percentile_estimate="Top 30%",
        local_ranking="Competitive at local club level",
        national_ranking="Above average for age group",
        competitive_analysis="Strong technique with room for endurance improvement",
    )

    session_id = session_history.save_session(
        user_id=user_id,
        session_info=session_info,
        metrics=metrics,
        s3_key=s3_key,
        ability_assessment=ability_assessment,
    )

    # Retrieve and verify ability_assessment data
    table = boto3.resource("dynamodb", region_name="us-east-1").Table(TABLE_NAME)
    response = table.get_item(
        Key={
            "user_id": user_id,
            "session_date": session_info.start_time,
        }
    )
    
    item = response["Item"]
    assert "ability_assessment" in item
    assessment_data = item["ability_assessment"]
    assert assessment_data["percentile_estimate"] == "Top 30%"
    assert assessment_data["local_ranking"] == "Competitive at local club level"
    assert assessment_data["national_ranking"] == "Above average for age group"
    assert assessment_data["competitive_analysis"] == "Strong technique with room for endurance improvement"


@mock_aws
def test_save_session_with_both_hr_zones_and_ability_assessment() -> None:
    """save_session should store both hr_zones and ability_assessment when both are provided."""
    import backend.session_history as session_history  # noqa: PLC0415
    session_history._dynamodb_resource = None

    _create_sessions_table()

    user_id = str(uuid.uuid4())
    session_info = SessionInfo(
        start_time="2024-06-15T13:00:00Z",
        pool_length_m=50.0,
        stroke="breaststroke",
        total_distance_m=1200.0,
        total_time_seconds=1440.0,
        num_lengths=24,
    )
    metrics = Metrics(pace=120.0, swolf=45.0, stroke_rate=22.0)
    s3_key = "uploads/complete_session.fit"
    
    hr_zones = HRZonesData(
        zone_1_seconds=200,
        zone_2_seconds=400,
        zone_3_seconds=500,
        zone_4_seconds=300,
        zone_5_seconds=40,
        zone_1_percent=13.9,
        zone_2_percent=27.8,
        zone_3_percent=34.7,
        zone_4_percent=20.8,
        zone_5_percent=2.8,
        max_hr=190,
        zone_boundaries={
            1: (95, 114),
            2: (114, 133),
            3: (133, 152),
            4: (152, 171),
            5: (171, 190),
        },
    )
    
    ability_assessment = AbilityAssessment(
        percentile_estimate="Top 25%",
        local_ranking="Elite at local level",
        national_ranking="Competitive at national level",
        competitive_analysis="Excellent pacing and technique",
    )

    session_id = session_history.save_session(
        user_id=user_id,
        session_info=session_info,
        metrics=metrics,
        s3_key=s3_key,
        hr_zones=hr_zones,
        ability_assessment=ability_assessment,
    )

    # Retrieve and verify both fields
    table = boto3.resource("dynamodb", region_name="us-east-1").Table(TABLE_NAME)
    response = table.get_item(
        Key={
            "user_id": user_id,
            "session_date": session_info.start_time,
        }
    )
    
    item = response["Item"]
    assert "hr_zones" in item
    assert "ability_assessment" in item
    assert item["hr_zones"]["max_hr"] == 190
    assert item["ability_assessment"]["percentile_estimate"] == "Top 25%"


@mock_aws
def test_save_session_without_optional_fields() -> None:
    """save_session should work correctly when hr_zones and ability_assessment are None."""
    import backend.session_history as session_history  # noqa: PLC0415
    session_history._dynamodb_resource = None

    _create_sessions_table()

    user_id = str(uuid.uuid4())
    session_info = SessionInfo(
        start_time="2024-06-15T14:00:00Z",
        pool_length_m=25.0,
        stroke="mixed",
        total_distance_m=500.0,
        total_time_seconds=450.0,
        num_lengths=20,
    )
    metrics = Metrics(pace=90.0, swolf=35.0, stroke_rate=30.0)
    s3_key = "uploads/basic_session.fit"

    session_id = session_history.save_session(
        user_id=user_id,
        session_info=session_info,
        metrics=metrics,
        s3_key=s3_key,
    )

    # Retrieve and verify optional fields are not present
    table = boto3.resource("dynamodb", region_name="us-east-1").Table(TABLE_NAME)
    response = table.get_item(
        Key={
            "user_id": user_id,
            "session_date": session_info.start_time,
        }
    )
    
    item = response["Item"]
    assert "hr_zones" not in item
    assert "ability_assessment" not in item
    # But all required fields should be present
    assert item["session_id"] == session_id
    assert item["user_id"] == user_id
    assert item["stroke_type"] == "mixed"


@mock_aws
def test_save_session_rounds_pace_to_two_decimals() -> None:
    """save_session should round average_pace_per_100m to 2 decimal places."""
    import backend.session_history as session_history  # noqa: PLC0415
    session_history._dynamodb_resource = None

    _create_sessions_table()

    user_id = str(uuid.uuid4())
    session_info = SessionInfo(
        start_time="2024-06-15T15:00:00Z",
        pool_length_m=25.0,
        stroke="freestyle",
        total_distance_m=1000.0,
        total_time_seconds=900.0,
        num_lengths=40,
    )
    # Provide pace with many decimal places
    metrics = Metrics(pace=92.456789, swolf=35.0, stroke_rate=30.0)
    s3_key = "uploads/precision_test.fit"

    session_history.save_session(
        user_id=user_id,
        session_info=session_info,
        metrics=metrics,
        s3_key=s3_key,
    )

    table = boto3.resource("dynamodb", region_name="us-east-1").Table(TABLE_NAME)
    response = table.get_item(
        Key={
            "user_id": user_id,
            "session_date": session_info.start_time,
        }
    )
    
    item = response["Item"]
    # Should be rounded to 2 decimal places
    assert item["average_pace_per_100m"] == Decimal("92.46")


@mock_aws
def test_save_session_rounds_stroke_rate_to_one_decimal() -> None:
    """save_session should round stroke_rate to 1 decimal place."""
    import backend.session_history as session_history  # noqa: PLC0415
    session_history._dynamodb_resource = None

    _create_sessions_table()

    user_id = str(uuid.uuid4())
    session_info = SessionInfo(
        start_time="2024-06-15T16:00:00Z",
        pool_length_m=25.0,
        stroke="freestyle",
        total_distance_m=1000.0,
        total_time_seconds=900.0,
        num_lengths=40,
    )
    # Provide stroke_rate with many decimal places
    metrics = Metrics(pace=90.0, swolf=35.0, stroke_rate=28.456789)
    s3_key = "uploads/stroke_rate_test.fit"

    session_history.save_session(
        user_id=user_id,
        session_info=session_info,
        metrics=metrics,
        s3_key=s3_key,
    )

    table = boto3.resource("dynamodb", region_name="us-east-1").Table(TABLE_NAME)
    response = table.get_item(
        Key={
            "user_id": user_id,
            "session_date": session_info.start_time,
        }
    )
    
    item = response["Item"]
    # Should be rounded to 1 decimal place
    assert item["stroke_rate"] == Decimal("28.5")


# ---------------------------------------------------------------------------
# Failure / error-propagation tests
# ---------------------------------------------------------------------------

@mock_aws
def test_save_session_exception_is_reraised_on_failure() -> None:
    """If DynamoDB raises an exception it must propagate to the caller."""
    import backend.session_history as session_history  # noqa: PLC0415
    session_history._dynamodb_resource = None

    # Do NOT create the table — put_item will raise a ClientError.

    user_id = str(uuid.uuid4())
    session_info = SessionInfo(
        start_time="2024-06-15T17:00:00Z",
        pool_length_m=25.0,
        stroke="freestyle",
        total_distance_m=1000.0,
        total_time_seconds=900.0,
        num_lengths=40,
    )
    metrics = Metrics(pace=90.0, swolf=35.0, stroke_rate=30.0)
    s3_key = "uploads/fail.fit"

    with pytest.raises(Exception):
        session_history.save_session(
            user_id=user_id,
            session_info=session_info,
            metrics=metrics,
            s3_key=s3_key,
        )


# ---------------------------------------------------------------------------
# Tests for aggregate_daily_distances
# ---------------------------------------------------------------------------

def test_aggregate_daily_distances_single_session_per_date() -> None:
    """aggregate_daily_distances should return correct totals for single sessions per date."""
    import backend.session_history as session_history  # noqa: PLC0415
    
    sessions = [
        Session(
            session_id="id1",
            user_id="user1",
            session_date="2024-06-15T10:00:00Z",
            pool_length_meters=25,
            total_distance_meters=1000,
            total_time_seconds=900,
            stroke_type="freestyle",
            average_pace_per_100m=90.0,
            swolf_score=35,
            stroke_rate=30.0,
            uploaded_at="2024-06-15T11:00:00Z",
            s3_key="uploads/session1.fit",
        ),
        Session(
            session_id="id2",
            user_id="user1",
            session_date="2024-06-16T10:00:00Z",
            pool_length_meters=25,
            total_distance_meters=1500,
            total_time_seconds=1350,
            stroke_type="freestyle",
            average_pace_per_100m=90.0,
            swolf_score=35,
            stroke_rate=30.0,
            uploaded_at="2024-06-16T11:00:00Z",
            s3_key="uploads/session2.fit",
        ),
    ]
    
    result = session_history.aggregate_daily_distances(sessions)
    
    assert result == {
        "2024-06-15": 1000,
        "2024-06-16": 1500,
    }


def test_aggregate_daily_distances_multiple_sessions_same_date() -> None:
    """aggregate_daily_distances should sum distances for multiple sessions on the same date."""
    import backend.session_history as session_history  # noqa: PLC0415
    
    sessions = [
        Session(
            session_id="id1",
            user_id="user1",
            session_date="2024-06-15T08:00:00Z",
            pool_length_meters=25,
            total_distance_meters=1000,
            total_time_seconds=900,
            stroke_type="freestyle",
            average_pace_per_100m=90.0,
            swolf_score=35,
            stroke_rate=30.0,
            uploaded_at="2024-06-15T09:00:00Z",
            s3_key="uploads/session1.fit",
        ),
        Session(
            session_id="id2",
            user_id="user1",
            session_date="2024-06-15T16:00:00Z",
            pool_length_meters=25,
            total_distance_meters=1500,
            total_time_seconds=1350,
            stroke_type="backstroke",
            average_pace_per_100m=95.0,
            swolf_score=40,
            stroke_rate=28.0,
            uploaded_at="2024-06-15T17:00:00Z",
            s3_key="uploads/session2.fit",
        ),
        Session(
            session_id="id3",
            user_id="user1",
            session_date="2024-06-16T10:00:00Z",
            pool_length_meters=50,
            total_distance_meters=2000,
            total_time_seconds=1800,
            stroke_type="butterfly",
            average_pace_per_100m=90.0,
            swolf_score=33,
            stroke_rate=32.0,
            uploaded_at="2024-06-16T11:00:00Z",
            s3_key="uploads/session3.fit",
        ),
    ]
    
    result = session_history.aggregate_daily_distances(sessions)
    
    assert result == {
        "2024-06-15": 2500,  # 1000 + 1500
        "2024-06-16": 2000,
    }


def test_aggregate_daily_distances_empty_list() -> None:
    """aggregate_daily_distances should return empty dict for empty session list."""
    import backend.session_history as session_history  # noqa: PLC0415
    
    result = session_history.aggregate_daily_distances([])
    
    assert result == {}


def test_aggregate_daily_distances_preserves_total_distance() -> None:
    """aggregate_daily_distances should preserve the sum of all individual distances."""
    import backend.session_history as session_history  # noqa: PLC0415
    
    sessions = [
        Session(
            session_id="id1",
            user_id="user1",
            session_date="2024-01-10T10:00:00Z",
            pool_length_meters=25,
            total_distance_meters=800,
            total_time_seconds=720,
            stroke_type="freestyle",
            average_pace_per_100m=90.0,
            swolf_score=35,
            stroke_rate=30.0,
            uploaded_at="2024-01-10T11:00:00Z",
            s3_key="uploads/s1.fit",
        ),
        Session(
            session_id="id2",
            user_id="user1",
            session_date="2024-01-10T18:00:00Z",
            pool_length_meters=25,
            total_distance_meters=1200,
            total_time_seconds=1080,
            stroke_type="freestyle",
            average_pace_per_100m=90.0,
            swolf_score=35,
            stroke_rate=30.0,
            uploaded_at="2024-01-10T19:00:00Z",
            s3_key="uploads/s2.fit",
        ),
        Session(
            session_id="id3",
            user_id="user1",
            session_date="2024-01-11T10:00:00Z",
            pool_length_meters=50,
            total_distance_meters=1500,
            total_time_seconds=1350,
            stroke_type="butterfly",
            average_pace_per_100m=90.0,
            swolf_score=33,
            stroke_rate=32.0,
            uploaded_at="2024-01-11T11:00:00Z",
            s3_key="uploads/s3.fit",
        ),
        Session(
            session_id="id4",
            user_id="user1",
            session_date="2024-01-12T10:00:00Z",
            pool_length_meters=25,
            total_distance_meters=1000,
            total_time_seconds=900,
            stroke_type="breaststroke",
            average_pace_per_100m=90.0,
            swolf_score=38,
            stroke_rate=26.0,
            uploaded_at="2024-01-12T11:00:00Z",
            s3_key="uploads/s4.fit",
        ),
    ]
    
    result = session_history.aggregate_daily_distances(sessions)
    
    # Sum of individual distances: 800 + 1200 + 1500 + 1000 = 4500
    total_individual = sum(s.total_distance_meters for s in sessions)
    total_aggregated = sum(result.values())
    
    assert total_aggregated == total_individual
    assert total_aggregated == 4500


def test_aggregate_daily_distances_handles_timezone_consistently() -> None:
    """aggregate_daily_distances should extract date part correctly regardless of time."""
    import backend.session_history as session_history  # noqa: PLC0415
    
    sessions = [
        Session(
            session_id="id1",
            user_id="user1",
            session_date="2024-06-15T00:00:01Z",  # Just after midnight
            pool_length_meters=25,
            total_distance_meters=500,
            total_time_seconds=450,
            stroke_type="freestyle",
            average_pace_per_100m=90.0,
            swolf_score=35,
            stroke_rate=30.0,
            uploaded_at="2024-06-15T01:00:00Z",
            s3_key="uploads/s1.fit",
        ),
        Session(
            session_id="id2",
            user_id="user1",
            session_date="2024-06-15T23:59:59Z",  # Just before midnight
            pool_length_meters=25,
            total_distance_meters=700,
            total_time_seconds=630,
            stroke_type="freestyle",
            average_pace_per_100m=90.0,
            swolf_score=35,
            stroke_rate=30.0,
            uploaded_at="2024-06-16T00:00:00Z",
            s3_key="uploads/s2.fit",
        ),
    ]
    
    result = session_history.aggregate_daily_distances(sessions)
    
    # Both sessions should be on the same date
    assert result == {
        "2024-06-15": 1200,  # 500 + 700
    }


# ---------------------------------------------------------------------------
# Property-based tests for aggregate_daily_distances
# ---------------------------------------------------------------------------

from datetime import datetime

@given(
    sessions_data=st.lists(
        st.tuples(
            st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),  # session_id
            st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),  # user_id
            # Generate valid ISO 8601 date-time strings (YYYY-MM-DDTHH:MM:SSZ)
            st.datetimes(
                min_value=datetime(2020, 1, 1),
                max_value=datetime(2025, 12, 31)
            ).map(lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%SZ")),
            st.integers(min_value=1, max_value=100000),  # total_distance_meters
        ),
        min_size=0,
        max_size=50,
    )
)
def test_property_15_daily_distance_aggregation(sessions_data: list[tuple[str, str, str, int]]) -> None:
    """
    **Property 15: Daily Distance Aggregation**
    
    For any list of sessions with session_date and total_distance_meters fields,
    grouping by date and summing distances SHALL produce a result where the sum
    of all daily distances equals the sum of all individual session distances.
    
    **Validates: Requirements 18.4**
    """
    import backend.session_history as session_history  # noqa: PLC0415
    
    # Build Session objects from generated data
    sessions = []
    for session_id, user_id, session_date, total_distance in sessions_data:
        session = Session(
            session_id=session_id,
            user_id=user_id,
            session_date=session_date,
            pool_length_meters=25,
            total_distance_meters=total_distance,
            total_time_seconds=900,
            stroke_type="freestyle",
            average_pace_per_100m=90.0,
            swolf_score=35,
            stroke_rate=30.0,
            uploaded_at="2024-06-15T11:00:00Z",
            s3_key="uploads/test.fit",
        )
        sessions.append(session)
    
    # Run aggregation
    result = session_history.aggregate_daily_distances(sessions)
    
    # Property: Sum of all daily distances equals sum of all individual distances
    total_individual = sum(s.total_distance_meters for s in sessions)
    total_aggregated = sum(result.values())
    
    assert total_aggregated == total_individual, (
        f"Aggregation failed: individual total={total_individual}, "
        f"aggregated total={total_aggregated}"
    )



# ---------------------------------------------------------------------------
# Tests for get_session_by_id
# ---------------------------------------------------------------------------

@mock_aws
def test_get_session_by_id_retrieves_session() -> None:
    """get_session_by_id should retrieve a session by its session_id using the GSI."""
    import backend.session_history as session_history  # noqa: PLC0415
    session_history._dynamodb_resource = None

    _create_sessions_table()

    user_id = str(uuid.uuid4())
    session_info = SessionInfo(
        start_time="2024-06-15T10:30:00Z",
        pool_length_m=25.0,
        stroke="freestyle",
        total_distance_m=1000.0,
        total_time_seconds=900.0,
        num_lengths=40,
    )
    metrics = Metrics(pace=90.0, swolf=35.0, stroke_rate=30.0)
    s3_key = "uploads/test.fit"

    # Save a session
    session_id = session_history.save_session(
        user_id=user_id,
        session_info=session_info,
        metrics=metrics,
        s3_key=s3_key,
    )

    # Retrieve the session by ID
    retrieved_session = session_history.get_session_by_id(session_id)

    # Verify all fields match
    assert retrieved_session.session_id == session_id
    assert retrieved_session.user_id == user_id
    assert retrieved_session.session_date == "2024-06-15T10:30:00Z"
    assert retrieved_session.pool_length_meters == 25
    assert retrieved_session.total_distance_meters == 1000
    assert retrieved_session.total_time_seconds == 900
    assert retrieved_session.stroke_type == "freestyle"
    assert retrieved_session.average_pace_per_100m == 90.0
    assert retrieved_session.swolf_score == 35
    assert retrieved_session.stroke_rate == 30.0
    assert retrieved_session.s3_key == s3_key
    assert ISO_8601_RE.match(retrieved_session.uploaded_at)
    assert retrieved_session.hr_zones is None
    assert retrieved_session.ability_assessment is None


@mock_aws
def test_get_session_by_id_with_hr_zones() -> None:
    """get_session_by_id should correctly deserialize hr_zones data."""
    import backend.session_history as session_history  # noqa: PLC0415
    session_history._dynamodb_resource = None

    _create_sessions_table()

    user_id = str(uuid.uuid4())
    session_info = SessionInfo(
        start_time="2024-06-15T11:00:00Z",
        pool_length_m=50.0,
        stroke="butterfly",
        total_distance_m=2000.0,
        total_time_seconds=1800.0,
        num_lengths=40,
    )
    metrics = Metrics(pace=88.0, swolf=33.0, stroke_rate=32.0)
    s3_key = "uploads/hr_session.fit"
    
    hr_zones = HRZonesData(
        zone_1_seconds=300,
        zone_2_seconds=600,
        zone_3_seconds=500,
        zone_4_seconds=300,
        zone_5_seconds=100,
        zone_1_percent=16.7,
        zone_2_percent=33.3,
        zone_3_percent=27.8,
        zone_4_percent=16.7,
        zone_5_percent=5.5,
        max_hr=180,
        zone_boundaries={
            1: (90, 108),
            2: (108, 126),
            3: (126, 144),
            4: (144, 162),
            5: (162, 180),
        },
    )

    # Save a session with hr_zones
    session_id = session_history.save_session(
        user_id=user_id,
        session_info=session_info,
        metrics=metrics,
        s3_key=s3_key,
        hr_zones=hr_zones,
    )

    # Retrieve the session by ID
    retrieved_session = session_history.get_session_by_id(session_id)

    # Verify hr_zones data is correctly deserialized
    assert retrieved_session.hr_zones is not None
    assert retrieved_session.hr_zones.zone_1_seconds == 300
    assert retrieved_session.hr_zones.zone_2_seconds == 600
    assert retrieved_session.hr_zones.zone_3_seconds == 500
    assert retrieved_session.hr_zones.zone_4_seconds == 300
    assert retrieved_session.hr_zones.zone_5_seconds == 100
    assert retrieved_session.hr_zones.zone_1_percent == 16.7
    assert retrieved_session.hr_zones.zone_2_percent == 33.3
    assert retrieved_session.hr_zones.max_hr == 180
    assert retrieved_session.hr_zones.zone_boundaries[1] == (90, 108)
    assert retrieved_session.hr_zones.zone_boundaries[5] == (162, 180)


@mock_aws
def test_get_session_by_id_with_ability_assessment() -> None:
    """get_session_by_id should correctly deserialize ability_assessment data."""
    import backend.session_history as session_history  # noqa: PLC0415
    session_history._dynamodb_resource = None

    _create_sessions_table()

    user_id = str(uuid.uuid4())
    session_info = SessionInfo(
        start_time="2024-06-15T12:00:00Z",
        pool_length_m=25.0,
        stroke="backstroke",
        total_distance_m=800.0,
        total_time_seconds=720.0,
        num_lengths=32,
    )
    metrics = Metrics(pace=95.0, swolf=40.0, stroke_rate=26.0)
    s3_key = "uploads/assessed_session.fit"
    
    ability_assessment = AbilityAssessment(
        percentile_estimate="Top 30%",
        local_ranking="Competitive at local club level",
        national_ranking="Above average for age group",
        competitive_analysis="Strong technique with room for endurance improvement",
    )

    # Save a session with ability_assessment
    session_id = session_history.save_session(
        user_id=user_id,
        session_info=session_info,
        metrics=metrics,
        s3_key=s3_key,
        ability_assessment=ability_assessment,
    )

    # Retrieve the session by ID
    retrieved_session = session_history.get_session_by_id(session_id)

    # Verify ability_assessment data is correctly deserialized
    assert retrieved_session.ability_assessment is not None
    assert retrieved_session.ability_assessment.percentile_estimate == "Top 30%"
    assert retrieved_session.ability_assessment.local_ranking == "Competitive at local club level"
    assert retrieved_session.ability_assessment.national_ranking == "Above average for age group"
    assert retrieved_session.ability_assessment.competitive_analysis == "Strong technique with room for endurance improvement"


@mock_aws
def test_get_session_by_id_raises_error_for_nonexistent_session() -> None:
    """get_session_by_id should raise ValueError when session_id doesn't exist."""
    import backend.session_history as session_history  # noqa: PLC0415
    session_history._dynamodb_resource = None

    _create_sessions_table()

    # Try to retrieve a non-existent session
    nonexistent_id = str(uuid.uuid4())
    
    with pytest.raises(ValueError, match=f"Session not found: {nonexistent_id}"):
        session_history.get_session_by_id(nonexistent_id)


@mock_aws
def test_get_session_by_id_with_both_hr_zones_and_ability_assessment() -> None:
    """get_session_by_id should correctly deserialize both hr_zones and ability_assessment."""
    import backend.session_history as session_history  # noqa: PLC0415
    session_history._dynamodb_resource = None

    _create_sessions_table()

    user_id = str(uuid.uuid4())
    session_info = SessionInfo(
        start_time="2024-06-15T13:00:00Z",
        pool_length_m=50.0,
        stroke="breaststroke",
        total_distance_m=1200.0,
        total_time_seconds=1440.0,
        num_lengths=24,
    )
    metrics = Metrics(pace=120.0, swolf=45.0, stroke_rate=22.0)
    s3_key = "uploads/complete_session.fit"
    
    hr_zones = HRZonesData(
        zone_1_seconds=200,
        zone_2_seconds=400,
        zone_3_seconds=500,
        zone_4_seconds=300,
        zone_5_seconds=40,
        zone_1_percent=13.9,
        zone_2_percent=27.8,
        zone_3_percent=34.7,
        zone_4_percent=20.8,
        zone_5_percent=2.8,
        max_hr=190,
        zone_boundaries={
            1: (95, 114),
            2: (114, 133),
            3: (133, 152),
            4: (152, 171),
            5: (171, 190),
        },
    )
    
    ability_assessment = AbilityAssessment(
        percentile_estimate="Top 25%",
        local_ranking="Elite at local level",
        national_ranking="Competitive at national level",
        competitive_analysis="Excellent pacing and technique",
    )

    # Save a session with both hr_zones and ability_assessment
    session_id = session_history.save_session(
        user_id=user_id,
        session_info=session_info,
        metrics=metrics,
        s3_key=s3_key,
        hr_zones=hr_zones,
        ability_assessment=ability_assessment,
    )

    # Retrieve the session by ID
    retrieved_session = session_history.get_session_by_id(session_id)

    # Verify both fields are correctly deserialized
    assert retrieved_session.hr_zones is not None
    assert retrieved_session.ability_assessment is not None
    assert retrieved_session.hr_zones.max_hr == 190
    assert retrieved_session.ability_assessment.percentile_estimate == "Top 25%"
    assert retrieved_session.session_id == session_id
    assert retrieved_session.user_id == user_id


# ---------------------------------------------------------------------------
# Tests for get_user_sessions
# ---------------------------------------------------------------------------

@mock_aws
def test_get_user_sessions_returns_all_sessions_for_user() -> None:
    """get_user_sessions should return all sessions for a specific user."""
    import backend.session_history as session_history  # noqa: PLC0415
    session_history._dynamodb_resource = None

    _create_sessions_table()

    user1_id = str(uuid.uuid4())
    user2_id = str(uuid.uuid4())

    # Create sessions for user1
    session_info1 = SessionInfo(
        start_time="2024-06-15T10:00:00Z",
        pool_length_m=25.0,
        stroke="freestyle",
        total_distance_m=1000.0,
        total_time_seconds=900.0,
        num_lengths=40,
    )
    metrics1 = Metrics(pace=90.0, swolf=35.0, stroke_rate=30.0)
    
    session_info2 = SessionInfo(
        start_time="2024-06-16T10:00:00Z",
        pool_length_m=25.0,
        stroke="backstroke",
        total_distance_m=1500.0,
        total_time_seconds=1350.0,
        num_lengths=60,
    )
    metrics2 = Metrics(pace=92.5, swolf=37.0, stroke_rate=28.5)

    # Create session for user2 (should not be returned)
    session_info3 = SessionInfo(
        start_time="2024-06-15T11:00:00Z",
        pool_length_m=50.0,
        stroke="butterfly",
        total_distance_m=2000.0,
        total_time_seconds=1800.0,
        num_lengths=40,
    )
    metrics3 = Metrics(pace=88.0, swolf=33.0, stroke_rate=32.0)

    session_history.save_session(user1_id, session_info1, metrics1, "uploads/s1.fit")
    session_history.save_session(user1_id, session_info2, metrics2, "uploads/s2.fit")
    session_history.save_session(user2_id, session_info3, metrics3, "uploads/s3.fit")

    # Get sessions for user1
    sessions = session_history.get_user_sessions(user1_id)

    assert len(sessions) == 2
    assert all(s.user_id == user1_id for s in sessions)
    assert sessions[0].session_date == "2024-06-16T10:00:00Z"  # Most recent first
    assert sessions[1].session_date == "2024-06-15T10:00:00Z"


@mock_aws
def test_get_user_sessions_returns_descending_order() -> None:
    """get_user_sessions should return sessions ordered by session_date descending (most recent first)."""
    import backend.session_history as session_history  # noqa: PLC0415
    session_history._dynamodb_resource = None

    _create_sessions_table()

    user_id = str(uuid.uuid4())

    # Create sessions in random order
    dates = [
        "2024-06-10T10:00:00Z",
        "2024-06-15T10:00:00Z",
        "2024-06-12T10:00:00Z",
        "2024-06-18T10:00:00Z",
    ]

    for date in dates:
        session_info = SessionInfo(
            start_time=date,
            pool_length_m=25.0,
            stroke="freestyle",
            total_distance_m=1000.0,
            total_time_seconds=900.0,
            num_lengths=40,
        )
        metrics = Metrics(pace=90.0, swolf=35.0, stroke_rate=30.0)
        session_history.save_session(user_id, session_info, metrics, f"uploads/{date}.fit")

    sessions = session_history.get_user_sessions(user_id)

    assert len(sessions) == 4
    # Should be in descending order (most recent first)
    assert sessions[0].session_date == "2024-06-18T10:00:00Z"
    assert sessions[1].session_date == "2024-06-15T10:00:00Z"
    assert sessions[2].session_date == "2024-06-12T10:00:00Z"
    assert sessions[3].session_date == "2024-06-10T10:00:00Z"


@mock_aws
def test_get_user_sessions_with_start_date_filter() -> None:
    """get_user_sessions should filter sessions by start_date (inclusive)."""
    import backend.session_history as session_history  # noqa: PLC0415
    session_history._dynamodb_resource = None

    _create_sessions_table()

    user_id = str(uuid.uuid4())

    dates = [
        "2024-06-10T10:00:00Z",
        "2024-06-12T10:00:00Z",
        "2024-06-15T10:00:00Z",
        "2024-06-18T10:00:00Z",
    ]

    for date in dates:
        session_info = SessionInfo(
            start_time=date,
            pool_length_m=25.0,
            stroke="freestyle",
            total_distance_m=1000.0,
            total_time_seconds=900.0,
            num_lengths=40,
        )
        metrics = Metrics(pace=90.0, swolf=35.0, stroke_rate=30.0)
        session_history.save_session(user_id, session_info, metrics, f"uploads/{date}.fit")

    # Filter sessions from 2024-06-12 onwards
    sessions = session_history.get_user_sessions(user_id, start_date="2024-06-12T10:00:00Z")

    assert len(sessions) == 3
    assert sessions[0].session_date == "2024-06-18T10:00:00Z"
    assert sessions[1].session_date == "2024-06-15T10:00:00Z"
    assert sessions[2].session_date == "2024-06-12T10:00:00Z"


@mock_aws
def test_get_user_sessions_with_end_date_filter() -> None:
    """get_user_sessions should filter sessions by end_date (inclusive)."""
    import backend.session_history as session_history  # noqa: PLC0415
    session_history._dynamodb_resource = None

    _create_sessions_table()

    user_id = str(uuid.uuid4())

    dates = [
        "2024-06-10T10:00:00Z",
        "2024-06-12T10:00:00Z",
        "2024-06-15T10:00:00Z",
        "2024-06-18T10:00:00Z",
    ]

    for date in dates:
        session_info = SessionInfo(
            start_time=date,
            pool_length_m=25.0,
            stroke="freestyle",
            total_distance_m=1000.0,
            total_time_seconds=900.0,
            num_lengths=40,
        )
        metrics = Metrics(pace=90.0, swolf=35.0, stroke_rate=30.0)
        session_history.save_session(user_id, session_info, metrics, f"uploads/{date}.fit")

    # Filter sessions up to 2024-06-15
    sessions = session_history.get_user_sessions(user_id, end_date="2024-06-15T10:00:00Z")

    assert len(sessions) == 3
    assert sessions[0].session_date == "2024-06-15T10:00:00Z"
    assert sessions[1].session_date == "2024-06-12T10:00:00Z"
    assert sessions[2].session_date == "2024-06-10T10:00:00Z"


@mock_aws
def test_get_user_sessions_with_date_range_filter() -> None:
    """get_user_sessions should filter sessions by both start_date and end_date (inclusive)."""
    import backend.session_history as session_history  # noqa: PLC0415
    session_history._dynamodb_resource = None

    _create_sessions_table()

    user_id = str(uuid.uuid4())

    dates = [
        "2024-06-10T10:00:00Z",
        "2024-06-12T10:00:00Z",
        "2024-06-15T10:00:00Z",
        "2024-06-18T10:00:00Z",
        "2024-06-20T10:00:00Z",
    ]

    for date in dates:
        session_info = SessionInfo(
            start_time=date,
            pool_length_m=25.0,
            stroke="freestyle",
            total_distance_m=1000.0,
            total_time_seconds=900.0,
            num_lengths=40,
        )
        metrics = Metrics(pace=90.0, swolf=35.0, stroke_rate=30.0)
        session_history.save_session(user_id, session_info, metrics, f"uploads/{date}.fit")

    # Filter sessions between 2024-06-12 and 2024-06-18 (inclusive)
    sessions = session_history.get_user_sessions(
        user_id, 
        start_date="2024-06-12T10:00:00Z", 
        end_date="2024-06-18T10:00:00Z"
    )

    assert len(sessions) == 3
    assert sessions[0].session_date == "2024-06-18T10:00:00Z"
    assert sessions[1].session_date == "2024-06-15T10:00:00Z"
    assert sessions[2].session_date == "2024-06-12T10:00:00Z"


@mock_aws
def test_get_user_sessions_returns_empty_list_for_no_sessions() -> None:
    """get_user_sessions should return empty list when user has no sessions."""
    import backend.session_history as session_history  # noqa: PLC0415
    session_history._dynamodb_resource = None

    _create_sessions_table()

    user_id = str(uuid.uuid4())

    sessions = session_history.get_user_sessions(user_id)

    assert sessions == []


@mock_aws
def test_get_user_sessions_deserializes_hr_zones() -> None:
    """get_user_sessions should deserialize hr_zones data correctly."""
    import backend.session_history as session_history  # noqa: PLC0415
    session_history._dynamodb_resource = None

    _create_sessions_table()

    user_id = str(uuid.uuid4())

    session_info = SessionInfo(
        start_time="2024-06-15T10:00:00Z",
        pool_length_m=25.0,
        stroke="freestyle",
        total_distance_m=1000.0,
        total_time_seconds=900.0,
        num_lengths=40,
    )
    metrics = Metrics(pace=90.0, swolf=35.0, stroke_rate=30.0)
    
    hr_zones = HRZonesData(
        zone_1_seconds=300,
        zone_2_seconds=600,
        zone_3_seconds=500,
        zone_4_seconds=300,
        zone_5_seconds=100,
        zone_1_percent=16.7,
        zone_2_percent=33.3,
        zone_3_percent=27.8,
        zone_4_percent=16.7,
        zone_5_percent=5.5,
        max_hr=180,
        zone_boundaries={
            1: (90, 108),
            2: (108, 126),
            3: (126, 144),
            4: (144, 162),
            5: (162, 180),
        },
    )

    session_history.save_session(user_id, session_info, metrics, "uploads/s1.fit", hr_zones=hr_zones)

    sessions = session_history.get_user_sessions(user_id)

    assert len(sessions) == 1
    assert sessions[0].hr_zones is not None
    assert sessions[0].hr_zones.zone_1_seconds == 300
    assert sessions[0].hr_zones.zone_2_seconds == 600
    assert sessions[0].hr_zones.zone_1_percent == 16.7
    assert sessions[0].hr_zones.max_hr == 180
    assert sessions[0].hr_zones.zone_boundaries[1] == (90, 108)


@mock_aws
def test_get_user_sessions_deserializes_ability_assessment() -> None:
    """get_user_sessions should deserialize ability_assessment data correctly."""
    import backend.session_history as session_history  # noqa: PLC0415
    session_history._dynamodb_resource = None

    _create_sessions_table()

    user_id = str(uuid.uuid4())

    session_info = SessionInfo(
        start_time="2024-06-15T10:00:00Z",
        pool_length_m=25.0,
        stroke="freestyle",
        total_distance_m=1000.0,
        total_time_seconds=900.0,
        num_lengths=40,
    )
    metrics = Metrics(pace=90.0, swolf=35.0, stroke_rate=30.0)
    
    ability_assessment = AbilityAssessment(
        percentile_estimate="Top 30%",
        local_ranking="Competitive at local club level",
        national_ranking="Above average for age group",
        competitive_analysis="Strong technique with room for endurance improvement",
    )

    session_history.save_session(
        user_id, session_info, metrics, "uploads/s1.fit", ability_assessment=ability_assessment
    )

    sessions = session_history.get_user_sessions(user_id)

    assert len(sessions) == 1
    assert sessions[0].ability_assessment is not None
    assert sessions[0].ability_assessment.percentile_estimate == "Top 30%"
    assert sessions[0].ability_assessment.local_ranking == "Competitive at local club level"
    assert sessions[0].ability_assessment.national_ranking == "Above average for age group"
    assert sessions[0].ability_assessment.competitive_analysis == "Strong technique with room for endurance improvement"
