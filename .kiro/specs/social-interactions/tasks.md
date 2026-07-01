# Implementation Plan: Social Interactions

## Overview

This plan implements commenting and kudos functionality for swim sessions. The backend is built first (interactions_service.py module, handler route wiring), then the frontend (API service, InteractionsPanel, KudosIcon, ActivityCard updates). The approach stores comments and kudos as list attributes on existing session items in DynamoDB — no new tables needed.

## Tasks

- [x] 1. Implement backend interactions service
  - [x] 1.1 Create `backend/interactions_service.py` with authorization helpers and get_interactions
    - Create the new module following the same pattern as `friends_service.py`
    - Implement `_get_sessions_table()` helper (reuse env var `SESSIONS_TABLE` / default `ai-swim-coach-sessions`)
    - Implement `_authorize_interaction(session_id, current_user_id)` — loads session item, checks if user is session owner OR is an authorized friend (mutual friendship via `friends_service.get_friends` + session owner has `activity_visibility = "shared"` via `friends_service.get_activity_visibility`). Returns `(session_item, is_owner)` tuple or raises `PermissionError`
    - Implement `get_interactions(session_id, current_user_id)` — calls `_authorize_interaction`, reads `comments` and `kudos` list attributes from session item, returns `{"comments": [...], "kudos_count": int, "user_has_kudos": bool}` with comments sorted ascending by `created_at`
    - _Requirements: 3.1, 6.1, 9.1, 9.2_

  - [x] 1.2 Add comment creation and deletion to `backend/interactions_service.py`
    - Implement `add_comment(session_id, user_id, text)` — validates text is 1-500 chars (not whitespace-only), calls `_authorize_interaction`, generates UUID v4 `comment_id` and ISO 8601 `created_at`, fetches `display_name` via `friends_service._get_display_name`, appends comment dict to session's `comments` list attribute using DynamoDB `list_append` UpdateExpression, returns the new comment dict
    - Implement `delete_comment(session_id, comment_id, user_id)` — loads session, finds comment by `comment_id`, verifies `user_id` matches comment author (raises `PermissionError` if not), removes the comment from the list using DynamoDB `REMOVE comments[index]` UpdateExpression
    - _Requirements: 1.2, 1.4, 2.2, 2.4, 4.3, 4.5_

  - [x] 1.3 Add kudos toggle to `backend/interactions_service.py`
    - Implement `toggle_kudos(session_id, user_id)` — calls `_authorize_interaction`, raises `PermissionError` if `is_owner` is True (owner cannot self-kudos), checks if user already in `kudos` list: if yes removes their entry, if no appends `{"user_id": ..., "created_at": ...}`, returns `{"action": "added"|"removed", "kudos_count": int}`
    - Use DynamoDB conditional expressions or read-modify-write with optimistic locking to enforce uniqueness
    - _Requirements: 5.2, 5.5, 5.7, 6.4, 9.3_

  - [x] 1.4 Wire interaction routes into `backend/handler.py`
    - Import `interactions_service` functions at top of handler.py
    - Add route matching for `GET /sessions/{id}/interactions`, `POST /sessions/{id}/comments`, `DELETE /sessions/{id}/comments/{comment_id}`, `POST /sessions/{id}/kudos`
    - Each route must use `@require_auth` decorator and extract `user_id` from `event["auth_context"]`
    - Apply rate limiting: comment creation 20/60s, kudos toggle 30/60s (using existing `_enforce_rate_limit` helper)
    - Map exceptions: `ValueError` → 400, `PermissionError` → 403, session not found → 404, `ClientError` → 500
    - _Requirements: 1.2, 2.4, 5.2, 9.1, 9.2, 9.3_

- [x] 2. Checkpoint - Backend tests pass
  - Ensure all tests pass with `cd backend && python -m pytest tests/ -x -q`, ask the user if questions arise.

