# Validation Tolerance Fixes - Bugfix Requirements Document

## Introduction

This bugfix addresses two related validation failures in the AI Swim Coach application that prevent users from successfully using core features. Both bugs share a common theme: overly strict or incomplete validation logic that rejects valid inputs or fails to handle AI-generated content defensively.

**Bug 1 (HR Zones)**: Users with completed profiles and valid FIT files containing heart rate data cannot see their HR zones analysis because the validation tolerance for time sum calculations is too strict (1 second), causing legitimate files with normal sampling gaps to fail with "Zone time sum does not equal total session time" errors.

**Bug 2 (Training Plans)**: AI-generated training plans fail validation when Claude produces goal_likelihood text exceeding 300 characters, because the code validates the length but doesn't truncate like other AI-generated fields (ability assessment fields have defensive truncation that prevents this issue).

These bugs affect critical user workflows: post-workout analysis (HR zones) and training plan generation.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a FIT file with heart rate data has sampling gaps or irregular intervals resulting in zone time sum differing from total session time by more than 1 second (e.g., 84 seconds difference) THEN the system crashes with ValueError "Zone time sum (X.Xs) does not equal total session time (Y.Ys)" and prevents HR zones analysis display

1.2 WHEN Claude generates a goal_likelihood field exceeding 300 characters during training plan generation THEN the system logs a warning "goal_likelihood exceeds 300 characters" and returns None, causing training plan generation to fail after retry

### Expected Behavior (Correct)

2.1 WHEN a FIT file with heart rate data has sampling gaps or irregular intervals resulting in zone time sum differing from total session time by a reasonable margin THEN the system SHALL calculate and display HR zones analysis without raising a validation error

2.2 WHEN Claude generates a goal_likelihood field exceeding 300 characters during training plan generation THEN the system SHALL truncate the field to 300 characters (matching the defensive pattern used for ability assessment fields) and successfully return the training plan

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a FIT file has heart rate data where zone time sum equals total session time within the current 1-second tolerance THEN the system SHALL CONTINUE TO calculate and display HR zones correctly as before

3.2 WHEN Claude generates a goal_likelihood field within the 300 character limit THEN the system SHALL CONTINUE TO use the field value without modification

3.3 WHEN ability assessment fields exceed their character limits THEN the system SHALL CONTINUE TO truncate them defensively as currently implemented (percentile_estimate[:100], local_ranking[:200], national_ranking[:200], competitive_analysis[:800])

3.4 WHEN calculating HR zones for files with continuous, regular sampling THEN the system SHALL CONTINUE TO produce accurate zone time calculations

3.5 WHEN training plan validation encounters other invalid fields (missing session_title, empty warm_up, invalid total_distance) THEN the system SHALL CONTINUE TO return None and trigger retry logic
