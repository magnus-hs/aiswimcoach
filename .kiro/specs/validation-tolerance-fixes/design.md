# Validation Tolerance Fixes - Bugfix Design

## Overview

This bugfix addresses two validation issues that prevent legitimate user operations: (1) overly strict HR zone time validation that rejects valid FIT files with normal sampling irregularities, and (2) missing defensive truncation for AI-generated goal_likelihood fields that causes training plan generation to fail. The fix involves relaxing the HR zone time tolerance to accommodate real-world FIT file characteristics and adding defensive truncation for goal_likelihood to match the pattern already used for ability assessment fields.

## Glossary

- **Bug_Condition_HR (C1)**: The condition that triggers the HR zones bug - when zone time sum differs from total session time by more than 1 second due to sampling gaps
- **Bug_Condition_Training (C2)**: The condition that triggers the training plan bug - when Claude generates goal_likelihood text exceeding 300 characters
- **Property_HR (P1)**: The desired behavior for HR zones - accept files with reasonable time discrepancies due to sampling characteristics
- **Property_Training (P2)**: The desired behavior for training plans - truncate goal_likelihood to prevent validation failure
- **Preservation_HR**: Existing accurate zone calculations for well-sampled files must remain unchanged
- **Preservation_Training**: Existing truncation behavior for other AI fields and validation for other training plan fields must remain unchanged
- **hr_samples**: List of (timestamp, heart_rate_bpm) tuples extracted from FIT files
- **zone_times**: Dictionary mapping zone numbers (1-5) to time spent in seconds
- **total_time**: Session duration calculated as last_timestamp - first_timestamp
- **goal_likelihood**: AI-generated assessment of user's likelihood to reach training goal (string field with 300 char limit)

## Bug Details

### Bug Condition - HR Zones

The HR zones bug manifests when FIT files have irregular sampling (gaps, pauses, variable recording rates) that causes the sum of time spent in each zone to differ from the total session time (last_timestamp - first_timestamp) by more than 1 second. The `calculate_hr_zones` function in `hr_zones.py` line 278 raises a ValueError with this strict validation.

**Real-world causes of time discrepancies:**
- Recording pauses during rest intervals
- Variable sampling rates from different devices
- GPS/sensor dropout periods
- Transition periods where HR isn't classified
- Edge effects at session boundaries

**Formal Specification:**
```
FUNCTION isBugCondition_HR(hr_samples)
  INPUT: hr_samples of type list[tuple[datetime, int]]
  OUTPUT: boolean
  
  valid_samples := FILTER hr_samples WHERE 0 < hr <= 300
  total_time := (valid_samples[-1].timestamp - valid_samples[0].timestamp).total_seconds()
  
  zone_times := CALCULATE_ZONE_TIMES(valid_samples)
  sum_zone_times := SUM(zone_times.values())
  
  time_difference := ABS(sum_zone_times - total_time)
  
  RETURN time_difference > 1.0 AND time_difference <= 90.0
END FUNCTION
```

**Note:** We cap the reasonable difference at 90 seconds (1.5 minutes) - beyond that likely indicates data quality issues that should still fail validation.

### Bug Condition - Training Plan

The training plan bug manifests when Claude generates goal_likelihood text exceeding 300 characters. The `_parse_training_plan_response` function in `bedrock_client.py` lines 424-427 validates the length but returns None instead of truncating, causing the training plan generation to fail even after retry.

**Formal Specification:**
```
FUNCTION isBugCondition_Training(goal_likelihood)
  INPUT: goal_likelihood of type string (AI-generated field)
  OUTPUT: boolean
  
  RETURN LENGTH(goal_likelihood) > 300
END FUNCTION
```

### Examples

**HR Zones Examples:**
- Input: FIT file with 1576s total time, zone sum 1492s (84s difference) → Current: ValueError raised, Expected: Calculate and display zones
- Input: FIT file with irregular sampling during rest periods → Current: May fail validation, Expected: Accept and calculate
- Edge case: FIT file with 95s difference → Expected: Still fail validation (exceeds reasonable tolerance)

