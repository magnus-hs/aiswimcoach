# Design Document

## Overview

Add friend profile picture avatars to the activity feed's Friends tab. The backend includes `profile_picture_url` in each friend activity response, and the frontend renders a 32×32 circular avatar (image or letter-initial fallback) to the left of the friend's display name.

This is a minimal, inline change — no new components or API endpoints are needed.

## Architecture

### Data Flow

```
DynamoDB Users Table (profile_picture_url)
        │
        ▼
_get_profile_picture_url(friend_id)  ← existing helper
        │
        ▼
get_friends_activities() loop  ← adds field to each dict
        │
        ▼
GET /friends/activities response JSON
        │
        ▼
FriendActivity interface  ← new optional field
        │
        ▼
ActivityFeed.tsx renderFriendsActivities()  ← inline avatar element
```

### Backend Changes (Python)

**File:** `backend/friends_service.py`

In `get_friends_activities()`, add `profile_picture_url` to the dict built for each session inside the `for friend in sharing_friends` loop:

```python
all_sessions.append({
    "session_id": item["session_id"],
    "session_date": item["session_date"],
    "total_distance_meters": int(item.get("total_distance_meters", 0)),
    "total_time_seconds": int(item.get("total_time_seconds", 0)),
    "stroke_type": item.get("stroke_type", ""),
    "average_pace_per_100m": float(item.get("average_pace_per_100m", 0)),
    "swolf_score": int(item.get("swolf_score", 0)),
    "friend_display_name": friend_display_name,
    "friend_user_id": friend_id,
    "profile_picture_url": _get_profile_picture_url(friend_id),
})
```

The `_get_profile_picture_url` helper already exists and returns `str | None`. It queries the Users table for the `profile_picture_url` attribute and returns `None` on absence or error.

**Optimization note:** The helper is called once per session, but a friend may have many sessions. To avoid repeated DynamoDB reads, cache the URL per friend_id within the loop:

```python
# Before the sessions loop
profile_pic_cache: dict[str, str | None] = {}

for friend in sharing_friends:
    friend_id = friend["user_id"]
    if friend_id not in profile_pic_cache:
        profile_pic_cache[friend_id] = _get_profile_picture_url(friend_id)
    profile_picture_url = profile_pic_cache[friend_id]
    # ... use profile_picture_url in each session dict
```

### Frontend Interface Change (TypeScript)

**File:** `frontend/src/api/friendsService.ts`

Add the field to the `FriendActivity` interface:

```typescript
export interface FriendActivity {
  session_id: string;
  session_date: string;
  total_distance_meters: number;
  total_time_seconds: number;
  stroke_type: string;
  average_pace_per_100m: number;
  swolf_score: number;
  friend_display_name: string;
  friend_user_id: string;
  profile_picture_url?: string | null;
}
```

### Frontend UI Change (React/TSX)

**File:** `frontend/src/components/ActivityFeed.tsx`

In `renderFriendsActivities()`, replace the plain `<span>` with an avatar + name row:

```tsx
{sortedFriendsActivities.map((activity) => (
  <div key={activity.session_id} className="activity-feed__friend-card">
    <div className="activity-feed__friend-header">
      {activity.profile_picture_url ? (
        <img
          src={activity.profile_picture_url}
          alt={activity.friend_display_name}
          className="activity-feed__friend-avatar"
          onError={(e) => {
            // Replace broken image with letter-initial fallback
            const target = e.currentTarget;
            const parent = target.parentElement;
            if (parent) {
              const placeholder = document.createElement('span');
              placeholder.className = 'activity-feed__friend-avatar activity-feed__friend-avatar--placeholder';
              placeholder.textContent = activity.friend_display_name.charAt(0).toUpperCase();
              placeholder.setAttribute('aria-label', activity.friend_display_name);
              parent.replaceChild(placeholder, target);
            }
          }}
        />
      ) : (
        <span
          className="activity-feed__friend-avatar activity-feed__friend-avatar--placeholder"
          aria-label={activity.friend_display_name}
        >
          {activity.friend_display_name.charAt(0).toUpperCase()}
        </span>
      )}
      <span className="activity-feed__friend-name">{activity.friend_display_name}</span>
    </div>
    <ActivityCard ... />
  </div>
))}
```

### CSS Additions

**File:** `frontend/src/components/ActivityFeed.css`

