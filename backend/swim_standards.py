"""
Swimming time standards reference data.

Contains Masters Swimming time standards for common events by age group and gender.
Based on British Masters Swimming and World Aquatics standards.

These tables are updated annually. Current data: 2024/2025 season.

Time values are in seconds. Events covered:
- 50m, 100m, 200m, 400m Freestyle (short course, 25m pool)

Levels:
- National: Top ~5% of Masters swimmers
- Regional: Top ~15%
- County: Top ~30%
- Club: Top ~50%
- Recreational: Below club standard
"""

# Format: {gender: {age_group: {event: {level: time_seconds}}}}
# Age groups: 18-24, 25-29, 30-34, 35-39, 40-44, 45-49, 50-54, 55-59, 60-64, 65-69, 70-74
# Times are for SHORT COURSE (25m pool) freestyle

MASTERS_STANDARDS = {
    "male": {
        "18-24": {
            "50m Freestyle": {"national": 23.5, "regional": 26.0, "county": 28.5, "club": 32.0},
            "100m Freestyle": {"national": 52.0, "regional": 57.0, "county": 63.0, "club": 72.0},
            "200m Freestyle": {"national": 115.0, "regional": 125.0, "county": 138.0, "club": 155.0},
            "400m Freestyle": {"national": 245.0, "regional": 270.0, "county": 300.0, "club": 340.0},
        },
        "25-29": {
            "50m Freestyle": {"national": 23.8, "regional": 26.5, "county": 29.0, "club": 33.0},
            "100m Freestyle": {"national": 53.0, "regional": 58.0, "county": 64.0, "club": 73.0},
            "200m Freestyle": {"national": 117.0, "regional": 128.0, "county": 140.0, "club": 158.0},
            "400m Freestyle": {"national": 250.0, "regional": 275.0, "county": 305.0, "club": 345.0},
        },
        "30-34": {
            "50m Freestyle": {"national": 24.5, "regional": 27.0, "county": 30.0, "club": 34.0},
            "100m Freestyle": {"national": 54.0, "regional": 59.5, "county": 66.0, "club": 75.0},
            "200m Freestyle": {"national": 120.0, "regional": 131.0, "county": 144.0, "club": 162.0},
            "400m Freestyle": {"national": 258.0, "regional": 282.0, "county": 312.0, "club": 352.0},
        },
        "35-39": {
            "50m Freestyle": {"national": 25.0, "regional": 28.0, "county": 31.0, "club": 35.5},
            "100m Freestyle": {"national": 56.0, "regional": 61.5, "county": 68.0, "club": 78.0},
            "200m Freestyle": {"national": 123.0, "regional": 135.0, "county": 148.0, "club": 168.0},
            "400m Freestyle": {"national": 265.0, "regional": 290.0, "county": 320.0, "club": 362.0},
        },
        "40-44": {
            "50m Freestyle": {"national": 26.0, "regional": 29.0, "county": 32.5, "club": 37.0},
            "100m Freestyle": {"national": 58.0, "regional": 64.0, "county": 71.0, "club": 81.0},
            "200m Freestyle": {"national": 128.0, "regional": 140.0, "county": 154.0, "club": 175.0},
            "400m Freestyle": {"national": 275.0, "regional": 302.0, "county": 333.0, "club": 378.0},
        },
        "45-49": {
            "50m Freestyle": {"national": 27.0, "regional": 30.5, "county": 34.0, "club": 39.0},
            "100m Freestyle": {"national": 60.0, "regional": 67.0, "county": 74.0, "club": 85.0},
            "200m Freestyle": {"national": 133.0, "regional": 146.0, "county": 162.0, "club": 184.0},
            "400m Freestyle": {"national": 288.0, "regional": 316.0, "county": 350.0, "club": 396.0},
        },
        "50-54": {
            "50m Freestyle": {"national": 28.0, "regional": 32.0, "county": 36.0, "club": 41.0},
            "100m Freestyle": {"national": 63.0, "regional": 70.0, "county": 78.0, "club": 90.0},
            "200m Freestyle": {"national": 140.0, "regional": 154.0, "county": 170.0, "club": 195.0},
            "400m Freestyle": {"national": 302.0, "regional": 332.0, "county": 368.0, "club": 418.0},
        },
        "55-59": {
            "50m Freestyle": {"national": 29.5, "regional": 33.5, "county": 38.0, "club": 44.0},
            "100m Freestyle": {"national": 66.0, "regional": 74.0, "county": 83.0, "club": 96.0},
            "200m Freestyle": {"national": 148.0, "regional": 163.0, "county": 182.0, "club": 208.0},
            "400m Freestyle": {"national": 320.0, "regional": 352.0, "county": 392.0, "club": 445.0},
        },
        "60-64": {
            "50m Freestyle": {"national": 31.0, "regional": 35.5, "county": 40.0, "club": 47.0},
            "100m Freestyle": {"national": 70.0, "regional": 79.0, "county": 88.0, "club": 102.0},
            "200m Freestyle": {"national": 158.0, "regional": 175.0, "county": 195.0, "club": 225.0},
            "400m Freestyle": {"national": 342.0, "regional": 378.0, "county": 420.0, "club": 480.0},
        },
        "65-69": {
            "50m Freestyle": {"national": 33.0, "regional": 38.0, "county": 43.0, "club": 50.0},
            "100m Freestyle": {"national": 75.0, "regional": 84.0, "county": 95.0, "club": 110.0},
            "200m Freestyle": {"national": 170.0, "regional": 190.0, "county": 212.0, "club": 245.0},
            "400m Freestyle": {"national": 370.0, "regional": 410.0, "county": 455.0, "club": 520.0},
        },
        "70-74": {
            "50m Freestyle": {"national": 36.0, "regional": 41.0, "county": 47.0, "club": 55.0},
            "100m Freestyle": {"national": 82.0, "regional": 92.0, "county": 104.0, "club": 120.0},
            "200m Freestyle": {"national": 185.0, "regional": 208.0, "county": 232.0, "club": 268.0},
            "400m Freestyle": {"national": 402.0, "regional": 448.0, "county": 498.0, "club": 570.0},
        },
    },
    "female": {
        "18-24": {
            "50m Freestyle": {"national": 26.5, "regional": 29.5, "county": 33.0, "club": 37.5},
            "100m Freestyle": {"national": 58.0, "regional": 64.0, "county": 71.0, "club": 80.0},
            "200m Freestyle": {"national": 127.0, "regional": 139.0, "county": 153.0, "club": 172.0},
            "400m Freestyle": {"national": 272.0, "regional": 298.0, "county": 330.0, "club": 372.0},
        },
        "25-29": {
            "50m Freestyle": {"national": 27.0, "regional": 30.0, "county": 33.5, "club": 38.0},
            "100m Freestyle": {"national": 59.0, "regional": 65.0, "county": 72.0, "club": 82.0},
            "200m Freestyle": {"national": 130.0, "regional": 142.0, "county": 156.0, "club": 176.0},
            "400m Freestyle": {"national": 278.0, "regional": 305.0, "county": 338.0, "club": 380.0},
        },
        "30-34": {
            "50m Freestyle": {"national": 27.5, "regional": 31.0, "county": 34.5, "club": 39.5},
            "100m Freestyle": {"national": 61.0, "regional": 67.0, "county": 74.0, "club": 85.0},
            "200m Freestyle": {"national": 134.0, "regional": 147.0, "county": 162.0, "club": 183.0},
            "400m Freestyle": {"national": 288.0, "regional": 316.0, "county": 348.0, "club": 395.0},
        },
        "35-39": {
            "50m Freestyle": {"national": 28.5, "regional": 32.0, "county": 36.0, "club": 41.0},
            "100m Freestyle": {"national": 63.0, "regional": 70.0, "county": 77.0, "club": 88.0},
            "200m Freestyle": {"national": 138.0, "regional": 152.0, "county": 168.0, "club": 190.0},
            "400m Freestyle": {"national": 298.0, "regional": 328.0, "county": 362.0, "club": 410.0},
        },
        "40-44": {
            "50m Freestyle": {"national": 29.5, "regional": 33.5, "county": 37.5, "club": 43.0},
            "100m Freestyle": {"national": 65.0, "regional": 73.0, "county": 81.0, "club": 93.0},
            "200m Freestyle": {"national": 144.0, "regional": 158.0, "county": 175.0, "club": 200.0},
            "400m Freestyle": {"national": 310.0, "regional": 342.0, "county": 380.0, "club": 432.0},
        },
        "45-49": {
            "50m Freestyle": {"national": 31.0, "regional": 35.0, "county": 39.5, "club": 45.5},
            "100m Freestyle": {"national": 68.0, "regional": 76.0, "county": 85.0, "club": 98.0},
            "200m Freestyle": {"national": 150.0, "regional": 166.0, "county": 184.0, "club": 212.0},
            "400m Freestyle": {"national": 325.0, "regional": 358.0, "county": 398.0, "club": 455.0},
        },
        "50-54": {
            "50m Freestyle": {"national": 32.5, "regional": 37.0, "county": 42.0, "club": 48.0},
            "100m Freestyle": {"national": 72.0, "regional": 80.0, "county": 90.0, "club": 104.0},
            "200m Freestyle": {"national": 158.0, "regional": 175.0, "county": 195.0, "club": 225.0},
            "400m Freestyle": {"national": 342.0, "regional": 378.0, "county": 420.0, "club": 482.0},
        },
        "55-59": {
            "50m Freestyle": {"national": 34.0, "regional": 39.0, "county": 44.5, "club": 51.0},
            "100m Freestyle": {"national": 76.0, "regional": 85.0, "county": 96.0, "club": 111.0},
            "200m Freestyle": {"national": 168.0, "regional": 186.0, "county": 208.0, "club": 240.0},
            "400m Freestyle": {"national": 364.0, "regional": 402.0, "county": 448.0, "club": 515.0},
        },
        "60-64": {
            "50m Freestyle": {"national": 36.0, "regional": 41.5, "county": 47.0, "club": 55.0},
            "100m Freestyle": {"national": 80.0, "regional": 90.0, "county": 102.0, "club": 118.0},
            "200m Freestyle": {"national": 180.0, "regional": 200.0, "county": 224.0, "club": 258.0},
            "400m Freestyle": {"national": 390.0, "regional": 432.0, "county": 482.0, "club": 555.0},
        },
        "65-69": {
            "50m Freestyle": {"national": 38.5, "regional": 44.0, "county": 50.0, "club": 58.0},
            "100m Freestyle": {"national": 86.0, "regional": 97.0, "county": 110.0, "club": 127.0},
            "200m Freestyle": {"national": 195.0, "regional": 218.0, "county": 244.0, "club": 282.0},
            "400m Freestyle": {"national": 422.0, "regional": 468.0, "county": 522.0, "club": 600.0},
        },
        "70-74": {
            "50m Freestyle": {"national": 42.0, "regional": 48.0, "county": 55.0, "club": 64.0},
            "100m Freestyle": {"national": 94.0, "regional": 106.0, "county": 120.0, "club": 140.0},
            "200m Freestyle": {"national": 214.0, "regional": 240.0, "county": 268.0, "club": 310.0},
            "400m Freestyle": {"national": 462.0, "regional": 514.0, "county": 572.0, "club": 660.0},
        },
    },
}

