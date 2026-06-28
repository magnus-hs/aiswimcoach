# Design Document: Next Session Tasks

## Overview

This design covers four distinct improvements to the AI Swim Coach application:

1. **IAM Permission Fix** — Add `dynamodb:UpdateItem` to the Lambda IAM policy so plan activation works
2. **SVG Logo** — Replace the raster `<img>` logo with an inline SVG using design tokens
3. **Structured PB Input** — Replace freeform event text input with stroke/distance dropdowns
4. **Grouped PB Display** — Show personal bests grouped by stroke with manual/derived comparison

Requirements 1 and 2 are infrastructure/UI changes with no complex logic. Requirements 3 and 4 involve frontend form logic, backend API changes, and data transformation that benefit from property-based testing.

## Architecture

### System Context

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (React/Vite)                                   │
│                                                          │
│  Navigation.tsx ──── inline SVG logo (Req 2)             │
│  PersonalBestManager.tsx ── structured form (Req 3)      │
│                           ── grouped display (Req 4)     │
│  planService.ts ── getPersonalBests() updated response   │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTPS
                           ▼
┌──────────────────────────────────────────────────────────┐
│  API Gateway (lp84bjpr2c)                                │
│  PATCH /plans/{id}/status   (Req 1 - already routed)     │
│  GET /personal-bests        (Req 4 - response change)    │
│  POST /personal-bests       (unchanged)                  │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│  Lambda: ai-swim-coach                                   │
│  handler.py → pb_resolver.py (Req 4 - merge logic)       │
│            → plan_lifecycle.py (Req 1 - already works)   │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│  DynamoDB                                                │
│  Sessions table ─── UpdateItem (Req 1 - needs IAM)       │
│  UserProfiles table ─── personal_bests map               │
└──────────────────────────────────────────────────────────┘
```

### Requirement 1: IAM Permission Fix

No code changes needed. The `plan_lifecycle.py` and `structured_plan_store.py` already implement `update_plan_status()` using `table.update_item()`. The issue is purely that the IAM inline policy `ai-swim-coach-lambda-permissions` is missing `dynamodb:UpdateItem` in the `DynamoDBSessions` statement.

**Fix**: Run AWS CLI to update the inline policy, adding `dynamodb:UpdateItem` to the existing Actions list for the Sessions table ARN.

```
Current Actions for Sessions table:
  - dynamodb:PutItem
  - dynamodb:GetItem
  - dynamodb:Query

After fix:
  - dynamodb:PutItem
  - dynamodb:GetItem
  - dynamodb:Query
  - dynamodb:UpdateItem
```

### Requirement 2: SVG Logo

Replace `<img src="/logo.png">` in `Navigation.tsx` with an inline `<svg>` element. The SVG will depict stylized swimming lanes (horizontal lines representing lane dividers with a wave accent).

**Design decisions:**
- Use 3 colors from tokens.css: `--color-primary`, `--color-primary-light`, `--color-secondary`
- SVG uses `currentColor` pattern for the primary stroke, with CSS custom properties for fills
- Height constrained via CSS: 36px default, 24px minimum at narrow viewports
- Inline SVG avoids an extra network request and allows CSS variable theming

### Requirement 3: Structured PB Input

Replace the single text `<input>` for event name with two `<select>` dropdowns (stroke, distance) plus a conditional custom-distance number input.

**Data flow:**

```
User selects:
  Stroke dropdown: [Freestyle | Backstroke | Breaststroke | Butterfly | IM]
  Distance dropdown: [50m | 100m | 200m | 400m | 800m | 1500m | Custom]
  (if Custom) → numeric input: 25..5000 meters

On submit:
  eventName = `${distance}m ${stroke}`   // e.g. "100m Freestyle"
  timeSeconds = parseTime(timeInput)     // M:SS → seconds

  POST /personal-bests { event: eventName, time_seconds: timeSeconds }
```

**Validation logic:**
- Time: must match `/^\d{1,2}:\d{2}$/` with minutes 0-59, seconds 00-59
- Custom distance: integer, 25 ≤ value ≤ 5000
- All fields required before submit enabled

### Requirement 4: Grouped PB Display

**Backend change**: `get_personal_bests()` in `pb_resolver.py` currently merges manual and derived PBs, returning only the manual entry when both exist for the same event. We need to change this to return BOTH entries so the frontend can show them side by side.

**Current merge logic** (line ~160 of pb_resolver.py):
```python
# Merge: manual entries take priority
all_pbs = dict(manual_pbs)
for event_name, pb_data in derived_pbs.items():
    if event_name not in all_pbs:
        all_pbs[event_name] = pb_data
