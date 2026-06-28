# Requirements Document

## Introduction

This feature transforms the AI Swim Coach from generating single training sessions into a full periodized multi-week training plan system. Plans span a configurable number of weeks with multiple sessions per week, progressively building in intensity toward the swimmer's goal. The system uses personal bests (manually entered or derived from FIT file history) to set target paces, manages plan lifecycle (Draft → Active → Archived), and provides a detailed week-by-week view of saved plans.

## Glossary

- **Training_Plan**: A structured multi-week training program containing weekly session breakdowns with progressive overload toward a goal
- **Plan_Generator**: The backend module that orchestrates AI-based generation of multi-week training plans via Bedrock
- **Plan_Store**: The persistence layer responsible for saving, retrieving, and updating training plans in DynamoDB
- **Personal_Best**: A swimmer's fastest recorded time for a specific event/distance, either manually entered or derived from session history
- **PB_Resolver**: The component that determines a swimmer's personal bests by checking manual entries first, then deriving from FIT file session history
- **Session_Template**: A single training session within a week, containing warm-up, main set, cool-down, distance, and focus area
- **Plan_Lifecycle_Manager**: The component responsible for transitioning plans between Draft, Active, and Archived states
- **Plan_Detail_View**: The frontend component that displays the full week-by-week breakdown of a training plan
- **Periodization_Engine**: The logic within the Plan_Generator that ensures progressive overload across weeks
- **Week_Block**: A grouping of sessions within a single week of a training plan

## Requirements

### Requirement 1: Plan Creation with Multi-Week Structure

**User Story:** As a swimmer, I want to generate a multi-week training plan so that I have a structured program that builds progressively toward my goal.

#### Acceptance Criteria

1. WHEN a user submits a plan generation request with event, target time, and duration in weeks, THE Plan_Generator SHALL produce a Training_Plan containing one Week_Block for each requested week
2. THE Plan_Generator SHALL support plan durations between 4 and 12 weeks inclusive
3. WHEN a plan generation request specifies sessions per week, THE Plan_Generator SHALL create that number of Session_Templates within each Week_Block
4. THE Plan_Generator SHALL support between 3 and 5 sessions per week inclusive
5. WHEN a plan generation request does not specify sessions per week, THE Plan_Generator SHALL default to 3 sessions per week
6. WHEN a plan is generated, each Session_Template SHALL contain a session title, warm-up set, main set, cool-down set, total distance, focus notes, and session type

### Requirement 2: Progressive Overload Across Weeks

**User Story:** As a swimmer, I want my training plan to get progressively harder each week so that I build fitness toward my goal time.

#### Acceptance Criteria

1. WHEN generating a multi-week plan, THE Periodization_Engine SHALL increase training intensity across weeks such that later weeks contain faster target paces or higher volumes than earlier weeks
2. WHEN generating a multi-week plan, THE Periodization_Engine SHALL assign a session type from the set (endurance, speed, technique, threshold) to each Session_Template within a Week_Block
3. WHEN generating a multi-week plan, THE Periodization_Engine SHALL vary session types within a single Week_Block so that no two consecutive sessions have the same type
4. WHEN generating a multi-week plan with duration of 6 weeks or more, THE Periodization_Engine SHALL include at least one recovery week where intensity decreases compared to the preceding week

### Requirement 3: Personal Best Management

**User Story:** As a swimmer, I want my personal bests to inform target paces in my training plan so that the plan is calibrated to my current ability.

#### Acceptance Criteria

1. WHEN a user manually enters a personal best time for an event, THE Plan_Store SHALL persist that personal best associated with the user
2. THE Plan_Store SHALL store personal bests as a combination of event name (e.g., "100m Freestyle") and time in seconds
3. WHEN generating a training plan and the user has a manually entered personal best for the plan event, THE PB_Resolver SHALL use the manually entered value
4. WHEN generating a training plan and the user has no manually entered personal best for the plan event, THE PB_Resolver SHALL derive the personal best from the fastest pace recorded in the user's session history for the matching stroke type
5. WHEN generating a training plan with a resolved personal best, THE Plan_Generator SHALL use the personal best to calculate interval target paces within each Session_Template
6. IF the user has no personal best and no session history for the relevant stroke, THEN THE Plan_Generator SHALL generate the plan using the user's stated target time as the sole pacing reference

### Requirement 4: Plan Lifecycle Management

**User Story:** As a swimmer, I want only one active plan at a time with previous plans archived so that I always know which plan to follow.

