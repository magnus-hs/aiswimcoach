# Requirements Document

## Introduction

The Drill Detection feature enables the AI Swim Coach app to identify, parse, and display drill segments within swim sessions synced from Garmin FIT files. Garmin watches mark drill lengths with a specific stroke type enum value (swim_stroke = 4) or length_type indicator. The app should detect these drill segments during FIT parsing, store them as part of the session data, and present them meaningfully in the session detail view, stroke breakdown, and AI coaching analysis. Drill lengths typically lack valid stroke count and SWOLF data since the swimmer performs varied technique work.

## Glossary

- **FIT_Parser**: The backend module (`fit_parser.py`) responsible for parsing Garmin .FIT file bytes and extracting swim session data including per-length splits.
- **Drill_Length**: A per-length record in a FIT file where the swim_stroke field equals 4 ("drill") or the length_type indicates a drill segment.
- **Session_Detail_Page**: The frontend page that displays per-length splits, stroke breakdown, session summary, and AI coaching for a single swim session.
- **Stroke_Breakdown**: The component within Session_Detail_Page that shows the percentage distribution of strokes swum during a session.
- **Drill_Summary**: A dedicated section within the Session_Detail_Page that aggregates drill-specific information such as total drill distance, drill count, and drill time.
- **AI_Coach**: The backend service that generates personalized coaching advice based on the swimmer's session data and history.
- **Activity_Card**: The dashboard component that displays a summary of each swim session in the session list.

## Requirements

### Requirement 1: Drill Length Identification from FIT Data

**User Story:** As a swimmer, I want the app to detect drill lengths from my Garmin FIT file, so that my drill work is recognized and tracked separately from regular swimming.

#### Acceptance Criteria

1. WHEN the FIT_Parser encounters a length record with swim_stroke value equal to 4, THE FIT_Parser SHALL classify that length as a Drill_Length.
2. WHEN the FIT_Parser encounters a length record with swim_stroke string value equal to "drill" (case-insensitive), THE FIT_Parser SHALL classify that length as a Drill_Length.
3. THE FIT_Parser SHALL store Drill_Length records in the splits list with the stroke field set to "drill".
4. WHEN a Drill_Length has a total_strokes value of 0 or null, THE FIT_Parser SHALL record the strokes field as 0 for that length.
5. THE FIT_Parser SHALL include Drill_Length elapsed time in the per-length time_seconds field.

### Requirement 2: Drill Distance and Time Accounting

**User Story:** As a swimmer, I want drill lengths to count toward my total session distance and time, so that my session summary accurately reflects all the work I did in the pool.

#### Acceptance Criteria

1. THE FIT_Parser SHALL include Drill_Length distance in the session total_distance_m calculation.
2. THE FIT_Parser SHALL include Drill_Length time in the session total_time_seconds calculation.
3. THE FIT_Parser SHALL include Drill_Length records in the session num_lengths count.
4. WHEN determining the dominant stroke for a session, THE FIT_Parser SHALL exclude Drill_Length records from the dominant stroke calculation.

### Requirement 3: Drill Summary Display

**User Story:** As a swimmer, I want to see a summary of my drill work in the session detail, so that I can understand how much of my session was dedicated to drills.

#### Acceptance Criteria

1. WHEN a session contains one or more Drill_Length records, THE Session_Detail_Page SHALL display a Drill_Summary section.
2. THE Drill_Summary SHALL display the total number of drill lengths in the session.
3. THE Drill_Summary SHALL display the total drill distance calculated as the number of Drill_Length records multiplied by the pool length.
4. THE Drill_Summary SHALL display the total drill time as the sum of all Drill_Length time_seconds values.
5. WHEN a session contains zero Drill_Length records, THE Session_Detail_Page SHALL hide the Drill_Summary section.

### Requirement 4: Drill Lengths in Split View

**User Story:** As a swimmer, I want to see drill lengths clearly marked in my split list, so that I can distinguish drill work from regular swimming intervals.

#### Acceptance Criteria

1. WHILE displaying per-length splits, THE Session_Detail_Page SHALL display Drill_Length records inline with other lengths in chronological order.
2. THE Session_Detail_Page SHALL display a visual indicator (distinct label or icon) on each Drill_Length split to differentiate it from regular stroke lengths.
3. THE Session_Detail_Page SHALL display the time_seconds value for each Drill_Length split.
4. WHEN a Drill_Length has a strokes value of 0, THE Session_Detail_Page SHALL display a dash or "N/A" in place of the stroke count for that length.
5. THE Session_Detail_Page SHALL omit SWOLF display for Drill_Length splits.

### Requirement 5: Stroke Breakdown with Drill Percentage

**User Story:** As a swimmer, I want the stroke breakdown chart to include drill as a category, so that I can see the proportion of my session spent on drills versus regular swimming.

#### Acceptance Criteria

1. WHEN a session contains Drill_Length records, THE Stroke_Breakdown SHALL include "Drill" as a category in the stroke distribution.
2. THE Stroke_Breakdown SHALL calculate the drill percentage as the number of Drill_Length records divided by the total number of active lengths, multiplied by 100.
3. THE Stroke_Breakdown SHALL display the drill category with a distinct visual style that differentiates it from stroke type categories.

### Requirement 6: Activity Card Drill Indicator

**User Story:** As a swimmer, I want to see at a glance on my dashboard whether a session included drills, so that I can quickly find my drill-focused workouts.

#### Acceptance Criteria

1. WHEN a session contains one or more Drill_Length records, THE Activity_Card SHALL display a drill indicator showing the drill count.
2. WHEN a session contains zero Drill_Length records, THE Activity_Card SHALL not display a drill indicator.
3. THE Activity_Card drill indicator SHALL display the number of drill lengths in the session.

### Requirement 7: AI Coach Drill Context

**User Story:** As a swimmer, I want the AI coach to acknowledge and reference my drill work when providing coaching advice, so that I receive relevant feedback on my technique training.

#### Acceptance Criteria

1. WHEN a session contains Drill_Length records, THE AI_Coach SHALL include drill information in the coaching prompt context.
2. THE AI_Coach drill context SHALL include the number of drill lengths, total drill distance, and the position of drills within the session (beginning, middle, or end).
3. WHEN a session contains Drill_Length records, THE AI_Coach SHALL reference the drill work in at least one coaching tip when contextually appropriate.

### Requirement 8: Drill Metrics Exclusion

**User Story:** As a swimmer, I want drill lengths excluded from my pace and SWOLF averages, so that my performance metrics accurately reflect my actual swimming ability.

#### Acceptance Criteria

1. WHEN calculating session average pace, THE FIT_Parser SHALL exclude Drill_Length records that have no valid avg_speed value from the pace calculation.
2. WHEN calculating session average SWOLF, THE FIT_Parser SHALL exclude Drill_Length records from the SWOLF calculation.
3. WHEN calculating session average stroke rate, THE FIT_Parser SHALL exclude Drill_Length records that have an avg_swimming_cadence of 0 or null from the stroke rate calculation.
4. IF all lengths in a session are Drill_Length records, THEN THE FIT_Parser SHALL report pace, SWOLF, and stroke_rate based on available Drill_Length data rather than raising a MetricsMissingError.
