# Requirements Document

## Introduction

The Friends Network feature enables users of the AI Swim Coach app to connect with other swimmers, view each other's activities, and build a social training community. Users can search for and add friends, manage their friend list, control the visibility of their own activities, and view a friends' activity feed on the dashboard.

## Glossary

- **Friends_Service**: The backend service responsible for managing friend relationships, including sending requests, accepting, rejecting, and removing friends.
- **User_Search_Service**: The backend service responsible for searching registered users by name or email.
- **Privacy_Service**: The backend service responsible for managing user activity visibility preferences.
- **Friends_Page**: The frontend page accessible from the Profile dropdown menu where users manage their friend list and search for other users.
- **Activity_Feed**: The dashboard component that displays session summaries, supporting both personal and friends' activity views.
- **Friend_Relationship**: A mutual connection between two users where both parties have accepted the friend request.
- **Activity_Visibility**: A per-user privacy setting that controls whether the user's swim sessions are visible to their friends.

## Requirements

### Requirement 1: Friends Page Navigation

**User Story:** As a swimmer, I want to access a Friends page from my profile menu, so that I can manage my social connections in one place.

#### Acceptance Criteria

1. WHEN the user opens the Profile dropdown menu, THE Navigation SHALL display a "Friends" menu item between "Goals" and "Critical Swim Speed".
2. WHEN the user clicks the "Friends" menu item, THE Navigation SHALL navigate the user to the Friends_Page at the route "/friends".

### Requirement 2: User Search

**User Story:** As a swimmer, I want to search for other users of the app, so that I can find and connect with people I know.

#### Acceptance Criteria

1. THE Friends_Page SHALL display a search input field with placeholder text "Search by name or email".
2. WHEN the user enters a search query of 2 or more characters, THE User_Search_Service SHALL return matching users within 2 seconds.
3. WHEN the User_Search_Service returns results, THE Friends_Page SHALL display each result showing the user's display name and email prefix.
4. THE User_Search_Service SHALL exclude the current user from search results.
5. WHEN the User_Search_Service finds no matching users, THE Friends_Page SHALL display the message "No users found".
6. IF the User_Search_Service encounters an error, THEN THE Friends_Page SHALL display an error message and provide a retry option.

### Requirement 3: Sending Friend Requests

**User Story:** As a swimmer, I want to send friend requests to other users, so that I can build my network of swim connections.

#### Acceptance Criteria

1. WHEN a search result displays a user who is not already a friend or pending request, THE Friends_Page SHALL display an "Add Friend" button next to that user.
2. WHEN the user clicks the "Add Friend" button, THE Friends_Service SHALL create a pending friend request from the current user to the target user.
3. WHEN the Friends_Service successfully creates a friend request, THE Friends_Page SHALL update the button to display "Request Sent" in a disabled state.
4. IF the Friends_Service fails to create a friend request, THEN THE Friends_Page SHALL display an error message and keep the "Add Friend" button active.
5. THE Friends_Service SHALL prevent duplicate friend requests between the same two users.

### Requirement 4: Receiving and Responding to Friend Requests

**User Story:** As a swimmer, I want to accept or reject incoming friend requests, so that I can control who I connect with.

#### Acceptance Criteria

1. THE Friends_Page SHALL display a "Pending Requests" section showing all incoming friend requests.
2. WHEN the Friends_Page loads, THE Friends_Service SHALL return all pending incoming requests for the current user.
3. THE Friends_Page SHALL display each pending request with the sender's display name and "Accept" and "Decline" buttons.
4. WHEN the user clicks "Accept", THE Friends_Service SHALL create a mutual Friend_Relationship between both users and remove the pending request.
5. WHEN the user clicks "Decline", THE Friends_Service SHALL delete the pending request without creating a Friend_Relationship.
6. WHEN a friend request is accepted or declined, THE Friends_Page SHALL remove the request from the "Pending Requests" section without a full page reload.

### Requirement 5: Friends List Management

**User Story:** As a swimmer, I want to view and manage my current friends, so that I can keep my network up to date.

#### Acceptance Criteria

1. THE Friends_Page SHALL display a "My Friends" section listing all users with an active Friend_Relationship with the current user.
2. THE Friends_Page SHALL display each friend's display name and a "Remove" button.
3. WHEN the user clicks "Remove" on a friend, THE Friends_Page SHALL display a confirmation prompt before proceeding.
4. WHEN the user confirms removal, THE Friends_Service SHALL delete the Friend_Relationship between both users.
5. WHEN the Friends_Service successfully removes a friend, THE Friends_Page SHALL remove that user from the "My Friends" list without a full page reload.
6. IF the Friends_Service fails to remove a friend, THEN THE Friends_Page SHALL display an error message.

### Requirement 6: Activity Visibility Privacy Setting

**User Story:** As a swimmer, I want to control whether my activities are visible to friends, so that I can maintain my privacy.

#### Acceptance Criteria

1. THE Friends_Page SHALL display an "Activity Sharing" toggle in a privacy settings section.
2. THE Privacy_Service SHALL default Activity_Visibility to "not shared" for new users.
3. WHEN the user enables the "Activity Sharing" toggle, THE Privacy_Service SHALL set Activity_Visibility to "shared" for that user.
4. WHEN the user disables the "Activity Sharing" toggle, THE Privacy_Service SHALL set Activity_Visibility to "not shared" for that user.
5. WHEN the Privacy_Service successfully updates Activity_Visibility, THE Friends_Page SHALL display a confirmation indicator.
6. IF the Privacy_Service fails to update Activity_Visibility, THEN THE Friends_Page SHALL revert the toggle to the previous state and display an error message.

### Requirement 7: Dashboard Activity Feed Tabs

**User Story:** As a swimmer, I want to switch between my activities and my friends' activities on the dashboard, so that I can stay motivated by seeing what others are doing.

#### Acceptance Criteria

1. THE Activity_Feed SHALL display two tabs: "My Activities" and "Friends' Activities".
2. THE Activity_Feed SHALL display "My Activities" as the default selected tab.
3. WHEN the user selects the "Friends' Activities" tab, THE Activity_Feed SHALL display swim sessions from friends who have Activity_Visibility set to "shared".
4. WHEN the user selects the "My Activities" tab, THE Activity_Feed SHALL display only the current user's swim sessions.
5. WHILE the "Friends' Activities" tab is selected, THE Activity_Feed SHALL display each session with the friend's display name attributed to the activity.
6. WHEN the Activity_Feed loads friends' activities, THE Activity_Feed SHALL sort sessions by session date in descending order.

### Requirement 8: Friends Activity Data Retrieval

**User Story:** As a swimmer, I want to see my friends' recent swim sessions, so that I can compare progress and stay motivated.

#### Acceptance Criteria

1. WHEN the "Friends' Activities" tab is selected, THE Friends_Service SHALL retrieve session summaries only from friends who have Activity_Visibility set to "shared".
2. THE Friends_Service SHALL return session data including session_date, total_distance_meters, total_time_seconds, stroke_type, average_pace_per_100m, and the friend's display name.
3. WHEN a friend has Activity_Visibility set to "not shared", THE Friends_Service SHALL exclude that friend's sessions from the response.
4. IF the Friends_Service encounters an error retrieving friends' activities, THEN THE Activity_Feed SHALL display an error message with a retry option.
5. WHILE friends' activities are loading, THE Activity_Feed SHALL display a loading skeleton state.
6. WHEN no friends have shared activities, THE Activity_Feed SHALL display the message "No friends' activities to show. Connect with more swimmers or ask friends to share their activities."
