# Requirements Document

## Introduction

This feature bundles three related improvements to the AI Swim Coach application:

1. **Fix plan activation** — The "Activate" button on training plans currently returns a
   500 error because the Lambda IAM role cannot write status updates to the sessions table.
   Structured plans are stored in the Sessions DynamoDB table (with `PLAN#`/`MPLAN#` sort
   keys), and activating a plan issues a DynamoDB `UpdateItem`. The Lambda role's inline
   policy grants `PutItem`, `GetItem`, and `Query` on that table but not `UpdateItem`.
2. **Replace the logo** — The old raster logo (`logo.png`) looked poor. It is replaced with
   a clean, minimal inline SVG rendered in the top navigation bar.
3. **Improve the Personal Bests page** — The Personal Bests page provides structured entry
   (stroke/distance dropdowns, custom distance, `M:SS` time input), displays entered PBs
   alongside PBs derived from session history with a faster/slower comparison, and groups
   entries by stroke.

The requirements below describe the intended end-state behavior. Portions of items 2 and 3
already exist in the codebase; these requirements formalize that behavior so gaps and
regressions can be detected, while item 1 captures the outstanding defect.

## Glossary

- **Lambda_Function**: The `ai-swim-coach` AWS Lambda function (region `us-east-1`) serving
  the backend API at `https://lp84bjpr2c.execute-api.us-east-1.amazonaws.com/prod`.
- **Lambda_Role**: The IAM execution role `ai-swim-coach-lambda-role` assumed by the
  Lambda_Function.
- **Inline_Policy**: The inline IAM policy `ai-swim-coach-lambda-permissions` attached to the
  Lambda_Role.
- **Sessions_Table**: The DynamoDB table storing swim sessions and structured training plans
  (default name `Sessions`).
- **DynamoDBSessions_Statement**: The statement within the Inline_Policy that grants DynamoDB
  actions on the Sessions_Table.
- **Plan_Lifecycle_Manager**: The backend module (`plan_lifecycle.py`) that manages plan state
  transitions (`draft` → `active` → `archived`).
- **Activation_Request**: An authenticated `POST`/`PUT` request that transitions a training
  plan to `active` status via the plan status endpoint.
- **Navigation_Bar**: The top navigation component (`Navigation.tsx`) rendered on every
  authenticated page.
- **Logo_Mark**: The inline SVG brand mark displayed at the left of the Navigation_Bar.
- **Personal_Best_Manager**: The frontend Personal Bests page component
  (`PersonalBestManager.tsx`).
- **PB_API**: The backend endpoints for personal bests (`POST /personal-bests`,
  `GET /personal-bests`).
- **Entered_PB**: A personal best manually recorded by the user (`source = "manual"`).
- **Derived_PB**: A personal best computed from the user's uploaded session history
  (`source = "derived"`).
- **Event_Name**: A personal-best event identifier in the format `"<distance>m <Stroke>"`,
  for example `"100m Freestyle"`.
- **Stroke_Type**: One of the supported strokes: Freestyle, Breaststroke, Backstroke, IM.
- **Standard_Distance**: One of the preset distances: 50, 100, 200, 400, 800, 1500 (meters).
- **Custom_Distance**: A user-supplied distance in meters selected via the "Custom" option.
- **Time_Input**: A time value entered in `M:SS` format (minutes, colon, two-digit seconds,
  with optional fractional seconds).

## Requirements

### Requirement 1: Grant plan-activation write permission

**User Story:** As a swimmer, I want the "Activate" button on a training plan to succeed, so
that I can make a plan my active plan without encountering a server error.

#### Acceptance Criteria

1. THE DynamoDBSessions_Statement SHALL include the action `dynamodb:UpdateItem` in addition
   to `dynamodb:PutItem`, `dynamodb:GetItem`, and `dynamodb:Query`.
2. WHEN the Plan_Lifecycle_Manager issues a DynamoDB `UpdateItem` against the Sessions_Table,
   THE Lambda_Role SHALL authorize the operation.
3. WHEN an authenticated Activation_Request is received for a plan in `draft` status, THE
   Lambda_Function SHALL update the plan status to `active` and respond with HTTP status 200.
4. WHEN a plan is activated WHILE another plan for the same user is `active`, THE
   Plan_Lifecycle_Manager SHALL transition the previously active plan to `archived` so that at
   most one plan per user is `active`.
5. IF an Activation_Request targets a plan that is not in `draft` status, THEN THE
   Lambda_Function SHALL respond with HTTP status 400 and a message describing the invalid
   transition.
6. IF an Activation_Request targets a plan identifier that does not exist for the
   authenticated user, THEN THE Lambda_Function SHALL respond with HTTP status 404.
7. THE DynamoDBSessions_Statement SHALL restrict the granted actions to the Sessions_Table
   resource and SHALL NOT grant DynamoDB actions on unrelated tables.

### Requirement 2: Display a clean inline SVG logo

**User Story:** As a user, I want a clean, professional brand mark in the navigation, so that
the application looks polished instead of showing a poor-quality generated image.

#### Acceptance Criteria