```

**New logic**: Return both manual and derived as separate entries in the array. The frontend groups them by event.

```python
# Return ALL PBs — both manual and derived (even for same event)
all_pbs = list(manual_pbs.values()) + list(derived_pbs.values())
return all_pbs
```

**Frontend grouping flow:**

```
GET /personal-bests
  → [{event: "100m Freestyle", source: "manual", ...},
     {event: "100m Freestyle", source: "derived", ...},
     {event: "200m Backstroke", source: "manual", ...}]

Frontend transform:
  1. Parse stroke from event name: "100m Freestyle" → stroke="Freestyle"
  2. Group by stroke type → Map<stroke, PB[]>
  3. Within each stroke group, subgroup by event (distance)
  4. For each event, show manual + derived side by side
  5. Calculate diff when both exist: |manual - derived| in seconds
```

## Components and Interfaces

### Navigation.tsx Changes (Req 2)

```tsx
// Replace:
<img src="/logo.png" alt="AI Swim Coach" className="nav__logo-img" />

// With:
<svg
  className="nav__logo-img"
  role="img"
  aria-label="AI Swim Coach"
  viewBox="0 0 48 36"
  xmlns="http://www.w3.org/2000/svg"
>
  {/* Lane lines */}
  <rect y="8" width="48" height="2" fill="var(--color-primary-light)" rx="1" />
  <rect y="16" width="48" height="2" fill="var(--color-primary-light)" rx="1" />
  <rect y="24" width="48" height="2" fill="var(--color-primary-light)" rx="1" />
  {/* Swimmer silhouette / wave */}
  <path
    d="M6 18 C12 14, 18 22, 24 18 C30 14, 36 22, 42 18"
    stroke="var(--color-primary)"
    strokeWidth="2.5"
    fill="none"
    strokeLinecap="round"
  />
  {/* Water accent */}
  <path
    d="M2 30 C8 27, 14 33, 20 30 C26 27, 32 33, 38 30 C44 27, 46 30, 48 30"
    stroke="var(--color-secondary)"
    strokeWidth="1.5"
    fill="none"
    strokeLinecap="round"
  />
</svg>
```

### PersonalBestManager.tsx Changes (Req 3 + 4)

**New interfaces:**

```typescript
interface PBFormState {
  stroke: StrokeType | '';
  distance: DistanceOption | '';
  customDistance: string;
  timeInput: string;
}

type StrokeType = 'Freestyle' | 'Backstroke' | 'Breaststroke' | 'Butterfly' | 'IM';
type DistanceOption = '50' | '100' | '200' | '400' | '800' | '1500' | 'Custom';

interface StrokeGroup {
  stroke: string;
  events: EventEntry[];
}

interface EventEntry {
  event: string;
  distance: number;
  manual?: PersonalBest;
  derived?: PersonalBest;
}
```

**Key functions to implement:**

```typescript
// Construct event name from form state
function buildEventName(stroke: StrokeType, distance: DistanceOption, customDistance: string): string {
  const dist = distance === 'Custom' ? customDistance : distance;
  return `${dist}m ${stroke}`;
}

// Parse stroke type from event string "100m Freestyle" → "Freestyle"
function parseStrokeFromEvent(event: string): string {
  const match = event.match(/^\d+m\s+(.+)$/);
  return match ? match[1] : 'Other';
}

// Parse distance from event string "100m Freestyle" → 100
function parseDistanceFromEvent(event: string): number {
  const match = event.match(/^(\d+)m/);
  return match ? parseInt(match[1], 10) : 0;
}

// Group PBs by stroke, then by event within stroke
function groupPersonalBests(pbs: PersonalBest[]): StrokeGroup[] {
  // 1. Build map: stroke → event → {manual?, derived?}
  // 2. Sort strokes alphabetically
  // 3. Sort events within stroke by distance ascending
  // 4. Omit stroke groups with no entries
}

// Validate time input (M:SS or MM:SS format)
function validateTimeInput(input: string): { valid: boolean; seconds?: number; error?: string } {
  const match = input.trim().match(/^(\d{1,2}):(\d{2})$/);
  if (!match) return { valid: false, error: 'Enter time as M:SS (e.g., 1:05)' };
  const minutes = parseInt(match[1], 10);
  const seconds = parseInt(match[2], 10);
  if (minutes < 0 || minutes > 59) return { valid: false, error: 'Minutes must be 0-59' };
  if (seconds < 0 || seconds > 59) return { valid: false, error: 'Seconds must be 00-59' };
  return { valid: true, seconds: minutes * 60 + seconds };
}

