"""
FIT file parser for AI Swim Coach.

Parses a Garmin .fit file and extracts swim metrics: pace, SWOLF, and stroke rate.

Processing strategy:
  1. Attempt to parse per-length records first (preferred).
  2. Fall back to per-lap records if no per-length data is found.
  3. Collect all missing metric names and raise MetricsMissingError if any are absent.
"""
from __future__ import annotations

import math
from typing import Any, Optional

from fitparse import FitFile

from models import Metrics, SessionInfo, LengthSplit


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class ParseError(Exception):
    """Raised when fitparse cannot parse the .fit file bytes (HTTP 422)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class MetricsMissingError(Exception):
    """Raised when one or more required metrics are absent from the file (HTTP 422).

    Attributes:
        missing: list of missing metric names (e.g. ["pace", "SWOLF"]).
    """

    def __init__(self, missing: list[str]) -> None:
        super().__init__(f"Missing metrics: {', '.join(missing)}")
        self.missing = missing


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def speed_to_pace(avg_speed: float) -> float:
    """Convert avg_speed (m/s) to pace (seconds per 100 m).

    Args:
        avg_speed: Speed in metres per second (must be > 0).

    Returns:
        Pace in seconds per 100 m.
    """
    return 100.0 / avg_speed


def compute_swolf(data: dict, length_m: float = 25.0) -> Optional[float]:
    """Extract or compute SWOLF from a record's field dict.

    Strategy:
      1. Use pre-computed 'swolf' field if present.
      2. Compute from total_strokes + total_elapsed_time (per-length SWOLF).
      3. Compute from avg_stroke_count + (length_m / avg_speed).

    Args:
        data:     Dict of field_name → value for one length/lap record.
        length_m: Pool length in metres (default 25 m).

    Returns:
        SWOLF value, or None if required fields are absent/invalid.
    """
    # 1. Check for pre-computed SWOLF field
    direct_swolf = data.get("swolf")
    if direct_swolf is not None:
        try:
            val = float(direct_swolf)
            if math.isfinite(val) and val > 0:
                return val
        except (ValueError, TypeError):
            pass

    # 2. Compute from total_strokes + total_elapsed_time (most common in per-length)
    total_strokes = data.get("total_strokes")
    total_elapsed_time = data.get("total_elapsed_time")
    if total_strokes is not None and total_elapsed_time is not None:
        try:
            swolf = float(total_strokes) + float(total_elapsed_time)
            if math.isfinite(swolf) and swolf > 0:
                return swolf
        except (ValueError, TypeError):
            pass

    # 3. Compute from avg_stroke_count + time_per_length
    avg_speed = data.get("avg_speed")
    avg_stroke_count = data.get("avg_stroke_count")

    if avg_speed is None or avg_stroke_count is None:
        return None
    if avg_speed <= 0:
        return None

    time_per_length = length_m / avg_speed
    swolf = avg_stroke_count + time_per_length

    if not math.isfinite(swolf):
        return None

    return swolf


def _average(values: list[float]) -> float:
    """Return the arithmetic mean of a non-empty list of finite floats."""
    return sum(values) / len(values)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_fit(fit_bytes: bytes) -> Metrics:
    """Parse raw .fit bytes and extract swim metrics.

    Processing order:
      1. Try per-length records.
      2. Fall back to per-lap records if no per-length data is found.

    Args:
        fit_bytes: Raw bytes of a Garmin .fit file.

    Returns:
        A :class:`Metrics` object with pace, swolf, and stroke_rate.

    Raises:
        ParseError:          If fitparse cannot parse the bytes.
        MetricsMissingError: If any required metric has no values in the file.
    """
    try:
        fitfile = FitFile(fit_bytes)
    except Exception as exc:
        raise ParseError(f"Malformed FIT file: {exc}") from exc

    # Try to get pool length from session record
    pool_length = 25.0  # default
    for record in fitfile.get_messages("session"):
        data = {f.name: f.value for f in record}
        pl = data.get("pool_length")
        if pl is not None and pl > 0:
            pool_length = float(pl)
            break

    pace_values: list[float] = []
    swolf_values: list[float] = []
    stroke_rate_values: list[float] = []

    # Prefer per-length records; fall back to per-lap records.
    for record_type in ("length", "lap"):
        for record in fitfile.get_messages(record_type):
            data = {f.name: f.value for f in record}

            # Pace from avg_speed (m/s → seconds per 100 m)
            avg_speed = data.get("avg_speed")
            if avg_speed is not None and avg_speed > 0:
                pace_values.append(speed_to_pace(avg_speed))

            # Stroke rate from avg_swimming_cadence (strokes per minute)
            cadence = data.get("avg_swimming_cadence")
            if cadence is not None:
                stroke_rate_values.append(float(cadence))

            # SWOLF: use pre-computed field or calculate from components
            swolf = compute_swolf(data, pool_length)
            if swolf is not None:
                swolf_values.append(swolf)

        # If we found any per-length data, stop — no need for lap fallback.
        if pace_values or swolf_values or stroke_rate_values:
            break

    # Collect all missing metrics before raising so the caller gets one error
    # that names every absent field.
    missing: list[str] = []
    if not pace_values:
        missing.append("pace")
    if not swolf_values:
        missing.append("SWOLF")
    if not stroke_rate_values:
        missing.append("stroke_rate")

    if missing:
        raise MetricsMissingError(missing)

    return Metrics(
        pace=_average(pace_values),
        swolf=_average(swolf_values),
        stroke_rate=_average(stroke_rate_values),
    )


# ---------------------------------------------------------------------------
# Stroke enum mapping (FIT SDK swim_stroke enum)
# ---------------------------------------------------------------------------

_STROKE_MAP: dict[int, str] = {
    0: "freestyle",
    1: "backstroke",
    2: "breaststroke",
    3: "butterfly",
    4: "drill",
    5: "mixed",
    6: "IM",
}


def _stroke_name(value: Any) -> str:
    """Convert a FIT swim_stroke enum value to a readable string."""
    if value is None:
        return "unknown"
    if isinstance(value, str):
        return value
    try:
        return _STROKE_MAP.get(int(value), "unknown")
    except (ValueError, TypeError):
        return "unknown"


def extract_session_info(fit_bytes: bytes) -> tuple[SessionInfo, list[LengthSplit]]:
    """Extract session-level info and per-length splits from a FIT file.

    Args:
        fit_bytes: Raw bytes of a Garmin .fit file.

    Returns:
        A tuple of (SessionInfo, list[LengthSplit]).

    Raises:
        ParseError: If fitparse cannot parse the bytes.
    """
    try:
        fitfile = FitFile(fit_bytes)
    except Exception as exc:
        raise ParseError(f"Malformed FIT file: {exc}") from exc

    # Extract session-level data
    start_time = ""
    pool_length_m = 25.0
    total_distance_m = 0.0
    total_time_seconds = 0.0

    for record in fitfile.get_messages("session"):
        data = {f.name: f.value for f in record}
        ts = data.get("start_time") or data.get("timestamp")
        if ts is not None:
            start_time = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
        pl = data.get("pool_length")
        if pl is not None and pl > 0:
            pool_length_m = float(pl)
        td = data.get("total_distance")
        if td is not None:
            total_distance_m = float(td)
        tt = data.get("total_elapsed_time") or data.get("total_timer_time")
        if tt is not None:
            total_time_seconds = float(tt)
        break  # only need first session record

    # Extract per-length splits
    splits: list[LengthSplit] = []
    stroke_counts: dict[str, int] = {}
    length_number = 0
    prev_timestamp = None

    for record in fitfile.get_messages("length"):
        data = {f.name: f.value for f in record}

        # Check for rest intervals (length_type == 1 means "idle")
        length_type = data.get("length_type")
        if length_type is not None:
            lt_str = str(length_type).lower()
            if lt_str in ("1", "idle"):
                # Capture rest duration and attach to preceding split
                elapsed = data.get("total_elapsed_time") or data.get("total_timer_time") or 0.0
                if splits and elapsed > 0:
                    splits[-1] = LengthSplit(
                        length_number=splits[-1].length_number,
                        time_seconds=splits[-1].time_seconds,
                        stroke=splits[-1].stroke,
                        strokes=splits[-1].strokes,
                        rest_after_seconds=round(float(elapsed), 2),
                        avg_hr=splits[-1].avg_hr,
                    )
                continue

        length_number += 1
        elapsed = data.get("total_elapsed_time") or data.get("total_timer_time") or 0.0
        stroke_val = data.get("swim_stroke")
        stroke = _stroke_name(stroke_val)
        total_strokes = data.get("total_strokes")
        strokes = int(total_strokes) if total_strokes is not None else 0
        avg_hr_val = data.get("avg_heart_rate")
        avg_hr = int(avg_hr_val) if avg_hr_val is not None and avg_hr_val > 0 else None

        # Detect rest from timestamp gaps (when no explicit idle records exist)
        current_timestamp = data.get("timestamp")
        if prev_timestamp is not None and current_timestamp is not None and splits:
            try:
                gap = (current_timestamp - prev_timestamp).total_seconds()
                # Sum of elapsed times for lengths sharing the previous timestamp
                # If gap > sum of their elapsed times + a small buffer, there's rest
                # Simpler: if timestamp changed and gap > current length time + 5s, it's a new set
                if gap > float(elapsed) + 5 and splits[-1].rest_after_seconds is None:
                    rest_duration = gap - float(elapsed)
                    if rest_duration > 3:  # At least 3 seconds to count as rest
                        splits[-1] = LengthSplit(
                            length_number=splits[-1].length_number,
                            time_seconds=splits[-1].time_seconds,
                            stroke=splits[-1].stroke,
                            strokes=splits[-1].strokes,
                            rest_after_seconds=round(rest_duration, 2),
                            avg_hr=splits[-1].avg_hr,
                        )
            except (TypeError, AttributeError):
                pass

        prev_timestamp = current_timestamp

        splits.append(LengthSplit(
            length_number=length_number,
            time_seconds=round(float(elapsed), 2),
            stroke=stroke,
            strokes=strokes,
            avg_hr=avg_hr,
        ))

        stroke_counts[stroke] = stroke_counts.get(stroke, 0) + 1

    # Determine dominant stroke
    dominant_stroke = "unknown"
    if stroke_counts:
        # Exclude "unknown" and "drill" when picking dominant stroke if possible
        filtered = {k: v for k, v in stroke_counts.items() if k not in ("unknown", "drill")}
        source = filtered if filtered else stroke_counts
        dominant_stroke = max(source, key=source.get)  # type: ignore[arg-type]

    num_lengths = len(splits)

    # If total_distance wasn't in session, estimate from pool length × lengths
    if total_distance_m == 0.0 and num_lengths > 0:
        total_distance_m = pool_length_m * num_lengths

    session_info = SessionInfo(
        start_time=start_time,
        pool_length_m=pool_length_m,
        stroke=dominant_stroke,
        total_distance_m=total_distance_m,
        total_time_seconds=total_time_seconds,
        num_lengths=num_lengths,
    )

    return session_info, splits
