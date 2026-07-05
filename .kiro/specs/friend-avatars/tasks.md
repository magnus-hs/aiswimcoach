# Implementation Plan: Friend Avatars

## Overview

Add profile picture avatars to the Friends tab in the activity feed. The backend includes `profile_picture_url` in friend activity responses (with per-friend caching), and the frontend renders a 32×32 circular avatar image or letter-initial fallback beside each friend's name.

## Tasks

- [ ] 1. Backend: Add profile_picture_url to friend activities response
  - [ ] 1.1 Add profile_picture_url field with per-friend caching in `get_friends_activities()`
    - Add a `profile_pic_cache` dict before the friends loop in `backend/friends_service.py`
    - Cache `_get_profile_picture_url(friend_id)` per friend_id to avoid repeated DynamoDB reads
    - Include `profile_picture_url` in each session dict appended to `all_sessions`
    - _Requirements: 1.1, 1.2_

- [ ] 2. Frontend: Update interface and render avatars
  - [ ] 2.1 Add `profile_picture_url` field to `FriendActivity` interface
    - In `frontend/src/api/friendsService.ts`, add `profile_picture_url?: string | null` to the `FriendActivity` interface
    - _Requirements: 1.3_

  - [ ] 2.2 Update `renderFriendsActivities()` to display avatar beside friend name
    - In `frontend/src/components/ActivityFeed.tsx`, replace the plain `<span>` friend name with a header div containing avatar + name
    - Render an `<img>` when `profile_picture_url` is present, with `onError` fallback to letter-initial placeholder
    - Render a `<span>` letter-initial placeholder when URL is null/undefined
    - Include `alt` attribute with the friend's display name for accessibility
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ] 2.3 Add CSS styles for friend avatar
    - In `frontend/src/components/ActivityFeed.css`, add `.activity-feed__friend-header` flex layout
    - Add `.activity-feed__friend-avatar` with 32×32px, border-radius 50%, object-fit cover
    - Add `.activity-feed__friend-avatar--placeholder` with centered letter-initial, background color, and font styling
    - _Requirements: 2.3_

- [ ] 3. Checkpoint
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- No new API endpoints or database changes are needed — uses existing `_get_profile_picture_url` helper and Users table
- Per-friend caching avoids redundant DynamoDB reads when a friend has multiple sessions
- The `onError` handler on `<img>` ensures graceful degradation if S3 URLs expire or return errors

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1"] },
    { "id": 1, "tasks": ["2.2", "2.3"] }
  ]
}
```
