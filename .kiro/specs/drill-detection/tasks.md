# Implementation Plan: Drill Detection

## Overview

Implement drill detection across the backend FIT parser (metrics exclusion), AI coaching context (prompt assembly), and frontend (DrillSummary component, ActivityCard badge, GroupedSplitsTable styling, StrokeBreakdown color). The FIT parser already maps `swim_stroke=4` to `"drill"` and the stroke breakdown already groups by stroke field, so the work focuses on metrics exclusion logic, AI drill context, and new/modified UI components.

## Tasks

- [x] 1. Backend: Drill metrics exclusion in parse_fit
  - [x] 1.1 Modify the metrics accumulation loop in `parse_fit` to skip drill lengths for pace, SWOLF, and stroke rate
    - Add `drill_pace_values`, `drill_swolf_values`, `drill_stroke_rate_values` lists
    - Check `_stroke_name(stroke_val) == "drill"` to route values into drill-specific lists
    - After the loop, fall back to drill values if no regular swim data exists
    - Ensure all-drill sessions don't raise `MetricsMissingError`
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 1.2 Write unit tests for drill metrics exclusion
    - Test mixed session: drill lengths excluded from averages
    - Test all-drill session: metrics computed from drill data without error
    - Test session with no drills: unchanged behavior
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [x] 2. Backend: Drill context for AI coach prompt
  - [x] 2.1 Implement `compute_drill_context` and `format_drill_context` in `prompt_assembler.py`
    - Add `DrillContext` dataclass with `drill_count`, `drill_distance_m`, `drill_time_seconds`, `drill_position`
    - Implement position classification logic (beginning/middle/end/throughout)
    - Format into human-readable string for the prompt
    - _Requirements: 7.1, 7.2_

  - [x] 2.2 Integrate drill context into `build_chat_messages` system prompt
    - Accept optional session data (splits, pool_length_m) parameter
    - Call `compute_drill_context` and append formatted result to system prompt when drills present
    - _Requirements: 7.1, 7.3_

  - [x] 2.3 Write unit tests for drill context computation and prompt integration
    - Test position classification for drills at beginning, middle, end, throughout
    - Test format output string content
    - Test that `build_chat_messages` includes drill context when session has drills
    - Test that no drill context appears when session has zero drills
    - _Requirements: 7.1, 7.2, 7.3_

- [x] 3. Checkpoint
  - Ensure all backend tests pass, ask the user if questions arise.

- [x] 4. Frontend: DrillSummary component
  - [x] 4.1 Create `DrillSummary.tsx` and `DrillSummary.css` in `frontend/src/components/`
    - Implement `computeDrillStats` utility function (count, totalDistance, totalTime)
    - Render drill count, distance, and time in a grid layout
    - Return `null` when no drill splits exist
    - Add `aria-label="Drill summary"` for accessibility
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 4.2 Integrate DrillSummary into SessionDetailPage
    - Import and render `<DrillSummary>` with splits and poolLengthM props
    - Place below session stats / above splits table
    - _Requirements: 3.1, 3.5_

- [x] 5. Frontend: ActivityCard drill badge
  - [x] 5.1 Add drill count badge to `ActivityCard.tsx`
    - Compute drill count from splits prop
    - Render badge with count when drills > 0, hide when 0
    - Add CSS class `activity-card__drill-badge` and style in `ActivityCard.css`
    - _Requirements: 6.1, 6.2, 6.3_

- [x] 6. Frontend: GroupedSplitsTable drill styling
  - [x] 6.1 Add drill row styling to `GroupedSplitsTable.tsx`
    - Add `grouped-splits__row--drill` CSS class on drill rows
    - Display "Drill" label in stroke column for drill splits
    - Ensure strokes shows "—" for drill lengths (verify existing behavior)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 6.2 Add drill CSS styles to `GroupedSplitsTable.css`
    - Style `.grouped-splits__row--drill` with subtle background differentiation
    - Style `.drill-indicator` label
    - _Requirements: 4.2_

- [x] 7. Frontend: StrokeBreakdown drill color
  - [x] 7.1 Add distinct CSS color for the "drill" category in stroke breakdown display
    - Add a unique color variable/class for drill in the breakdown visualization
    - _Requirements: 5.3_

- [x] 8. Final checkpoint
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- The FIT parser already maps `swim_stroke=4` to `"drill"` — no classification logic changes needed
- `extract_session_info` already excludes drill from dominant stroke calculation
- `computeBreakdownFromSplits` already groups by stroke field so drill appears as a category automatically
- Full end-to-end testing requires a real FIT file with drill lengths; unit tests use mocked data
- No new API endpoints needed — frontend computes drill stats client-side from existing splits data

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1", "4.1", "7.1"] },
    { "id": 1, "tasks": ["1.2", "2.2", "4.2", "5.1", "6.1"] },
    { "id": 2, "tasks": ["2.3", "6.2"] }
  ]
}
```
