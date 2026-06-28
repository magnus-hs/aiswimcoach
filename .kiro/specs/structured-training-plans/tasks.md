# Implementation Plan: Structured Training Plans

## Overview

This plan implements a periodized multi-week training plan system for the AI Swim Coach. The implementation proceeds bottom-up: data models and store layer first, then business logic modules (PB resolver, periodization engine, plan generator, lifecycle manager), then API routes in the handler, and finally the frontend components. Each backend module is testable in isolation before wiring together.

## Tasks

- [x] 1. Create data models and plan store
  - [x] 1.1 Create `backend/structured_plan_store.py` with data models and DynamoDB persistence
    - Define `SessionTemplate`, `WeekBlock`, and `StructuredTrainingPlan` dataclasses
    - Implement `save_structured_plan(user_id, plan)` — saves plan with `MPLAN#<created_at>` sort key
    - Implement `get_user_structured_plans(user_id)` — returns plan summaries ordered by created_at descending
    - Implement `get_plan_by_id(user_id, plan_id)` — returns full plan with all weeks and sessions
    - Implement `update_plan_status(user_id, plan_id, new_status)` — updates status and status_updated_at
    - Use existing SESSIONS_TABLE and follow patterns from `training_plan_store.py`
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ]* 1.2 Write property tests for plan store round-trip persistence
    - **Property 11: Plan persistence round trip preserves all data**
    - **Property 12: Plans returned in descending creation order**
    - **Property 13: Status update persists with transition timestamp**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**

  - [ ]* 1.3 Write unit tests for plan store
    - Test plan save and retrieval with known data
    - Test status update changes status and timestamp
    - Test empty plan list returns empty list
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 2. Implement personal best resolver
  - [x] 2.1 Create `backend/pb_resolver.py` with PB resolution logic
    - Implement `save_personal_best(user_id, event, time_seconds)` — stores PB on UserProfiles table
    - Implement `get_personal_bests(user_id)` — returns all PBs (manual + derived)
    - Implement `resolve_personal_best(user_id, event)` — manual first, then derived from history
    - Implement `derive_pb_from_history(user_id, stroke_type, distance_m)` — pace degradation scaling from session history
    - Store PBs as `personal_bests` map attribute on existing UserProfiles table items
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 7.1, 7.2, 7.3, 7.4_

  - [ ]* 2.2 Write property tests for PB resolver
    - **Property 6: Personal best persistence round trip**
    - **Property 7: Manual personal best takes priority over derived**
    - **Property 8: Derived PB uses fastest matching pace**
    - **Property 9: Pace degradation scaling is monotonically increasing**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 7.1, 7.2, 7.4**

  - [ ]* 2.3 Write unit tests for PB resolver
    - Test manual PB save and retrieval
    - Test derive PB from session history with known paces
    - Test manual PB overrides derived value
    - Test no PB returns None
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 3. Implement plan lifecycle manager
  - [x] 3.1 Create `backend/plan_lifecycle.py` with state transition logic
    - Define `VALID_TRANSITIONS` map (draft→active, active→archived)
    - Implement `activate_plan(user_id, plan_id)` — archives any currently active plan, then activates target
    - Implement `archive_plan(user_id, plan_id)` — archives an active plan
    - Implement `get_plan_status(user_id, plan_id)` — returns current status
    - Raise ValueError on invalid transitions
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [ ]* 3.2 Write property tests for plan lifecycle
    - **Property 10: Plan lifecycle invariant — at most one active plan**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**

  - [ ]* 3.3 Write unit tests for plan lifecycle
    - Test draft→active transition
    - Test active→archived transition
    - Test invalid transitions raise ValueError
    - Test activating plan archives previously active plan
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 4. Checkpoint - Ensure all backend module tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement periodization engine
  - [x] 5.1 Create `backend/periodization_engine.py` with prompt building and validation
    - Implement `build_plan_prompt(event, target_time, personal_best_seconds, weeks, sessions_per_week)` — builds system prompt with progressive overload constraints, session type variety rules, and recovery week instructions
    - Implement `validate_plan_structure(plan, weeks, sessions_per_week)` — validates AI output matches requested structure (correct week count, session count, valid types, no consecutive same types)
    - Define `MULTI_WEEK_PLAN_TOOL_SCHEMA` for Bedrock tool-use invocation
    - _Requirements: 1.1, 1.3, 1.6, 2.1, 2.2, 2.3, 2.4_

  - [ ]* 5.2 Write property tests for periodization engine validation
    - **Property 1: Plan structure matches request parameters**
    - **Property 2: Parameter validation rejects invalid input**
    - **Property 3: Every session contains required fields with valid types**
    - **Property 4: No consecutive same session types within a week**
    - **Property 5: Progressive intensity with recovery weeks**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.6, 2.1, 2.2, 2.3, 2.4**

  - [ ]* 5.3 Write unit tests for periodization engine
    - Test prompt includes PB when provided
    - Test prompt uses target_time when no PB
    - Test validation rejects wrong week count
    - Test validation rejects invalid session types
    - Test validation catches consecutive same types
    - _Requirements: 1.1, 1.3, 2.2, 2.3, 3.5, 3.6_