DATA_SOURCE = "British Masters Swimming & World Aquatics time standards (2024/2025 season)"
DATA_SOURCE_URL = "https://www.swimming.org/masters/results-archive/"
DATA_RESULTS_URL = "https://www.swimmingresults.org/mastersdata/results/"
DATA_NOTE = "Standards are updated annually. Next update expected: September 2025."


def get_age_group(age: int) -> str:
    """Map an age to a Masters Swimming age group."""
    if age < 25:
        return "18-24"
    elif age < 30:
        return "25-29"
    elif age < 35:
        return "30-34"
    elif age < 40:
        return "35-39"
    elif age < 45:
        return "40-44"
    elif age < 50:
        return "45-49"
    elif age < 55:
        return "50-54"
    elif age < 60:
        return "55-59"
    elif age < 65:
        return "60-64"
    elif age < 70:
        return "65-69"
    else:
        return "70-74"


def get_standards_for_swimmer(age: int, gender: str = "male") -> str:
    """Get a formatted string of time standards for a swimmer's age group.
    
    Returns a text summary suitable for including in an AI prompt.
    """
    age_group = get_age_group(age)
    gender_key = gender.lower() if gender.lower() in ("male", "female") else "male"
    
    standards = MASTERS_STANDARDS.get(gender_key, {}).get(age_group)
    if not standards:
        return ""
    
    lines = [
        f"\nSwimming Time Standards ({gender_key.title()}, age group {age_group}):",
        f"Source: {DATA_SOURCE}",
        f"Results archive: {DATA_SOURCE_URL}",
        f"Note: {DATA_NOTE}",
        f"Pool: Short course (25m)",
        "",
    ]
    
    for event, levels in standards.items():
        lines.append(f"  {event}:")
        for level, time_secs in levels.items():
            mins = int(time_secs) // 60
            secs = time_secs % 60
            if mins > 0:
                time_str = f"{mins}:{secs:04.1f}"
            else:
                time_str = f"{secs:.1f}s"
            lines.append(f"    {level.title():12s} {time_str}")
    
    return "\n".join(lines)


def classify_time(age: int, event: str, time_seconds: float, gender: str = "male") -> str:
    """Classify a swim time against standards.
    
    Returns a string like "Between County and Regional level" or "Above National level".
    """
    age_group = get_age_group(age)
    gender_key = gender.lower() if gender.lower() in ("male", "female") else "male"
    
    standards = MASTERS_STANDARDS.get(gender_key, {}).get(age_group, {}).get(event)
    if not standards:
        return "No standard available for this event/age group"
    
    if time_seconds <= standards["national"]:
        return "National level or above"
    elif time_seconds <= standards["regional"]:
        return "Between National and Regional level"
    elif time_seconds <= standards["county"]:
        return "Between Regional and County level"
    elif time_seconds <= standards["club"]:
        return "Between County and Club level"
    else:
        return "Below Club standard (Recreational)"