// Validate custom distance
function validateCustomDistance(input: string): { valid: boolean; error?: string } {
  const num = parseInt(input, 10);
  if (isNaN(num) || !Number.isInteger(parseFloat(input))) {
    return { valid: false, error: 'Distance must be a whole number' };
  }
  if (num < 25 || num > 5000) {
    return { valid: false, error: 'Distance must be between 25 and 5000 meters' };
  }
  return { valid: true };
}
```

### pb_resolver.py Changes (Req 4)

**Modified `get_personal_bests` function:**

```python
def get_personal_bests(user_id: str) -> list[dict]:
    """Return all PBs (manual + derived) for a user.

    Returns BOTH manual and derived entries even when they exist for the
    same event, enabling side-by-side comparison in the frontend.
    """
    # ... existing code to fetch manual_pbs and derived_pbs ...

    # Return all entries — do NOT de-duplicate by event
    all_pbs = list(manual_pbs.values()) + list(derived_pbs.values())
    return all_pbs
```

This is the only backend code change needed. The response format remains `PersonalBest[]` — the frontend already has a `source` field to distinguish manual from derived.

## Data Models

### PersonalBest (unchanged shape, new semantics)

The `PersonalBest` TypeScript interface stays the same:

```typescript
interface PersonalBest {
  event: string;        // e.g. "100m Freestyle"
  time_seconds: number; // e.g. 65.5
  source: 'manual' | 'derived';
  updated_at: string;   // ISO 8601
}
```

**Semantic change**: Previously, `getPersonalBests()` returned at most one entry per event (manual took priority). Now it may return two entries for the same event — one manual, one derived. The frontend must handle this when grouping.

### Stroke/Distance Constants

```typescript
const STROKES: StrokeType[] = ['Freestyle', 'Backstroke', 'Breaststroke', 'Butterfly', 'IM'];
const DISTANCES: DistanceOption[] = ['50', '100', '200', '400', '800', '1500', 'Custom'];
const CUSTOM_DISTANCE_MIN = 25;
const CUSTOM_DISTANCE_MAX = 5000;
```

### IAM Policy Document (Req 1)

The updated policy statement for the Sessions table:

```json
{
  "Sid": "DynamoDBSessions",
  "Effect": "Allow",
  "Action": [
    "dynamodb:PutItem",
    "dynamodb:GetItem",
    "dynamodb:Query",
    "dynamodb:UpdateItem"
  ],
  "Resource": [
    "arn:aws:dynamodb:us-east-1:*:table/Sessions",
    "arn:aws:dynamodb:us-east-1:*:table/Sessions/index/session_id-index"
  ]
}
```



## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Time validation round trip

*For any* pair (minutes, seconds) where 0 ≤ minutes ≤ 59 and 0 ≤ seconds ≤ 59, formatting as `"${minutes}:${seconds.toString().padStart(2, '0')}"` and passing to `validateTimeInput` SHALL return `{ valid: true, seconds: minutes * 60 + seconds }`. Conversely, *for any* string that does not match the pattern `/^\d{1,2}:\d{2}$/` with both parts in valid ranges, `validateTimeInput` SHALL return `{ valid: false }`.

**Validates: Requirements 3.5, 3.8**

### Property 2: Custom distance validation boundaries

*For any* integer `n` where 25 ≤ n ≤ 5000, `validateCustomDistance(n.toString())` SHALL return `{ valid: true }`. *For any* integer `n` where n < 25 or n > 5000, or *for any* non-integer numeric string, `validateCustomDistance` SHALL return `{ valid: false }`.

**Validates: Requirements 3.3, 3.9**

### Property 3: Event name construction

*For any* stroke in `['Freestyle', 'Backstroke', 'Breaststroke', 'Butterfly', 'IM']` and *for any* valid distance (either a standard distance from `[50, 100, 200, 400, 800, 1500]` or a custom integer in `[25, 5000]`), `buildEventName` SHALL produce the string `"${distance}m ${stroke}"`.

**Validates: Requirements 3.6, 3.7**

### Property 4: Grouping produces sorted non-empty stroke groups

*For any* non-empty list of `PersonalBest` entries where each event matches the format `"{distance}m {stroke}"`, `groupPersonalBests` SHALL return stroke groups that are (a) sorted alphabetically by stroke name and (b) each contain at least one event entry. No stroke group with zero events SHALL appear in the output.

**Validates: Requirements 4.1, 4.6**

### Property 5: Source merging correctness

*For any* list of `PersonalBest` entries, when two entries share the same event string but differ in source (one "manual", one "derived"), `groupPersonalBests` SHALL produce exactly one `EventEntry` for that event with both `manual` and `derived` fields populated. When only one source exists for an event, the `EventEntry` SHALL have only that source populated and the other undefined.

**Validates: Requirements 4.3, 4.8**

### Property 6: Time difference calculation

*For any* two positive numbers `manualTime` and `derivedTime`, the displayed time difference SHALL equal `Math.abs(manualTime - derivedTime)` rounded to one decimal place, labeled "faster" when `manualTime < derivedTime` and "slower" when `manualTime > derivedTime`.

**Validates: Requirements 4.4**

## Error Handling

### Requirement 1 (IAM Fix)

| Error Condition | Response | Notes |
|---|---|---|
| IAM permission missing | HTTP 500 + error body | DynamoDB ClientError propagates as 500 |
| Plan not found | HTTP 404 + error body | ValueError from plan_lifecycle |
| Invalid state transition | HTTP 400 + error body | ValueError from plan_lifecycle |

### Requirement 2 (SVG Logo)

No runtime errors — the SVG is static markup. If CSS variables are undefined, the browser falls back to transparent/black.

### Requirement 3 (Structured Input)

| Error Condition | Behavior |
|---|---|
| Invalid time format | Inline error: "Enter time as M:SS (e.g., 1:05)" |
| Custom distance out of range | Inline error: "Distance must be between 25 and 5000 meters" |
| Custom distance non-integer | Inline error: "Distance must be a whole number" |
| Empty stroke/distance selection | Submit button disabled (form incomplete) |
| Backend POST failure | Inline error: "Failed to save personal best" + preserve form data |

### Requirement 4 (Grouped Display)

| Error Condition | Behavior |
|---|---|
| GET /personal-bests fails | Error message shown, no PB list rendered, no stale data |
| Event name doesn't match format | Grouped under "Other" category (graceful degradation) |
| No PBs exist at all | Empty state message (existing behavior) |

## Testing Strategy

### Unit Tests (Example-Based)

- **Navigation SVG**: Render component, assert SVG present with correct `role`, `aria-label`, no `<img>` tag
- **PB Form**: Render with each non-Custom distance selected, verify custom input hidden
- **PB Form submission**: Mock API, verify successful submit clears form
- **PB Form error preservation**: Mock API failure, verify form data preserved
- **Grouped display headings**: Render with mock data, verify stroke group headings
- **Source badges**: Verify "manual" / "derived" badge labels render correctly
- **API error state**: Mock getPersonalBests failure, verify error message and no list

### Property-Based Tests

Property-based testing applies to this feature because Requirements 3 and 4 involve pure validation functions (`validateTimeInput`, `validateCustomDistance`, `buildEventName`) and a pure data transformation function (`groupPersonalBests`) with large or infinite input spaces.

**Library**: [fast-check](https://github.com/dubzzz/fast-check) (already the standard for TypeScript PBT)

**Configuration**: Each property test runs a minimum of 100 iterations.

**Test tag format**: `Feature: next-session-tasks, Property {N}: {title}`

| Property | Function Under Test | Generator Strategy |
|---|---|---|
| 1: Time validation round trip | `validateTimeInput` | Generate (minutes: 0-59, seconds: 0-59) for valid; arbitrary strings for invalid |
| 2: Custom distance validation | `validateCustomDistance` | Generate integers across full range, non-integers, boundary values |
| 3: Event name construction | `buildEventName` | Generate stroke from enum, distance from standard + custom range |
| 4: Sorted non-empty groups | `groupPersonalBests` | Generate lists of PB objects with random event names matching format |
| 5: Source merging | `groupPersonalBests` | Generate PB lists with controlled duplicates (same event, different source) |
| 6: Time difference | Diff calculation function | Generate pairs of positive floats |

### Integration Tests

- **Req 1**: After IAM fix, PATCH `/plans/{id}/status` with draft plan → 200 with status "active"
- **Req 4**: GET `/personal-bests` returns both manual and derived entries for same event (backend integration test using mocked DynamoDB)

### Backend Unit Tests

- `get_personal_bests` returns both manual and derived entries for the same event (not de-duplicated)
- `get_personal_bests` returns only manual when no derived exists, and vice versa
- Existing tests for `activate_plan`, `archive_plan` continue to pass (no logic change)
