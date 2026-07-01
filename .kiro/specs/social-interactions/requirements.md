# Requirements Document

## Introduction

The Social Interactions feature adds commenting and kudos (thumbs up) functionality to swim sessions in the AI Swim Coach app. Session owners can comment on their own sessions, friends can comment on shared sessions, and friends can give kudos to shared sessions. This feature enhances the social layer by enabling lightweight encouragement and conversation around swim activities.

## Glossary

- **Interactions_Service**: The backend service responsible for creating, retrieving, and deleting comments and kudos associated with swim sessions.
- **Comment**: A text-based message associated with a specific swim session, authored by either the session owner or an authorized friend.
- **Kudos**: A single "thumbs up" acknowledgment given by a friend to a swim session, limited to one per user per session.
- **Session_Owner**: The user whose user_id matches the session's user_id field in the ai-swim-coach-sessions table.
- **Authorized_Friend**: A user who has a mutual Friend_Relationship with the Session_Owner and whose session has Activity_Visibility set to "shared".
- **Interactions_Panel**: The UI section on the ActivityDetailPage that displays comments and kudos for a session.
- **Kudos_Icon**: A refined, minimal line-art SVG thumbs-up icon used to represent kudos throughout the application.
- **ActivityCard_Kudos**: The kudos indicator displayed on ActivityCard components in the activity feed.

## Requirements

### Requirement 1: Comment Creation by Session Owner

**User Story:** As a swimmer, I want to add a comment to my own swim session, so that I can record personal notes and reflections about my training.

#### Acceptance Criteria

1. WHEN the Session_Owner views their own session on the ActivityDetailPage, THE Interactions_Panel SHALL display a text input field for adding a comment.
2. WHEN the Session_Owner submits a comment with 1 to 500 characters, THE Interactions_Service SHALL store the comment associated with the session_id, the user_id of the author, a generated comment_id (UUID v4), and a created_at timestamp in ISO 8601 format.
3. WHEN the Interactions_Service successfully stores a comment, THE Interactions_Panel SHALL append the new comment to the comment list without a full page reload.
4. IF the Session_Owner submits an empty comment or a comment exceeding 500 characters, THEN THE Interactions_Panel SHALL display a validation error and prevent submission.
5. IF the Interactions_Service fails to store the comment, THEN THE Interactions_Panel SHALL display an error message and retain the comment text in the input field.

### Requirement 2: Comment Creation by Friends

**User Story:** As a swimmer, I want to comment on my friend's shared swim session, so that I can offer encouragement and feedback.

#### Acceptance Criteria

1. WHEN an Authorized_Friend views a shared session on the ActivityDetailPage, THE Interactions_Panel SHALL display a text input field for adding a comment.
2. WHEN an Authorized_Friend submits a comment with 1 to 500 characters, THE Interactions_Service SHALL store the comment associated with the session_id, the user_id of the commenter, a generated comment_id (UUID v4), and a created_at timestamp in ISO 8601 format.
3. WHEN a user who is not the Session_Owner and not an Authorized_Friend views a session, THE Interactions_Panel SHALL NOT display the comment input field.
4. IF the Interactions_Service receives a comment request from a user who is not the Session_Owner and not an Authorized_Friend, THEN THE Interactions_Service SHALL reject the request with a 403 Forbidden status.

### Requirement 3: Comment Display

**User Story:** As a swimmer, I want to see all comments on a session, so that I can read feedback and follow conversations.

#### Acceptance Criteria

1. WHEN the ActivityDetailPage loads a session, THE Interactions_Service SHALL return all comments for that session_id sorted by created_at in ascending order.
2. THE Interactions_Panel SHALL display each comment with the author's display name, the comment text, and a relative timestamp (e.g., "2 hours ago").
3. WHEN a session has no comments, THE Interactions_Panel SHALL display the placeholder text "No comments yet. Be the first to add one."
4. WHILE comments are loading, THE Interactions_Panel SHALL display a loading indicator.
5. IF the Interactions_Service fails to retrieve comments, THEN THE Interactions_Panel SHALL display an error message with a retry option.

### Requirement 4: Comment Deletion

**User Story:** As a swimmer, I want to delete my own comments, so that I can remove messages I no longer want displayed.

#### Acceptance Criteria

1. THE Interactions_Panel SHALL display a delete option on comments authored by the current user.
2. WHEN the user selects the delete option on their own comment, THE Interactions_Panel SHALL display a confirmation prompt before proceeding.
3. WHEN the user confirms deletion, THE Interactions_Service SHALL remove the comment identified by comment_id from storage.
4. WHEN the Interactions_Service successfully deletes a comment, THE Interactions_Panel SHALL remove the comment from the displayed list without a full page reload.
5. IF the Interactions_Service receives a delete request from a user who is not the comment author, THEN THE Interactions_Service SHALL reject the request with a 403 Forbidden status.
6. IF the Interactions_Service fails to delete the comment, THEN THE Interactions_Panel SHALL display an error message and retain the comment in the list.

