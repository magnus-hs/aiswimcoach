# Requirements Document

## Introduction

This feature adds Critical Swim Speed (CSS) management and training load analysis to the AI Swim Coach application. Swimmers can enter their 400m and 200m time trial results to calculate their CSS pace, which is then used to categorize each set in a session by energy system (Sprint, Threshold, Aerobic) and compute a rest-adjusted training load score. A visualization on the Activity Detail page shows per-set energy system breakdown and session training load summary.

## Glossary

- **CSS**: Critical Swim Speed — a swimmer's threshold pace in seconds per 100m, calculated as 200 / (T400 - T200) where T400 and T200 are time trial durations in seconds
- **CSS_Page**: The dedicated page at route /css where users view CSS explanation, enter time trials, and save their CSS pace
- **Training_Load_Calculator**: The frontend module that computes per-set training load using CSS, pace, distance, and rest data
- **Energy_System**: Classification of a set's intensity relative to CSS: Sprint (pace < CSS - 5), Threshold (pace within ±5 of CSS), or Aerobic (pace > CSS + 5), all in seconds per 100m
- **Set_Load**: The training stress score for a single set, calculated as distance × intensity_factor × rest_multiplier
- **Session_Load**: The sum of all Set_Load values for a session
- **Training_Load_Visualization**: The UI section on the Activity Detail page displaying per-set energy system data and session load summary
- **Profile_Service**: The frontend API service that handles saving and retrieving user profile data including CSS pace
- **SplitGroup**: An existing frontend data structure representing a group of consecutive same-stroke lengths separated by rest, with totalDistance, totalTime, avgPacePer100m, and restAfter fields

## Requirements

### Requirement 1: CSS Page Navigation

**User Story:** As a swimmer, I want to access the CSS page from the Profile dropdown menu, so that I can easily find and manage my Critical Swim Speed.

#### Acceptance Criteria

1. THE CSS_Page SHALL be accessible at the route /css
2. WHEN a user opens the Profile dropdown menu, THE Navigation SHALL display a link labeled "Critical Swim Speed" that navigates to /css
3. THE CSS_Page SHALL be a protected route requiring authentication

### Requirement 2: CSS Explanation Display

**User Story:** As a swimmer, I want to understand what CSS is before entering my times, so that I know why this metric matters for my training.

#### Acceptance Criteria

1. WHEN the CSS_Page loads, THE CSS_Page SHALL display an explanation section describing CSS as the swimmer's threshold pace
2. THE CSS_Page SHALL explain that CSS is calculated from 400m and 200m time trials
3. THE CSS_Page SHALL display the formula: CSS = 200 / (T400 - T200) where times are in seconds

### Requirement 3: CSS Calculation from Time Trials

**User Story:** As a swimmer, I want to enter my 400m and 200m time trial results and have my CSS pace calculated automatically, so that I do not need to compute it manually.

#### Acceptance Criteria

1. THE CSS_Page SHALL provide an input field for 400m time in M:SS format
2. THE CSS_Page SHALL provide an input field for 200m time in M:SS format
3. WHEN both time fields contain valid values, THE CSS_Page SHALL calculate CSS pace as 200 / (T400_seconds - T200_seconds) and display the result in seconds per 100m
4. IF the 400m time is less than or equal to the 200m time, THEN THE CSS_Page SHALL display a validation error indicating that 400m time must be greater than 200m time
5. IF a time field contains a value not matching the M:SS format, THEN THE CSS_Page SHALL display a validation error for that field

### Requirement 4: CSS Persistence

**User Story:** As a swimmer, I want my CSS pace saved to my profile, so that it persists across sessions and can be used for training load analysis.

#### Acceptance Criteria

1. WHEN the user clicks the Save button with a valid calculated CSS value, THE Profile_Service SHALL store the css_pace_per_100m field (in seconds) in the UserProfiles DynamoDB table
2. WHEN the CSS_Page loads and the user has a previously saved CSS value, THE CSS_Page SHALL display the stored CSS pace
3. THE Backend SHALL accept and persist the css_pace_per_100m field as part of the user profile data

### Requirement 5: Energy System Categorization

**User Story:** As a swimmer, I want each set in my session classified by energy system based on my CSS, so that I can understand the physiological demands of my training.

#### Acceptance Criteria

1. WHEN a set's avgPacePer100m is less than the user's css_pace_per_100m minus 5, THE Training_Load_Calculator SHALL categorize the set as Sprint
2. WHEN a set's avgPacePer100m is within 5 seconds (inclusive) of the user's css_pace_per_100m, THE Training_Load_Calculator SHALL categorize the set as Threshold
3. WHEN a set's avgPacePer100m is greater than the user's css_pace_per_100m plus 5, THE Training_Load_Calculator SHALL categorize the set as Aerobic
4. IF the user has no saved CSS value, THEN THE Training_Load_Calculator SHALL skip energy system categorization

### Requirement 6: Rest-Adjusted Training Load Calculation

**User Story:** As a swimmer, I want a training load score for each set that accounts for distance, intensity, and rest duration, so that I can quantify my session stress.

#### Acceptance Criteria

1. THE Training_Load_Calculator SHALL compute base_load for each set as totalDistance multiplied by intensity_factor, where intensity_factor is 1.5 for Sprint, 1.0 for Threshold, and 0.7 for Aerobic
2. THE Training_Load_Calculator SHALL compute work_to_rest_ratio for each set as totalTime divided by restAfter seconds
3. THE Training_Load_Calculator SHALL compute rest_multiplier as the minimum of 1.5 and (0.8 + (work_to_rest_ratio × 0.2))
4. THE Training_Load_Calculator SHALL compute Set_Load as base_load multiplied by rest_multiplier
5. THE Training_Load_Calculator SHALL compute Session_Load as the sum of all Set_Load values in the session
6. IF a set has no rest (restAfter is null or zero), THEN THE Training_Load_Calculator SHALL apply the maximum rest_multiplier of 1.5
7. IF the user has no saved CSS value, THEN THE Training_Load_Calculator SHALL skip training load calculation entirely

### Requirement 7: Training Load Visualization

**User Story:** As a swimmer, I want to see a visual breakdown of energy systems and training load for each set on my activity page, so that I can review my session intensity distribution.

#### Acceptance Criteria

1. WHEN viewing an activity with splits data and the user has a saved CSS value, THE Training_Load_Visualization SHALL appear after the Efficiency Curve section and before the Coaching Tips section
2. THE Training_Load_Visualization SHALL display each set with its energy system category color-coded: red for Sprint, amber for Threshold, green for Aerobic
3. THE Training_Load_Visualization SHALL display each set's actual pace alongside the user's CSS pace for comparison
4. THE Training_Load_Visualization SHALL display each set's computed Set_Load value
5. THE Training_Load_Visualization SHALL display a summary section showing the total Session_Load
6. THE Training_Load_Visualization SHALL display a summary breakdown showing total load per energy system category
7. IF the user has no saved CSS value, THEN THE Training_Load_Visualization SHALL not render
8. IF the session has no splits data, THEN THE Training_Load_Visualization SHALL not render
