# Design Document: Notes UI Restructure

## Overview

This design restructures the Training Notes feature by:
1. Removing the TrainingNotes component from the Dashboard sidebar
2. Creating a dedicated `/notes` page accessible from the Profile dropdown
3. Adding per-session notes to the Activity Detail Page
4. Extending the backend and frontend API client to support optional `session_id` on notes

The architecture leverages the existing `TrainingNotes` component and `notesService` with minimal modifications, adding a new page component and a session-scoped notes section.

## Architecture

### Component Structure

```
App.tsx
├── Navigation.tsx (+ "Training Notes" menu item)
├── Routes
│   ├── /notes → TrainingNotesPage (new)
│   ├── /activity/:id → ActivityDetailPage
│   │   └── SessionNotesSection (new, above InteractionsPanel)
│   └── / → DashboardPage (TrainingNotes removed)
```

### Data Flow

```
┌─────────────────────┐        ┌──────────────────────┐
│  TrainingNotesPage   │        │  SessionNotesSection  │
│  (global notes)      │        │  (per-session notes)  │
└─────────┬───────────┘        └──────────┬───────────┘
          │                               │
          ▼                               ▼
┌─────────────────────────────────────────────────────┐
│              notesService.ts                         │
│  createNote(text, sessionId?)                       │
│  getNotes(sessionId?)                               │
│  deleteNote(noteId)                                 │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│              Backend: handler.py                     │
│  POST /notes  { text, session_id? }                 │
│  GET  /notes  ?session_id=xyz                       │
│  DELETE /notes/:id                                  │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│              notes_service.py                        │
│  create_note(user_id, text, session_id=None)        │
│  get_notes(user_id, session_id=None)                │
│  delete_note(user_id, note_id)                      │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│  DynamoDB: ai-swim-coach-notes                      │
│  PK: user_id  SK: note_id                           │
│  Attributes: text, timestamp, session_id (optional) │
└─────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. TrainingNotesPage (New)

**File:** `frontend/src/pages/TrainingNotesPage.tsx`

A dedicated page at `/notes` that reuses the existing note CRUD pattern from `TrainingNotes` but adds an explanatory header and filters to show only global notes (no `session_id`).

```typescript
import { useState, useEffect, FormEvent } from 'react';
import { createNote, getNotes, deleteNote, TrainingNote } from '../api/notesService';
import { formatRelativeTime } from '../utils/relativeTime';

export function TrainingNotesPage() {
  const [notes, setNotes] = useState<TrainingNote[]>([]);
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [fetchLoading, setFetchLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function fetchNotes() {
      try {
        // No session_id → returns only global notes
        const data = await getNotes();
        if (!cancelled) {
          setNotes(data.slice(0, 50));
          setFetchLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load notes.');
          setFetchLoading(false);
        }
      }
    }
    fetchNotes();
    return () => { cancelled = true; };
  }, []);

  // handleSubmit creates a global note (no session_id)
  // handleDelete removes a note by ID
  // Renders: explanatory section + form + notes list
}
```

### 2. SessionNotesSection (New)

**File:** `frontend/src/components/SessionNotesSection.tsx`

A self-contained section rendered within `ActivityDetailPage` that manages notes scoped to a specific session.

```typescript
interface SessionNotesSectionProps {
  sessionId: string;
}

export function SessionNotesSection({ sessionId }: SessionNotesSectionProps) {
  const [notes, setNotes] = useState<TrainingNote[]>([]);
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [fetchLoading, setFetchLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Fetch notes filtered by sessionId
    getNotes(sessionId).then(data => setNotes(data));
  }, [sessionId]);

  // handleSubmit creates a note with session_id
  // handleDelete removes a note by ID
  // Renders: heading + form + session-specific notes list
}
```

### 3. Navigation Changes

**File:** `frontend/src/components/Navigation.tsx`

Add a "Training Notes" menu item between "Critical Swim Speed" and "Edit Profile":

```typescript
<button
  className="nav__dropdown-item"
  role="menuitem"
  onClick={() => { setProfileMenuOpen(false); navigate('/notes'); }}
>
  Training Notes
</button>
```

### 4. App.tsx Route Addition

Add a new protected route:

```typescript
<Route
  path="/notes"
  element={
    <ProtectedRoute>
      <TrainingNotesPage />
    </ProtectedRoute>
  }
/>
```

### 5. DashboardPage Changes

**File:** `frontend/src/pages/DashboardPage.tsx`

Remove the `<TrainingNotes />` component and its import from the sidebar section.

### 6. ActivityDetailPage Changes

**File:** `frontend/src/pages/ActivityDetailPage.tsx`

Insert `<SessionNotesSection sessionId={id} />` in the `renderSessionDetail` function, positioned after `TrainingLoadChart`/`CoachingResult`/`TrainingPlanResult` and before `InteractionsPanel`. Only render when `isCurrentUserOwner()` is true and mode is view.

### Interfaces

#### Frontend

```typescript
// Updated TrainingNote interface (notesService.ts)
export interface TrainingNote {
  note_id: string;
  text: string;
  timestamp: string;
  session_id?: string;  // New optional field
}

// Updated API functions
export async function createNote(text: string, sessionId?: string): Promise<TrainingNote>;
export async function getNotes(sessionId?: string): Promise<TrainingNote[]>;
export async function deleteNote(noteId: string): Promise<void>;
```

#### Backend

```python
# Updated notes_service.py signatures
def create_note(user_id: str, text: str, session_id: str | None = None) -> TrainingNote:
    """Create a note with optional session association."""

