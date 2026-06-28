# Design Document: UI Update

## Overview

This document describes the frontend redesign of the AI Swim Coach application, transforming it into a polished, Strava-inspired professional UI. The redesign introduces a design token system, a new three-route structure (Dashboard, Activity Detail, Training Plans), a sidebar-based dashboard layout, and restyled components emphasizing large bold metrics and muted professional tones.

## Architecture

The UI update transforms the existing functional interface into a Strava-inspired professional layout using a design token system, new route structure, and restyled components. The architecture follows a top-down approach:

1. **Design Token Layer** — CSS custom properties on `:root` providing the visual foundation
2. **Layout Layer** — New page shells (Dashboard, ActivityDetail, TrainingPlans) with responsive behavior
3. **Component Layer** — Restyled existing components consuming tokens, plus new components (ActivityCard, Sidebar, ProfileModal)
4. **Routing Layer** — Simplified three-route structure with backward-compatible redirects

No backend changes are required. The frontend consumes the same API endpoints with the same data shapes.

## Components and Interfaces

### New Components

| Component | Responsibility |
|-----------|---------------|
| `Dashboard` | Page shell: two-column layout with Sidebar + ActivityFeed |
| `Sidebar` | Profile summary, aggregate stats, streak display |
| `ActivityFeed` | Chronological list of ActivityCards with loading/empty states |
| `ActivityCard` | Clickable card displaying session metrics |
| `ActivityDetailPage` | Unified view/upload page replacing SessionDetailPage + UploadPage |
| `TrainingPlansPage` | Dedicated page for plan creation and display |
| `ProfileModal` | Accessible modal overlay with focus trap for profile editing |
| `Navigation` | Top header bar with route links and active indicator |

### Modified Components

| Component | Changes |
|-----------|---------|
| `SessionSummary` | Replace hardcoded colors/sizes with token variables; add `--large` value class |
| `SplitsTable` | Token-based alternating row colors |
| `HRZonesCard` | Token-based card styling |
| `CoachingResult` | Token-based typography and spacing |
| `AbilityAssessmentCard` | Token-based card styling |
| `CalendarView` | Token-based grid/cell styling |
| `ProgressGraph` | Token-based container styling |
| `TrainingGoalForm` | Token-based form inputs and buttons |
| `TrainingPlanResult` | Token-based section layout |
| `Header` | Replaced by new `Navigation` component |

### Removed Components/Pages

| Component | Reason |
|-----------|--------|
| `UploadPage` | Merged into `ActivityDetailPage` |
| `HistoryPage` | Replaced by `Dashboard` with `ActivityFeed` |

## Data Models

### Design Token System

All tokens are defined as CSS custom properties on `:root` in a dedicated `tokens.css` file imported before all other styles.

```css
/* tokens.css */
:root {
  /* Colors — Desaturated professional blue palette */
  --color-primary: hsl(215, 35%, 45%);
  --color-primary-light: hsl(215, 30%, 60%);
  --color-primary-dark: hsl(215, 40%, 30%);
  --color-secondary: hsl(200, 25%, 50%);

  /* Neutral grays (7 shades) */
  --color-gray-50: hsl(210, 20%, 98%);
  --color-gray-100: hsl(210, 16%, 95%);
  --color-gray-200: hsl(210, 14%, 89%);
  --color-gray-300: hsl(210, 12%, 78%);
  --color-gray-400: hsl(210, 10%, 58%);
  --color-gray-500: hsl(210, 8%, 45%);
  --color-gray-600: hsl(210, 12%, 32%);
  --color-gray-700: hsl(210, 15%, 22%);
  --color-gray-800: hsl(210, 18%, 14%);
  --color-gray-900: hsl(210, 20%, 8%);

  /* Semantic colors */
  --color-bg: var(--color-gray-50);
  --color-surface: #ffffff;
  --color-text: var(--color-gray-800);
  --color-text-muted: var(--color-gray-500);
  --color-error: hsl(0, 60%, 50%);
  --color-success: hsl(145, 50%, 38%);

  /* Typography */
  --font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI',
    Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  --font-size-xs: 0.75rem;
  --font-size-sm: 0.875rem;
  --font-size-base: 1rem;
  --font-size-lg: 1.125rem;
  --font-size-xl: 1.5rem;
  --font-size-2xl: 1.75rem;
  --font-size-3xl: 2rem;
  --font-weight-regular: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;
  --line-height-tight: 1.2;
  --line-height-normal: 1.5;
  --line-height-relaxed: 1.75;

  /* Spacing (8-step scale) */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-5: 1.5rem;
  --space-6: 2rem;
  --space-7: 3rem;
  --space-8: 4rem;

  /* Border radius */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;

  /* Shadows */
  --shadow-subtle: 0 1px 2px rgba(0, 0, 0, 0.06);
  --shadow-card: 0 2px 8px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.04);
  --shadow-elevated: 0 8px 24px rgba(0, 0, 0, 0.12), 0 2px 8px rgba(0, 0, 0, 0.06);
}
```

