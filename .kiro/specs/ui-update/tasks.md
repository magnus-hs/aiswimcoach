# Implementation Plan: UI Update

## Overview

Transform the AI Swim Coach frontend into a polished, Strava-inspired professional UI. The implementation proceeds in layers: design tokens first, then layout/routing changes, then new components, then restyling existing components, and finally wiring everything together.

## Tasks

- [x] 1. Create design token system and global styles foundation
  - [x] 1.1 Create `src/tokens.css` with all CSS custom properties
    - Define color palette (primary, secondary, neutrals, semantic colors)
    - Define typography scale (font-family, sizes, weights, line-heights)
    - Define spacing scale, border-radius, and box-shadow tokens
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 1.2 Update `src/index.css` to import tokens and set base styles
    - Import tokens.css before all other styles
    - Apply token-based body/html defaults (font-family, background, text color)
    - Remove any hardcoded color values from global styles
    - _Requirements: 1.1, 9.1_

- [x] 2. Implement route structure and navigation
  - [x] 2.1 Update `App.tsx` with new route configuration
    - Define routes: `/` → Dashboard, `/activity/:id` → ActivityDetailPage, `/activity/new` → ActivityDetailPage (upload mode), `/plans` → TrainingPlansPage
    - Add `/session/:id` redirect to `/activity/:id` for backward compatibility
    - Remove `/upload` and `/history` routes
    - Retain `/login` and `/register` as public routes
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [x] 2.2 Create `Navigation` component (`src/components/Navigation.tsx` + `Navigation.css`)
    - Render app name/logo on the left
    - Render NavLink items for Dashboard, Training Plans, and Profile button
    - Apply active route indicator using NavLink className
    - Use flat clean design with token-based styling
    - Support compact format below 768px
    - _Requirements: 7.1, 7.2, 7.3, 7.5, 11.4_

  - [ ]* 2.3 Write property test for protected route redirect
    - **Property 1: Protected route redirect**
    - **Validates: Requirements 2.4**

  - [ ]* 2.4 Write property test for session path backward compatibility
    - **Property 2: Session path backward compatibility**
    - **Validates: Requirements 2.6**

- [x] 3. Implement Dashboard page with Sidebar and ActivityFeed
  - [x] 3.1 Create `computeStreak` utility (`src/utils/computeStreak.ts`)
    - Implement consecutive-day streak computation from session dates
    - Count backward from today for each consecutive calendar day with a session
    - _Requirements: 3.3_

  - [x] 3.2 Create `Sidebar` component (`src/components/Sidebar.tsx` + `Sidebar.css`)
    - Display profile picture (or placeholder avatar), display name, member-since date
    - Display aggregate stats: total sessions, total distance, streak
    - Render stat values using large bold typography (≥1.5rem, bold)
    - _Requirements: 3.2, 3.3, 3.4_

  - [x] 3.3 Create `ActivityCard` component (`src/components/ActivityCard.tsx` + `ActivityCard.css`)
    - Display session date, stroke type, total distance, total time, pace, SWOLF
    - Render distance as primary metric (≥1.75rem, bold)
    - Render secondary metrics in smaller muted text
    - Apply card-level shadow and border-radius from tokens
    - Navigate to `/activity/:id` on click
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 3.4 Create `ActivityFeed` component (`src/components/ActivityFeed.tsx` + `ActivityFeed.css`)
    - Render ActivityCards in descending session date order
    - Handle loading state with skeleton cards (3 placeholders)
    - Handle empty state with CTA to upload first session
    - Handle error state with ErrorBanner and retry
    - _Requirements: 3.5, 12.1, 12.2, 12.4_

  - [x] 3.5 Create `DashboardPage` (`src/pages/DashboardPage.tsx`)
    - Two-column grid layout: Sidebar (280px) + ActivityFeed (flex)
    - Fetch sessions and user data, compute aggregates
    - Include "+ New Activity" button navigating to `/activity/new`
    - Responsive: collapse to single-column below 768px
    - No inline upload capability (read-only feed)
    - _Requirements: 3.1, 3.6, 3.7, 3.8_

  - [ ]* 3.6 Write property test for sidebar aggregate stats correctness
    - **Property 3: Sidebar aggregate stats correctness**
    - **Validates: Requirements 3.3**

  - [ ]* 3.7 Write property test for activity feed ordering
    - **Property 4: Activity feed ordering**
    - **Validates: Requirements 3.5**

  - [ ]* 3.8 Write property test for activity card completeness and navigation
    - **Property 5: Activity card completeness and navigation**
    - **Validates: Requirements 4.1, 4.4**

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement ActivityDetailPage and TrainingPlansPage
  - [x] 5.1 Create `ActivityDetailPage` (`src/pages/ActivityDetailPage.tsx`)
    - When accessed with valid session ID: fetch and display session summary, splits, HR zones, coaching tips, ability assessment, training plan
    - When accessed in upload mode (via `/activity/new`): display FileDropZone
    - On successful upload: display resulting session data in detail layout
    - Include back-navigation link to Dashboard
    - Display metrics using large bold typography from token system
    - Show loading indicator during fetch, error state on failure
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 12.3, 12.4_

  - [x] 5.2 Create `TrainingPlansPage` (`src/pages/TrainingPlansPage.tsx`)
    - Display TrainingGoalForm for creating new plans
    - Display generated plan result below form
    - Use card-based layout consistent with design tokens
    - Accessible from Navigation at all times when authenticated
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 6. Implement ProfileModal
  - [x] 6.1 Create `ProfileModal` component (`src/components/ProfileModal.tsx` + `ProfileModal.css`)
    - Render as centered overlay with backdrop
    - Include existing profile view/edit functionality
    - Implement focus trap (Tab/Shift+Tab cycling)
    - Dismiss on Escape key, backdrop click, or close button
    - Return focus to trigger element on close
    - Apply role="dialog", aria-modal="true", aria-label
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

  - [ ]* 6.2 Write unit tests for ProfileModal accessibility
    - Test focus trap behavior (Tab cycling)
    - Test Escape key dismissal
    - Test backdrop click dismissal
    - Test focus return to trigger element
    - _Requirements: 10.3, 10.4, 10.5_