def get_notes(user_id: str, session_id: str | None = None, limit: int = 200) -> list[TrainingNote]:
    """
    Retrieve notes for a user.
    - If session_id is provided: return only notes with that session_id.
    - If session_id is None: return only notes without a session_id (global).
    """
```

```python
# Updated TrainingNote dataclass
@dataclass
class TrainingNote:
    user_id: str
    note_id: str
    text: str
    timestamp: str
    session_id: str | None = None  # New optional field
```

#### API Contract

**POST /notes**
```json
// Request
{ "text": "Shoulder felt tight", "session_id": "abc-123" }  // session_id optional

// Response 201
{ "note_id": "uuid", "text": "Shoulder felt tight", "timestamp": "2024-...", "session_id": "abc-123" }
```

**GET /notes**
```
GET /notes                    → returns global notes only (no session_id)
GET /notes?session_id=abc-123 → returns notes for that session only
```

```json
// Response 200
{ "notes": [{ "note_id": "...", "text": "...", "timestamp": "...", "session_id": "abc-123" }] }
```

**DELETE /notes/:note_id** — unchanged.

## Data Models

### DynamoDB Table: ai-swim-coach-notes

| Attribute   | Type   | Key  | Description                                |
|-------------|--------|------|--------------------------------------------|
| user_id     | String | PK   | Cognito user ID                            |
| note_id     | String | SK   | UUID v4                                    |
| text        | String |      | Note content (1–500 chars)                 |
| timestamp   | String |      | ISO 8601 UTC creation time                 |
| session_id  | String |      | Optional — links note to a swim session    |

No new GSI is needed. The `get_notes` function already queries by `user_id` and does in-memory filtering/sorting. Adding a `session_id` filter attribute to the in-memory filter is straightforward given the existing pagination pattern that fetches all user notes.

## Error Handling

| Scenario                          | Frontend Behavior                              | Backend Behavior                     |
|-----------------------------------|------------------------------------------------|--------------------------------------|
| Network failure                   | Display error banner with retry guidance       | N/A                                  |
| 401 Unauthorized                  | Redirect to login via ProtectedRoute           | Return 401 response                  |
| 400 Invalid input                 | Display validation error message               | Return 400 with error detail         |
| 500 Server error                  | Display generic error with retry option        | Log error, return 500                |
| Note not found on delete          | Rollback optimistic removal, show error        | Return 404                           |
| session_id not a valid string     | Frontend validates before sending              | Backend ignores invalid, stores null |

## Testing Strategy

### Unit Tests (Example-Based)
- Dashboard renders without TrainingNotes component (Req 1.1, 1.2)
- Navigation dropdown includes "Training Notes" in correct position (Req 2.1, 2.2, 2.3)
- TrainingNotesPage renders explanatory section and form (Req 3.1, 3.2, 3.3)
- TrainingNotesPage allows note deletion (Req 3.5)
- TrainingNotesPage shows error on API failure (Req 3.7)
- Route requires authentication (Req 3.8)
- SessionNotesSection renders in view mode for owner (Req 4.1, 4.2, 4.3)
- SessionNotesSection allows deletion (Req 4.6)
- SessionNotesSection shows error on API failure (Req 4.7)
- SessionNotesSection hidden for non-owner (Req 4.8)
- notesService accepts optional session_id (Req 6.1, 6.3, 6.5)

### Property Tests (100+ iterations)
- Notes ordering is always reverse chronological (Req 3.4, 4.5)
- Global notes filter excludes session notes (Req 3.6, 5.5)
- Session filter returns only matching notes (Req 5.3, 5.4, 4.4)
- session_id round-trip persistence (Req 5.1, 5.2)
- Frontend service correctly passes session_id through (Req 6.2, 6.4)

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Notes are displayed in reverse chronological order

*For any* list of notes (global or session-scoped) returned by the API, the notes SHALL be ordered such that for every adjacent pair (note_i, note_{i+1}), the timestamp of note_i is greater than or equal to the timestamp of note_{i+1}.

**Validates: Requirements 3.4, 4.5**

### Property 2: Global notes query returns only notes without session_id

*For any* set of notes stored for a user (containing a mix of global and session-associated notes), calling the GET endpoint without a session_id parameter SHALL return only notes where session_id is absent or null, and SHALL never include notes with a session_id value.

**Validates: Requirements 3.6, 5.5**

### Property 3: Session-filtered query returns only matching notes

*For any* session_id value and any set of stored notes for a user, calling the GET endpoint with that session_id SHALL return only notes whose stored session_id exactly matches the query parameter, and SHALL never include notes with a different session_id or no session_id.

**Validates: Requirements 5.3, 5.4, 4.4**

### Property 4: Session_id round-trip persistence

*For any* valid note text and any valid session_id string, creating a note with that session_id and then retrieving notes filtered by the same session_id SHALL return a note containing the exact same session_id value that was provided at creation.

**Validates: Requirements 5.1, 5.2**

### Property 5: Frontend service session_id passthrough

*For any* non-empty session_id string, calling `createNote(text, sessionId)` SHALL produce a request body containing a `session_id` field equal to the provided string, and calling `getNotes(sessionId)` SHALL produce a request URL containing `session_id` as a query parameter equal to the provided string.

**Validates: Requirements 6.2, 6.4**