## Interfaces

### Route Configuration

```typescript
// App.tsx route structure
interface RouteConfig {
  path: string;
  element: React.ReactNode;
  protected: boolean;
}

const routes: RouteConfig[] = [
  { path: '/', element: <Dashboard />, protected: true },
  { path: '/activity/:id', element: <ActivityDetailPage />, protected: true },
  { path: '/activity/new', element: <ActivityDetailPage mode="upload" />, protected: true },
  { path: '/plans', element: <TrainingPlansPage />, protected: true },
  { path: '/session/:id', element: <RedirectToActivity />, protected: true },
  { path: '/login', element: <LoginPage />, protected: false },
  { path: '/register', element: <RegisterPage />, protected: false },
];
```

### ActivityCard Props

```typescript
interface ActivityCardProps {
  sessionId: string;
  sessionDate: string;
  strokeType: string;
  totalDistanceMeters: number;
  totalTimeSeconds: number;
  averagePacePer100m: number;
  swolfScore: number;
}
```

### Sidebar Props

```typescript
interface SidebarProps {
  profilePictureUrl: string | null;
  displayName: string;
  memberSince: string;
  totalSessions: number;
  totalDistanceMeters: number;
  currentStreakDays: number;
}
```

### ProfileModal Props

```typescript
interface ProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  triggerRef: React.RefObject<HTMLElement>;
}
```

### ActivityDetailPage Props

```typescript
interface ActivityDetailPageProps {
  mode?: 'view' | 'upload';
}
```

## Data Flow

### Dashboard Data Loading

```
Dashboard (mount)
  ├── GET /auth/user → { email, profile_picture_url, created_at }
  ├── GET /sessions → SessionSummary[]
  └── Compute aggregates:
        totalSessions = sessions.length
        totalDistance = sum(sessions.map(s => s.total_distance_meters))
        streak = computeStreak(sessions.map(s => s.session_date))
```

### Streak Computation

```typescript
/**
 * Compute consecutive-day training streak from session dates.
 * A streak counts backward from today, incrementing for each
 * consecutive calendar day that has at least one session.
 */
function computeStreak(sessionDates: string[]): number {
  if (sessionDates.length === 0) return 0;

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const uniqueDays = new Set(
    sessionDates.map(d => {
      const date = new Date(d);
      date.setHours(0, 0, 0, 0);
      return date.getTime();
    })
  );

  let streak = 0;
  let checkDate = new Date(today);

  while (uniqueDays.has(checkDate.getTime())) {
    streak++;
    checkDate.setDate(checkDate.getDate() - 1);
  }

  return streak;
}
```

### Route Redirect Logic

```typescript
// /session/:id → /activity/:id redirect component
function RedirectToActivity() {
  const { id } = useParams<{ id: string }>();
  return <Navigate to={`/activity/${id}`} replace />;
}
```

