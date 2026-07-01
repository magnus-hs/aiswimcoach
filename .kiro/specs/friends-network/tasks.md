# Implementation Plan: Friends Network

## Overview

This plan implements the Friends Network feature by building the backend service first (DynamoDB table setup, friends_service module, handler routes), then the frontend components (API service, Friends page, ActivityFeed tabs, navigation update). Property-based tests validate correctness properties from the design, and integration tests wire everything together.

## Tasks

- [x] 1. Set up DynamoDB table and IAM permissions
  - [x] 1.1 Create DynamoDB table `ai-swim-coach-friends` with infrastructure script
    - Create a setup script or document the AWS CLI commands to create the `ai-swim-coach-friends` table with `pk` (String) partition key and `sk` (String) sort key
    - Create GSI `sk-pk-index` with `sk` as partition key and `pk` as sort key
    - Add DynamoDB permissions for the new table to the `ai-swim-coach-lambda-permissions` inline policy on the `ai-swim-coach-lambda-role` IAM role
    - _Requirements: Infrastructure prerequisite for all friend operations_

- [x] 2. Implement backend friends_service module
  - [x] 2.1 Create `backend/friends_service.py` with core relationship functions
    - Implement `send_friend_request(from_user_id, to_user_id)` — creates pending request item in DynamoDB, validates no duplicate/existing friendship, prevents self-requests
    - Implement `get_pending_requests(user_id)` — queries `sk-pk-index` GSI for incoming pending requests, enriches with sender display name
    - Implement `accept_friend_request(request_id, user_id)` — creates two mutual FRIEND# items, deletes the pending REQ# item
    - Implement `decline_friend_request(request_id, user_id)` — deletes the pending REQ# item without creating friendship
    - Implement `get_friends(user_id)` — queries main table for all items with `begins_with(sk, "FRIEND#")`, enriches with display names
    - Implement `remove_friend(user_id, friend_user_id)` — deletes both directional FRIEND# items
    - _Requirements: 3.2, 3.5, 4.2, 4.4, 4.5, 5.4_

  - [x] 2.2 Add user search function to `backend/friends_service.py`
    - Implement `search_users(query, current_user_id)` — searches `ai-swim-coach-users` table (email-index GSI with `begins_with`) and `ai-swim-coach-user-profiles` table (scan with filter for display name)
    - Exclude current user from results
    - Enrich results with relationship status (none, pending_sent, pending_received, friends)
    - Return display_name and email_prefix for each match
    - _Requirements: 2.2, 2.3, 2.4_

  - [x] 2.3 Add activity visibility and friends' activities functions to `backend/friends_service.py`
    - Implement `update_activity_visibility(user_id, visible)` — updates `activity_visibility` attribute on user profile in `ai-swim-coach-user-profiles` table
    - Implement `get_activity_visibility(user_id)` — reads visibility setting, defaults to `"not_shared"` if not present
    - Implement `get_friends_activities(user_id)` — gets friends list, filters to those with `activity_visibility = "shared"`, queries `ai-swim-coach-sessions` for each sharing friend, returns aggregated sessions sorted by date descending
    - Return fields: session_date, total_distance_meters, total_time_seconds, stroke_type, average_pace_per_100m, friend display_name
    - _Requirements: 6.2, 6.3, 6.4, 8.1, 8.2, 8.3_

  - [ ]* 2.4 Write property tests for friend request lifecycle (Properties 3, 4, 5)
    - **Property 3: Duplicate friend requests are prevented** — For any pair of users, if a pending request or friendship already exists, a second send_friend_request SHALL be rejected
    - **Property 4: Accepting a request creates mutual friendship** — For any pending request from A to B, accepting creates FRIEND#B under A and FRIEND#A under B, and removes the REQ# item
    - **Property 5: Declining a request removes pending without creating friendship** — For any pending request from A to B, declining removes the REQ# item and no FRIEND# items exist
    - **Validates: Requirements 3.5, 4.4, 4.5**

  - [ ]* 2.5 Write property tests for friend removal (Property 6)
    - **Property 6: Removing a friend deletes both directions** — For any confirmed friendship between A and B, removal deletes both FRIEND#B under A and FRIEND#A under B
    - **Validates: Requirements 5.4**

  - [ ]* 2.6 Write property tests for search (Properties 1, 2)
    - **Property 1: Search results match query** — For any query of 2+ chars, all returned users have display_name containing query (case-insensitive) OR email starting with query (case-insensitive)
    - **Property 2: Current user excluded from search** — For any query, the current user's ID never appears in results
    - **Validates: Requirements 2.2, 2.4**

  - [ ]* 2.7 Write property tests for activity visibility and feed (Properties 7, 8, 9, 10)
    - **Property 7: Activity visibility toggle round-trip** — set shared → read returns shared; set not_shared → read returns not_shared; no prior set → read returns not_shared
    - **Property 8: Privacy filtering of friends' activities** — only sessions from friends with visibility "shared" appear in results
    - **Property 9: Friends' activities sorted descending by date** — returned sessions are in non-ascending session_date order
    - **Property 10: Friend activity response completeness** — every returned session includes all required fields (session_date, total_distance_meters, total_time_seconds, stroke_type, average_pace_per_100m, friend display_name)
    - **Validates: Requirements 6.2, 6.3, 6.4, 7.3, 7.6, 8.1, 8.2, 8.3**