**Training Plan Examples:**
- Input: Claude generates 350-character goal_likelihood → Current: Validation fails, returns None, Expected: Truncate to 300 chars
- Input: Claude generates 250-character goal_likelihood → Current: Passes validation, Expected: No change (preserve)
- Edge case: Claude generates empty goal_likelihood → Expected: Still fail validation (empty check remains)

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors - HR Zones:**
- Files with zone time sum within 1 second of total time must continue to pass validation exactly as before
- Zone time calculations for well-sampled files must produce identical results
- Other validation checks (empty samples, age range, minimum samples) must remain unchanged
- Zone boundary calculations based on max HR must remain unchanged

**Unchanged Behaviors - Training Plans:**
- Ability assessment field truncation (percentile_estimate[:100], local_ranking[:200], national_ranking[:200], competitive_analysis[:800]) must continue working identically
- Validation for other training plan fields (session_title, warm_up, main_set, cool_down, total_distance, focus_notes) must remain unchanged
- Training plans with goal_likelihood under 300 characters must be processed without modification
- Retry logic when validation fails must continue to work as before

**Scope:**
All inputs that do NOT involve the specific bug conditions should be completely unaffected by this fix. This includes:
- HR zone calculations for files with regular, continuous sampling
- Training plan generation when goal_likelihood is within limits
- All other validation logic in both functions
- Zone percentage calculations and HRZonesData construction

## Hypothesized Root Cause

### HR Zones Root Cause

Based on the bug description and code analysis, the root cause is **overly strict validation tolerance**:

1. **Insufficient Tolerance**: The 1-second tolerance at line 278 (`abs(sum_zone_times - total_time) > 1.0`) is too strict for real-world FIT files that may have:
   - Recording gaps during transitions
   - Variable sampling rates (some devices sample at 1Hz, others at variable rates)
   - Pauses that aren't reflected in zone time accumulation

2. **Algorithm Limitation**: The current algorithm accumulates zone time by iterating consecutive samples and calculating `(next_ts - current_ts).total_seconds()`. If there are gaps in recording, this sum may legitimately be less than the total session span.

3. **No Accommodation for Real-World Data**: The validation assumes perfect, continuous sampling, which doesn't match how fitness devices actually record data.

### Training Plan Root Cause

Based on the bug description and code analysis, the root cause is **missing defensive truncation**:

1. **Inconsistent Defensive Coding**: Ability assessment parsing (lines 620-623) defensively truncates all AI-generated text fields BEFORE passing to constructor:
   ```python
   percentile_estimate = percentile_estimate[:100]
   local_ranking = local_ranking[:200]
   national_ranking = national_ranking[:200]
   competitive_analysis = competitive_analysis[:800]
   ```
   
2. **Missing Truncation**: Training plan parsing (lines 424-427) validates but doesn't truncate:
   ```python
   if len(goal_likelihood) > 300:
       logger.warning("goal_likelihood exceeds 300 characters in training plan response")
       return None
   ```

3. **AI Unpredictability**: Claude's text generation is nondeterministic and may occasionally exceed expected limits, so defensive truncation is the correct pattern (already proven by ability assessment implementation).

## Correctness Properties

Property 1: Bug Condition - HR Zones Tolerance

_For any_ HR samples where the zone time sum differs from total session time by more than 1 second but less than or equal to 90 seconds (isBugCondition_HR returns true), the fixed calculate_hr_zones function SHALL successfully calculate and return HRZonesData without raising a validation error, accommodating normal sampling irregularities in real-world FIT files.

**Validates: Requirements 2.1**

Property 2: Bug Condition - Training Plan Truncation

_For any_ goal_likelihood value where the length exceeds 300 characters (isBugCondition_Training returns true), the fixed _parse_training_plan_response function SHALL truncate the field to 300 characters and successfully return a TrainingPlan object, matching the defensive pattern used for ability assessment fields.

**Validates: Requirements 2.2**

Property 3: Preservation - HR Zones Accuracy

_For any_ HR samples where the zone time sum is within 1 second of total session time (isBugCondition_HR returns false), the fixed function SHALL produce exactly the same HRZonesData as the original function, preserving accurate zone calculations for well-sampled files.