- [x] 7. Restyle existing components with design tokens
  - [x] 7.1 Restyle `SessionSummary` component
    - Replace hardcoded colors/sizes with token variables
    - Render primary metrics (distance, time) at ≥2rem bold
    - _Requirements: 8.1, 8.10, 9.3_

  - [x] 7.2 Restyle `SplitsTable` component
    - Apply token variables for colors and spacing
    - Add alternating row backgrounds using neutral token colors
    - _Requirements: 8.2_

  - [x] 7.3 Restyle `HRZonesCard`, `CoachingResult`, `AbilityAssessmentCard` CSS
    - Update HRZonesCard.css with token variables, maintain bar chart colors
    - Update CoachingResult.css with token typography and spacing
    - Update AbilityAssessmentCard.css with token card styling
    - _Requirements: 8.3, 8.4, 8.5_

  - [x] 7.4 Restyle `CalendarView`, `ProgressGraph`, `TrainingGoalForm`, `TrainingPlanResult`
    - Update CalendarView.css with token grid/cell styling
    - Update ProgressGraph.css with token container styling
    - Update TrainingGoalForm with token form inputs, labels, buttons
    - Update TrainingPlanResult with token section layout and typography
    - _Requirements: 8.6, 8.7, 8.8, 8.9_

- [x] 8. Typography, responsive polish, and integration wiring
  - [x] 8.1 Apply global typography and visual hierarchy rules
    - Ensure system sans-serif stack is base typeface
    - Page headings at ≥1.5rem bold
    - Key numeric metrics at ≥1.75rem bold across all contexts
    - Secondary labels: uppercase, 0.75rem, medium weight, muted color
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [x] 8.2 Wire Navigation and ProfileModal into App shell
    - Replace Header with Navigation in App.tsx
    - Add ProfileModal state management (open/close) in App or layout wrapper
    - Connect Profile button in Navigation to open ProfileModal
    - _Requirements: 7.4, 10.1_

  - [x] 8.3 Verify responsive behavior across breakpoints
    - Dashboard two-column above 768px, stacked below
    - ActivityDetail constrained to max-width 48rem, centered
    - Navigation compact below 768px
    - ActivityCard tap targets ≥44x44px on touch devices
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

  - [ ]* 8.4 Write property test for navigation active indicator
    - **Property 6: Navigation active indicator**
    - **Validates: Requirements 7.2**

  - [ ]* 8.5 Write property test for design token contrast compliance
    - **Property 7: Design token contrast compliance**
    - **Validates: Requirements 9.5**

- [x] 9. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The existing `UploadPage`, `HistoryPage`, and `Header` components are replaced but should not be deleted until integration is confirmed
- All new components use TypeScript and plain CSS (no CSS-in-JS or preprocessors)

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2"] },
    { "id": 2, "tasks": ["2.1", "2.2", "3.1", "3.2", "3.3"] },
    { "id": 3, "tasks": ["2.3", "2.4", "3.4", "3.5", "5.2"] },
    { "id": 4, "tasks": ["3.6", "3.7", "3.8", "5.1"] },
    { "id": 5, "tasks": ["6.1", "7.1", "7.2", "7.3", "7.4"] },
    { "id": 6, "tasks": ["6.2", "8.1", "8.2"] },
    { "id": 7, "tasks": ["8.3", "8.4", "8.5"] }
  ]
}
```