- [x] 3. Wire backend routes into handler.py
  - [x] 3.1 Add friend management routes to `backend/handler.py`
    - Add route: `GET /friends/search?q={query}` → `search_users` (with rate limiting: 30/60s)
    - Add route: `POST /friends/request` → `send_friend_request` (with rate limiting: 20/60s)
    - Add route: `GET /friends/requests` → `get_pending_requests`
    - Add route: `POST /friends/requests/{request_id}/accept` → `accept_friend_request`
    - Add route: `POST /friends/requests/{request_id}/decline` → `decline_friend_request`
    - Add route: `GET /friends` → `get_friends`
    - Add route: `DELETE /friends/{friend_user_id}` → `remove_friend`
    - Add route: `GET /friends/activities` → `get_friends_activities`
    - Add route: `PUT /friends/visibility` → `update_activity_visibility`
    - Add route: `GET /friends/visibility` → `get_activity_visibility`
    - All routes require authentication via `@require_auth` decorator
    - Use proper HTTP status codes and error responses per design error handling table
    - _Requirements: 2.2, 3.2, 4.2, 4.4, 4.5, 5.4, 6.3, 6.4, 8.1_

  - [ ]* 3.2 Write unit tests for handler route integration
    - Test each route returns correct status codes for success and error cases
    - Test authentication requirement on all routes
    - Test rate limiting on search and request endpoints
    - Test request validation (query length, missing fields)
    - _Requirements: 2.2, 3.2, 3.5, 4.4, 4.5_

- [x] 4. Checkpoint - Backend complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement frontend API service
  - [x] 5.1 Create `frontend/src/api/friendsService.ts`
    - Implement `searchUsers(query: string): Promise<UserSearchResult[]>`
    - Implement `sendFriendRequest(targetUserId: string): Promise<void>`
    - Implement `getPendingRequests(): Promise<FriendRequest[]>`
    - Implement `acceptRequest(requestId: string): Promise<void>`
    - Implement `declineRequest(requestId: string): Promise<void>`
    - Implement `getFriends(): Promise<Friend[]>`
    - Implement `removeFriend(friendUserId: string): Promise<void>`
    - Implement `getFriendsActivities(): Promise<FriendActivity[]>`
    - Implement `getActivityVisibility(): Promise<boolean>`
    - Implement `updateActivityVisibility(visible: boolean): Promise<void>`
    - Define TypeScript interfaces: `UserSearchResult`, `FriendRequest`, `Friend`, `FriendActivity`
    - Follow existing pattern from `sessionService.ts` for API calls and error handling
    - _Requirements: 2.2, 3.2, 4.4, 4.5, 5.4, 6.3, 6.4, 8.1_