**Validates: Requirements 3.1, 3.4**

Property 4: Preservation - Training Plan Validation

_For any_ training plan response where goal_likelihood is 300 characters or less (isBugCondition_Training returns false), the fixed function SHALL process the field identically to the original function without modification, and all other validation logic SHALL remain unchanged.

**Validates: Requirements 3.2, 3.5**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File 1**: `/home/magnus/aiswimcoach/backend/hr_zones.py`

**Function**: `calculate_hr_zones`

**Specific Changes**:
1. **Relax Time Validation Tolerance** (line 278):
   - Change from: `if abs(sum_zone_times - total_time) > 1.0:`
   - Change to: `if abs(sum_zone_times - total_time) > 90.0:` (90 seconds = 1.5 minutes)
   - Rationale: Allows reasonable sampling irregularities while still catching major data quality issues

2. **Update Error Message** (line 280):
   - Update message to reflect new tolerance expectation
   - Consider adding contextual information about why this validation exists

**File 2**: `/home/magnus/aiswimcoach/backend/bedrock_client.py`

**Function**: `_parse_training_plan_response`

**Specific Changes**:
1. **Add Defensive Truncation** (between lines 423 and 428):
   - Remove the validation-only check that returns None
   - Add truncation: `goal_likelihood = goal_likelihood[:300]`
   - This matches the pattern from ability assessment (lines 620-623)
   - Keep the empty/missing validation check

2. **Remove or Adjust Warning Log**:
   - Either remove the length warning (since truncation handles it)
   - Or change to info-level log noting truncation occurred

**Defensive Pattern Consistency**:
Both functions should follow the principle: "validate what matters (presence, type), truncate what varies (AI-generated text length)".

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bugs on unfixed code, then verify the fixes work correctly and preserve existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate both bugs BEFORE implementing the fix. Confirm or refute the root cause analysis. If we refute, we will need to re-hypothesize.

**Test Plan - HR Zones**: Create synthetic HR samples with controlled time discrepancies, run calculate_hr_zones on UNFIXED code to observe failures.

**Test Cases - HR Zones**:
1. **84-Second Gap Test**: Create HR samples with total_time=1576s, zone_sum=1492s (matches reported bug) - will fail on unfixed code
2. **30-Second Gap Test**: Create samples with moderate sampling gap (30s difference) - will fail on unfixed code
3. **60-Second Gap Test**: Create samples with larger gap (60s difference) - will fail on unfixed code
4. **95-Second Gap Test**: Create samples with 95s difference (should still fail even after fix) - will fail on unfixed code

**Expected Counterexamples - HR Zones**:
- ValueError raised for any difference > 1.0 seconds
- Error message shows exact time discrepancy
- Confirms that tolerance is too strict for real-world data

**Test Plan - Training Plans**: Create mock Bedrock responses with goal_likelihood fields of varying lengths, run _parse_training_plan_response on UNFIXED code to observe failures.

**Test Cases - Training Plans**:
1. **350-Character Test**: Mock response with 350-char goal_likelihood - will return None on unfixed code
2. **500-Character Test**: Mock response with 500-char goal_likelihood - will return None on unfixed code
3. **Exactly 300-Character Test**: Mock response with exactly 300 chars - should pass on unfixed code (boundary)
4. **Empty String Test**: Mock response with empty goal_likelihood - should fail on unfixed code (different validation)

**Expected Counterexamples - Training Plans**:
- Function returns None for lengths > 300
- Warning logged: "goal_likelihood exceeds 300 characters"
- Confirms that validation rejects instead of truncating

### Fix Checking

**Goal**: Verify that for all inputs where the bug conditions hold, the fixed functions produce the expected behavior.

**Pseudocode - HR Zones:**
```
FOR ALL hr_samples WHERE isBugCondition_HR(hr_samples) DO
  result := calculate_hr_zones_fixed(hr_samples, age)
  ASSERT result IS HRZonesData (not ValueError)
  ASSERT result.zone_1_seconds + ... + result.zone_5_seconds approximates total session time
END FOR
```