## Component Structure

### Dashboard Layout

```
<Dashboard>
  <div className="dashboard">
    <aside className="dashboard__sidebar">
      <Sidebar {...sidebarProps} />
    </aside>
    <section className="dashboard__feed">
      <div className="dashboard__feed-header">
        <h1>Activity Feed</h1>
        <Link to="/activity/new" className="dashboard__new-activity-btn">
          + New Activity
        </Link>
      </div>
      <ActivityFeed sessions={sessions} loading={loading} error={error} />
    </section>
  </div>
</Dashboard>
```

### Navigation Structure

```
<Navigation>
  <header className="nav">
    <div className="nav__left">
      <span className="nav__logo">🏊</span>
      <span className="nav__app-name">AI Swim Coach</span>
    </div>
    <nav className="nav__links">
      <NavLink to="/" className={activeClass}>Dashboard</NavLink>
      <NavLink to="/plans" className={activeClass}>Training Plans</NavLink>
      <button onClick={openProfileModal} className={activeClass}>Profile</button>
    </nav>
  </header>
</Navigation>
```

### ProfileModal Accessibility

```typescript
// Focus trap implementation
function ProfileModal({ isOpen, onClose, triggerRef }: ProfileModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;

    const focusableElements = modalRef.current?.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    
    const firstFocusable = focusableElements?.[0];
    const lastFocusable = focusableElements?.[focusableElements.length - 1];

    firstFocusable?.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
        triggerRef.current?.focus();
        return;
      }
      if (e.key === 'Tab') {
        if (e.shiftKey && document.activeElement === firstFocusable) {
          e.preventDefault();
          lastFocusable?.focus();
        } else if (!e.shiftKey && document.activeElement === lastFocusable) {
          e.preventDefault();
          firstFocusable?.focus();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose, triggerRef]);

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        ref={modalRef}
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label="Profile settings"
        onClick={e => e.stopPropagation()}
      >
        <button className="modal__close" onClick={onClose} aria-label="Close">×</button>
        {/* Profile content */}
      </div>
    </div>
  );
}
```

## Responsive Strategy

```css
/* Dashboard responsive breakpoint */
.dashboard {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: var(--space-6);
  max-width: 72rem;
  margin: 0 auto;
  padding: var(--space-6);
}

@media (max-width: 767px) {
  .dashboard {
    grid-template-columns: 1fr;
  }
}

/* Activity Detail max-width constraint */
.activity-detail {
  max-width: 48rem;
  margin: 0 auto;
  padding: var(--space-6) var(--space-4);
}

/* Navigation compact mode */
@media (max-width: 767px) {
  .nav__links {
    gap: var(--space-2);
  }
  .nav__links a,
  .nav__links button {
    font-size: var(--font-size-sm);
    padding: var(--space-2);
  }
}
```

## File Structure