#### Acceptance Criteria

1. WHEN a plan is first generated, THE Plan_Lifecycle_Manager SHALL assign the plan a status of "draft"
2. WHEN a user activates a draft plan, THE Plan_Lifecycle_Manager SHALL transition the plan status to "active"
3. WHEN a user activates a plan and another plan is currently active, THE Plan_Lifecycle_Manager SHALL transition the previously active plan to "archived" status before activating the new plan
4. THE Plan_Lifecycle_Manager SHALL enforce that at most one plan per user has "active" status at any time
5. WHEN a user explicitly archives an active plan, THE Plan_Lifecycle_Manager SHALL transition the plan status to "archived"
6. WHILE a plan has "archived" status, THE Plan_Lifecycle_Manager SHALL retain the plan data for read-only access

### Requirement 5: Plan Detail View

**User Story:** As a swimmer, I want to click on a saved plan and see its full week-by-week content so that I can review and follow the plan.

#### Acceptance Criteria

1. WHEN a user selects a saved plan from the plan list, THE Plan_Detail_View SHALL display the full plan content organized by week
2. WHEN displaying a plan, THE Plan_Detail_View SHALL show each Week_Block with its week number and all Session_Templates within that week
3. WHEN displaying a Session_Template, THE Plan_Detail_View SHALL show the session title, session type, warm-up set, main set, cool-down set, total distance, and focus notes
4. WHEN displaying the plan list, THE Plan_Detail_View SHALL show the plan status (draft, active, archived) for each plan
5. WHEN displaying the plan list, THE Plan_Detail_View SHALL visually distinguish the active plan from draft and archived plans

### Requirement 6: Plan Persistence

**User Story:** As a swimmer, I want my training plans stored reliably so that I can access them across sessions.

#### Acceptance Criteria

1. WHEN a training plan is generated, THE Plan_Store SHALL persist the complete plan including all Week_Blocks and Session_Templates
2. THE Plan_Store SHALL store each plan with a unique plan identifier, user identifier, creation timestamp, goal parameters, plan status, and plan duration in weeks
3. WHEN a user requests their plans, THE Plan_Store SHALL return all plans for that user ordered by creation date descending
4. WHEN a user requests a specific plan by identifier, THE Plan_Store SHALL return the complete plan with all Week_Blocks and Session_Templates
5. WHEN a plan status is updated, THE Plan_Store SHALL persist the new status and record the transition timestamp

### Requirement 7: Personal Best Derivation from Session History

**User Story:** As a swimmer, I want the system to automatically determine my personal bests from uploaded FIT files so that I don't have to manually enter them.

#### Acceptance Criteria

1. WHEN the PB_Resolver derives a personal best from session history, THE PB_Resolver SHALL identify the session with the fastest average pace per 100m for the matching stroke type
2. WHEN deriving a personal best, THE PB_Resolver SHALL scale the fastest 100m pace to the target event distance using a standard pace degradation factor
3. WHEN a user uploads a new session that contains a faster pace than the current derived personal best, THE PB_Resolver SHALL update the derived personal best on the next plan generation request
4. THE PB_Resolver SHALL treat manually entered personal bests as authoritative over derived values for the same event

### Requirement 8: Plan Generation API

**User Story:** As a frontend developer, I want clear API endpoints for plan operations so that I can build the training plan UI.

#### Acceptance Criteria

1. WHEN a POST request is made to the plan generation endpoint with valid goal parameters and week count, THE Plan_Generator SHALL return the generated Training_Plan with a unique plan identifier
2. WHEN a GET request is made to the user plans endpoint, THE Plan_Store SHALL return a summary list of all plans for the authenticated user
3. WHEN a GET request is made to the plan detail endpoint with a valid plan identifier, THE Plan_Store SHALL return the complete plan content
4. WHEN a PATCH request is made to update a plan status, THE Plan_Lifecycle_Manager SHALL validate the transition and update the plan status
5. IF a plan generation request contains invalid parameters (weeks outside 4-12 or sessions per week outside 3-5), THEN THE Plan_Generator SHALL return a validation error with a descriptive message
6. WHEN a POST request is made to the personal bests endpoint with an event and time, THE Plan_Store SHALL persist the personal best for the authenticated user
7. WHEN a GET request is made to the personal bests endpoint, THE PB_Resolver SHALL return all personal bests for the authenticated user including both manual entries and derived values