- [x] 6. Implement Friends page frontend
  - [x] 6.1 Create `frontend/src/pages/FriendsPage.tsx` with search and friend management
    - Implement search input with placeholder "Search by name or email" and 300ms debounce
    - Render search results with display name, email prefix, and contextual button (Add Friend / Request Sent / Already Friends)
    - Show "No users found" when search returns empty results
    - Show error banner with retry on search failure
    - Implement "Pending Requests" section with Accept/Decline buttons, removing items on action without page reload
    - Implement "My Friends" section listing friends with Remove button and confirmation dialog
    - Show error messages for failed friend operations (removal, request)
    - _Requirements: 2.1, 2.3, 2.5, 2.6, 3.1, 3.3, 3.4, 4.1, 4.3, 4.6, 5.1, 5.2, 5.3, 5.5, 5.6_

  - [x] 6.2 Add privacy settings section to `FriendsPage.tsx`
    - Implement "Activity Sharing" toggle in a privacy settings section
    - Load current visibility state on page mount via `getActivityVisibility()`
    - On toggle change, call `updateActivityVisibility()` and show confirmation indicator on success
    - On failure, revert toggle to previous state and display error message
    - _Requirements: 6.1, 6.3, 6.4, 6.5, 6.6_

  - [x] 6.3 Create `frontend/src/pages/FriendsPage.css` with styles
    - Style search input, results list, pending requests section, friends list, and privacy toggle
    - Match existing app design patterns and token usage from `tokens.css`
    - _Requirements: UI consistency_

- [x] 7. Update ActivityFeed with friends' activities tab
  - [x] 7.1 Update `frontend/src/components/ActivityFeed.tsx` with tab support
    - Add tab bar with "My Activities" and "Friends' Activities" tabs
    - Default to "My Activities" as selected tab
    - "My Activities" tab shows only the current user's sessions (existing behavior)
    - "Friends' Activities" tab calls `getFriendsActivities()` and renders sessions with friend's display name attributed
    - Sort friends' sessions by session_date descending
    - Show loading skeleton while friends' activities are loading
    - Show error message with retry option on failure
    - Show "No friends' activities to show. Connect with more swimmers or ask friends to share their activities." when empty
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 8.4, 8.5, 8.6_

  - [x] 7.2 Update `frontend/src/components/ActivityFeed.css` with tab styles
    - Style tab bar, active/inactive tab states
    - Style friend attribution display on activity cards
    - _Requirements: UI consistency_

- [x] 8. Update navigation and routing
  - [x] 8.1 Update `frontend/src/components/Navigation.tsx` to add Friends menu item
    - Add "Friends" item in the Profile dropdown menu between "Goals" and "Critical Swim Speed"
    - Link to `/friends` route
    - _Requirements: 1.1, 1.2_

  - [x] 8.2 Update `frontend/src/App.tsx` with Friends page route
    - Add route `/friends` pointing to `FriendsPage` component
    - Wrap in `ProtectedRoute` for authentication
    - _Requirements: 1.2_

- [x] 9. Checkpoint - Frontend complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Integration tests and final validation
  - [ ]* 10.1 Write backend integration tests for the full friend lifecycle
    - Test end-to-end flow: send request → accept → verify friends list → remove friend
    - Test activity visibility flow: set shared → verify friend can see activities → set not_shared → verify exclusion
    - Use moto mock for DynamoDB table creation and operations
    - _Requirements: 3.2, 4.4, 5.4, 8.1, 8.3_

  - [ ]* 10.2 Write frontend component tests for FriendsPage and ActivityFeed
    - Test search input renders with correct placeholder
    - Test "Add Friend" button renders for non-friend users
    - Test pending requests section renders with Accept/Decline buttons
    - Test removal confirmation dialog flow
    - Test ActivityFeed renders two tabs with "My Activities" as default
    - Test friends' activities tab shows loading skeleton and empty state message
    - _Requirements: 2.1, 3.1, 4.1, 4.3, 5.3, 7.1, 7.2, 8.5, 8.6_

- [x] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design (using Hypothesis for Python backend)
- The backend uses moto for DynamoDB mocking in tests
- Frontend follows existing patterns from `sessionService.ts` and page components
- Rate limiting reuses the existing `backend/rate_limit.py` module
- CORS/security headers are handled via the existing `backend/http_headers.py` module

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1", "2.2", "2.3"] },
    { "id": 2, "tasks": ["2.4", "2.5", "2.6", "2.7", "3.1"] },
    { "id": 3, "tasks": ["3.2", "5.1"] },
    { "id": 4, "tasks": ["6.1", "6.2", "6.3", "7.1", "7.2", "8.1", "8.2"] },
    { "id": 5, "tasks": ["10.1", "10.2"] }
  ]
}
```
