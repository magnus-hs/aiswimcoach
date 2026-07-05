# Requirements Document

## Introduction

Display friend avatars (profile pictures) alongside friend names in the activity feed's Friends tab, so users can visually identify who performed each activity without relying solely on text names.

## Glossary

- **ActivityFeed**: The frontend component that displays swim session activities in "My Activities" and "Friends" tabs.
- **FriendsService_Backend**: The Python backend module (`friends_service.py`) responsible for fetching friend relationships and friend activities from DynamoDB.
- **FriendsService_Frontend**: The TypeScript frontend module (`friendsService.ts`) that defines interfaces and API calls for friend-related data.
- **FriendActivityCard**: The UI element within the Friends tab that displays a single friend's swim session, including the friend's name and activity details.
- **Avatar**: A small circular profile picture image rendered beside a friend's display name.
- **ProfilePictureURL**: An S3 URL pointing to a user's uploaded profile picture, stored in the Users table.

## Requirements

### Requirement 1

**User Story:** As a user viewing my friends' activities, I want to see each friend's profile picture next to their name, so that I can quickly identify who completed each swim session.

#### Acceptance Criteria

1. WHEN the FriendsService_Backend retrieves friend activities, THE FriendsService_Backend SHALL include the `profile_picture_url` field for each friend activity entry by looking up the friend's profile picture using the existing `_get_profile_picture_url` helper.
2. IF the friend has no profile picture stored, THEN THE FriendsService_Backend SHALL return `null` for the `profile_picture_url` field in that friend activity entry.
3. THE FriendsService_Frontend SHALL define `profile_picture_url` as an optional nullable string field on the `FriendActivity` interface.

### Requirement 2

**User Story:** As a user viewing the Friends tab, I want to see a recognizable avatar image next to each friend's name, so that the activity feed is easy to scan visually.

#### Acceptance Criteria

1. WHEN a friend activity has a non-null `profile_picture_url`, THE FriendActivityCard SHALL render an Avatar image using that URL, positioned to the left of the friend's display name.
2. WHEN a friend activity has a null or missing `profile_picture_url`, THE FriendActivityCard SHALL render a default placeholder Avatar displaying the first letter of the friend's display name.
3. THE Avatar SHALL render as a circular image with dimensions of 32×32 pixels.
4. THE Avatar SHALL include an `alt` attribute containing the friend's display name for screen reader accessibility.
5. IF the Avatar image fails to load, THEN THE FriendActivityCard SHALL display the default placeholder Avatar instead of a broken image icon.
