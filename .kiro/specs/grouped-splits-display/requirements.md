# Requirements Document

## Introduction

The Grouped Splits Display feature transforms the flat per-length splits table into a structured view that groups consecutive swim lengths into reps/sets. Each group represents a continuous effort at the same stroke type, separated by rest intervals. The grouped view shows total distance and time per rep with expandable detail rows, and displays rest durations between groups — giving swimmers a clear picture of their session structure (e.g., 4×100m freestyle with 15s rest).

## Glossary

- **FIT_Parser**: The Python backend module (`fit_parser.py`) that extracts session data and per-length splits from Garmin FIT files.
- **Length_Record**: A single pool-length entry from the FIT file, classified as either "active" (swimming) or "idle" (resting).
- **Split**: A data object representing one active swim length, containing length number, elapsed time, stroke type, and stroke count.
- **Rest_Interval**: The idle time between active swimming efforts, extracted from "idle" Length_Records in the FIT file.
- **Split_Group**: A collection of consecutive Splits sharing the same stroke type with no Rest_Interval between them, representing a single rep or repetition.
- **GroupedSplitsTable**: The React frontend component that renders Split_Groups as expandable rows with Rest_Intervals displayed between them.
- **Pool_Length**: The length of the pool in meters (e.g., 25m or 50m), available from session metadata.

## Requirements

### Requirement 1: Extract Rest Intervals from FIT Files

**User Story:** As a swimmer, I want rest durations captured from my FIT file, so that I can see how long I rested between efforts.

#### Acceptance Criteria

1. WHEN the FIT_Parser encounters a Length_Record with length_type "idle", THE FIT_Parser SHALL extract the total_elapsed_time value as the Rest_Interval duration in seconds.
2. WHEN a Rest_Interval is extracted, THE FIT_Parser SHALL associate the Rest_Interval with the preceding active Split by storing the duration in a `rest_after_seconds` field on that Split.
3. WHEN no idle Length_Record exists between two consecutive active Length_Records, THE FIT_Parser SHALL set the `rest_after_seconds` field to null on the preceding Split.
4. WHEN the first Length_Record in a session is idle, THE FIT_Parser SHALL discard the Rest_Interval without associating it to any Split.
5. THE FIT_Parser SHALL round extracted Rest_Interval durations to two decimal places.

### Requirement 2: Split Data Model Extension

**User Story:** As a developer, I want the split data model to include rest information, so that the frontend can render rest indicators between groups.

#### Acceptance Criteria

1. THE LengthSplit model SHALL include a `rest_after_seconds` field of type float or null.
2. WHEN `rest_after_seconds` is null, THE LengthSplit model SHALL indicate that no rest follows the Split.
3. WHEN `rest_after_seconds` is a float, THE LengthSplit model SHALL represent the rest duration in seconds with two decimal places.
4. THE FIT_Parser SHALL return LengthSplit objects with the `rest_after_seconds` field populated for all Splits in the session.

### Requirement 3: Group Consecutive Splits by Stroke

**User Story:** As a swimmer, I want consecutive same-stroke lengths grouped together, so that I can see my reps as single entries rather than individual lengths.

#### Acceptance Criteria

1. THE GroupedSplitsTable SHALL group consecutive Splits that share the same stroke type into a single Split_Group.
2. WHEN two consecutive Splits have different stroke types, THE GroupedSplitsTable SHALL place them into separate Split_Groups.
3. WHEN a Split has a non-null `rest_after_seconds` value, THE GroupedSplitsTable SHALL end the current Split_Group after that Split.
4. WHEN a Split_Group contains N Splits, THE GroupedSplitsTable SHALL calculate the group distance as N multiplied by Pool_Length meters.
5. WHEN a Split_Group contains multiple Splits, THE GroupedSplitsTable SHALL calculate the group total time as the sum of `time_seconds` for all Splits in the group.

### Requirement 4: Display Grouped Rows

