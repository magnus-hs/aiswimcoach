"""
Shared data models for the AI Swim Coach backend.

Invariants:
  Metrics:         all three float fields must be finite (not NaN, not ±Infinity)
  CoachingResponse: tips contains exactly 3 items, each non-empty and ≤ 300 chars;
                    drill is non-empty and ≤ 500 chars
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class Metrics:
    """Extracted swim metrics from a FIT file.

    All fields must be finite floats (no NaN, no ±Infinity).

    Attributes:
        pace:         seconds per 100 m
        swolf:        dimensionless SWOLF score
        stroke_rate:  strokes per minute
    """
    pace: float
    swolf: float
    stroke_rate: float

    def __post_init__(self) -> None:
        for field_name in ("pace", "swolf", "stroke_rate"):
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)):
                raise TypeError(
                    f"Metrics.{field_name} must be a float, got {type(value).__name__}"
                )
            if not math.isfinite(float(value)):
                raise ValueError(
                    f"Metrics.{field_name} must be a finite number, got {value}"
                )


@dataclass
class LengthSplit:
    """Per-length split data."""
    length_number: int
    time_seconds: float
    stroke: str
    strokes: int
    rest_after_seconds: float | None = None
    avg_hr: int | None = None


@dataclass
class SessionInfo:
    """High-level session information extracted from the FIT file."""
    start_time: str          # ISO format datetime string
    pool_length_m: float
    stroke: str              # dominant stroke
    total_distance_m: float
    total_time_seconds: float
    num_lengths: int


@dataclass
class CoachingResponse:
    """AI-generated coaching response.

    Invariants:
      - tips contains exactly 3 items
      - each tip is a non-empty string of ≤ 300 characters
      - drill is a non-empty string of ≤ 500 characters

    Attributes:
        tips:  exactly three concise, actionable improvement tips
        drill: one specific drill recommendation targeting the swimmer's weakest area
    """
    tips: list[str]
    drill: str

    def __post_init__(self) -> None:
        if len(self.tips) != 3:
            raise ValueError(
                f"CoachingResponse.tips must contain exactly 3 items, got {len(self.tips)}"
            )
        for i, tip in enumerate(self.tips):
            if not isinstance(tip, str) or not tip:
                raise ValueError(f"CoachingResponse.tips[{i}] must be a non-empty string")
            if len(tip) > 300:
                raise ValueError(
                    f"CoachingResponse.tips[{i}] exceeds 300 characters (length={len(tip)})"
                )
        if not isinstance(self.drill, str) or not self.drill:
            raise ValueError("CoachingResponse.drill must be a non-empty string")
        if len(self.drill) > 500:
            raise ValueError(
                f"CoachingResponse.drill exceeds 500 characters (length={len(self.drill)})"
            )


@dataclass
class TrainingGoal:
    """User-submitted training goal."""
    event: str
    target_time: str
    volume_meters: int
    timeframe: str


@dataclass
class TrainingPlan:
    """AI-generated training session plan.

    Extended with goal likelihood assessment that evaluates whether the
    swimmer's stated goal is achievable based on current performance.

    Attributes:
        session_title:   title/name of the training session
        warm_up:         list of warm-up exercises
        main_set:        list of main set exercises
        cool_down:       list of cool-down exercises
        total_distance:  total planned distance in meters
        focus_notes:     coaching notes on session focus areas
        goal_likelihood: AI assessment of goal achievability (max 300 characters)
    """
    session_title: str
    warm_up: list[str]
    main_set: list[str]
    cool_down: list[str]
    total_distance: int
    focus_notes: str
    goal_likelihood: str

    def __post_init__(self) -> None:
        # Validate goal_likelihood
        if not isinstance(self.goal_likelihood, str):
            raise TypeError(
                f"TrainingPlan.goal_likelihood must be a str, got {type(self.goal_likelihood).__name__}"
            )
        if len(self.goal_likelihood) == 0:
            raise ValueError("goal_likelihood must be non-empty")
        if len(self.goal_likelihood) > 300:
            raise ValueError(
                f"goal_likelihood must not exceed 300 characters (length={len(self.goal_likelihood)})"
            )


@dataclass
class UserProfile:
    """User demographic and ability profile.

    Invariants:
      - age must be between 10 and 100 inclusive
      - nationality must be 1-100 characters if provided
      - locality must be 1-100 characters if provided
      - ability_level must be one of: beginner, intermediate, advanced, elite (case-insensitive)

    Attributes:
        age:           user's age in years (10-100)
        nationality:   user's nationality (max 100 characters)
        locality:      user's locality/region (max 100 characters)
        ability_level: user's self-assessed ability level
    """
    age: int
    nationality: str
    locality: str
    ability_level: str

    def __post_init__(self) -> None:
        # Validate age range
        if not isinstance(self.age, int):
            raise TypeError(f"UserProfile.age must be an int, got {type(self.age).__name__}")
        if self.age < 10 or self.age > 100:
            raise ValueError("age must be between 10 and 100")

        # Validate nationality length
        if not isinstance(self.nationality, str):
            raise TypeError(f"UserProfile.nationality must be a str, got {type(self.nationality).__name__}")
        if len(self.nationality) == 0 or len(self.nationality) > 100:
            raise ValueError("nationality must be 1-100 characters if provided")

        # Validate locality length
        if not isinstance(self.locality, str):
            raise TypeError(f"UserProfile.locality must be a str, got {type(self.locality).__name__}")
        if len(self.locality) == 0 or len(self.locality) > 100:
            raise ValueError("locality must be 1-100 characters if provided")

        # Validate ability_level enum
        if not isinstance(self.ability_level, str):
            raise TypeError(f"UserProfile.ability_level must be a str, got {type(self.ability_level).__name__}")
        valid_levels = {"beginner", "intermediate", "advanced", "elite"}
        if self.ability_level.lower() not in valid_levels:
            raise ValueError("ability_level must be one of: beginner, intermediate, advanced, elite")


@dataclass
class HRZonesData:
    """Heart rate zone distribution data.

    Invariants:
      - all zone times must be non-negative integers
      - all zone percentages must be non-negative floats
      - zone percentages should sum to approximately 100% (99.0-101.0 accounting for rounding)
      - max_hr must be a positive integer
      - zone_boundaries must contain exactly 5 zones with valid ranges

    Attributes:
        zone_1_seconds:   time spent in Zone 1 (50-60% max HR) in seconds
        zone_2_seconds:   time spent in Zone 2 (60-70% max HR) in seconds
        zone_3_seconds:   time spent in Zone 3 (70-80% max HR) in seconds
        zone_4_seconds:   time spent in Zone 4 (80-90% max HR) in seconds
        zone_5_seconds:   time spent in Zone 5 (90-100% max HR) in seconds
        zone_1_percent:   percentage of total time in Zone 1 (one decimal place)
        zone_2_percent:   percentage of total time in Zone 2 (one decimal place)
        zone_3_percent:   percentage of total time in Zone 3 (one decimal place)
        zone_4_percent:   percentage of total time in Zone 4 (one decimal place)
        zone_5_percent:   percentage of total time in Zone 5 (one decimal place)
        max_hr:           maximum heart rate used for zone calculations
        zone_boundaries:  dict mapping zone number (1-5) to (lower_bound, upper_bound) tuples
    """
    zone_1_seconds: int
    zone_2_seconds: int
    zone_3_seconds: int
    zone_4_seconds: int
    zone_5_seconds: int
    zone_1_percent: float
    zone_2_percent: float
    zone_3_percent: float
    zone_4_percent: float
    zone_5_percent: float
    max_hr: int
    zone_boundaries: dict[int, tuple[int, int]]

    def __post_init__(self) -> None:
        # Validate zone times are non-negative integers
        for zone_num in range(1, 6):
            field_name = f"zone_{zone_num}_seconds"
            value = getattr(self, field_name)
            if not isinstance(value, int):
                raise TypeError(
                    f"HRZonesData.{field_name} must be an int, got {type(value).__name__}"
                )
            if value < 0:
                raise ValueError(
                    f"HRZonesData.{field_name} must be non-negative, got {value}"
                )

        # Validate zone percentages are non-negative floats
        for zone_num in range(1, 6):
            field_name = f"zone_{zone_num}_percent"
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)):
                raise TypeError(
                    f"HRZonesData.{field_name} must be a float, got {type(value).__name__}"
                )
            if value < 0:
                raise ValueError(
                    f"HRZonesData.{field_name} must be non-negative, got {value}"
                )

        # Validate percentages sum to approximately 100%
        total_percent = sum(
            getattr(self, f"zone_{zone_num}_percent") for zone_num in range(1, 6)
        )
        if not (0.0 <= total_percent <= 101.0):
            raise ValueError(
                f"HRZonesData zone percentages must sum to 0.0-101.0%, got {total_percent:.1f}%"
            )

        # Validate max_hr is a positive integer
        if not isinstance(self.max_hr, int):
            raise TypeError(
                f"HRZonesData.max_hr must be an int, got {type(self.max_hr).__name__}"
            )
        if self.max_hr <= 0:
            raise ValueError(
                f"HRZonesData.max_hr must be positive, got {self.max_hr}"
            )

        # Validate zone_boundaries structure
        if not isinstance(self.zone_boundaries, dict):
            raise TypeError(
                f"HRZonesData.zone_boundaries must be a dict, got {type(self.zone_boundaries).__name__}"
            )
        if len(self.zone_boundaries) != 5:
            raise ValueError(
                f"HRZonesData.zone_boundaries must contain exactly 5 zones, got {len(self.zone_boundaries)}"
            )
        # Check each zone exists before validating its contents
        for zone_num in range(1, 6):
            if zone_num not in self.zone_boundaries:
                raise ValueError(
                    f"HRZonesData.zone_boundaries missing zone {zone_num}"
                )
        # Validate each zone's boundary tuple
        for zone_num in range(1, 6):
            bounds = self.zone_boundaries[zone_num]
            if not isinstance(bounds, tuple) or len(bounds) != 2:
                raise ValueError(
                    f"HRZonesData.zone_boundaries[{zone_num}] must be a 2-tuple, got {bounds}"
                )
            lower, upper = bounds
            if not isinstance(lower, int) or not isinstance(upper, int):
                raise ValueError(
                    f"HRZonesData.zone_boundaries[{zone_num}] must contain integers, got ({lower}, {upper})"
                )
            if lower >= upper:
                raise ValueError(
                    f"HRZonesData.zone_boundaries[{zone_num}] lower bound must be less than upper bound, got ({lower}, {upper})"
                )


@dataclass
class AbilityAssessment:
    """AI-generated competitive ability assessment.

    Invariants:
      - percentile_estimate must be non-empty and ≤ 100 characters
      - local_ranking must be non-empty and ≤ 200 characters
      - national_ranking must be non-empty and ≤ 200 characters
      - competitive_analysis must be non-empty and ≤ 800 characters

    Attributes:
        percentile_estimate:   estimated percentile ranking within age group (e.g., "top 25%")
        local_ranking:         estimated local competition ranking in specified locality
        national_ranking:      estimated national competition ranking in specified nationality
        competitive_analysis:  assessment of competitiveness for age and population context
    """
    percentile_estimate: str
    local_ranking: str
    national_ranking: str
    competitive_analysis: str

    def __post_init__(self) -> None:
        # Validate percentile_estimate
        if not isinstance(self.percentile_estimate, str):
            raise TypeError(
                f"AbilityAssessment.percentile_estimate must be a str, got {type(self.percentile_estimate).__name__}"
            )
        if len(self.percentile_estimate) == 0:
            raise ValueError("percentile_estimate must be non-empty")
        if len(self.percentile_estimate) > 100:
            raise ValueError(
                f"percentile_estimate must not exceed 100 characters (length={len(self.percentile_estimate)})"
            )

        # Validate local_ranking
        if not isinstance(self.local_ranking, str):
            raise TypeError(
                f"AbilityAssessment.local_ranking must be a str, got {type(self.local_ranking).__name__}"
            )
        if len(self.local_ranking) == 0:
            raise ValueError("local_ranking must be non-empty")
        if len(self.local_ranking) > 200:
            raise ValueError(
                f"local_ranking must not exceed 200 characters (length={len(self.local_ranking)})"
            )

        # Validate national_ranking
        if not isinstance(self.national_ranking, str):
            raise TypeError(
                f"AbilityAssessment.national_ranking must be a str, got {type(self.national_ranking).__name__}"
            )
        if len(self.national_ranking) == 0:
            raise ValueError("national_ranking must be non-empty")
        if len(self.national_ranking) > 200:
            raise ValueError(
                f"national_ranking must not exceed 200 characters (length={len(self.national_ranking)})"
            )

        # Validate competitive_analysis
        if not isinstance(self.competitive_analysis, str):
            raise TypeError(
                f"AbilityAssessment.competitive_analysis must be a str, got {type(self.competitive_analysis).__name__}"
            )
        if len(self.competitive_analysis) == 0:
            raise ValueError("competitive_analysis must be non-empty")
        if len(self.competitive_analysis) > 800:
            raise ValueError(
                f"competitive_analysis must not exceed 800 characters (length={len(self.competitive_analysis)})"
            )


@dataclass
class Session:
    """Complete session record for storage and retrieval.

    Represents a single swim session with all associated data including
    metrics, optional HR zones, and optional ability assessment.

    Attributes:
        session_id:            unique session identifier (UUID v4)
        user_id:               user identifier (UUID v4)
        session_date:          session start date/time in ISO 8601 format
        pool_length_meters:    pool length in meters
        total_distance_meters: total distance swum in meters
        total_time_seconds:    total session time in seconds
        stroke_type:           dominant stroke type (max 50 characters)
        average_pace_per_100m: average pace in seconds per 100m (two decimal places)
        swolf_score:           SWOLF score
        stroke_rate:           average stroke rate in strokes per minute (one decimal place)
        uploaded_at:           upload timestamp in ISO 8601 format
        s3_key:                S3 key for the FIT file
        hr_zones:              optional heart rate zone data
        ability_assessment:    optional AI-generated ability assessment
    """
    session_id: str
    user_id: str
    session_date: str
    pool_length_meters: int
    total_distance_meters: int
    total_time_seconds: int
    stroke_type: str
    average_pace_per_100m: float
    swolf_score: int
    stroke_rate: float
    uploaded_at: str
    s3_key: str
    hr_zones: HRZonesData | None = None
    ability_assessment: AbilityAssessment | None = None
    splits: list | None = None
    coaching: dict | None = None
    hr_timeseries: list | None = None
    kudos: list | None = None
    comments: list | None = None

    def __post_init__(self) -> None:
        # Validate session_id
        if not isinstance(self.session_id, str) or not self.session_id:
            raise ValueError("session_id must be a non-empty string")

        # Validate user_id
        if not isinstance(self.user_id, str) or not self.user_id:
            raise ValueError("user_id must be a non-empty string")

        # Validate session_date
        if not isinstance(self.session_date, str) or not self.session_date:
            raise ValueError("session_date must be a non-empty string")

        # Validate pool_length_meters
        if not isinstance(self.pool_length_meters, int):
            raise TypeError(
                f"Session.pool_length_meters must be an int, got {type(self.pool_length_meters).__name__}"
            )
        if self.pool_length_meters <= 0:
            raise ValueError(
                f"Session.pool_length_meters must be positive, got {self.pool_length_meters}"
            )

        # Validate total_distance_meters
        if not isinstance(self.total_distance_meters, int):
            raise TypeError(
                f"Session.total_distance_meters must be an int, got {type(self.total_distance_meters).__name__}"
            )
        if self.total_distance_meters <= 0:
            raise ValueError(
                f"Session.total_distance_meters must be positive, got {self.total_distance_meters}"
            )

        # Validate total_time_seconds
        if not isinstance(self.total_time_seconds, int):
            raise TypeError(
                f"Session.total_time_seconds must be an int, got {type(self.total_time_seconds).__name__}"
            )
        if self.total_time_seconds <= 0:
            raise ValueError(
                f"Session.total_time_seconds must be positive, got {self.total_time_seconds}"
            )

        # Validate stroke_type
        if not isinstance(self.stroke_type, str) or not self.stroke_type:
            raise ValueError("stroke_type must be a non-empty string")
        if len(self.stroke_type) > 50:
            raise ValueError(
                f"stroke_type must not exceed 50 characters (length={len(self.stroke_type)})"
            )

        # Validate average_pace_per_100m
        if not isinstance(self.average_pace_per_100m, (int, float)):
            raise TypeError(
                f"Session.average_pace_per_100m must be a float, got {type(self.average_pace_per_100m).__name__}"
            )
        if not math.isfinite(self.average_pace_per_100m):
            raise ValueError("average_pace_per_100m must be a finite number")
        if self.average_pace_per_100m <= 0:
            raise ValueError(
                f"Session.average_pace_per_100m must be positive, got {self.average_pace_per_100m}"
            )

        # Validate swolf_score
        if not isinstance(self.swolf_score, int):
            raise TypeError(
                f"Session.swolf_score must be an int, got {type(self.swolf_score).__name__}"
            )

        # Validate stroke_rate
        if not isinstance(self.stroke_rate, (int, float)):
            raise TypeError(
                f"Session.stroke_rate must be a float, got {type(self.stroke_rate).__name__}"
            )
        if not math.isfinite(self.stroke_rate):
            raise ValueError("stroke_rate must be a finite number")
        if self.stroke_rate < 0:
            raise ValueError(
                f"Session.stroke_rate must be non-negative, got {self.stroke_rate}"
            )

        # Validate uploaded_at
        if not isinstance(self.uploaded_at, str) or not self.uploaded_at:
            raise ValueError("uploaded_at must be a non-empty string")

        # Validate s3_key
        if not isinstance(self.s3_key, str) or not self.s3_key:
            raise ValueError("s3_key must be a non-empty string")

        # Validate hr_zones if provided
        if self.hr_zones is not None and not isinstance(self.hr_zones, HRZonesData):
            raise TypeError(
                f"Session.hr_zones must be HRZonesData or None, got {type(self.hr_zones).__name__}"
            )

        # Validate ability_assessment if provided
        if self.ability_assessment is not None and not isinstance(self.ability_assessment, AbilityAssessment):
            raise TypeError(
                f"Session.ability_assessment must be AbilityAssessment or None, got {type(self.ability_assessment).__name__}"
            )


@dataclass
class FullResponse:
    """Complete API response combining session info, splits, metrics, and coaching.

    Extended with optional heart rate zones, ability assessment, and session ID
    for authenticated users with profiles.

    Attributes:
        session:            session metadata
        splits:             per-length split data
        metrics:            calculated performance metrics
        coaching:           AI-generated coaching tips and drill
        hr_zones:           optional heart rate zone analysis (requires user age)
        ability_assessment: optional competitive ability assessment (requires complete profile)
        session_id:         optional session identifier (returned after session saved)
    """
    session: SessionInfo
    splits: list[LengthSplit]
    metrics: Metrics
    coaching: CoachingResponse
    hr_zones: HRZonesData | None = None
    ability_assessment: AbilityAssessment | None = None
    session_id: str | None = None
    hr_timeseries: list | None = None
