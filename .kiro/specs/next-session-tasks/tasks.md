# Implementation Plan: Next Session Tasks

## Overview

This plan covers four improvements: fixing IAM permissions for plan activation, replacing the raster logo with inline SVG, restructuring PB input with dropdowns and validation, and implementing grouped PB display with manual/derived comparison. Tasks are organized so independent work (IAM, logo) can proceed in parallel, while PB input and display tasks follow logical dependencies.

## Tasks

- [x] 1. Fix Plan Activate IAM Permission
  - [x] 1.1 Update IAM inline policy via AWS CLI
    - Run AWS CLI command to add `dynamodb:UpdateItem` to the `DynamoDBSessions` statement in the `ai-swim-coach-lambda-permissions` inline policy on `ai-swim-coach-lambda-role`
    - The policy statement must include: `dynamodb:PutItem`, `dynamodb:GetItem`, `dynamodb:Query`, `dynamodb:UpdateItem` on the Sessions table and its `session_id-index`
    - Verify by describing the policy after update
    - _Requirements: 1.2, 1.1_

- [x] 2. Replace Logo with Inline SVG
  - [x] 2.1 Replace img tag with inline SVG in Navigation.tsx
    - In `frontend/src/components/Navigation.tsx`, remove the `<img src="/logo.png" ...>` element
    - Replace with the inline SVG from the design document (lane lines + swimmer wave + water accent)
    - SVG must have `role="img"`, `aria-label="AI Swim Coach"`, `viewBox="0 0 48 36"`, class `nav__logo-img`
    - Use CSS custom properties for colors: `var(--color-primary)`, `var(--color-primary-light)`, `var(--color-secondary)`
    - Update `Navigation.css` to set max-height 40px on `.nav__logo-img`, maintain aspect ratio, and ensure min-height 24px at viewports below 600px
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

- [x] 3. Structured Personal Best Input
  - [x] 3.1 Create PB validation utility functions
    - Create `frontend/src/utils/pbValidation.ts` with exported functions:
      - `validateTimeInput(input: string): { valid: boolean; seconds?: number; error?: string }` — validates M:SS / MM:SS format, minutes 0-59, seconds 00-59
      - `validateCustomDistance(input: string): { valid: boolean; error?: string }` — validates integer between 25 and 5000
      - `buildEventName(stroke: StrokeType, distance: DistanceOption, customDistance: string): string` — constructs event name in format `"{distance}m {stroke}"`
    - Export types `StrokeType`, `DistanceOption`, and constants `STROKES`, `DISTANCES`, `CUSTOM_DISTANCE_MIN`, `CUSTOM_DISTANCE_MAX`
    - _Requirements: 3.5, 3.6, 3.7, 3.8, 3.9_

  - [ ]* 3.2 Write property tests for PB validation utilities
    - Create `frontend/src/utils/pbValidation.test.ts` using vitest + fast-check
    - **Property 1: validateTimeInput round trip** — For any (minutes: 0-59, seconds: 0-59), formatting as `"${m}:${s.toString().padStart(2,'0')}"` and validating returns `{ valid: true, seconds: m*60+s }`. For invalid strings, returns `{ valid: false }`.
    - **Validates: Requirements 3.5, 3.8**
    - **Property 2: validateCustomDistance boundary validation** — For any integer 25 ≤ n ≤ 5000, returns `{ valid: true }`. For any integer n < 25 or n > 5000 or non-integer, returns `{ valid: false }`.
    - **Validates: Requirements 3.3, 3.9**
    - **Property 3: buildEventName construction** — For any stroke in STROKES and any valid distance, produces `"${distance}m ${stroke}"`.
    - **Validates: Requirements 3.6, 3.7**

  - [x] 3.3 Implement structured form UI in PersonalBestManager
    - In `frontend/src/components/PersonalBestManager.tsx`, replace the freeform event `<input>` with:
      - A stroke `<select>` dropdown with options: Freestyle, Backstroke, Breaststroke, Butterfly, IM
      - A distance `<select>` dropdown with options: 50m, 100m, 200m, 400m, 800m, 1500m, Custom
      - A conditional custom distance `<input type="number">` visible only when Custom is selected (min=25, max=5000, step=1)
    - Keep the existing time input field, update placeholder to "M:SS (e.g., 1:05)"
    - Disable submit button when required fields are empty
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 3.4 Implement form submission with validation and error handling
    - On submit, call `validateTimeInput` and `validateCustomDistance` (if Custom selected)
    - Display inline error messages when validation fails; do not submit the form
    - On valid submission, call `buildEventName` to construct event name, convert time to seconds, and call `savePersonalBest(eventName, timeSeconds)`
    - On backend failure, display error message and preserve form data
    - On success, clear form and reload PB list
    - _Requirements: 3.5, 3.6, 3.7, 3.8, 3.9, 3.10_

