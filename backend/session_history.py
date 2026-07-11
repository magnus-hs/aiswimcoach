"""
Session history module for AI Swim Coach.

Provides functions for persisting and retrieving swim session data.
Sessions are stored in DynamoDB with user_id as partition key and
session_date as sort key, with a GSI on session_id for direct lookups.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

from models import (
    AbilityAssessment,
    HRZonesData,
    Metrics,
    Session,
    SessionInfo,
)

# Module-level placeholder for DynamoDB resource (lazy initialization)
_dynamodb_resource = None


def _get_dynamodb() -> "boto3.resources.base.ServiceResource":
    """Return the (cached) DynamoDB resource, creating it if necessary."""
    global _dynamodb_resource  # noqa: PLW0603
    if _dynamodb_resource is None:
        _dynamodb_resource = boto3.resource("dynamodb")
    return _dynamodb_resource


def _serialize_hr_zones(hr_zones: HRZonesData | None) -> dict | None:
    """Serialize HRZonesData to DynamoDB-compatible dict.
    
    Args:
        hr_zones: HRZonesData object or None
        
    Returns:
        dict with Decimal values for DynamoDB or None
    """
    if hr_zones is None:
        return None
    
    return {
        "zone_1_seconds": hr_zones.zone_1_seconds,
        "zone_2_seconds": hr_zones.zone_2_seconds,
        "zone_3_seconds": hr_zones.zone_3_seconds,
        "zone_4_seconds": hr_zones.zone_4_seconds,
        "zone_5_seconds": hr_zones.zone_5_seconds,
        "zone_1_percent": Decimal(str(hr_zones.zone_1_percent)),
        "zone_2_percent": Decimal(str(hr_zones.zone_2_percent)),
        "zone_3_percent": Decimal(str(hr_zones.zone_3_percent)),
        "zone_4_percent": Decimal(str(hr_zones.zone_4_percent)),
        "zone_5_percent": Decimal(str(hr_zones.zone_5_percent)),
        "max_hr": hr_zones.max_hr,
        "zone_boundaries": {
            str(k): {"lower": v[0], "upper": v[1]}
            for k, v in hr_zones.zone_boundaries.items()
        },
    }


def _serialize_ability_assessment(assessment: AbilityAssessment | None) -> dict | None:
    """Serialize AbilityAssessment to DynamoDB-compatible dict.
    
    Args:
        assessment: AbilityAssessment object or None
        
    Returns:
        dict with assessment fields or None
    """
    if assessment is None:
        return None
    
    return {
        "percentile_estimate": assessment.percentile_estimate,
        "local_ranking": assessment.local_ranking,
        "national_ranking": assessment.national_ranking,
        "competitive_analysis": assessment.competitive_analysis,
    }


def _deserialize_hr_zones(hr_zones_dict: dict | None) -> HRZonesData | None:
    """Deserialize HRZonesData from DynamoDB dict.
    
    Args:
        hr_zones_dict: dict from DynamoDB or None
        
    Returns:
        HRZonesData object or None
    """
    if hr_zones_dict is None:
        return None
    
    # Convert Decimal to int for boundaries, float for percentages
    return HRZonesData(
        zone_1_seconds=int(hr_zones_dict["zone_1_seconds"]),
        zone_2_seconds=int(hr_zones_dict["zone_2_seconds"]),
        zone_3_seconds=int(hr_zones_dict["zone_3_seconds"]),
        zone_4_seconds=int(hr_zones_dict["zone_4_seconds"]),
        zone_5_seconds=int(hr_zones_dict["zone_5_seconds"]),
        zone_1_percent=float(hr_zones_dict["zone_1_percent"]),
        zone_2_percent=float(hr_zones_dict["zone_2_percent"]),
        zone_3_percent=float(hr_zones_dict["zone_3_percent"]),
        zone_4_percent=float(hr_zones_dict["zone_4_percent"]),
        zone_5_percent=float(hr_zones_dict["zone_5_percent"]),
        max_hr=int(hr_zones_dict["max_hr"]),
        zone_boundaries={
            int(k): (int(v["lower"]), int(v["upper"]))
            for k, v in hr_zones_dict["zone_boundaries"].items()
        },
    )


def _deserialize_ability_assessment(assessment_dict: dict | None) -> AbilityAssessment | None:
    """Deserialize AbilityAssessment from DynamoDB dict.
    
    Args:
        assessment_dict: dict from DynamoDB or None
        
    Returns:
        AbilityAssessment object or None
    """
    if assessment_dict is None:
        return None
    
    return AbilityAssessment(
        percentile_estimate=assessment_dict["percentile_estimate"],
        local_ranking=assessment_dict["local_ranking"],
        national_ranking=assessment_dict["national_ranking"],
        competitive_analysis=assessment_dict["competitive_analysis"],
    )


def _deserialize_splits(splits_list: list | None) -> list | None:
    """Deserialize splits from DynamoDB list."""
    if splits_list is None:
        return None

    return [
        {
            "length_number": int(s.get("length_number", 0)),
            "time_seconds": float(s.get("time_seconds", 0)),
            "strokes": int(s.get("strokes", 0)),
            "stroke": str(s.get("stroke", "unknown")),
            "rest_after_seconds": float(s["rest_after_seconds"]) if s.get("rest_after_seconds") is not None else None,
            "avg_hr": int(s["avg_hr"]) if s.get("avg_hr") is not None else None,
        }
        for s in splits_list
    ]


def _deserialize_hr_timeseries(ts_list: list | None) -> list | None:
    """Deserialize HR time series from DynamoDB list.

    Args:
        ts_list: list of {t, hr} dicts from DynamoDB or None

    Returns:
        list of {t: int, hr: int} dicts, or None
    """
    if ts_list is None:
        return None

    return [
        {"t": int(p.get("t", 0)), "hr": int(p.get("hr", 0))}
        for p in ts_list
    ]


def save_session(
    user_id: str,
    session_info: SessionInfo,
    metrics: Metrics,
    s3_key: str,
    hr_zones: HRZonesData | None = None,
    ability_assessment: AbilityAssessment | None = None,
    splits: list | None = None,
    coaching: dict | None = None,
    hr_timeseries: list | None = None,
) -> str:
    """Persist session to Sessions table.
    
    Generates a unique session_id (UUID v4) and stores the complete session
    record in DynamoDB. The Sessions table uses user_id as partition key and
    session_date as sort key, with a GSI on session_id for direct lookups.
    
    Args:
        user_id: User identifier (UUID v4)
        session_info: Session metadata (start_time, pool_length, etc.)
        metrics: Calculated metrics (pace, swolf, stroke_rate)
        s3_key: S3 key for the FIT file
        hr_zones: Optional HR zones data
        ability_assessment: Optional ability assessment
        splits: Optional list of per-length split dicts
        coaching: Optional coaching tips dict (tips + drill)
    
    Returns:
        session_id (UUID v4 string)
    
    Raises:
        Exception: Any exception raised by DynamoDB put_item operation
    """
    # Generate unique session_id
    session_id = str(uuid.uuid4())
    
    # Get current timestamp for uploaded_at
    now = datetime.now(tz=timezone.utc)
    uploaded_at = now.isoformat()
    
    # Build DynamoDB item
    item = {
        "session_id": session_id,
        "user_id": user_id,
        "session_date": session_info.start_time,
        "pool_length_meters": int(session_info.pool_length_m),
        "total_distance_meters": int(session_info.total_distance_m),
        "total_time_seconds": int(session_info.total_time_seconds),
        "stroke_type": session_info.stroke,
        "average_pace_per_100m": Decimal(str(round(metrics.pace, 2))),
        "swolf_score": int(metrics.swolf),
        "stroke_rate": Decimal(str(round(metrics.stroke_rate, 1))),
        "uploaded_at": uploaded_at,
        "s3_key": s3_key,
    }
    
    # Add optional fields if present
    if hr_zones is not None:
        item["hr_zones"] = _serialize_hr_zones(hr_zones)
    
    if ability_assessment is not None:
        item["ability_assessment"] = _serialize_ability_assessment(ability_assessment)
    
    if splits is not None and len(splits) > 0:
        # Store splits as a list of dicts with Decimal for numeric values
        serialized_splits = []
        for i, s in enumerate(splits):
            split_item: dict = {
                "length_number": int(s.get("length_number", i + 1)),
                "time_seconds": Decimal(str(round(float(s.get("time_seconds", 0)), 1))),
                "strokes": int(s.get("strokes", 0)),
                "stroke": str(s.get("stroke", "unknown")),
            }
            if s.get("rest_after_seconds") is not None:
                split_item["rest_after_seconds"] = Decimal(str(round(float(s["rest_after_seconds"]), 2)))
            if s.get("avg_hr") is not None:
                split_item["avg_hr"] = int(s["avg_hr"])
            serialized_splits.append(split_item)
        item["splits"] = serialized_splits
    
    if coaching is not None:
        item["coaching"] = coaching
    
    if hr_timeseries is not None and len(hr_timeseries) > 0:
        item["hr_timeseries"] = [
            {"t": int(p["t"]), "hr": int(p["hr"])}
            for p in hr_timeseries
        ]
    
    # Get table name from environment
    table_name = os.environ.get("SESSIONS_TABLE", "Sessions")
    
    # Write to DynamoDB
    table = _get_dynamodb().Table(table_name)
    table.put_item(Item=item)
    
    return session_id


def get_user_sessions(
    user_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int | None = None,
    lightweight: bool = False,
) -> list[Session]:
    """Retrieve user's session history.
    
    Queries the Sessions table by user_id (partition key) with optional
    date range filtering on session_date (sort key). Returns sessions
    ordered by session_date in descending order (most recent first).
    
    Args:
        user_id: User identifier (UUID v4)
        start_date: Optional ISO 8601 date filter (inclusive)
        end_date: Optional ISO 8601 date filter (inclusive)
        limit: Optional max number of sessions to return (DynamoDB-level)
        lightweight: If True, use ProjectionExpression to skip heavy fields
    
    Returns:
        List of Session objects ordered by session_date descending
    
    Raises:
        Exception: Any exception raised by DynamoDB query operation
    """
    # Get table name from environment
    table_name = os.environ.get("SESSIONS_TABLE", "Sessions")
    table = _get_dynamodb().Table(table_name)
    
    # Build query parameters
    query_params: dict = {
        "KeyConditionExpression": Key("user_id").eq(user_id),
        "ScanIndexForward": False,  # Descending order (most recent first)
    }
    
    # For lightweight list view, only fetch fields needed for activity cards
    if lightweight:
        query_params["ProjectionExpression"] = (
            "session_id, user_id, session_date, pool_length_meters, "
            "total_distance_meters, total_time_seconds, stroke_type, "
            "average_pace_per_100m, swolf_score, stroke_rate, "
            "uploaded_at, s3_key, kudos, comments"
        )
    
    # Add date range filtering if provided
    if start_date is not None and end_date is not None:
        query_params["KeyConditionExpression"] &= Key("session_date").between(
            start_date, end_date
        )
    elif start_date is not None:
        query_params["KeyConditionExpression"] &= Key("session_date").gte(
            start_date
        )
    elif end_date is not None:
        query_params["KeyConditionExpression"] &= Key("session_date").lte(
            end_date
        )
    else:
        # Default: only fetch sessions with valid ISO date format (1990-2030)
        # This excludes garbage dates like "9634", "92125", "PLAN#..." at the DynamoDB level
        query_params["KeyConditionExpression"] &= Key("session_date").between(
            "1990", "2030-12-31T23:59:59"
        )
    
    # Execute query — with pagination support and optional limit
    items = []
    sessions_found = 0
    target_limit = limit or 999999
    
    while True:
        response = table.query(**query_params)
        batch_items = response.get("Items", [])
        
        for item in batch_items:
            # Skip plan items
            if item.get("session_date", "").startswith("PLAN#"):
                continue
            if item.get("session_date", "").startswith("MPLAN#"):
                continue
            if "session_id" not in item:
                continue
            items.append(item)
            sessions_found += 1
            if sessions_found >= target_limit:
                break
        
        if sessions_found >= target_limit:
            break
        if "LastEvaluatedKey" not in response:
            break
        query_params["ExclusiveStartKey"] = response["LastEvaluatedKey"]
    
    # Deserialize items into Session objects
    sessions = []
    for item in items:
        session = Session(
            session_id=item["session_id"],
            user_id=item["user_id"],
            session_date=item["session_date"],
            pool_length_meters=int(item.get("pool_length_meters", 25)),
            total_distance_meters=int(item.get("total_distance_meters", 0)),
            total_time_seconds=int(item.get("total_time_seconds", 0)),
            stroke_type=item.get("stroke_type", "unknown"),
            average_pace_per_100m=float(item.get("average_pace_per_100m", 0)),
            swolf_score=int(item.get("swolf_score", 0)),
            stroke_rate=float(item.get("stroke_rate", 0)),
            uploaded_at=item.get("uploaded_at", ""),
            s3_key=item.get("s3_key", ""),
            hr_zones=_deserialize_hr_zones(item.get("hr_zones")) if not lightweight else None,
            ability_assessment=_deserialize_ability_assessment(item.get("ability_assessment")) if not lightweight else None,
            splits=_deserialize_splits(item.get("splits")),
            coaching=item.get("coaching") if not lightweight else None,
            hr_timeseries=_deserialize_hr_timeseries(item.get("hr_timeseries")) if not lightweight else None,
            kudos=item.get("kudos"),
            comments=item.get("comments"),
        )
        sessions.append(session)
    
    return sessions


def get_session_by_id(session_id: str) -> Session:
    """Retrieve single session by ID.
    
    Queries the session_id-index GSI to retrieve the full session record.
    Returns a complete Session object with all details including optional
    HR zones and ability assessment.
    
    Args:
        session_id: Session identifier (UUID v4)
    
    Returns:
        Session object with full details
    
    Raises:
        ValueError: If session doesn't exist (404 case)
        Exception: Any exception raised by DynamoDB query operation
    """
    # Get table name from environment
    table_name = os.environ.get("SESSIONS_TABLE", "Sessions")
    
    # Query the session_id-index GSI
    table = _get_dynamodb().Table(table_name)
    response = table.query(
        IndexName="session_id-index",
        KeyConditionExpression=Key("session_id").eq(session_id),
    )
    
    # Check if session exists
    items = response.get("Items", [])
    if not items:
        raise ValueError(f"Session not found: {session_id}")
    
    # Get the first (and only) item
    item = items[0]
    
    # Deserialize optional fields
    hr_zones = _deserialize_hr_zones(item.get("hr_zones"))
    ability_assessment = _deserialize_ability_assessment(item.get("ability_assessment"))
    
    # Build and return Session object
    return Session(
        session_id=item["session_id"],
        user_id=item["user_id"],
        session_date=item["session_date"],
        pool_length_meters=int(item["pool_length_meters"]),
        total_distance_meters=int(item["total_distance_meters"]),
        total_time_seconds=int(item["total_time_seconds"]),
        stroke_type=item["stroke_type"],
        average_pace_per_100m=float(item["average_pace_per_100m"]),
        swolf_score=int(item["swolf_score"]),
        stroke_rate=float(item["stroke_rate"]),
        uploaded_at=item["uploaded_at"],
        s3_key=item["s3_key"],
        hr_zones=hr_zones,
        ability_assessment=ability_assessment,
        splits=_deserialize_splits(item.get("splits")),
        coaching=item.get("coaching"),
        hr_timeseries=_deserialize_hr_timeseries(item.get("hr_timeseries")),
        kudos=item.get("kudos"),
        comments=item.get("comments"),
    )


def compute_stroke_breakdown(
    splits: list | None,
    fallback_stroke: str | None = None,
) -> list[dict]:
    """Compute a per-stroke percentage breakdown from per-length splits.

    Each length is treated as an equal unit (pool length is constant within a
    session), so the percentage is the share of lengths swum with each stroke.

    Args:
        splits:          List of split dicts (each with a "stroke" key), or None.
        fallback_stroke: Stroke to report as 100% when no splits are available.

    Returns:
        A list of {"stroke": str, "lengths": int, "percent": float} entries
        sorted by length count descending. Percentages are rounded to one
        decimal place and sum to ~100. Returns an empty list if neither splits
        nor a fallback stroke are available.
    """
    counts: dict[str, int] = {}
    if splits:
        for s in splits:
            stroke = str(s.get("stroke", "unknown")) if isinstance(s, dict) else str(getattr(s, "stroke", "unknown"))
            counts[stroke] = counts.get(stroke, 0) + 1

    if not counts:
        if fallback_stroke:
            return [{"stroke": fallback_stroke, "lengths": 0, "percent": 100.0}]
        return []

    total = sum(counts.values())
    breakdown = [
        {
            "stroke": stroke,
            "lengths": n,
            "percent": round(n * 100.0 / total, 1),
        }
        for stroke, n in counts.items()
    ]
    # Sort by length count descending, then stroke name for stable ordering.
    breakdown.sort(key=lambda b: (-b["lengths"], b["stroke"]))
    return breakdown


def aggregate_daily_distances(sessions: list[Session]) -> dict[str, int]:
    """Aggregate total distance by date from a list of sessions.
    
    Groups sessions by their session_date (date part only) and sums the
    total_distance_meters for each date. This is useful for generating
    progress graphs showing daily training volume.
    
    Args:
        sessions: List of Session objects
    
    Returns:
        dict mapping date string (YYYY-MM-DD) to total distance in meters
    
    Examples:
        >>> s1 = Session(session_date="2024-01-15T10:00:00Z", total_distance_meters=1000, ...)
        >>> s2 = Session(session_date="2024-01-15T16:00:00Z", total_distance_meters=1500, ...)
        >>> s3 = Session(session_date="2024-01-16T10:00:00Z", total_distance_meters=2000, ...)
        >>> aggregate_daily_distances([s1, s2, s3])
        {'2024-01-15': 2500, '2024-01-16': 2000}
    """
    daily_totals: dict[str, int] = {}
    
    for session in sessions:
        # Extract date part from ISO 8601 timestamp (YYYY-MM-DD)
        # session_date format: "2024-06-15T10:30:00Z"
        date_part = session.session_date.split("T")[0]
        
        # Sum distances for each date
        daily_totals[date_part] = (
            daily_totals.get(date_part, 0) + session.total_distance_meters
        )
    
    return daily_totals
