# Design Document

## Overview

This document details the architecture and component design for the Drill Detection feature. The feature enables the AI Swim Coach to identify drill lengths from Garmin FIT files, track them as a distinct activity type, display drill information in the frontend, and incorporate drill context into AI coaching prompts.

The implementation touches three layers: the backend FIT parser (Python), the frontend components (React TypeScript), and the AI coaching prompt assembly. Drill lengths are identified by the existing `swim_stroke=4` mapping and integrated into the existing data flow without breaking changes to the session storage schema.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Garmin FIT File                          │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              fit_parser.py (Backend - Python)                │
│                                                             │
│  ┌───────────────┐  ┌──────────────────┐  ┌─────────────┐  │
│  │ _stroke_name  │  │extract_session   │  │ parse_fit    │  │
│  │ (already maps │  │_info (splits,    │  │ (metrics w/  │  │
│  │  4→"drill")   │  │ session totals)  │  │  exclusion)  │  │
│  └───────────────┘  └──────────────────┘  └─────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              DynamoDB (Session Storage)                      │
│  Session record with splits[] containing drill lengths      │
└────────────────────────────┬────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
┌──────────────────┐ ┌─────────────┐ ┌──────────────────┐
│ SessionDetailPage│ │ActivityCard │ │ prompt_assembler  │
│ + DrillSummary   │ │+ drill badge│ │ + drill context   │
│ + GroupedSplits  │ │             │ │                   │
│ + StrokeBreakdown│ │             │ │                   │
└──────────────────┘ └─────────────┘ └──────────────────┘
```

## Components and Interfaces

### 1. Backend: FIT Parser Drill Classification

**File:** `backend/fit_parser.py`

The existing `_stroke_name` function already maps `swim_stroke=4` to `"drill"`. The `extract_session_info` function already stores these as `LengthSplit` objects with `stroke="drill"`. The primary changes are:

1. **Dominant stroke exclusion** (already implemented): The existing code excludes `"drill"` from dominant stroke calculation via the `filtered` dict in `extract_session_info`.
2. **Metrics exclusion in `parse_fit`**: Modify the loop to skip drill lengths when accumulating pace, SWOLF, and stroke rate values. Fall back to drill data if all lengths are drills.

```python
def parse_fit(fit_bytes: bytes) -> Metrics:
    # ... existing parsing setup ...

    for record_type in ("length", "lap"):
        for record in fitfile.get_messages(record_type):
            data = {f.name: f.value for f in record}
            
            stroke_val = data.get("swim_stroke")
            is_drill = _stroke_name(stroke_val) == "drill"

            avg_speed = data.get("avg_speed")
            if avg_speed is not None and avg_speed > 0:
                if not is_drill:
                    pace_values.append(speed_to_pace(avg_speed))
                else:
                    drill_pace_values.append(speed_to_pace(avg_speed))

            cadence = data.get("avg_swimming_cadence")
            if cadence is not None and cadence > 0:
                if not is_drill:
                    stroke_rate_values.append(float(cadence))
                else:
                    drill_stroke_rate_values.append(float(cadence))

            swolf = compute_swolf(data, pool_length)
            if swolf is not None:
                if not is_drill:
                    swolf_values.append(swolf)
                else:
                    drill_swolf_values.append(swolf)

        if pace_values or swolf_values or stroke_rate_values:
            break
        if drill_pace_values or drill_swolf_values or drill_stroke_rate_values:
            break

    # Fall back to drill values if no regular swim data
    final_pace = pace_values or drill_pace_values
    final_swolf = swolf_values or drill_swolf_values
    final_stroke_rate = stroke_rate_values or drill_stroke_rate_values

    # ... rest of metrics computation ...
```

### 2. Backend: Drill Context for AI Coach

**File:** `backend/prompt_assembler.py`

Add a helper function to compute drill context from splits data and integrate it into the coaching prompt.

```python
@dataclass
class DrillContext:
    """Aggregated drill information for AI coaching context."""
    drill_count: int
    drill_distance_m: float
    drill_time_seconds: float
    drill_position: str  # "beginning", "middle", "end", or "throughout"


def compute_drill_context(splits: list[dict], pool_length_m: float) -> DrillContext | None:
    """Compute drill summary from session splits.
    
    Args:
        splits: List of split dicts with 'stroke' and 'time_seconds' fields.
        pool_length_m: Pool length in meters.
    
    Returns:
        DrillContext if drills exist, None otherwise.
    """
    drill_indices = [i for i, s in enumerate(splits) if s.get("stroke") == "drill"]
    if not drill_indices:
        return None

    drill_count = len(drill_indices)
    drill_distance = drill_count * pool_length_m
    drill_time = sum(splits[i].get("time_seconds", 0) for i in drill_indices)
    
    # Determine position
    total = len(splits)
    if total == 0:
        position = "throughout"
    else:
        avg_position = sum(drill_indices) / len(drill_indices)
        relative = avg_position / (total - 1) if total > 1 else 0.5
        if relative <= 0.33:
            position = "beginning"
        elif relative >= 0.67:
            position = "end"
        elif all(i < total * 0.67 and i >= total * 0.33 for i in drill_indices):
            position = "middle"
        else:
            position = "throughout"

    return DrillContext(
        drill_count=drill_count,
        drill_distance_m=drill_distance,
        drill_time_seconds=drill_time,
        drill_position=position,
    )