- [x] 4. Checkpoint
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Personal Bests Grouped Display
  - [x] 5.1 Modify backend get_personal_bests to return both manual and derived
    - In `backend/pb_resolver.py`, change the `get_personal_bests` function to return ALL PBs (both manual and derived) even when they exist for the same event
    - Replace the merge logic that prioritizes manual with: `all_pbs = list(manual_pbs.values()) + list(derived_pbs.values())`
    - _Requirements: 4.3, 4.8_

  - [ ]* 5.2 Write backend tests for updated get_personal_bests
    - In `backend/tests/test_pb_resolver.py`, add tests verifying:
      - When both manual and derived exist for the same event, both are returned (not de-duplicated)
      - When only manual exists, only manual is returned
      - When only derived exists, only derived is returned
    - _Requirements: 4.3, 4.8_

  - [x] 5.3 Create groupPersonalBests utility function
    - Create `frontend/src/utils/pbGrouping.ts` with exported function:
      - `groupPersonalBests(pbs: PersonalBest[]): StrokeGroup[]` — groups PBs by stroke (parsed from event name), merges manual/derived for same event into one EventEntry, sorts groups alphabetically, sorts events by distance ascending, omits empty groups
    - Export interfaces `StrokeGroup`, `EventEntry` and helper functions `parseStrokeFromEvent`, `parseDistanceFromEvent`
    - Include a `formatTimeDiff(manual: number, derived: number): { diff: string; label: 'faster' | 'slower' }` helper for calculating the absolute difference to 1 decimal place
    - _Requirements: 4.1, 4.3, 4.4, 4.6_

  - [ ]* 5.4 Write property tests for groupPersonalBests
    - Create `frontend/src/utils/pbGrouping.test.ts` using vitest + fast-check
    - **Property 4: groupPersonalBests sorted non-empty groups** — For any non-empty PB list with valid event format, returned groups are sorted alphabetically by stroke and each group has at least one event.
    - **Validates: Requirements 4.1, 4.6**
    - **Property 5: groupPersonalBests source merging** — When two PBs share the same event but differ in source, produces one EventEntry with both manual and derived populated. When only one source exists, only that field is populated.
    - **Validates: Requirements 4.3, 4.8**
    - **Property 6: Time difference calculation** — For any two positive numbers, `formatTimeDiff` returns `Math.abs(a - b)` rounded to 1 decimal, labeled "faster" when manual < derived, "slower" otherwise.
    - **Validates: Requirements 4.4**

  - [x] 5.5 Implement grouped display UI in PersonalBestManager
    - Replace the flat PB list rendering in `PersonalBestManager.tsx` with grouped display:
      - Import and call `groupPersonalBests(pbs)` to transform the flat list
      - Render each stroke group with a heading showing the stroke name
      - Within each group, render events sorted by distance
      - For each event, show manual and derived times side by side with source badges ("manual" / "derived")
      - When both exist, display time difference (e.g., "2.3s faster") using `formatTimeDiff`
      - When only one source exists, show single time with badge, no difference
    - Update `PersonalBestManager.css` with styles for grouped layout, side-by-side comparison, and diff labels
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8_

- [x] 6. Final checkpoint — Build and verify
  - [x] 6.1 Build frontend and verify no errors
    - Run `cd frontend && npm run build` to ensure TypeScript compilation and Vite build succeed with no errors
    - Run `cd frontend && npm run test` to ensure all frontend tests pass
    - Run `cd backend && python -m pytest tests/` to ensure all backend tests pass
    - _Requirements: 1.1, 2.1, 3.1, 4.1_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- fast-check is already in frontend devDependencies; vitest is the test runner
- Backend tests use pytest with moto/mocks for DynamoDB

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1", "3.1", "5.1"] },
    { "id": 1, "tasks": ["3.2", "3.3", "5.2", "5.3"] },
    { "id": 2, "tasks": ["3.4", "5.4"] },
    { "id": 3, "tasks": ["5.5"] },
    { "id": 4, "tasks": ["6.1"] }
  ]
}
```