```
frontend/src/
├── tokens.css                         (NEW - design token definitions)
├── App.tsx                            (MODIFIED - new route config)
├── index.css                          (MODIFIED - uses tokens, removes hardcoded values)
├── pages/
│   ├── DashboardPage.tsx              (NEW)
│   ├── ActivityDetailPage.tsx         (NEW - replaces SessionDetailPage + UploadPage)
│   ├── TrainingPlansPage.tsx          (NEW)
│   ├── LoginPage.tsx                  (unchanged)
│   └── RegisterPage.tsx               (unchanged)
├── components/
│   ├── Navigation.tsx                 (NEW - replaces Header)
│   ├── Navigation.css                 (NEW)
│   ├── Sidebar.tsx                    (NEW)
│   ├── Sidebar.css                    (NEW)
│   ├── ActivityFeed.tsx               (NEW)
│   ├── ActivityFeed.css               (NEW)
│   ├── ActivityCard.tsx               (NEW)
│   ├── ActivityCard.css               (NEW)
│   ├── ProfileModal.tsx               (NEW)
│   ├── ProfileModal.css               (NEW)
│   ├── SessionSummary.tsx             (MODIFIED)
│   ├── SplitsTable.tsx                (MODIFIED)
│   ├── HRZonesCard.css                (MODIFIED)
│   ├── CoachingResult.css             (MODIFIED)
│   ├── AbilityAssessmentCard.css      (MODIFIED)
│   ├── CalendarView.css               (MODIFIED)
│   ├── ProgressGraph.css              (MODIFIED)
│   ├── TrainingGoalForm.tsx           (MODIFIED - token classes)
│   └── TrainingPlanResult.tsx         (MODIFIED - token classes)
├── utils/
│   ├── computeStreak.ts              (NEW)
│   └── validateFile.ts               (unchanged)
└── hooks/
    ├── useAuth.tsx                    (unchanged)
    └── index.ts                       (unchanged)
```

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Dashboard fetch fails | Show ErrorBanner with retry button in feed area; Sidebar shows placeholder |
| Activity detail fetch fails | Show ErrorBanner with back link to Dashboard |
| Upload fails | Show ErrorBanner within upload section with retry |
| Profile fetch fails in modal | Show inline error message within modal |
| Empty sessions list | Show empty state with CTA to upload first activity |

## Loading States

| Page | Loading Behavior |
|------|-----------------|
| Dashboard | Skeleton cards in ActivityFeed area (3 placeholder cards) |
| Activity Detail | Centered LoadingIndicator spinner |
| Training Plans | Disabled submit button + spinner during generation |



## Testing Strategy

- **Unit tests (vitest + @testing-library/react):** Verify specific component rendering, route behavior, modal interactions, and loading/empty/error state handling. Focus on concrete examples and edge cases.
- **Property tests (fast-check + vitest):** Verify universal properties — route protection, session redirect, aggregate computation, feed ordering, card completeness, and token contrast ratios.
- **Snapshot tests:** Capture rendered component output to catch unintended visual regressions in restyled components.
- **Accessibility checks:** Verify focus trap behavior, ARIA attributes, and keyboard navigation in the ProfileModal.

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Protected route redirect

*For any* protected route path (/, /activity/:id, /plans), when an unauthenticated user navigates to that path, the application SHALL redirect to /login.

**Validates: Requirements 2.4**

### Property 2: Session path backward compatibility

*For any* valid session ID string, navigating to `/session/{id}` SHALL result in a redirect to `/activity/{id}` preserving the same ID.

**Validates: Requirements 2.6**

### Property 3: Sidebar aggregate stats correctness

*For any* list of session summaries, the Sidebar SHALL display `totalSessions` equal to the list length and `totalDistance` equal to the sum of all `total_distance_meters` values in the list.

**Validates: Requirements 3.3**

### Property 4: Activity feed ordering

*For any* non-empty list of session summaries with distinct dates, the Activity_Feed SHALL render Activity_Cards in strictly descending order by session date.

**Validates: Requirements 3.5**

### Property 5: Activity card completeness and navigation

*For any* valid session summary data, the Activity_Card SHALL render the session date, stroke type, total distance, total time, average pace, and SWOLF score, AND clicking the card SHALL produce a navigation event to `/activity/{sessionId}`.

**Validates: Requirements 4.1, 4.4**

### Property 6: Navigation active indicator

*For any* authenticated route path in the set {/, /plans, /activity/*}, the Navigation component SHALL apply the active visual indicator to exactly one link — the one whose path matches the current route.

**Validates: Requirements 7.2**

### Property 7: Design token contrast compliance

*For any* pair of (text-color token, background-color token) that are used together in the application, the computed contrast ratio SHALL be at least 4.5:1 for normal text sizes and at least 3:1 for large text sizes (≥ 1.5rem bold or ≥ 1.75rem regular).

**Validates: Requirements 9.5**