**Pseudocode - Training Plans:**
```
FOR ALL response WHERE isBugCondition_Training(response.goal_likelihood) DO
  result := _parse_training_plan_response_fixed(response)
  ASSERT result IS TrainingPlan (not None)
  ASSERT LENGTH(result.goal_likelihood) <= 300
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug conditions do NOT hold, the fixed functions produce the same results as the original functions.

**Pseudocode - HR Zones:**
```
FOR ALL hr_samples WHERE NOT isBugCondition_HR(hr_samples) DO
  ASSERT calculate_hr_zones_original(hr_samples, age) = calculate_hr_zones_fixed(hr_samples, age)
END FOR
```

**Pseudocode - Training Plans:**
```
FOR ALL response WHERE NOT isBugCondition_Training(response.goal_likelihood) DO
  ASSERT _parse_training_plan_response_original(response) = _parse_training_plan_response_fixed(response)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs
- For HR zones: can generate various sampling patterns with time differences ≤ 1 second
- For training plans: can generate responses with goal_likelihood strings of varying lengths ≤ 300

**Test Plan - HR Zones Preservation**: Observe behavior on UNFIXED code with well-sampled HR data (time difference ≤ 1 second), then write property-based tests capturing that behavior.

**Test Cases - HR Zones Preservation**:
1. **Perfect Sampling**: Generate HR samples with continuous 1Hz sampling (0s difference) - verify zones calculated correctly on unfixed code
2. **Sub-Second Difference**: Generate samples with 0.5s difference - verify passes on unfixed code
3. **Exactly 1-Second Difference**: Generate samples with exactly 1.0s difference - verify passes on unfixed code
4. **Various Zone Distributions**: Generate samples across different zone distributions - verify calculations match

**Test Plan - Training Plans Preservation**: Observe behavior on UNFIXED code with valid goal_likelihood lengths, then write property-based tests capturing that behavior.

**Test Cases - Training Plans Preservation**:
1. **Short Strings**: Generate goal_likelihood with 50-200 characters - verify passes on unfixed code
2. **Near Limit**: Generate goal_likelihood with 290-299 characters - verify passes on unfixed code
3. **Other Field Validation**: Generate invalid values for other fields (empty session_title, invalid total_distance) - verify still returns None

### Unit Tests

**HR Zones:**
- Test with reported bug case (84s difference) - should pass after fix
- Test with various time discrepancies (5s, 30s, 60s, 89s) - should pass after fix
- Test boundary at 90s - should still fail (data quality threshold)
- Test with perfect sampling (0s difference) - should pass (preservation)
- Test edge cases (2 samples only, all HR in one zone)

**Training Plans:**
- Test with 350-char goal_likelihood - should return TrainingPlan after fix
- Test with 500-char goal_likelihood - should truncate to 300 after fix
- Test with 299-char goal_likelihood - should pass unchanged (preservation)
- Test with empty goal_likelihood - should return None (existing validation)
- Test truncation doesn't affect other fields

### Property-Based Tests

**HR Zones:**
- Generate random HR samples with controlled time discrepancies (1-90s range) - verify all pass after fix
- Generate random well-sampled HR data (≤1s difference) - verify zone calculations match original
- Generate random age values (1-120) - verify behavior consistent across age ranges
- Test with random zone distributions - verify percentages sum to 100%

**Training Plans:**
- Generate random goal_likelihood strings (301-500 chars) - verify all truncate correctly
- Generate random valid goal_likelihood strings (1-300 chars) - verify no modification
- Generate random values for other fields - verify validation logic unchanged
- Test with random combinations of valid/invalid fields - verify overall validation behavior

### Integration Tests

**HR Zones:**
- Test full workflow: upload FIT file with sampling gaps → process → display HR zones
- Test with real FIT files from different devices (Garmin, Wahoo, Apple Watch)
- Verify UI displays zones correctly for files that previously failed
- Test session history retrieval includes HR zones for previously failing files

**Training Plans:**
- Test full workflow: submit training goal → call Bedrock → parse response → return plan
- Test with real Claude responses that previously failed
- Verify retry logic still works for other validation failures
- Test that ability assessment truncation continues working (regression check)
