# Implementation Plan

- [ ] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Owner Cannot Self-Kudos
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Confirm the bug exists by rendering InteractionsPanel with `isOwner=true`
  - **Scoped PBT Approach**: Scope to concrete failing cases: `isOwner=true` with both `canInteract=true` and `canInteract=false`
  - Test that `canGiveKudos` evaluates to `true` when `isOwner=true` (assert kudos button has onClick handler)
  - Run test on UNFIXED code - expect FAILURE (confirms bug exists: `canInteract && !isOwner` yields `false` when `isOwner=true`)
  - Document counterexample: kudos button receives `onClick={undefined}` when `isOwner=true`
  - _Requirements: 1.1, 1.2, 2.1, 2.2_

- [ ] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Non-Owner Kudos Behavior Unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - Observe: `isOwner=false, canInteract=true` → kudos button enabled (has onClick) on unfixed code
  - Observe: `isOwner=false, canInteract=false` → kudos button disabled (no onClick) on unfixed code
  - Write test asserting: for non-owner cases, kudos enabled state equals `canInteract` value
  - Verify tests pass on UNFIXED code
  - _Requirements: 3.1, 3.2_

- [ ] 3. Fix self-kudos bug

  - [ ] 3.1 Apply the one-line fix
    - Change line 139 of `frontend/src/components/InteractionsPanel.tsx`
    - Before: `const canGiveKudos = canInteract && !isOwner;`
    - After: `const canGiveKudos = canInteract || isOwner;`
    - _Bug_Condition: isBugCondition(input) where input.isOwner === true_
    - _Expected_Behavior: canGiveKudos === true for all inputs where isOwner === true_
    - _Preservation: Non-owner inputs produce same result as canInteract_
    - _Requirements: 2.1, 2.2, 3.1, 3.2, 3.3, 3.4_

  - [ ] 3.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Owner Can Self-Kudos
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms owner can now self-kudos)
    - _Requirements: 2.1, 2.2_

  - [ ] 3.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Non-Owner Kudos Behavior Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions for friend/non-friend kudos)

- [ ] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