- [x] 3. Implement frontend API service and KudosIcon
  - [x] 3.1 Create `frontend/src/api/interactionsService.ts`
    - Define TypeScript interfaces: `Comment` (comment_id, user_id, display_name, text, created_at), `InteractionsData` (comments, kudos_count, user_has_kudos), `KudosToggleResult` (action, kudos_count)
    - Implement `getInteractions(sessionId)` — GET `/sessions/${sessionId}/interactions`
    - Implement `addComment(sessionId, text)` — POST `/sessions/${sessionId}/comments` with `{ text }` body
    - Implement `deleteComment(sessionId, commentId)` — DELETE `/sessions/${sessionId}/comments/${commentId}`
    - Implement `toggleKudos(sessionId)` — POST `/sessions/${sessionId}/kudos`
    - Follow the same auth header pattern as `friendsService.ts` (Bearer token from localStorage)
    - _Requirements: 1.2, 1.3, 4.3, 5.2, 5.5_

  - [x] 3.2 Create `frontend/src/components/KudosIcon.tsx`
    - Create a refined minimal line-art SVG component depicting a thumbs-up hand in side profile
    - Props: `active: boolean` (filled vs outline), `size?: number` (default 24), `onClick?: () => void`, `className?: string`
    - Inactive state: single-color outline using `var(--text-secondary)` stroke with uniform stroke-width
    - Active state: filled with `var(--color-primary)` accent color
    - Render as inline SVG, scale proportionally based on `size` prop, no viewBox distortion
    - Must NOT use emoji or bitmap images — pure SVG path elements with a premium, classy aesthetic
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

- [x] 4. Implement InteractionsPanel component
  - [x] 4.1 Create `frontend/src/components/InteractionsPanel.tsx` and `InteractionsPanel.css`
    - Props: `sessionId: string`, `isOwner: boolean`, `canInteract: boolean` (authorized friend)
    - On mount, call `getInteractions(sessionId)` and display loading state
    - Render kudos section: KudosIcon (clickable if `canInteract && !isOwner`), kudos count (hidden when 0), optimistic toggle with revert on error
    - Render comment list: each comment shows `display_name`, `text`, relative timestamp (e.g. "2 hours ago"), and delete button if authored by current user
    - Empty state: "No comments yet. Be the first to add one." placeholder
    - Comment input: text field + submit button, shown only if `isOwner || canInteract`, validate 1-500 chars client-side, show validation error inline, retain text on submission failure
    - Delete flow: confirmation prompt before calling `deleteComment`, show error and retain comment on failure
    - Error states: inline error banner with retry for network/500 errors, "permission denied" message for 403
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 2.1, 2.3, 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.4, 4.6, 5.1, 5.3, 5.4, 5.6, 5.8, 6.1, 6.2, 6.3, 6.5_

  - [x] 4.2 Integrate InteractionsPanel into `frontend/src/pages/ActivityDetailPage.tsx`
    - Import and render `<InteractionsPanel>` below the existing session detail content
    - Determine `isOwner` by comparing authenticated user_id with session's user_id
    - Determine `canInteract` by checking if user is viewing a friend's shared session (use context from how the page was navigated to, or check friendship status)
    - Pass `sessionId`, `isOwner`, `canInteract` props
    - _Requirements: 1.1, 2.1, 6.5_

- [x] 5. Update ActivityCard with kudos indicator
  - [x] 5.1 Modify `frontend/src/components/ActivityCard.tsx` to show kudos count
    - Add optional `kudosCount?: number` prop
    - When `kudosCount > 0`, render a small `<KudosIcon active size={16} />` with the count beside it
    - When `kudosCount` is 0 or undefined, render nothing (no kudos indicator)
    - Style to fit inline with existing card metadata
    - _Requirements: 8.1, 8.2, 8.3_

  - [x] 5.2 Update ActivityFeed to pass kudos data to ActivityCard
    - Ensure session data from friends' activities feed and own activities includes `kudos_count` if present
    - Pass `kudosCount` prop to each `<ActivityCard>` where applicable
    - _Requirements: 8.1, 8.3_

- [-] 6. Final checkpoint - Full stack verification
  - Ensure all tests pass with `cd backend && python -m pytest tests/ -x -q` and `cd frontend && npx tsc --noEmit`, ask the user if questions arise.

## Notes

- No new DynamoDB table needed — comments and kudos stored as list attributes on existing session items
- Authorization reuses existing `friends_service.py` functions for friendship verification
- Rate limiting follows the same pattern as existing friend-request endpoints
- KudosIcon must be a refined, minimal line-art SVG — premium and classy, not emoji
- Optimistic UI for kudos toggle improves perceived responsiveness
- Comment text retained in input on submission failure for better UX

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3"] },
    { "id": 2, "tasks": ["1.4"] },
    { "id": 3, "tasks": ["3.1", "3.2"] },
    { "id": 4, "tasks": ["4.1"] },
    { "id": 5, "tasks": ["4.2", "5.1"] },
    { "id": 6, "tasks": ["5.2"] }
  ]
}
```
