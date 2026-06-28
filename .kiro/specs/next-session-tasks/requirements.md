# Requirements Document

## Introduction

This specification covers three improvements to the AI Swim Coach application: fixing the Plan Activate button (IAM permission issue), replacing the generated logo with a clean SVG, and improving the Personal Bests page with structured input controls and grouped display.

## Glossary

- **Lambda_Role**: The IAM role `ai-swim-coach-lambda-role` used by the `ai-swim-coach` Lambda function, with inline policy `ai-swim-coach-lambda-permissions`
- **Sessions_Table**: The DynamoDB table `Sessions` storing swim sessions and structured plans
- **Plan_Activate_Endpoint**: The PATCH `/plans/{plan_id}/status` API endpoint that transitions a plan from draft to active
- **Navigation_Component**: The `Navigation.tsx` React component rendering the top navigation bar including the application logo
- **Logo_Element**: The visual brand mark displayed in the navigation bar identifying the application
- **PB_Manager**: The `PersonalBestManager.tsx` React component for viewing and entering personal best times
- **PB_API**: The backend endpoints POST `/personal-bests` and GET `/personal-bests` for personal best persistence
- **Stroke_Type**: One of the four competitive swimming strokes: Freestyle, Breaststroke, Backstroke, or IM (Individual Medley)
- **Event_Format**: The string format `"{distance}m {stroke}"` used by the backend (e.g., "100m Freestyle")
- **Derived_PB**: A personal best estimated from session history using pace degradation factors
- **Manual_PB**: A personal best explicitly entered by the user

## Requirements

### Requirement 1: Fix Plan Activate IAM Permission

**User Story:** As a swimmer, I want to activate my training plan, so that I can begin following the structured training schedule.

#### Acceptance Criteria

1. WHEN a user sends a PATCH request to `/plans/{plan_id}/status` with the target status "active" for a plan in "draft" status, THE Plan_Activate_Endpoint SHALL transition the plan status from "draft" to "active" and return an HTTP 200 response containing the updated plan status
2. THE Lambda_Role inline policy `ai-swim-coach-lambda-permissions` SHALL include `dynamodb:UpdateItem` permission on the Sessions_Table and its `session_id-index` in the `DynamoDBSessions` policy statement, in addition to the existing `dynamodb:PutItem`, `dynamodb:GetItem`, and `dynamodb:Query` permissions
3. IF the Lambda_Role lacks the required DynamoDB permission, THEN THE Plan_Activate_Endpoint SHALL return an HTTP 500 response with a body containing an error message indicating a server-side failure
4. IF a user attempts to activate a plan that is not in "draft" status, THEN THE Plan_Activate_Endpoint SHALL return an HTTP 400 response with a body containing an error message indicating an invalid state transition
5. WHEN a user activates a draft plan and another plan for the same user is currently in "active" status, THE Plan_Activate_Endpoint SHALL first transition the previously active plan to "archived" status before transitioning the target plan to "active" status

### Requirement 2: Replace Logo with SVG

**User Story:** As a user, I want to see a clean, professional logo in the navigation bar, so that the application looks polished and trustworthy.

#### Acceptance Criteria

1. THE Navigation_Component SHALL render an inline SVG element as the Logo_Element instead of an `<img>` tag referencing `logo.png`
2. THE Logo_Element SHALL contain a single recognizable graphic depicting stylized water lanes or a swimmer silhouette, using no more than 3 distinct colors from `tokens.css`
3. THE Logo_Element SHALL reference only CSS custom properties defined in `tokens.css` for all fill and stroke color values
4. THE Logo_Element SHALL render at a maximum height of 40 pixels and maintain a fixed aspect ratio so that width scales proportionally when height is constrained
5. WHEN the viewport width is below 600 pixels, THE Logo_Element SHALL remain visible with a rendered height no smaller than 24 pixels and shall not overflow its parent container
6. THE Logo_Element SHALL include an accessible `aria-label` attribute with the value "AI Swim Coach"
7. THE Logo_Element SHALL have a `role="img"` attribute so that assistive technologies identify it as a meaningful image

### Requirement 3: Structured Personal Best Input

**User Story:** As a swimmer, I want to select stroke and distance from dropdowns when entering a personal best, so that I avoid typos and use consistent event names.

#### Acceptance Criteria

1. THE PB_Manager SHALL display a Stroke_Type dropdown with options: Freestyle, Backstroke, Breaststroke, Butterfly, IM
2. THE PB_Manager SHALL display a distance dropdown with options: 50m, 100m, 200m, 400m, 800m, 1500m, Custom
3. WHEN the user selects "Custom" from the distance dropdown, THE PB_Manager SHALL display an additional numeric input field for entering a custom distance in meters, accepting whole numbers between 25 and 5000 inclusive
4. WHILE "Custom" is not selected, THE PB_Manager SHALL hide the custom distance input field
5. THE PB_Manager SHALL display a time input field accepting values in MM:SS or M:SS format where minutes is 0–59 and seconds is 00–59 (e.g., "1:05", "0:28")
6. WHEN the user submits the form with all fields valid, THE PB_Manager SHALL construct the event name in Event_Format by combining the selected distance and stroke (e.g., "100m Freestyle")
7. WHEN the user submits the form with a custom distance, THE PB_Manager SHALL construct the event name using the custom distance value (e.g., "350m Backstroke")
8. IF the user submits the form with an invalid or empty time value, THEN THE PB_Manager SHALL display an inline error message indicating the expected time format and not submit the form
9. IF the user selects "Custom" and enters a distance value outside the range 25–5000 or a non-integer value, THEN THE PB_Manager SHALL display an inline error message indicating the valid distance range and not submit the form
10. IF the form submission to the backend fails, THEN THE PB_Manager SHALL display an error message indicating the save was unsuccessful and preserve the user's entered data

### Requirement 4: Personal Bests Grouped Display

**User Story:** As a swimmer, I want to see my personal bests grouped by stroke type with manual and derived times compared side by side, so that I can assess my progress at a glance.

#### Acceptance Criteria

1. THE PB_Manager SHALL group all personal bests by Stroke_Type (parsed from the event name format "{distance}m {Stroke_Type}") and display each group as a separate section ordered alphabetically by Stroke_Type name
2. THE PB_Manager SHALL display each stroke group with a visible heading showing the Stroke_Type name (one of: Backstroke, Breaststroke, Freestyle, IM)
3. WHEN both a Manual_PB and a Derived_PB exist for the same event (same distance and stroke combination), THE PB_Manager SHALL display both times side by side within that event's row, with the Manual_PB time and the Derived_PB time each labeled by source
4. WHEN both a Manual_PB and a Derived_PB exist for the same event, THE PB_Manager SHALL display the absolute time difference in seconds (to one decimal place) labeled as "faster" if the Manual_PB is lower than the Derived_PB, or "slower" if the Manual_PB is higher than the Derived_PB
5. THE PB_Manager SHALL visually distinguish Manual_PB entries from Derived_PB entries using distinct badge labels reading "manual" and "derived" respectively
6. WHEN no personal bests exist for a stroke group, THE PB_Manager SHALL omit that group from the display entirely so that only stroke types with at least one recorded PB are shown
7. IF the GET /personal-bests request fails or returns an error, THEN THE PB_Manager SHALL display an error message indicating that personal bests could not be loaded and SHALL NOT display any stale or partial data
8. WHEN only a Manual_PB or only a Derived_PB exists for a given event (but not both), THE PB_Manager SHALL display the single available time with its source badge and SHALL NOT display a time difference
