# Bugfix Requirements Document

## Introduction

Users cannot give kudos to their own swim activities. The `InteractionsPanel` component explicitly prevents the activity owner from clicking the kudos button by checking `!isOwner` in the `canGiveKudos` logic. This is a frontend-only restriction — the backend `toggleKudos` endpoint has no owner restriction. The fix should allow users to kudos their own swims using the same interaction as for friends' activities.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the logged-in user views their own activity THEN the system disables the kudos button (no click handler attached) preventing self-kudos
1.2 WHEN the logged-in user views their own activity and clicks the kudos icon THEN the system does nothing because the `onClick` handler is `undefined`

### Expected Behavior (Correct)

2.1 WHEN the logged-in user views their own activity THEN the system SHALL enable the kudos button with a click handler, allowing self-kudos
2.2 WHEN the logged-in user views their own activity and clicks the kudos icon THEN the system SHALL toggle kudos (add or remove) the same way it does for friends' activities

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a friend views another user's activity and has `canInteract` permission THEN the system SHALL CONTINUE TO allow them to toggle kudos
3.2 WHEN a user who cannot interact (no `canInteract` permission) views any activity THEN the system SHALL CONTINUE TO disable the kudos button
3.3 WHEN any user toggles kudos THEN the system SHALL CONTINUE TO perform optimistic UI updates and revert on failure
3.4 WHEN any user views the interactions panel THEN the system SHALL CONTINUE TO display the correct kudos count and active state