def format_drill_context(ctx: DrillContext) -> str:
    """Format drill context into a string for the coaching prompt."""
    minutes = int(ctx.drill_time_seconds // 60)
    seconds = int(ctx.drill_time_seconds % 60)
    return (
        f"Drill work: {ctx.drill_count} drill lengths "
        f"({ctx.drill_distance_m:.0f}m, {minutes}m {seconds}s), "
        f"positioned at the {ctx.drill_position} of the session."
    )
```

### 3. Frontend: Drill Summary Component

**File:** `frontend/src/components/DrillSummary.tsx`

A new component that renders drill aggregation data when drills are present.

```typescript
interface DrillSummaryProps {
  splits: LengthSplit[];
  poolLengthM: number;
}

interface DrillStats {
  count: number;
  totalDistance: number;
  totalTime: number;
}

export function computeDrillStats(splits: LengthSplit[], poolLengthM: number): DrillStats | null {
  const drillSplits = splits.filter(s => s.stroke === 'drill');
  if (drillSplits.length === 0) return null;
  return {
    count: drillSplits.length,
    totalDistance: drillSplits.length * poolLengthM,
    totalTime: drillSplits.reduce((sum, s) => sum + s.time_seconds, 0),
  };
}

export function DrillSummary({ splits, poolLengthM }: DrillSummaryProps) {
  const stats = computeDrillStats(splits, poolLengthM);
  if (!stats) return null;
  
  return (
    <section className="drill-summary" aria-label="Drill summary">
      <h3>Drill Work</h3>
      <div className="drill-summary__grid">
        <div className="drill-summary__item">
          <span className="drill-summary__label">Lengths</span>
          <span className="drill-summary__value">{stats.count}</span>
        </div>
        <div className="drill-summary__item">
          <span className="drill-summary__label">Distance</span>
          <span className="drill-summary__value">{stats.totalDistance}m</span>
        </div>
        <div className="drill-summary__item">
          <span className="drill-summary__label">Time</span>
          <span className="drill-summary__value">{formatTime(stats.totalTime)}</span>
        </div>
      </div>
    </section>
  );
}
```

### 4. Frontend: Activity Card Drill Badge

**File:** `frontend/src/components/ActivityCard.tsx`

Add a drill count badge when splits contain drills.

```typescript
// Add to ActivityCard props:
// drillCount is computed from splits
const drillCount = splits?.filter(s => s.stroke === 'drill').length ?? 0;

// Render in card when drillCount > 0:
{drillCount > 0 && (
  <span className="activity-card__drill-badge" aria-label={`${drillCount} drill lengths`}>
    🏊‍♂️ {drillCount} drill{drillCount > 1 ? 's' : ''}
  </span>
)}
```

### 5. Frontend: Grouped Splits Table Drill Formatting

**File:** `frontend/src/components/GroupedSplitsTable.tsx`

Modify the detail rows to handle drill splits:
- Display "—" for strokes when strokes = 0 (already handled by existing `split.strokes > 0 ? ... : '—'` logic)
- Display "—" for DPS when strokes = 0 (already handled)
- Add a visual drill indicator (CSS class on drill rows)
- Omit SWOLF for drill rows (no SWOLF column exists currently, so this is inherently satisfied)

```typescript
// In DetailRows, add drill-specific class:
<tr key={split.length_number} className={split.stroke === 'drill' ? 'grouped-splits__row--drill' : ''}>
  {/* ... existing columns ... */}
  <td>{split.stroke === 'drill' ? <span className="drill-indicator">Drill</span> : capitalize(split.stroke)}</td>
</tr>
```

### 6. Frontend: Stroke Breakdown Integration

The existing `computeBreakdownFromSplits` utility already handles drill as a stroke category — it groups all splits by their `stroke` field and calculates percentages. The `strokeLabel` function already maps `"drill"` → `"Drill"`. No logic changes needed.

Visual differentiation for the drill category will be handled via CSS using a distinct color for the drill entry in the breakdown display.

## Data Models

### Existing Models (No Changes Required)

The `LengthSplit` dataclass already supports drill lengths:

```python
@dataclass
class LengthSplit:
    length_number: int
    time_seconds: float
    stroke: str          # "drill" for drill lengths
    strokes: int         # 0 for drills without stroke data
    rest_after_seconds: float | None = None
    avg_hr: int | None = None
```

The `SessionInfo` dataclass needs no changes — `num_lengths` already includes drills, `stroke` (dominant) already excludes drills.

### New Data Model: DrillContext

```python
@dataclass
class DrillContext:
    drill_count: int           # number of drill lengths
    drill_distance_m: float    # drill_count × pool_length
    drill_time_seconds: float  # sum of drill time_seconds
    drill_position: str        # "beginning" | "middle" | "end" | "throughout"
```

### Frontend Type Addition

```typescript
export interface DrillStats {
  count: number;
  totalDistance: number;
  totalTime: number;
}
```

## Interfaces

### Backend API

No new endpoints required. The existing session detail endpoint already returns splits with `stroke: "drill"`. The frontend computes drill stats client-side from the splits array.

### Prompt Assembly Interface

```python
def compute_drill_context(splits: list[dict], pool_length_m: float) -> DrillContext | None
def format_drill_context(ctx: DrillContext) -> str
```

### Frontend Utility Interface

```typescript
// In utils/drillStats.ts or within DrillSummary component
function computeDrillStats(splits: LengthSplit[], poolLengthM: number): DrillStats | null

// Drill position classification for AI context (if needed client-side)
function classifyDrillPosition(splits: LengthSplit[]): 'beginning' | 'middle' | 'end' | 'throughout'
```

## Error Handling

| Scenario | Handling |
|----------|----------|
| All lengths are drills, no valid speed data | `parse_fit` uses available drill data; if truly no data exists, raises `MetricsMissingError` as before |
| All lengths are drills with valid speed/cadence | Use drill data for metrics (no error) |
| Drill length with null total_strokes | Store as `strokes=0` in split |
| Drill length with null avg_speed | Exclude from pace calculation (skip, don't error) |
| No drill lengths in session | DrillSummary component returns null, drill badge hidden, no drill context in prompt |
| Mixed session with some drills having data | Use available drill data as fallback only when no regular swim data exists |

## Testing Strategy

**Unit Tests (Example-based):**
- Render DrillSummary with and without drill splits, verify visibility (Req 3.1, 3.5)
- Render drill splits inline in GroupedSplitsTable, verify visual indicator (Req 4.1, 4.2, 4.3)
- Render ActivityCard with zero drills, verify no badge (Req 6.2)
- Verify drill category gets distinct CSS class in StrokeBreakdown (Req 5.3)
- Verify prompt includes drill context when drills present (Req 7.1)

**Property Tests (100+ iterations):**
- Drill classification from stroke enum values (Properties 1, 2)
- Session totals include drill lengths (Property 3)
- Dominant stroke never "drill" when non-drills exist (Property 4)
- Drill stats computation correctness (Property 5)
- Stroke breakdown percentage calculation (Property 6)
- Activity card count matches drill splits (Property 7)
- Drill position classification logic (Property 8)
- Metrics exclusion for drills (Property 9)
- All-drill session graceful handling (Property 10)

**Integration Tests:**
- End-to-end FIT file upload with drill lengths, verify stored session (Req 7.1, 7.3)

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Drill stroke classification

For any FIT length record where swim_stroke equals 4 (integer) or any case variation of the string "drill", the parser SHALL produce a LengthSplit with stroke field equal to "drill".

**Validates: Requirements 1.1, 1.2, 1.3**

### Property 2: Drill split data integrity

For any drill length record, the output LengthSplit SHALL have strokes equal to 0 when total_strokes is 0 or null, and time_seconds equal to the record's elapsed time value.

**Validates: Requirements 1.4, 1.5**

### Property 3: Drill inclusion in session totals

For any session containing N active lengths (including drill lengths), the session's num_lengths SHALL equal N and total_distance_m SHALL be at least N × pool_length_m (accounting for drill lengths contributing to distance).

**Validates: Requirements 2.1, 2.3**

### Property 4: Dominant stroke excludes drill

For any session containing at least one non-drill active length, the computed dominant stroke SHALL never be "drill".

**Validates: Requirements 2.4**

### Property 5: Drill summary computation

For any non-empty splits array and positive pool length, computeDrillStats SHALL return a DrillStats where count equals the number of splits with stroke "drill", totalDistance equals count × poolLength, and totalTime equals the sum of time_seconds of all drill splits.

**Validates: Requirements 3.2, 3.3, 3.4**

### Property 6: Drill percentage in stroke breakdown

For any splits array containing at least one drill length, computeBreakdownFromSplits SHALL include a "drill" entry whose percent equals (drill_count / total_lengths) × 100 (rounded to one decimal place).

**Validates: Requirements 5.1, 5.2**

### Property 7: Activity card drill count

For any splits array, the drill indicator count displayed on the ActivityCard SHALL equal the number of splits with stroke "drill", and the indicator SHALL be visible if and only if that count is greater than zero.

**Validates: Requirements 6.1, 6.2, 6.3**

### Property 8: Drill position classification

For any non-empty splits array containing drill lengths, the computed drill position SHALL be "beginning" when the average index of drill lengths is in the first third, "end" when in the last third, "middle" when all drills are in the middle third, and "throughout" otherwise.

**Validates: Requirements 7.2**

### Property 9: Drill exclusion from metrics

For any session containing both drill and non-drill lengths, the computed session average pace SHALL only include non-drill lengths with valid speed, the session average SWOLF SHALL exclude all drill lengths, and the session stroke rate SHALL exclude drill lengths with zero or null cadence.

**Validates: Requirements 8.1, 8.2, 8.3**

### Property 10: All-drill session graceful handling

For any session where all active lengths are drill lengths, the parse_fit function SHALL NOT raise a MetricsMissingError, and SHALL compute metrics from available drill data.

**Validates: Requirements 8.4**