- [x] 6. Implement plan generator
  - [x] 6.1 Create `backend/plan_generator.py` with orchestration logic
    - Implement `generate_multi_week_plan(user_id, event, target_time, weeks, sessions_per_week)` — orchestrates full generation flow
    - Validate input parameters (weeks 4-12, sessions_per_week 3-5, default 3)
    - Call `pb_resolver.resolve_personal_best()` to get PB for the event
    - Call `periodization_engine.build_plan_prompt()` to build the Bedrock prompt
    - Invoke Bedrock Claude with tool-use schema via existing `bedrock_client.py`
    - Validate AI response with `periodization_engine.validate_plan_structure()`
    - Retry once on malformed response; return 502 if retry fails
    - Save valid plan via `structured_plan_store.save_structured_plan()` with status "draft"
    - Return complete plan dict with plan_id
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 3.5, 3.6, 4.1, 8.1, 8.5_

  - [ ]* 6.2 Write unit tests for plan generator
    - Test parameter validation rejects weeks outside 4-12
    - Test parameter validation rejects sessions_per_week outside 3-5
    - Test default sessions_per_week is 3
    - Test PB is included in prompt when available
    - Test plan saved with "draft" status
    - Mock Bedrock client for all tests
    - _Requirements: 1.2, 1.4, 1.5, 3.5, 3.6, 4.1, 8.5_

- [x] 7. Add API routes to Lambda handler
  - [x] 7.1 Add structured plan API routes to `backend/handler.py`
    - Add `POST /plans/generate` route → calls `plan_generator.generate_multi_week_plan()`
    - Add `GET /plans/structured` route → calls `structured_plan_store.get_user_structured_plans()`
    - Add `GET /plans/:plan_id` route → calls `structured_plan_store.get_plan_by_id()`
    - Add `PATCH /plans/:plan_id/status` route → calls `plan_lifecycle.activate_plan()` or `archive_plan()`
    - Add `POST /personal-bests` route → calls `pb_resolver.save_personal_best()`
    - Add `GET /personal-bests` route → calls `pb_resolver.get_personal_bests()`
    - All routes require authentication (follow existing pattern)
    - Return proper HTTP status codes and error messages per design error table
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_

  - [ ]* 7.2 Write integration tests for new API routes
    - Test POST /plans/generate with valid params returns plan with plan_id
    - Test GET /plans/structured returns user's plan list
    - Test GET /plans/:plan_id returns full plan
    - Test PATCH /plans/:plan_id/status performs transitions
    - Test POST /personal-bests persists entry
    - Test GET /personal-bests returns manual + derived
    - Test invalid params return 400 with descriptive messages
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_

- [x] 8. Checkpoint - Build and deploy backend
  - Ensure all tests pass, ask the user if questions arise.
  - Run `build-lambda.sh` to rebuild the Lambda package
  - Deploy updated Lambda to AWS

