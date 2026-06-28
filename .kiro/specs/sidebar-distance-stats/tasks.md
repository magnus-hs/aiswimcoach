# Implementation Plan: Sidebar Distance Stats

## Overview

Add distance-per-week, distance-per-month, and distance-year-to-date statistics to the Sidebar component. This is a frontend-only change touching two files: `DashboardPage.tsx` (compute stats) and `Sidebar.tsx` (extend props and render stats). The existing `formatDistance` utility handles all formatting.

## Tasks

- [ ] 1. Extend SidebarProps interface and destructure new props
  - [ ] 1.1 Add `distanceThisWeekMeters: number`, `distanceThisMonthMeters: number`, and `distanceYTDMeters: number` to the `SidebarProps` interface in `frontend/src/components/Sidebar.tsx`
    - _Requirements: 6.1, 6.2, 6.3_
  - [ ] 1.2 Destructure the three new props in the Sidebar function component parameters
    - _Requirements: 6.1, 6.2, 6.3_

- [ ] 2. Compute distance statistics in DashboardPage
  - [ ] 2.1 Add `distanceThisWeek`, `distanceThisMonth`, and `distanceYTD` computations that sum `total_distance_meters` for sessions within each time period in `frontend/src/pages/DashboardPage.tsx`
    - Sum sessions with `session_date >= startOfWeek` for weekly, `>= startOfMonth` for monthly, `>= startOfYear` for YTD
    - _Requirements: 1.1, 1.3, 2.1, 2.3, 3.1, 3.3_
  - [ ] 2.2 Pass `distanceThisWeekMeters`, `distanceThisMonthMeters`, and `distanceYTDMeters` props to the `<Sidebar>` component
    - _Requirements: 1.2, 2.2, 3.2_

- [ ] 3. Render distance statistics in Sidebar
  - [ ] 3.1 Add "Distance / Week" stat item after the "Swims / Week" stat, displaying `formatDistance(distanceThisWeekMeters)` with `role="listitem"` in `frontend/src/components/Sidebar.tsx`
    - _Requirements: 4.1, 4.4, 4.5_
  - [ ] 3.2 Add "Distance / Month" stat item after the "Swims / Month" stat, displaying `formatDistance(distanceThisMonthMeters)` with `role="listitem"`
    - _Requirements: 4.2, 4.4, 4.5_
  - [ ] 3.3 Add "Distance Year to Date" stat item after the "Swims Year to Date" stat, displaying `formatDistance(distanceYTDMeters)` with `role="listitem"`
    - _Requirements: 4.3, 4.4, 4.5_

- [ ] 4. Checkpoint - Verify build and existing tests
  - Ensure all tests pass, ask the user if questions arise.
  - [ ] 4.1 Run TypeScript compilation to verify no type errors from the prop additions
    - _Requirements: 6.1, 6.2, 6.3_
  - [ ] 4.2 Run existing frontend tests to confirm no regressions
    - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1_

## Notes

- This is a small frontend-only change touching 2 files: `DashboardPage.tsx` and `Sidebar.tsx`
- The existing `formatDistance` utility already handles all formatting requirements (km/m conversion, zero handling)
- No new dependencies or backend changes required
- Each task references specific requirements for traceability

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "2.1"] },
    { "id": 2, "tasks": ["2.2", "3.1", "3.2", "3.3"] },
    { "id": 3, "tasks": ["4.1", "4.2"] }
  ]
}
```
