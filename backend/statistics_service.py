"""Pre-computed user statistics stored in S3."""
import json
import logging
import os
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def _get_s3_client():
    return boto3.client("s3")


def _get_bucket():
    return os.environ["S3_BUCKET"]


def _stats_key(user_id: str) -> str:
    return f"statistics/{user_id}/stats.json"


def get_statistics(user_id: str) -> dict | None:
    """Read pre-computed stats from S3. Returns None if not yet computed."""
    try:
        s3 = _get_s3_client()
        response = s3.get_object(Bucket=_get_bucket(), Key=_stats_key(user_id))
        body = response["Body"].read().decode("utf-8")
        return json.loads(body)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "NoSuchKey":
            return None
        logger.error("Failed to read statistics for user %s: %s", user_id, exc)
        return None
    except Exception as exc:
        logger.error("Unexpected error reading statistics for user %s: %s", user_id, exc)
        return None


def recompute_user_statistics(user_id: str) -> dict:
    """Recompute yearly statistics from all sessions and store in S3.

    Queries all sessions for the user, groups by year, computes totals,
    and stores the result in S3 for instant retrieval.
    """
    from session_history import get_user_sessions

    sessions = get_user_sessions(user_id, lightweight=True)

    def _sane_time(s) -> int:
        """Return a plausible session duration in seconds.

        Some FIT files recorded absurd elapsed times (watch left running for
        hours). If the stored time implies a pace slower than 600 s/100m
        (impossibly slow), fall back to the sum of the per-length swim times,
        or a nominal 120 s/100m estimate if no splits are available.
        """
        dist = s.total_distance_meters or 0
        stored = s.total_time_seconds or 0
        if dist <= 0:
            return stored
        implied_pace = stored / (dist / 100.0)
        if implied_pace <= 600:
            return stored
        # Implausible — recompute from splits if we have them
        splits = s.splits or []
        split_sum = 0
        for sp in splits:
            try:
                split_sum += int(float(sp.get("time_seconds", 0)))
            except (TypeError, ValueError):
                pass
        if split_sum > 0:
            return split_sum
        # No splits — estimate at 120 s/100m
        return int((dist / 100.0) * 120)

    # Group by year
    by_year: dict[int, list] = {}
    for s in sessions:
        try:
            year = int(s.session_date[:4])
            if year < 1990 or year > 2100:
                continue
        except (ValueError, TypeError):
            continue
        if year not in by_year:
            by_year[year] = []
        by_year[year].append(s)

    # Compute per-year stats
    yearly = []
    for year in sorted(by_year.keys(), reverse=True):
        year_sessions = by_year[year]
        total_dist = sum(s.total_distance_meters for s in year_sessions)
        total_time = sum(_sane_time(s) for s in year_sessions)
        paces = [s.average_pace_per_100m for s in year_sessions if s.average_pace_per_100m > 0]
        swolfs = [s.swolf_score for s in year_sessions if s.swolf_score > 0]
        longest = max((s.total_distance_meters for s in year_sessions), default=0)

        yearly.append({
            "year": year,
            "sessions": len(year_sessions),
            "total_distance_m": total_dist,
            "total_time_seconds": total_time,
            "avg_pace": round(sum(paces) / len(paces), 1) if paces else 0,
            "avg_swolf": round(sum(swolfs) / len(swolfs)) if swolfs else 0,
            "longest_session_m": longest,
        })

    # All-time totals
    total_sessions = sum(len(v) for v in by_year.values())
    total_distance = sum(s.total_distance_meters for ss in by_year.values() for s in ss)
    total_time = sum(_sane_time(s) for ss in by_year.values() for s in ss)

    stats = {
        "all_time": {
            "sessions": total_sessions,
            "total_distance_m": total_distance,
            "total_time_seconds": total_time,
        },
        "yearly": yearly,
        "computed_at": datetime.now(tz=timezone.utc).isoformat(),
    }

    # Store in S3
    try:
        s3 = _get_s3_client()
        s3.put_object(
            Bucket=_get_bucket(),
            Key=_stats_key(user_id),
            Body=json.dumps(stats).encode("utf-8"),
            ContentType="application/json",
        )
    except Exception as exc:
        logger.error("Failed to store statistics for user %s: %s", user_id, exc)

    return stats