- [x] 9. Create frontend API service for plans
  - [x] 9.1 Create `frontend/src/api/planService.ts` with API client functions
    - Implement `generatePlan(params)` — POST /plans/generate
    - Implement `getPlans()` — GET /plans/structured
    - Implement `getPlanById(planId)` — GET /plans/:plan_id
    - Implement `updatePlanStatus(planId, status)` — PATCH /plans/:plan_id/status
    - Implement `savePersonalBest(event, timeSeconds)` — POST /personal-bests
    - Implement `getPersonalBests()` — GET /personal-bests
    - Define TypeScript interfaces for Plan, WeekBlock, SessionTemplate, PersonalBest
    - Follow existing patterns from `sessionService.ts` and `profileService.ts`
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.6, 8.7_

- [x] 10. Implement frontend components
  - [x] 10.1 Create `StructuredPlanForm` component
    - Form inputs: event (text), target time (text), duration in weeks (number 4-12), sessions per week (number 3-5)
    - Client-side validation for range boundaries
    - Loading state during generation (skeleton UI with estimated wait)
    - Error state with retry button on failure
    - On success, navigate to plan detail view
    - Create `StructuredPlanForm.css` with design tokens
    - _Requirements: 1.2, 1.4, 1.5, 8.1, 8.5_

  - [x] 10.2 Create `PlanListView` component
    - Display all user plans as cards with event, duration, created date
    - Show status badges (draft, active, archived) with visual distinction for active
    - Activate button on draft plans, Archive button on active plans
    - Optimistic UI updates for status changes with rollback on failure
    - Link each plan card to its detail view
    - Create `PlanListView.css` with design tokens
    - _Requirements: 5.4, 5.5, 4.2, 4.5, 6.3_

  - [x] 10.3 Create `PlanDetailView` component
    - Week-by-week expandable view showing all sessions
    - Each week section shows week number and session cards
    - Each session card shows title, type badge, warm-up, main set, cool-down, distance, focus notes
    - Plan header with goal info, status, and duration
    - Create `PlanDetailView.css` with design tokens
    - _Requirements: 5.1, 5.2, 5.3_

  - [x] 10.4 Create `PersonalBestManager` component
    - Form for manual PB entry (event name, time input)
    - Display list of all PBs with source indicator (manual/derived)
    - Validation for positive time values
    - Success/error feedback on save
    - Create `PersonalBestManager.css` with design tokens
    - _Requirements: 3.1, 3.2, 8.6, 8.7_

- [x] 11. Wire frontend routing and navigation
  - [x] 11.1 Add routes and navigation for training plans
    - Add `/plans` route → PlanListView
    - Add `/plans/new` route → StructuredPlanForm
    - Add `/plans/:planId` route → PlanDetailView
    - Add `/personal-bests` route → PersonalBestManager
    - Add navigation links in existing app navigation
    - Update `App.tsx` with new routes using react-router-dom v6
    - _Requirements: 5.1, 5.4_

  - [ ]* 11.2 Write frontend component tests
    - Test StructuredPlanForm validates input ranges
    - Test PlanListView renders plans with correct status badges
    - Test PlanDetailView renders week structure
    - Test PersonalBestManager displays PBs with source labels
    - Test loading and error states render correctly
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 12. Final checkpoint - Full integration verification
  - Ensure all tests pass, ask the user if questions arise.
  - Push frontend to git for Amplify deploy

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Backend uses Python with Hypothesis for property-based testing
- Frontend uses TypeScript/React with plain CSS and design tokens
- Existing `bedrock_client.py` is reused for AI invocation; new modules extend, not replace, existing code

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "2.2", "2.3", "3.1"] },
    { "id": 2, "tasks": ["3.2", "3.3", "5.1"] },
    { "id": 3, "tasks": ["5.2", "5.3", "6.1"] },
    { "id": 4, "tasks": ["6.2", "7.1"] },
    { "id": 5, "tasks": ["7.2", "9.1"] },
    { "id": 6, "tasks": ["10.1", "10.2", "10.3", "10.4"] },
    { "id": 7, "tasks": ["11.1", "11.2"] }
  ]
}
```
