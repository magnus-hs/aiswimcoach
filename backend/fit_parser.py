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

    # Drill-specific accumulation lists for fallback when all lengths are drills
    drill_pace_values: list[float] = []
    drill_swolf_values: list[float] = []
    drill_stroke_rate_values: list[float] = []

    # Prefer per-length records; fall back to per-lap records.
    for record_type in ("length", "lap"):
        for record in fitfile.get_messages(record_type):
            data = {f.name: f.value for f in record}

            stroke_val = data.get("swim_stroke")
            is_drill = _stroke_name(stroke_val) == "drill"

            # Pace from avg_speed (m/s → seconds per 100 m)
            avg_speed = data.get("avg_speed")
            if avg_speed is not None and avg_speed > 0:
                if not is_drill:
                    pace_values.append(speed_to_pace(avg_speed))
                else:
                    drill_pace_values.append(speed_to_pace(avg_speed))

            # Stroke rate from avg_swimming_cadence (strokes per minute)
            cadence = data.get("avg_swimming_cadence")
            if cadence is not None and cadence > 0:
                if not is_drill:
                    stroke_rate_values.append(float(cadence))
                else:
                    drill_stroke_rate_values.append(float(cadence))

            # SWOLF: use pre-computed field or calculate from components
            swolf = compute_swolf(data, pool_length)
            if swolf is not None:
                if not is_drill:
                    swolf_values.append(swolf)
                else:
                    drill_swolf_values.append(swolf)

        # If we found any per-length data, stop — no need for lap fallback.
        if pace_values or swolf_values or stroke_rate_values:
            break
        if drill_pace_values or drill_swolf_values or drill_stroke_rate_values:
            break

    # Fall back to drill values if no regular swim data exists
    final_pace = pace_values or drill_pace_values
    final_swolf = swolf_values or drill_swolf_values
    final_stroke_rate = stroke_rate_values or drill_stroke_rate_values

    # Collect all missing metrics before raising so the caller gets one error
    # that names every absent field.
    missing: list[str] = []
    if not final_pace:
        missing.append("pace")
    if not final_swolf:
        missing.append("SWOLF")
    if not final_stroke_rate:
        missing.append("stroke_rate")

    if missing:
        raise MetricsMissingError(missing)

    return Metrics(
        pace=_average(final_pace),
        swolf=_average(final_swolf),
        stroke_rate=_average(final_stroke_rate),
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

    # ------------------------------------------------------------------
    # Build lap boundaries. Garmin swim files record a "lap" message every
    # time the swimmer presses the lap button (typically once per set). Each
    # lap knows which length records belong to it (first_length_index +
    # num_lengths) and its own start_time / elapsed time. This is the
    # authoritative source for set/rest structure — far more reliable than
    # the per-length `timestamp` field, which Garmin writes in batches (many
    # lengths share one timestamp), making timestamp-gap heuristics misfire
    # and incorrectly split continuous swims (e.g. a 400m read as 250m).
    #
    # Strategy:
    #   - For each lap, compute the rest that follows it as the gap between
    #     the lap's end (start_time + elapsed) and the NEXT lap's start_time.
    #   - Attach that rest to the last active length of the lap.
    # ------------------------------------------------------------------
    lap_infos: list[dict[str, Any]] = []
    for record in fitfile.get_messages("lap"):
        data = {f.name: f.value for f in record}
        st = data.get("start_time")
        el = data.get("total_elapsed_time") or data.get("total_timer_time") or 0.0
        first_idx = data.get("first_length_index")
        n_lengths = data.get("num_lengths")
        if n_lengths is None:
            n_lengths = data.get("num_active_lengths")
        lap_infos.append({
            "start_time": st,
            "elapsed": float(el) if el is not None else 0.0,
            "first_index": int(first_idx) if first_idx is not None else None,
            "num_lengths": int(n_lengths) if n_lengths is not None else None,
        })

    # rest_by_raw_index maps a 0-based length-message index to the rest (s)
    # that should be recorded after that length.
    rest_by_raw_index: dict[int, float] = {}
    for i, lap in enumerate(lap_infos):
        first_idx = lap["first_index"]
        n_lengths = lap["num_lengths"]
        if first_idx is None or n_lengths is None or n_lengths <= 0:
            continue
        last_raw_index = first_idx + n_lengths - 1
        # Rest = gap between this lap's end and the next lap's start.
        if i + 1 < len(lap_infos):
            next_start = lap_infos[i + 1]["start_time"]
            this_start = lap["start_time"]
            this_elapsed = lap["elapsed"]
            if next_start is not None and this_start is not None:
                try:
                    lap_end = this_start.timestamp() + this_elapsed
                    rest = next_start.timestamp() - lap_end
                    if rest > 2:  # ignore sub-2s turnaround noise
                        rest_by_raw_index[last_raw_index] = round(rest, 2)
                except (TypeError, AttributeError):
                    pass

    have_lap_data = bool(rest_by_raw_index) or len(lap_infos) > 1

    # Extract per-length splits
    splits: list[LengthSplit] = []
    stroke_counts: dict[str, int] = {}
    length_number = 0
    raw_index = -1  # 0-based index over ALL length messages (incl. idle)
    prev_start_time = None
    prev_elapsed = 0.0

    for record in fitfile.get_messages("length"):
        data = {f.name: f.value for f in record}
        raw_index += 1

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

        current_start_time = data.get("start_time")

        # Fallback rest detection (only when lap messages are unavailable):
        # use each length's reliable start_time, NOT the batched `timestamp`.
        # If the actual start of this length is later than the expected start
        # (previous start + previous elapsed) by a meaningful margin, the gap
        # is rest between sets.
        if not have_lap_data and prev_start_time is not None and current_start_time is not None and splits:
            try:
                expected_next = prev_start_time.timestamp() + prev_elapsed
                gap = current_start_time.timestamp() - expected_next
                if gap > 3 and splits[-1].rest_after_seconds is None:
                    splits[-1] = LengthSplit(
                        length_number=splits[-1].length_number,
                        time_seconds=splits[-1].time_seconds,
                        stroke=splits[-1].stroke,
                        strokes=splits[-1].strokes,
                        rest_after_seconds=round(gap, 2),
                        avg_hr=splits[-1].avg_hr,
                    )
            except (TypeError, AttributeError):
                pass

        prev_start_time = current_start_time
        prev_elapsed = float(elapsed)

        splits.append(LengthSplit(
            length_number=length_number,
            time_seconds=round(float(elapsed), 2),
            stroke=stroke,
            strokes=strokes,
            avg_hr=avg_hr,
        ))

        # Apply lap-boundary rest (authoritative) to this length if applicable.
        if raw_index in rest_by_raw_index:
            splits[-1] = LengthSplit(
                length_number=splits[-1].length_number,
                time_seconds=splits[-1].time_seconds,
                stroke=splits[-1].stroke,
                strokes=splits[-1].strokes,
                rest_after_seconds=rest_by_raw_index[raw_index],
                avg_hr=splits[-1].avg_hr,
            )

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
