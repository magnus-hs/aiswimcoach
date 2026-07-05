# Implementation Plan: Notes UI Restructure

## Overview

Restructure the Training Notes feature by removing notes from the Dashboard, creating a dedicated `/notes` page accessible from the Profile dropdown, adding per-session notes to the Activity Detail Page, and extending the backend/frontend API to support optional `session_id` on notes.

## Tasks

- [ ] 1. Backend: Add session_id support to notes service
  - [ ] 1.1 Extend TrainingNote dataclass and `create_note` to accept optional `session_id`
    - Add `session_id: str | None = None` field to the `TrainingNote` dataclass
    - Update `create_note` signature to accept `session_id: str | None = None`
    - Include `session_id` in the DynamoDB `put_item` call when provided
    - Return `session_id` in the created `TrainingNote`
    - _Requirements: 5.1, 5.2_

  - [ ] 1.2 Update `get_notes` to filter by `session_id`
    - Add `session_id: str | None = None` parameter to `get_notes`
    - When `session_id` is provided, filter results to only notes matching that `session_id`
    - When `session_id` is None, filter results to only notes without a `session_id` (global notes)
    - Include `session_id` in the returned `TrainingNote` objects
    - _Requirements: 5.3, 5.4, 5.5_

  - [ ] 1.3 Update handler.py to pass `session_id` through API endpoints
    - In the POST `/notes` handler, extract optional `session_id` from request body and pass to `create_note`
    - In the GET `/notes` handler, extract optional `session_id` query parameter and pass to `get_notes`
    - Include `session_id` in the JSON response when present
    - _Requirements: 5.1, 5.3_

  - [ ]* 1.4 Write property tests for session_id filtering logic
    - **Property 2: Global notes query returns only notes without session_id**
    - **Property 3: Session-filtered query returns only matching notes**
    - **Property 4: Session_id round-trip persistence**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**

  - [ ]* 1.5 Write unit tests for backend session_id support
    - Test `create_note` with and without `session_id`
    - Test `get_notes` filtering: global-only vs session-specific
    - Test handler endpoint with `session_id` in body and query param
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 2. Frontend: Update notesService API client
  - [ ] 2.1 Add `session_id` to `TrainingNote` interface and update API functions
    - Add optional `session_id?: string` field to the `TrainingNote` interface
    - Update `createNote` to accept optional `sessionId` parameter and include it in request body
    - Update `getNotes` to accept optional `sessionId` parameter and append as query parameter
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ]* 2.2 Write property test for frontend service session_id passthrough
    - **Property 5: Frontend service session_id passthrough**
    - **Validates: Requirements 6.2, 6.4**

- [ ] 3. Checkpoint - Backend and API client complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Frontend: Remove TrainingNotes from Dashboard
  - [ ] 4.1 Remove TrainingNotes component from DashboardPage
    - Remove the `<TrainingNotes />` component and its import from `DashboardPage.tsx`
    - Verify the dashboard still renders activity feed, distance chart, and other sidebar components
    - _Requirements: 1.1, 1.2_

- [ ] 5. Frontend: Add Training Notes page and navigation
  - [ ] 5.1 Create TrainingNotesPage component
    - Create `frontend/src/pages/TrainingNotesPage.tsx`
    - Implement explanatory section about how notes help the AI coach
    - Implement form with text input (max 500 chars) and submit button
    - Display global notes in reverse chronological order using `getNotes()` (no sessionId)
    - Implement delete functionality for individual notes
    - Display error messages on API failures
    - _Requirements: 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

  - [ ] 5.2 Add `/notes` route to App.tsx
    - Import `TrainingNotesPage`
    - Add protected route at `/notes` wrapped in `<ProtectedRoute>`
    - _Requirements: 3.1, 3.8_

  - [ ] 5.3 Add "Training Notes" menu item to Navigation dropdown
    - Add a "Training Notes" button to the Profile dropdown in `Navigation.tsx`
    - Position it between "Critical Swim Speed" and "Edit Profile"
    - On click, navigate to `/notes` and close the dropdown
    - _Requirements: 2.1, 2.2, 2.3_

  - [ ]* 5.4 Write unit tests for TrainingNotesPage and navigation
    - Test that TrainingNotesPage renders explanatory section and form
    - Test that the navigation dropdown includes "Training Notes" in the correct position
    - Test that the route requires authentication
    - _Requirements: 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.8_

- [ ] 6. Frontend: Add SessionNotesSection to Activity Detail Page
  - [ ] 6.1 Create SessionNotesSection component
    - Create `frontend/src/components/SessionNotesSection.tsx`
    - Accept `sessionId` prop
    - Fetch notes filtered by `sessionId` using `getNotes(sessionId)`
    - Implement form with text input (max 500 chars) and submit button
    - Display session notes in reverse chronological order
    - Implement delete functionality for individual notes
    - Display error messages on API failures
    - _Requirements: 4.3, 4.4, 4.5, 4.6, 4.7_

  - [ ] 6.2 Integrate SessionNotesSection into ActivityDetailPage
    - Import `SessionNotesSection` in `ActivityDetailPage.tsx`
    - Render `<SessionNotesSection sessionId={id} />` in the `renderSessionDetail` function
    - Position it after training load/coaching results and before `InteractionsPanel`
    - Only render when user is the session owner and mode is view
    - _Requirements: 4.1, 4.2, 4.8_

  - [ ]* 6.3 Write property test for notes ordering
    - **Property 1: Notes are displayed in reverse chronological order**
    - **Validates: Requirements 3.4, 4.5**

  - [ ]* 6.4 Write unit tests for SessionNotesSection
    - Test that SessionNotesSection renders form and notes for a session
    - Test that it only renders for session owner in view mode
    - Test deletion and error handling
    - _Requirements: 4.1, 4.2, 4.3, 4.6, 4.7, 4.8_

- [ ] 7. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The backend changes are implemented first so the frontend can immediately use the updated API

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2"] },
    { "id": 2, "tasks": ["1.3", "2.1"] },
    { "id": 3, "tasks": ["1.4", "1.5", "2.2"] },
    { "id": 4, "tasks": ["4.1", "5.1", "5.2", "5.3"] },
    { "id": 5, "tasks": ["5.4", "6.1"] },
    { "id": 6, "tasks": ["6.2"] },
    { "id": 7, "tasks": ["6.3", "6.4"] }
  ]
}
```
