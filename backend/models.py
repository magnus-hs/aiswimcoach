"""
Shared data models for the AI Swim Coach backend.

Invariants:
  Metrics:         all three float fields must be finite (not NaN, not ±Infinity)
  CoachingResponse: tips contains exactly 3 items, each non-empty and ≤ 300 chars;
                    drill is non-empty and ≤ 500 chars
"""
from __future__ import annotations

import math
from dataclasses import dataclass


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
