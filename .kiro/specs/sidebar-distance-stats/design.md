# Implementation Plan

## Overview

Add distance-per-week, distance-per-month, and distance-year-to-date statistics to the Sidebar component. This is a frontend-only change that reuses the existing session data, date boundary computations, and `formatDistance` utility already present in the codebase.

## Architecture

### Component Flow

```
DashboardPage (computes distance sums) → Sidebar (receives & displays via props)
```

### Data Flow

1. `DashboardPage` already loads all user sessions and computes `startOfWeek`, `startOfMonth`, `startOfYear`
2. New computations sum `total_distance_meters` for sessions in each period (same filter logic already used for swim counts)
3. Three new numeric props are passed to `Sidebar`
4. `Sidebar` formats each value using the existing `formatDistance` function and renders them as stat items

## Components and Interfaces

### SidebarProps Interface

The existing `SidebarProps` interface in `frontend/src/components/Sidebar.tsx` is extended with three new required numeric properties:

```typescript
export interface SidebarProps {
  // ...existing props (swimsThisWeek, swimsThisMonth, swimsYTD, etc.)...
  distanceThisWeekMeters: number;
  distanceThisMonthMeters: number;
  distanceYTDMeters: number;
}
```

### Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| `DashboardPage` | Loads sessions, computes distance sums per period, passes props to Sidebar |
| `Sidebar` | Receives distance props, formats via `formatDistance`, renders stat items |
| `formatDistance` | Pure utility — converts meters to human-readable string ("X.X km" or "X m") |

## Data Models

No new data models are introduced. The feature reuses the existing `Session` model which already contains the `total_distance_meters` (number) and `session_date` (string) fields needed for computation.

## Detailed Design

### 1. DashboardPage Changes

**File:** `frontend/src/pages/DashboardPage.tsx`

Add three distance computations immediately after the existing swim count computations:

```typescript
const distanceThisWeek = sessions
  .filter(s => new Date(s.session_date) >= startOfWeek)
  .reduce((sum, s) => sum + s.total_distance_meters, 0);

const distanceThisMonth = sessions
  .filter(s => new Date(s.session_date) >= startOfMonth)
  .reduce((sum, s) => sum + s.total_distance_meters, 0);

const distanceYTD = sessions
  .filter(s => new Date(s.session_date) >= startOfYear)
  .reduce((sum, s) => sum + s.total_distance_meters, 0);
```

Pass these as new props to `<Sidebar>`:

```tsx
<Sidebar
  ...existing props...
  distanceThisWeekMeters={distanceThisWeek}
  distanceThisMonthMeters={distanceThisMonth}
  distanceYTDMeters={distanceYTD}
/>
```

### 2. Sidebar Props Interface Extension

**File:** `frontend/src/components/Sidebar.tsx`

Extend `SidebarProps`:

```typescript
export interface SidebarProps {
  // ...existing props...
  distanceThisWeekMeters: number;
  distanceThisMonthMeters: number;
  distanceYTDMeters: number;
}
```

### 3. Sidebar Rendering

Add three new stat items in the `sidebar__stats` section. Each distance stat is placed directly after its corresponding swim count stat for visual pairing:

```tsx
{/* After "Swims / Week" stat */}
<div className="sidebar__stat" role="listitem">
  <span className="sidebar__stat-value">{formatDistance(distanceThisWeekMeters)}</span>
  <span className="sidebar__stat-label">Distance / Week</span>
</div>

{/* After "Swims / Month" stat */}
<div className="sidebar__stat" role="listitem">
  <span className="sidebar__stat-value">{formatDistance(distanceThisMonthMeters)}</span>
  <span className="sidebar__stat-label">Distance / Month</span>
</div>

{/* After "Swims Year to Date" stat */}
<div className="sidebar__stat" role="listitem">
  <span className="sidebar__stat-value">{formatDistance(distanceYTDMeters)}</span>
  <span className="sidebar__stat-label">Distance Year to Date</span>
</div>
```

### 4. formatDistance Function

The existing `formatDistance` function already handles all formatting requirements:
- ≥1000m → `"X.X km"` (decimal omitted for whole numbers)
- <1000m → `"X m"`
- 0 → `"0 m"`

No changes needed to this function.

## Correctness Properties

### Property 1: Distance Sum Invariant
*For any* set of sessions and any time period, the computed distance sum must equal the sum of `total_distance_meters` across all sessions whose `session_date` falls within that period. No session outside the period contributes to the sum.

**Validates: Requirements 1.1, 2.1, 3.1**

### Property 2: Zero When Empty
*For any* time period that contains no sessions, the computed distance for that period must be exactly zero.

**Validates: Requirements 1.3, 2.3, 3.3**

### Property 3: Monotonicity of Period Containment
*For any* set of sessions, because the current week is contained within the current month which is contained within the year to date, `distanceThisWeek <= distanceThisMonth <= distanceYTD` must always hold.

**Validates: Requirements 1.1, 2.1, 3.1**

### Property 4: formatDistance Round-Trip Consistency
*For any* non-negative distance value in meters, the formatted output must always end in either " km" or " m". Values ≥1000 produce " km" suffix; values <1000 produce " m" suffix. The numeric prefix correctly represents the original value (within display rounding).

**Validates: Requirements 5.1, 5.2, 5.3**

### Property 5: Prop Completeness
*For any* call site rendering the Sidebar component, all three distance props (`distanceThisWeekMeters`, `distanceThisMonthMeters`, `distanceYTDMeters`) must be provided. TypeScript compilation enforces that all required props in `SidebarProps` are supplied.

**Validates: Requirements 6.1, 6.2, 6.3**

## Error Handling

This feature has minimal error handling needs since it operates on data already loaded by `DashboardPage`:

- **Sessions fail to load**: If the session fetch fails or returns an empty array, all distance computations naturally produce `0` (the `reduce` starts with initial value `0` over an empty filtered list).
- **Missing `total_distance_meters`**: Sessions without this field are treated as contributing `0` distance (falsy coercion via `s.total_distance_meters || 0` or upstream data guarantees).
- **Invalid dates**: Sessions with unparseable `session_date` values will fail the date comparison filter and be excluded from sums — no crash, just omission.

No additional error UI is needed; the Sidebar gracefully shows "0 m" when no data is available.

## Files to Modify

| File | Change |
|------|--------|
| `frontend/src/pages/DashboardPage.tsx` | Add distance computations and pass new props |
| `frontend/src/components/Sidebar.tsx` | Extend `SidebarProps`, destructure new props, render distance stats |

## Testing Strategy

- Unit test: Verify `formatDistance` handles boundary values (0, 999, 1000, 1500, 10000)
- Component test: Verify Sidebar renders distance stats with correct labels when given prop values
- Integration: Verify DashboardPage correctly computes distances from mock session data
