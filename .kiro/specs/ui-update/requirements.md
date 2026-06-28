# Requirements Document

## Introduction

A comprehensive frontend redesign of the AI Swim Coach application, transforming the current functional but informal interface into a polished, Strava-inspired professional UI. The redesign introduces a new route structure (Dashboard, Activity Detail, Training Plans), a design token system using CSS custom properties, a sidebar-based layout, and restyled components with emphasis on large bold metrics and muted professional tones.

## Glossary

- **App**: The AI Swim Coach React single-page application
- **Dashboard**: The root authenticated page (/) displaying a left sidebar and center activity feed
- **Activity_Detail_Page**: The page (/activity/:id) showing full session data and upload functionality
- **Training_Plans_Page**: The dedicated page (/plans) for creating and viewing training plans
- **Design_Token_System**: A set of CSS custom properties defining colors, typography, spacing, and shadows
- **Sidebar**: A persistent left-hand column on the Dashboard showing profile summary, key stats, and streak
- **Activity_Feed**: A chronological list of recent swim sessions displayed in the center of the Dashboard
- **Activity_Card**: A clickable card in the Activity_Feed representing a single swim session
- **Upload_Section**: The file drop zone and upload flow embedded within the Activity_Detail_Page
- **Profile_Modal**: A modal overlay for viewing and editing user profile information
- **Navigation**: The persistent top-level header and route navigation elements

## Requirements

### Requirement 1: Design Token System

**User Story:** As a developer, I want a centralized set of CSS custom properties for colors, typography, and spacing, so that the design remains consistent and easy to maintain.

#### Acceptance Criteria