1. THE Navigation_Bar SHALL render the Logo_Mark as an inline SVG element.
2. THE Navigation_Bar SHALL NOT reference the raster image `logo.png` for the brand mark.
3. THE Logo_Mark SHALL use a minimal, professional design based on a swim-related motif
   (for example water lanes, goggles, or a swimmer silhouette).
4. THE Logo_Mark SHALL derive its colors from the application design tokens defined in
   `frontend/src/tokens.css` so that the mark adapts to the active theme.
5. THE Logo_Mark SHALL expose an accessible name of "AI Swim Coach" to assistive technology.
6. WHEN a user activates the Logo_Mark, THE Navigation_Bar SHALL navigate to the application
   home route (`/`).

### Requirement 3: Structured personal-best entry

**User Story:** As a swimmer, I want to enter a personal best by selecting a stroke and
distance and typing a time, so that I can record PBs accurately without free-form text.

#### Acceptance Criteria

1. THE Personal_Best_Manager SHALL present a Stroke_Type selection control offering exactly:
   Freestyle, Breaststroke, Backstroke, and IM.
2. THE Personal_Best_Manager SHALL present a distance selection control offering each
   Standard_Distance (50m, 100m, 200m, 400m, 800m, 1500m) and a "Custom" option.
3. WHERE the "Custom" distance option is selected, THE Personal_Best_Manager SHALL display a
   numeric Custom_Distance input.
4. WHERE a Standard_Distance is selected, THE Personal_Best_Manager SHALL hide the
   Custom_Distance input.
5. THE Personal_Best_Manager SHALL provide a Time_Input control that accepts values in `M:SS`
   format.
6. IF the Time_Input value is not valid `M:SS` format, THEN THE Personal_Best_Manager SHALL
   display a validation message and SHALL NOT submit the personal best.
7. IF the "Custom" option is selected AND the Custom_Distance is outside the range 25 to 5000
   meters inclusive, THEN THE Personal_Best_Manager SHALL display a validation message and
   SHALL NOT submit the personal best.
8. WHILE the stroke, distance, or time fields are incomplete, THE Personal_Best_Manager SHALL
   keep the submit control disabled.
9. WHEN the user submits a valid entry, THE Personal_Best_Manager SHALL construct an
   Event_Name in the format `"<distance>m <Stroke>"` and send it with the time in seconds to
   the PB_API.
10. WHEN a personal best is saved successfully, THE Personal_Best_Manager SHALL clear the entry
    fields and refresh the displayed personal bests.

### Requirement 4: Display and compare personal bests grouped by stroke

**User Story:** As a swimmer, I want to see my entered PBs next to my derived PBs grouped by
stroke, so that I can compare recorded times against times computed from my swims.

#### Acceptance Criteria

1. THE Personal_Best_Manager SHALL group displayed personal bests by Stroke_Type.
2. WHEN both an Entered_PB and a Derived_PB exist for the same Event_Name, THE
   Personal_Best_Manager SHALL display them together in one row for that event.
3. WHEN both an Entered_PB and a Derived_PB exist for the same Event_Name, THE
   Personal_Best_Manager SHALL display the time difference and label the difference as
   "faster" WHEN the entered time is lower than the derived time and "slower" WHEN the entered
   time is higher than the derived time.
4. WHERE only one source (Entered_PB or Derived_PB) exists for an event, THE
   Personal_Best_Manager SHALL display that value and show a placeholder for the missing
   source and for the difference.
5. WHERE a Derived_PB has an associated session identifier, THE Personal_Best_Manager SHALL
   link the derived time to that session's detail view.
6. WHEN no personal bests exist for the user, THE Personal_Best_Manager SHALL display an empty
   state message.
7. IF loading personal bests fails, THEN THE Personal_Best_Manager SHALL display an error
   message.
8. THE Personal_Best_Manager SHALL display each personal-best time in a minutes-and-seconds
   format.

### Requirement 5: Personal-best API persistence and retrieval

**User Story:** As a swimmer, I want my entered personal bests stored and returned alongside
derived ones, so that my records persist and I can review them across sessions.

#### Acceptance Criteria

1. WHEN the PB_API receives a `POST /personal-bests` request with a non-empty Event_Name and a
   positive time in seconds, THE PB_API SHALL persist the value as an Entered_PB and respond
   with HTTP status 200.
2. IF a `POST /personal-bests` request omits the Event_Name or provides a time that is not a
   positive number, THEN THE PB_API SHALL respond with HTTP status 400.
3. WHEN the PB_API receives a `GET /personal-bests` request, THE PB_API SHALL return all
   Entered_PBs for the authenticated user together with all Derived_PBs computed from session
   history.
4. THE PB_API SHALL label each returned personal best with a `source` of `"manual"` for an
   Entered_PB or `"derived"` for a Derived_PB.
5. WHEN both an Entered_PB and a Derived_PB exist for the same Event_Name, THE PB_API SHALL
   return both entries.
6. IF a `POST /personal-bests` or `GET /personal-bests` request is not authenticated, THEN THE
   PB_API SHALL respond with HTTP status 401.
7. IF a DynamoDB operation fails while saving or retrieving personal bests, THEN THE PB_API
   SHALL respond with HTTP status 500.
