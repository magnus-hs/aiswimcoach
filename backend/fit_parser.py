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
from typing import Optional

from fitparse import FitFile

from models import Metrics


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