1. THE Design_Token_System SHALL define CSS custom properties on the `:root` selector for primary color (desaturated professional blue), secondary color, neutral grays (at least 5 shades), background colors, surface colors, text colors, error color, and success color.
2. THE Design_Token_System SHALL define CSS custom properties for font-family (system sans-serif stack), font sizes (at least 6 scale steps from small to display), font weights (regular, medium, semibold, bold), and line heights.
3. THE Design_Token_System SHALL define CSS custom properties for spacing values (at least 8 scale steps from 0.25rem to 4rem), border-radius values (small, medium, large), and box-shadow values (subtle, card, elevated).
4. THE Design_Token_System SHALL use desaturated blue tones as the accent palette with neutral grays for backgrounds and surfaces, replacing saturated blue (#3b82f6) with a more muted professional variant.

### Requirement 2: Route Structure

**User Story:** As a user, I want a clean three-page navigation structure, so that I can access all features through a simple and predictable layout.

#### Acceptance Criteria

1. THE App SHALL define exactly three primary routes: Dashboard at path `/`, Activity_Detail_Page at path `/activity/:id`, and Training_Plans_Page at path `/plans`.
2. THE App SHALL remove the `/upload` route and the `/history` route entirely from the route configuration.
3. WHEN an authenticated user navigates to the root path `/`, THE App SHALL render the Dashboard.
4. WHEN an unauthenticated user navigates to any protected route, THE App SHALL redirect the user to the `/login` page.
5. THE App SHALL retain `/login` and `/register` as public routes for authentication.
6. THE App SHALL retain the `/session/:id` path as an alias that redirects to `/activity/:id` to preserve backward compatibility for any existing links.

### Requirement 3: Dashboard Layout

**User Story:** As a user, I want a dashboard with a sidebar and activity feed, so that I can see my profile summary and recent sessions at a glance.

#### Acceptance Criteria

1. THE Dashboard SHALL render a two-column layout with a fixed-width Sidebar on the left (280px) and a flexible-width Activity_Feed in the center.
2. THE Sidebar SHALL display the user's profile picture (or placeholder avatar), display name, and member-since date.
3. THE Sidebar SHALL display key aggregate stats including total sessions count, total distance swum, and current training streak in days.
4. THE Sidebar SHALL display stat values using large bold typography (at least 1.5rem font-size, bold weight).
5. THE Activity_Feed SHALL display a chronological list of Activity_Cards ordered by session date descending.
6. THE Dashboard SHALL display a "+ New Activity" button that navigates the user to the Activity_Detail_Page in upload mode.
7. WHEN the viewport width is below 768px, THE Dashboard SHALL collapse the Sidebar above the Activity_Feed in a single-column stacked layout.
8. THE Dashboard SHALL be a read-only feed with no inline file upload capability.

### Requirement 4: Activity Card

**User Story:** As a user, I want activity cards showing key metrics prominently, so that I can quickly scan my recent sessions.

#### Acceptance Criteria

1. THE Activity_Card SHALL display the session date, stroke type, total distance, total time, average pace per 100m, and SWOLF score.
2. THE Activity_Card SHALL render total distance using large bold typography (at least 1.75rem font-size, bold weight) as the primary metric.
3. THE Activity_Card SHALL render secondary metrics (time, pace, SWOLF) in smaller muted text below the primary metric.
4. WHEN the user clicks an Activity_Card, THE App SHALL navigate to the Activity_Detail_Page for that session.
5. THE Activity_Card SHALL use card-level box-shadow from the Design_Token_System and border-radius for a contained elevated appearance.

### Requirement 5: Activity Detail Page

**User Story:** As a user, I want a single page where I can both view session details and upload new sessions, so that the upload flow is contextually located.

#### Acceptance Criteria

1. WHEN the Activity_Detail_Page is accessed with a valid session ID, THE Activity_Detail_Page SHALL fetch and display the session summary, splits table, heart rate zones, coaching tips, ability assessment, and training plan (when available).
2. WHEN the Activity_Detail_Page is accessed via the "+ New Activity" action (without a session ID or with a dedicated upload mode), THE Activity_Detail_Page SHALL display the Upload_Section with file drop zone.
3. WHEN a file upload completes successfully, THE Activity_Detail_Page SHALL display the resulting session data in the same detail layout.
4. THE Activity_Detail_Page SHALL display a back-navigation link to the Dashboard.
5. THE Activity_Detail_Page SHALL render all metric values using large bold typography consistent with the Design_Token_System display font sizes.

### Requirement 6: Training Plans Page

**User Story:** As a user, I want a dedicated page for training plans, so that plan creation and review is separate from individual session analysis.

#### Acceptance Criteria

1. THE Training_Plans_Page SHALL display the training goal form for creating new plans.
2. WHEN a training plan is generated, THE Training_Plans_Page SHALL display the plan result below the form.
3. THE Training_Plans_Page SHALL be accessible from the Navigation at all times when authenticated.
4. THE Training_Plans_Page SHALL use card-based layout consistent with the Design_Token_System styling.

### Requirement 7: Navigation

**User Story:** As a user, I want clear and minimal top navigation, so that I can move between sections without confusion.

#### Acceptance Criteria

1. THE Navigation SHALL display links to Dashboard, Training Plans, and Profile across all authenticated pages.
2. THE Navigation SHALL visually indicate the currently active route using a distinct color or underline style from the Design_Token_System.
3. THE Navigation SHALL display the application name or logo on the left side.
4. WHEN the user clicks the Profile link, THE App SHALL open the Profile_Modal as an overlay.
5. THE Navigation SHALL use a clean flat design with no heavy borders or gradients, consistent with the professional muted aesthetic.

### Requirement 8: Component Restyling

**User Story:** As a user, I want all data display components to look polished and professional, so that the interface feels modern and trustworthy.

#### Acceptance Criteria

1. THE SessionSummary component SHALL use Design_Token_System variables for all colors, spacing, border-radius, and shadows.
2. THE SplitsTable component SHALL use Design_Token_System variables and display table rows with subtle alternating row backgrounds using token-defined neutral colors.
3. THE HRZonesCard component SHALL use Design_Token_System variables and maintain the horizontal bar chart with zone colors.
4. THE CoachingResult component SHALL use Design_Token_System variables and display tips in a clean list format with muted label typography.
5. THE AbilityAssessmentCard component SHALL use Design_Token_System variables for consistent card styling.
6. THE CalendarView component SHALL use Design_Token_System variables for grid and cell styling.
7. THE ProgressGraph component SHALL use Design_Token_System variables for chart container styling.
8. THE TrainingGoalForm component SHALL use Design_Token_System variables for form inputs, labels, and button styling.
9. THE TrainingPlanResult component SHALL use Design_Token_System variables for plan section layout and typography.
10. WHEN displaying numeric metrics, THE SessionSummary component SHALL render primary values (distance, time) with at least 2rem font-size and bold weight.

### Requirement 9: Typography and Visual Hierarchy

**User Story:** As a user, I want clear visual hierarchy with bold numbers and clean type, so that important data stands out immediately.

#### Acceptance Criteria

1. THE App SHALL use a system sans-serif font stack as the base typeface for all UI text.
2. THE App SHALL render page headings at a minimum of 1.5rem font-size with bold weight.
3. THE App SHALL render key numeric metrics (distance, time, pace) at a minimum of 1.75rem font-size with bold weight in all contexts.
4. THE App SHALL render secondary labels using uppercase, small font-size (0.75rem), medium weight, and muted color from the Design_Token_System.
5. THE App SHALL maintain a minimum contrast ratio of 4.5:1 for normal text and 3:1 for large text as defined by WCAG 2.1 AA.

### Requirement 10: Profile Modal

**User Story:** As a user, I want my profile accessible as a modal overlay, so that I can review or edit profile info without leaving the current page context.

#### Acceptance Criteria

1. WHEN the user activates the Profile link in the Navigation, THE App SHALL display the Profile_Modal as a centered overlay with a backdrop.
2. THE Profile_Modal SHALL contain the existing profile view and edit functionality.
3. WHEN the user clicks the backdrop or a close button, THE Profile_Modal SHALL close and return focus to the triggering element.
4. THE Profile_Modal SHALL trap keyboard focus within the modal while open (WCAG 2.1 AA).
5. THE Profile_Modal SHALL be dismissible via the Escape key.

### Requirement 11: Responsive Design

**User Story:** As a user, I want the application to work well on both desktop and mobile screens, so that I can check my data from any device.

#### Acceptance Criteria

1. WHEN the viewport width is 768px or above, THE Dashboard SHALL display the two-column layout (Sidebar + Activity_Feed).
2. WHEN the viewport width is below 768px, THE Dashboard SHALL stack the Sidebar content above the Activity_Feed in a single column.
3. THE Activity_Detail_Page SHALL constrain content to a maximum width of 48rem and center horizontally on wide viewports.
4. THE Navigation SHALL remain accessible and functional at all viewport widths, collapsing to a compact format below 768px.
5. THE Activity_Card SHALL maintain readability and tap targets of at least 44x44px on touch devices.

### Requirement 12: Empty and Loading States

**User Story:** As a user, I want clear feedback when data is loading or unavailable, so that I understand the application state.

#### Acceptance Criteria

1. WHILE the Dashboard is fetching session data, THE Dashboard SHALL display a loading skeleton or indicator in the Activity_Feed area.
2. WHEN the Activity_Feed contains zero sessions, THE Dashboard SHALL display an empty state message with a call-to-action to upload a first session.
3. WHILE the Activity_Detail_Page is fetching session data, THE Activity_Detail_Page SHALL display a loading indicator.
4. IF a data fetch fails, THEN THE App SHALL display an error message with a description of the failure and a retry option when the error is retryable.