### Requirement 5: Kudos on Shared Sessions

**User Story:** As a swimmer, I want to give a thumbs up to my friend's swim session, so that I can quickly acknowledge their effort.

#### Acceptance Criteria

1. WHEN an Authorized_Friend views a shared session on the ActivityDetailPage, THE Interactions_Panel SHALL display the Kudos_Icon as a clickable button.
2. WHEN an Authorized_Friend clicks the Kudos_Icon and has not already given kudos to that session, THE Interactions_Service SHALL store a kudos record associated with the session_id, the user_id of the giver, and a created_at timestamp in ISO 8601 format.
3. WHEN the Interactions_Service successfully stores a kudos record, THE Interactions_Panel SHALL update the Kudos_Icon to an active/filled state and increment the kudos count.
4. WHEN an Authorized_Friend has already given kudos to a session, THE Interactions_Panel SHALL display the Kudos_Icon in an active/filled state.
5. WHEN an Authorized_Friend clicks the Kudos_Icon and has already given kudos to that session, THE Interactions_Service SHALL remove the kudos record for that user and session.
6. WHEN the Interactions_Service successfully removes a kudos record, THE Interactions_Panel SHALL update the Kudos_Icon to an inactive/outline state and decrement the kudos count.
7. THE Interactions_Service SHALL enforce a maximum of one kudos record per user per session.
8. IF the Interactions_Service fails to store or remove a kudos record, THEN THE Interactions_Panel SHALL display an error message and revert the Kudos_Icon to its previous state.

### Requirement 6: Kudos Display and Count

**User Story:** As a swimmer, I want to see how many kudos a session has received, so that I can feel encouraged by my friends' support.

#### Acceptance Criteria

1. WHEN the ActivityDetailPage loads a session, THE Interactions_Service SHALL return the total kudos count and whether the current user has given kudos to that session.
2. THE Interactions_Panel SHALL display the Kudos_Icon alongside the total kudos count.
3. WHEN a session has zero kudos, THE Interactions_Panel SHALL display the Kudos_Icon in an inactive/outline state with no count number shown.
4. THE Session_Owner SHALL NOT be able to give kudos to their own session.
5. WHEN the Session_Owner views their own session with kudos, THE Interactions_Panel SHALL display the kudos count but the Kudos_Icon SHALL NOT be clickable.

### Requirement 7: Kudos Icon Design

**User Story:** As a product designer, I want the kudos icon to feel refined and classy, so that the UI maintains a premium, professional aesthetic.

#### Acceptance Criteria

1. THE Kudos_Icon SHALL be rendered as an inline SVG element using a minimal line-art style with uniform stroke width.
2. THE Kudos_Icon SHALL depict a thumbs-up hand gesture in a side-profile orientation.
3. THE Kudos_Icon inactive state SHALL use a single-color outline matching the application's secondary text color.
4. THE Kudos_Icon active state SHALL use a filled style with the application's primary accent color.
5. THE Kudos_Icon SHALL render at 24x24 pixels by default and scale proportionally when displayed in other contexts.
6. THE Kudos_Icon SHALL NOT use emoji characters or bitmap images.

### Requirement 8: Kudos on Activity Cards in Feed

**User Story:** As a swimmer, I want to see kudos counts on activity cards in the feed, so that I can quickly see which sessions received recognition.

#### Acceptance Criteria

1. WHILE the "Friends' Activities" tab is selected, THE ActivityCard_Kudos SHALL display the Kudos_Icon and the total kudos count for each session that has received at least one kudos.
2. WHEN a session in the feed has zero kudos, THE ActivityCard_Kudos SHALL NOT display a kudos indicator on that card.
3. WHEN the user views their own "My Activities" tab, THE ActivityCard_Kudos SHALL display the kudos count for sessions that have received at least one kudos from friends.

### Requirement 9: Authorization and Access Control

**User Story:** As a swimmer, I want the system to enforce visibility rules, so that only authorized users can interact with my sessions.

#### Acceptance Criteria

1. IF a user who is not the Session_Owner and not an Authorized_Friend attempts to add a comment, THEN THE Interactions_Service SHALL reject the request with a 403 Forbidden status.
2. IF a user attempts to give kudos to a session where the Session_Owner has Activity_Visibility set to "not_shared", THEN THE Interactions_Service SHALL reject the request with a 403 Forbidden status.
3. IF a user attempts to give kudos to their own session, THEN THE Interactions_Service SHALL reject the request with a 403 Forbidden status.
4. WHEN a Session_Owner changes Activity_Visibility from "shared" to "not_shared", THE Interactions_Service SHALL retain existing comments and kudos but THE ActivityDetailPage SHALL NOT be accessible to friends.