```css
/* Friend avatar */
.activity-feed__friend-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding-left: var(--space-2);
}

.activity-feed__friend-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.activity-feed__friend-avatar--placeholder {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-primary);
  color: var(--color-surface);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
}
```

## Components and Interfaces

### Backend

| Component | File | Responsibility |
|-----------|------|----------------|
| `get_friends_activities()` | `backend/friends_service.py` | Adds `profile_picture_url` to each session dict |
| `_get_profile_picture_url()` | `backend/friends_service.py` | Existing helper; fetches URL from Users table |

### Frontend

| Component | File | Responsibility |
|-----------|------|----------------|
| `FriendActivity` interface | `frontend/src/api/friendsService.ts` | Adds optional `profile_picture_url` field |
| `ActivityFeed` (renderFriendsActivities) | `frontend/src/components/ActivityFeed.tsx` | Renders inline avatar before friend name |
| Avatar CSS classes | `frontend/src/components/ActivityFeed.css` | Styles 32×32 circular avatar + placeholder |

### Interfaces

**Backend response shape** (per activity in `GET /friends/activities`):

```typescript
{
  session_id: string;
  session_date: string;
  total_distance_meters: number;
  total_time_seconds: number;
  stroke_type: string;
  average_pace_per_100m: number;
  swolf_score: number;
  friend_display_name: string;
  friend_user_id: string;
  profile_picture_url: string | null;  // NEW
}
```

**Avatar rendering interface** (inline in ActivityFeed.tsx):

```typescript
// Determined by: activity.profile_picture_url
// If truthy → <img src={url} alt={name} class="...friend-avatar" onError={fallback}>
// If falsy  → <span class="...friend-avatar ...--placeholder" aria-label={name}>{initial}</span>
```

## Data Models

No new tables or indexes are required. The existing `Users` table already stores `profile_picture_url` per user. The change reads this field via the existing `_get_profile_picture_url` helper and passes it through the API response.

**Existing schema (Users table):**

| Attribute | Type | Notes |
|-----------|------|-------|
| `user_id` | String (PK) | Partition key |
| `profile_picture_url` | String (optional) | S3 URL or absent |

## Error Handling

| Scenario | Behavior |
|----------|----------|
| `_get_profile_picture_url` throws `ClientError` | Returns `None`; field is `null` in JSON |
| Image URL returns 404 or fails to load | `onError` handler replaces `<img>` with letter-initial placeholder |
| `friend_display_name` is empty string | `charAt(0)` returns `""`, placeholder shows blank (edge case; display names are required elsewhere) |

## Testing Strategy

### Unit Tests (Example-based)
- Avatar renders at 32×32 pixels with circular border-radius (Req 2.3)
- Image `onError` replaces broken image with letter-initial placeholder (Req 2.5)

### Property Tests (fast-check / Hypothesis)
- Backend: For random friend profiles (with/without picture URL), `get_friends_activities` always returns matching `profile_picture_url` values (Property 1)
- Frontend: For random `FriendActivity` objects, rendering produces correct avatar element (Properties 2, 3, 4)

### Integration Tests
- End-to-end: Friends tab loads and displays avatars for friends with pictures and placeholders for those without

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Backend profile_picture_url matches stored value

*For any* friend activity returned by `get_friends_activities()`, the `profile_picture_url` field SHALL equal the value returned by `_get_profile_picture_url(friend_user_id)` — either a valid URL string or `None`.

**Validates: Requirements 1.1, 1.2**

### Property 2: Avatar renders image when URL is present

*For any* `FriendActivity` with a non-null, non-empty `profile_picture_url`, rendering the friend activity card SHALL produce an `<img>` element whose `src` attribute equals that URL.

**Validates: Requirements 2.1**

### Property 3: Avatar renders letter-initial placeholder when URL is absent

*For any* `FriendActivity` with a null or undefined `profile_picture_url` and any non-empty `friend_display_name`, rendering the friend activity card SHALL produce a placeholder element whose text content equals the first character of `friend_display_name` uppercased.

**Validates: Requirements 2.2**

### Property 4: Avatar alt text matches display name

*For any* `FriendActivity` with a non-empty `friend_display_name`, the rendered avatar element (whether `<img>` or placeholder) SHALL have an accessible name equal to `friend_display_name`.

**Validates: Requirements 2.4**
