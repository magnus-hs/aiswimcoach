# Requirements Document

## Introduction

This feature restructures the Training Notes UI by removing the TrainingNotes component from the main dashboard, creating a dedicated Training Notes page accessible from the Profile dropdown menu, and adding per-swim session notes to individual activity detail pages. The goal is to reduce dashboard clutter while making notes more accessible and contextual.

## Glossary

- **Dashboard**: The main authenticated landing page at `/` that displays recent swim activities and summary statistics.
- **Training_Notes_Page**: A dedicated page at `/notes` that displays all global training notes and explains their purpose to the AI coach.
- **Profile_Dropdown**: The "Profile ▾" dropdown menu in the top navigation bar that provides access to user-related pages.
- **Activity_Detail_Page**: The page at `/activity/:id` that displays detailed metrics and data for a single swim session.
- **Session_Notes_Section**: A UI section on the Activity Detail Page that allows users to create, view, and delete notes tied to a specific swim session.
- **Global_Note**: A training note not associated with any specific session, used to inform the AI coach about general context (injuries, group changes, illness).
- **Session_Note**: A training note associated with a specific swim session via a `session_id` field.
- **Notes_API**: The existing backend notes endpoints (`POST /notes`, `GET /notes`, `DELETE /notes/:id`) that handle note CRUD operations.
- **Navigation_Component**: The top navigation header containing route links and the Profile Dropdown.

## Requirements

### Requirement 1: Remove TrainingNotes from Dashboard

**User Story:** As a swimmer, I want a cleaner dashboard focused on my recent activities, so that I can quickly see my swim history without unrelated UI elements.

#### Acceptance Criteria

1. THE Dashboard SHALL render without the TrainingNotes component.
2. THE Dashboard SHALL continue to display the activity feed, distance chart, and sidebar components without modification.

### Requirement 2: Add Training Notes Link to Profile Dropdown

**User Story:** As a swimmer, I want to access my Training Notes from the Profile dropdown menu, so that I can find them in a consistent location alongside other profile-related features.

#### Acceptance Criteria

1. THE Profile_Dropdown SHALL include a "Training Notes" menu item.
2. WHEN the user clicks the "Training Notes" menu item, THE Navigation_Component SHALL navigate the user to the `/notes` route.
3. THE "Training Notes" menu item SHALL appear between "Critical Swim Speed" and "Edit Profile" in the dropdown order.

### Requirement 3: Dedicated Training Notes Page

**User Story:** As a swimmer, I want a dedicated page for my training notes that explains how notes help the AI coach, so that I understand the value of recording observations.

#### Acceptance Criteria

1. THE Training_Notes_Page SHALL be accessible at the `/notes` route for authenticated users.
2. THE Training_Notes_Page SHALL display an explanatory section that communicates notes help drive AI coach answers by providing context about injuries, group changes, illness, and other relevant information.
3. THE Training_Notes_Page SHALL display a form for creating new global notes with a text input (maximum 500 characters) and a submit button.
4. THE Training_Notes_Page SHALL display all Global_Note entries in reverse chronological order (most recent first).
5. THE Training_Notes_Page SHALL allow the user to delete individual global notes.
6. THE Training_Notes_Page SHALL display only notes that have no associated session_id (global notes).
7. IF the Notes_API returns an error, THEN THE Training_Notes_Page SHALL display an error message to the user.
8. THE Training_Notes_Page SHALL require authentication and redirect unauthenticated users to the login page.

### Requirement 4: Per-Swim Session Notes Section

**User Story:** As a swimmer, I want to annotate individual swim sessions with notes, so that I can record session-specific observations like how I felt or technique focus areas.

#### Acceptance Criteria

1. THE Activity_Detail_Page SHALL display a Session_Notes_Section when viewing an existing session in view mode.
2. THE Session_Notes_Section SHALL appear below the session detail components and above the InteractionsPanel.
3. THE Session_Notes_Section SHALL display a form for creating new session notes with a text input (maximum 500 characters) and a submit button.
4. THE Session_Notes_Section SHALL display only notes associated with the current session's session_id.
5. THE Session_Notes_Section SHALL display session notes in reverse chronological order (most recent first).
6. THE Session_Notes_Section SHALL allow the user to delete individual session notes.
7. IF the Notes_API returns an error, THEN THE Session_Notes_Section SHALL display an error message to the user.
8. THE Session_Notes_Section SHALL only be visible to the session owner.

### Requirement 5: Backend Support for Session-Specific Notes

**User Story:** As a swimmer, I want my per-swim notes stored separately from global notes, so that each swim shows only its own annotations.

#### Acceptance Criteria

1. THE Notes_API SHALL accept an optional `session_id` field when creating a note.
2. WHEN a note is created with a `session_id`, THE Notes_API SHALL store the session_id association with the note.
3. THE Notes_API SHALL support filtering notes by `session_id` query parameter on the GET endpoint.
4. WHEN the GET endpoint is called with a `session_id` parameter, THE Notes_API SHALL return only notes matching that session_id.
5. WHEN the GET endpoint is called without a `session_id` parameter, THE Notes_API SHALL return only notes that have no session_id (global notes).

### Requirement 6: Frontend Notes API Client Updates

**User Story:** As a developer, I want the frontend notes service to support session-specific notes, so that the UI can create and fetch notes scoped to individual sessions.

#### Acceptance Criteria

1. THE notesService `createNote` function SHALL accept an optional `session_id` parameter.
2. WHEN `session_id` is provided, THE notesService `createNote` function SHALL include the session_id in the request body.
3. THE notesService `getNotes` function SHALL accept an optional `session_id` parameter.
4. WHEN `session_id` is provided, THE notesService `getNotes` function SHALL include the session_id as a query parameter in the request URL.
5. THE `TrainingNote` interface SHALL include an optional `session_id` field of type string.
