# Self-Kudos Fix — Bugfix Design

## Overview

The `InteractionsPanel` component uses the expression `canInteract && !isOwner` to gate the kudos button, which incorrectly prevents activity owners from giving themselves kudos. The fix changes the logic to `canInteract || isOwner` so that owners can always kudos their own activities while preserving existing friend-kudos behavior. This is a single-line frontend change with no backend modifications.

## Glossary

- **Bug_Condition (C)**: The condition where `isOwner === true` causes the kudos button to be disabled despite the owner wanting to self-kudos
- **Property (P)**: When `isOwner` is true, the kudos button should be enabled with a click handler
- **Preservation**: Existing behavior for friends (canInteract-based kudos) and non-interacting users (disabled kudos) must remain unchanged
- **canGiveKudos**: The boolean computed on line 139 of `InteractionsPanel.tsx` that determines whether the kudos `onClick` handler is attached
- **isOwner**: Prop indicating the current user owns the activity being viewed
- **canInteract**: Prop indicating the current user has permission to interact with this activity (friend relationship)

## Bug Details

### Bug Condition

The bug manifests when the logged-in user views their own activity. The `canGiveKudos` variable evaluates to `false` because `!isOwner` is `false`, regardless of `canInteract`.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type { isOwner: boolean, canInteract: boolean }
  OUTPUT: boolean
  
  RETURN input.isOwner === true
END FUNCTION
```

### Examples

- User views own activity (`isOwner=true`, `canInteract=true`): Expected kudos enabled, actual kudos disabled
- User views own activity (`isOwner=true`, `canInteract=false`): Expected kudos enabled, actual kudos disabled
- Friend views activity (`isOwner=false`, `canInteract=true`): Kudos enabled (correct, not a bug)
- Non-friend views activity (`isOwner=false`, `canInteract=false`): Kudos disabled (correct, not a bug)

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Friends with `canInteract=true` can still toggle kudos on others' activities
- Users without `canInteract` permission and who are not owners cannot give kudos
- Optimistic UI updates and error rollback continue to work identically
- Kudos count display and active state rendering are unaffected

**Scope:**
All inputs where `isOwner === false` should behave identically before and after the fix. The `canInteract` prop continues to gate kudos for non-owners.

## Hypothesized Root Cause

The logic on line 139 of `frontend/src/components/InteractionsPanel.tsx`:

```typescript
const canGiveKudos = canInteract && !isOwner;
```

This expression was likely written with the intent to prevent owners from kudos-ing themselves, but the product requirement is that self-kudos should be allowed. The `&&  !isOwner` clause is the sole cause of the bug.

## Correctness Properties

Property 1: Bug Condition - Owner Can Self-Kudos

_For any_ input where `isOwner` is `true`, the fixed `canGiveKudos` expression SHALL evaluate to `true`, enabling the kudos button with a click handler regardless of the `canInteract` value.

**Validates: Requirements 2.1, 2.2**

Property 2: Preservation - Non-Owner Kudos Behavior

_For any_ input where `isOwner` is `false`, the fixed `canGiveKudos` expression SHALL produce the same result as `canInteract`, preserving existing friend/non-friend kudos gating.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

## Fix Implementation

### Changes Required

**File**: `frontend/src/components/InteractionsPanel.tsx`

**Line**: 139

**Specific Changes**:
1. **Replace logical expression**: Change `canInteract && !isOwner` to `canInteract || isOwner`
   - Before: `const canGiveKudos = canInteract && !isOwner;`
   - After: `const canGiveKudos = canInteract || isOwner;`

This single change produces the correct truth table:
| isOwner | canInteract | canGiveKudos (fixed) |
|---------|-------------|---------------------|
| true    | true        | true                |
| true    | false       | true                |
| false   | true        | true                |
| false   | false       | false               |

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm the root cause is the `&& !isOwner` clause.

**Test Plan**: Render the `InteractionsPanel` with `isOwner=true` and verify the kudos button has no click handler. Run on UNFIXED code to confirm the bug.

**Test Cases**:
1. **Owner with canInteract=true**: Render with `isOwner=true, canInteract=true` → kudos button should have no onClick (will fail on unfixed code)
2. **Owner with canInteract=false**: Render with `isOwner=true, canInteract=false` → kudos button should have no onClick (will fail on unfixed code)

**Expected Counterexamples**:
- `KudosIcon` receives `onClick={undefined}` when `isOwner=true`
- Root cause confirmed: `canInteract && !isOwner` evaluates to `false` whenever `isOwner=true`

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed expression produces the expected behavior.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := (input.canInteract || input.isOwner)
  ASSERT result === true
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed expression produces the same result as `canInteract`.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT (input.canInteract || input.isOwner) === input.canInteract
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It exhaustively covers the boolean input space (which is small but still benefits from PBT structure)
- It ensures no edge case is missed in the non-owner path

**Test Plan**: Observe behavior on UNFIXED code for non-owner cases, then write property-based tests capturing that behavior.

**Test Cases**:
1. **Friend kudos preservation**: Verify `canInteract=true, isOwner=false` still enables kudos
2. **Non-friend blocked preservation**: Verify `canInteract=false, isOwner=false` still disables kudos

### Unit Tests

- Test `canGiveKudos` evaluates to `true` when `isOwner=true` (both canInteract values)
- Test `canGiveKudos` evaluates to `true` when `canInteract=true, isOwner=false`
- Test `canGiveKudos` evaluates to `false` when `canInteract=false, isOwner=false`

### Property-Based Tests

- Generate random `{ isOwner: boolean, canInteract: boolean }` inputs and assert `canGiveKudos === (canInteract || isOwner)`
- For non-owner inputs, assert the fixed result matches the original `canInteract` value

### Integration Tests

- Render `InteractionsPanel` as owner and click kudos → verify optimistic update
- Render `InteractionsPanel` as friend and click kudos → verify behavior unchanged
- Render `InteractionsPanel` as non-friend non-owner → verify button disabled