**User Story:** As a swimmer, I want to see each rep as a single row with total distance and time, so that I can quickly understand my session structure.

#### Acceptance Criteria

1. THE GroupedSplitsTable SHALL display each Split_Group as a single row showing: total distance (in meters), total time, stroke type, and average pace per 100m.
2. THE GroupedSplitsTable SHALL calculate average pace per 100m as (total_time_seconds / total_distance_meters) × 100.
3. WHEN a Split_Group contains exactly one Split, THE GroupedSplitsTable SHALL display the group as a single row without an expand indicator.
4. WHEN a Split_Group contains more than one Split, THE GroupedSplitsTable SHALL display an expand/collapse indicator on the group row.
5. THE GroupedSplitsTable SHALL format total distance as a whole number followed by "m" (e.g., "100m").
6. THE GroupedSplitsTable SHALL format total time in minutes and seconds (e.g., "1:32.5").

### Requirement 5: Expandable Detail Rows

**User Story:** As a swimmer, I want to expand a grouped row to see individual length details, so that I can analyze my pacing within a rep.

#### Acceptance Criteria

1. WHEN a user activates the expand control on a Split_Group row, THE GroupedSplitsTable SHALL reveal the individual Split rows within that group.
2. WHEN individual Split rows are revealed, THE GroupedSplitsTable SHALL display each Split's length number, time in seconds, stroke count, and stroke type.
3. WHEN a user activates the collapse control on an expanded Split_Group row, THE GroupedSplitsTable SHALL hide the individual Split rows.
4. THE GroupedSplitsTable SHALL render all Split_Groups in collapsed state by default.
5. THE GroupedSplitsTable SHALL allow multiple Split_Groups to be expanded simultaneously.

### Requirement 6: Rest Interval Display Between Groups

**User Story:** As a swimmer, I want to see rest durations between reps, so that I can understand my work-to-rest ratio.

#### Acceptance Criteria

1. WHEN a Split_Group's last Split has a non-null `rest_after_seconds` value, THE GroupedSplitsTable SHALL display a rest indicator row between the current Split_Group row and the next Split_Group row.
2. THE GroupedSplitsTable SHALL format rest duration as whole seconds with "s" suffix when the value is 60 seconds or less (e.g., "15s").
3. WHEN the rest duration exceeds 60 seconds, THE GroupedSplitsTable SHALL format it as minutes and seconds (e.g., "1:30").
4. THE GroupedSplitsTable SHALL visually distinguish rest indicator rows from Split_Group rows using reduced emphasis styling.
5. THE GroupedSplitsTable SHALL not display a rest indicator after the final Split_Group in the session.

### Requirement 7: Accessibility of Grouped Display

**User Story:** As a swimmer using assistive technology, I want the grouped splits table to be accessible, so that I can navigate and understand my session structure.

#### Acceptance Criteria

1. THE GroupedSplitsTable SHALL use appropriate ARIA attributes to indicate expandable/collapsible state of Split_Group rows.
2. THE GroupedSplitsTable SHALL allow expand/collapse activation via keyboard (Enter and Space keys).
3. THE GroupedSplitsTable SHALL announce state changes (expanded/collapsed) to screen readers when a Split_Group row is toggled.
4. THE GroupedSplitsTable SHALL provide an accessible label for the table section (e.g., "Grouped length splits").

### Requirement 8: Backward Compatibility of API Response

**User Story:** As a developer, I want the API response to remain backward compatible, so that existing clients continue to work without changes.

#### Acceptance Criteria

1. THE FIT_Parser SHALL include the `rest_after_seconds` field as an additional field in the splits array without removing or renaming existing fields.
2. WHEN an existing API consumer does not use the `rest_after_seconds` field, THE API response SHALL continue to function correctly with the additional field present.
3. THE FIT_Parser SHALL maintain the existing ordering of Splits by length_number in the response.
