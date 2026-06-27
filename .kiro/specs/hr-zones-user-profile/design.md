# Design Document: Heart Rate Zones, User Profile, and Authentication

## Overview

This feature extends the AI Swim Coach application with user authentication, profile management, heart rate zone analysis, and session history tracking. The design introduces three new backend modules (`auth`, `hr_zones`, `session_history`), three new DynamoDB tables (`Users`, `UserProfiles`, `Sessions`), one S3 bucket for profile pictures, and comprehensive frontend components for authentication, profile management, and historical data visualization.

**Key Design Decisions:**

1. **JWT-based authentication**: Stateless authentication using JWT tokens with 7-day expiration, allowing horizontal scaling without session management infrastructure
2. **Separation of Users and UserProfiles**: `Users` table handles authentication credentials; `UserProfiles` table stores optional demographic data, enabling core upload functionality without requiring profile completion
3. **Best-effort session storage**: Session persistence failures do not block the primary upload workflow, ensuring coaching results are always delivered
4. **Client-side routing with protected routes**: React Router handles navigation with authentication guards, providing a SPA experience similar to Strava/Garmin
5. **HR zones as optional enhancement**: HR zone calculation requires user age from profile; system gracefully omits zones when profile is incomplete

## Architecture

### Backend Architecture

**New Modules:**

```
backend/
├── auth.py              # User registration, login, JWT generation/verification
├── hr_zones.py          # HR zone calculation from heart rate samples
├── session_history.py   # Session CRUD operations (create, retrieve)
├── profile_manager.py   # User profile CRUD operations
└── middleware.py        # JWT authentication middleware
```

**Existing Modules (Modified):**

- `handler.py`: Add routes for `/auth/*`, `/profile`, `/sessions`, `/sessions/:id`
- `models.py`: Add dataclasses for `UserProfile`, `AbilityAssessment`, `HRZonesData`, `Session`

**New DynamoDB Tables:**

1. **Users** table:
   - Partition key: `user_id` (String, UUID v4)
   - GSI: `email-index` (partition key: `email`)
   - Attributes: `user_id`, `email`, `hashed_password`, `profile_picture_url`, `created_at`

2. **UserProfiles** table:
   - Partition key: `user_id` (String, UUID v4)
   - Attributes: `user_id`, `age`, `nationality`, `locality`, `ability_level`, `updated_at`

3. **Sessions** table:
   - Partition key: `user_id` (String, UUID v4)
   - Sort key: `session_date` (String, ISO 8601 format)
   - GSI: `session_id-index` (partition key: `session_id`)
   - Attributes: `session_id`, `user_id`, `session_date`, `pool_length_meters`, `total_distance_meters`, `total_time_seconds`, `stroke_type`, `average_pace_per_100m`, `swolf_score`, `stroke_rate`, `uploaded_at`, `s3_key`, `hr_zones` (optional), `ability_assessment` (optional)

**New S3 Bucket:**

- Bucket name: `ai-swim-coach-profile-pictures`
- Public read access for all objects
- Object key format: `{user_id}_{timestamp}.{extension}`

**Environment Variables:**

- `JWT_SECRET`: Secret key for signing JWT tokens (256-bit minimum)
- `PROFILE_PICTURES_BUCKET`: S3 bucket name for profile pictures
- `USERS_TABLE`: DynamoDB table name for users
- `PROFILES_TABLE`: DynamoDB table name for user profiles
- `SESSIONS_TABLE`: DynamoDB table name for sessions

### Frontend Architecture

**New Components:**

```
frontend/src/
├── components/
│   ├── Login.tsx              # Login form
│   ├── Register.tsx           # Registration form
│   ├── ProfilePage.tsx        # User profile form with picture upload
│   ├── HistoryPage.tsx        # Session history with calendar and graph
│   ├── CalendarView.tsx       # Monthly calendar with session indicators
│   ├── ProgressGraph.tsx      # Line chart showing distance over time
│   ├── SessionDetail.tsx      # Detailed session view (reuses upload result layout)
│   ├── HRZonesCard.tsx        # Heart rate zones visualization
│   ├── AbilityAssessmentCard.tsx  # Ability assessment display
│   ├── ProtectedRoute.tsx     # Authentication guard for routes
│   └── Header.tsx             # App header with navigation and user avatar
├── hooks/
│   └── useAuth.tsx            # Authentication state management hook
└── services/
    ├── authService.ts         # API calls for authentication
    ├── profileService.ts      # API calls for profile management
    └── sessionService.ts      # API calls for session history
```

**Routing Structure:**

```
/ (redirect to /login or /upload based on auth state)
/login
/register
/upload (protected)
/profile (protected)
/history (protected)
/session/:sessionId (protected)
```

## Components and Interfaces

### Backend Components

#### 1. Authentication Module (`auth.py`)

**Functions:**

```python
def register_user(email: str, password: str) -> dict:
    """Register a new user with email and password.
    
    Args:
        email: Valid email address
        password: Plain text password (min 8 characters)
    
    Returns:
        dict with user_id and email
    
    Raises:
        ValueError: If email invalid or password too short
        ConflictError: If email already exists
    """

def login_user(email: str, password: str) -> dict:
    """Authenticate user and generate JWT token.
    
    Args:
        email: Registered email address
        password: Plain text password
    
    Returns:
        dict with token, user_id, and email
    
    Raises:
        AuthenticationError: If credentials invalid
    """

def verify_token(token: str) -> dict:
    """Verify JWT token and extract claims.
    
    Args:
        token: JWT token string
    
    Returns:
        dict with user_id and email
    
    Raises:
        AuthenticationError: If token invalid or expired
    """

def hash_password(password: str) -> str:
    """Hash password using bcrypt with cost factor 12.
    
    Args:
        password: Plain text password
    
    Returns:
        Bcrypt hashed password string
    """

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against bcrypt hash.
    
    Args:
        password: Plain text password
        hashed: Bcrypt hashed password
    
    Returns:
        True if password matches, False otherwise
    """
```

**DynamoDB Operations:**

- `create_user(user_id, email, hashed_password)`: Insert into Users table
- `get_user_by_email(email)`: Query email-index GSI
- `get_user_by_id(user_id)`: Get item from Users table

#### 2. Heart Rate Zones Module (`hr_zones.py`)

**Functions:**

```python
def extract_heart_rate_data(fit_bytes: bytes) -> list[tuple[datetime, int]]:
    """Extract heart rate samples from FIT file.
    
    Args:
        fit_bytes: Raw FIT file bytes
    
    Returns:
        List of (timestamp, heart_rate_bpm) tuples, filtered for valid values
    
    Raises:
        FitParseError: If FIT file cannot be parsed
    """

def calculate_max_hr(age: int) -> int:
    """Calculate maximum heart rate from age.
    
    Args:
        age: User age (1-120)
    
    Returns:
        Max HR as 220 - age
    
    Raises:
        ValueError: If age outside valid range
    """

def calculate_zone_boundaries(max_hr: int) -> dict[int, tuple[int, int]]:
    """Calculate HR zone boundaries.
    
    Args:
        max_hr: Maximum heart rate
    
    Returns:
        dict mapping zone number (1-5) to (lower_bound, upper_bound) tuples
    """

def calculate_hr_zones(
    hr_samples: list[tuple[datetime, int]],
    age: int
) -> HRZonesData:
    """Calculate time and percentage in each HR zone.
    
    Args:
        hr_samples: List of (timestamp, hr_bpm) tuples
        age: User age for max HR calculation
    
    Returns:
        HRZonesData with time and percentage per zone
    
    Raises:
        ValueError: If no valid HR samples or invalid age
    """
```

#### 3. Session History Module (`session_history.py`)

**Functions:**

```python
def save_session(
    user_id: str,
    session_info: SessionInfo,
    metrics: Metrics,
    s3_key: str,
    hr_zones: HRZonesData | None = None,
    ability_assessment: AbilityAssessment | None = None
) -> str:
    """Persist session to Sessions table.
    
    Args:
        user_id: User identifier
        session_info: Session metadata
        metrics: Calculated metrics
        s3_key: S3 key for FIT file
        hr_zones: Optional HR zones data
        ability_assessment: Optional ability assessment
    
    Returns:
        session_id (UUID v4)
    
    Raises:
        StorageError: If DynamoDB write fails
    """

def get_user_sessions(
    user_id: str,
    start_date: str | None = None,
    end_date: str | None = None
) -> list[Session]:
    """Retrieve user's session history.
    
    Args:
        user_id: User identifier
        start_date: Optional ISO 8601 date filter (inclusive)
        end_date: Optional ISO 8601 date filter (inclusive)
    
    Returns:
        List of Session objects ordered by session_date descending
    
    Raises:
        StorageError: If DynamoDB query fails
    """

def get_session_by_id(session_id: str) -> Session:
    """Retrieve single session by ID.
    
    Args:
        session_id: Session identifier (UUID v4)
    
    Returns:
        Session object with full details
    
    Raises:
        NotFoundError: If session doesn't exist
        StorageError: If DynamoDB query fails
    """
```

#### 4. Profile Manager Module (`profile_manager.py`)

**Functions:**

```python
def save_profile(user_id: str, profile: UserProfile) -> None:
    """Persist or update user profile.
    
    Args:
        user_id: User identifier
        profile: UserProfile object
    
    Raises:
        StorageError: If DynamoDB write fails
    """

def get_profile(user_id: str) -> UserProfile | None:
    """Retrieve user profile.
    
    Args:
        user_id: User identifier
    
    Returns:
        UserProfile object or None if profile doesn't exist
    
    Raises:
        StorageError: If DynamoDB query fails
    """

def upload_profile_picture(
    user_id: str,
    image_bytes: bytes,
    content_type: str
) -> str:
    """Upload profile picture to S3 and update user record.
    
    Args:
        user_id: User identifier
        image_bytes: Image file bytes
        content_type: MIME type (image/jpeg, image/png, image/gif)
    
    Returns:
        S3 URL of uploaded image
    
    Raises:
        ValueError: If image invalid or too large
        StorageError: If S3 upload or DynamoDB update fails
    """
```

#### 5. Middleware Module (`middleware.py`)

**Functions:**

```python
def require_auth(handler_func):
    """Decorator to enforce JWT authentication on Lambda handlers.
    
    Extracts and verifies JWT from Authorization header.
    Injects user_id and email into event['auth_context'].
    
    Returns HTTP 401 if token missing, invalid, or expired.
    """
```

### Data Models

**New Models in `models.py`:**

```python
@dataclass
class UserProfile:
    """User demographic and ability profile."""
    age: int
    nationality: str  # max 100 chars
    locality: str     # max 100 chars
    ability_level: str  # one of: beginner, intermediate, advanced, elite

@dataclass
class AbilityAssessment:
    """AI-generated competitive ability assessment."""
    percentile_estimate: str   # max 100 chars
    local_ranking: str         # max 200 chars
    national_ranking: str      # max 200 chars
    competitive_analysis: str  # max 800 chars

@dataclass
class HRZonesData:
    """Heart rate zone distribution."""
    zone_1_seconds: int
    zone_2_seconds: int
    zone_3_seconds: int
    zone_4_seconds: int
    zone_5_seconds: int
    zone_1_percent: float  # one decimal place
    zone_2_percent: float
    zone_3_percent: float
    zone_4_percent: float
    zone_5_percent: float
    max_hr: int
    zone_boundaries: dict[int, tuple[int, int]]  # zone -> (lower, upper)

@dataclass
class Session:
    """Complete session record."""
    session_id: str
    user_id: str
    session_date: str  # ISO 8601
    pool_length_meters: int
    total_distance_meters: int
    total_time_seconds: int
    stroke_type: str
    average_pace_per_100m: float
    swolf_score: int
    stroke_rate: float
    uploaded_at: str  # ISO 8601
    s3_key: str
    hr_zones: HRZonesData | None = None
    ability_assessment: AbilityAssessment | None = None
```

**Modified Models:**

```python
@dataclass
class FullResponse:
    """Extended API response with optional HR zones and ability assessment."""
    session: SessionInfo
    splits: list[LengthSplit]
    metrics: Metrics
    coaching: CoachingResponse
    hr_zones: HRZonesData | None = None
    ability_assessment: AbilityAssessment | None = None
    session_id: str | None = None  # returned after session saved

@dataclass
class TrainingPlan:
    """Extended with goal likelihood assessment."""
    session_title: str
    warm_up: list[str]
    main_set: list[str]
    cool_down: list[str]
    total_distance: int
    focus_notes: str
    goal_likelihood: str  # max 300 chars
```

### Frontend Components

#### 1. Authentication Components

**Login.tsx**

- Email and password form
- Client-side validation (email format, password length)
- Calls `authService.login()` on submit
- Stores JWT token in localStorage
- Redirects to `/upload` on success
- Displays error messages from backend

**Register.tsx**

- Email, password, confirm password form
- Client-side validation (email format, password match, min 8 chars)
- Calls `authService.register()` on submit
- Redirects to `/login` on success with "Registration successful" message
- Displays error messages from backend

**ProtectedRoute.tsx**

- Wrapper component for authenticated routes
- Checks for `auth_token` in localStorage on mount
- Calls `authService.verifyToken()` to validate token
- Redirects to `/login` if no token or verification fails
- Renders child components if authenticated

#### 2. Profile Components

**ProfilePage.tsx**

- User profile form: age (number input), nationality (text), locality (text), ability level (dropdown)
- Profile picture upload with preview
- Client-side validation (age 10-100, ability level required)
- Calls `profileService.saveProfile()` and `profileService.uploadProfilePicture()`
- Displays current profile data on load
- Success/error message display

#### 3. History Components

**HistoryPage.tsx**

- Container component managing state for calendar, graph, and session list
- Fetches session history on mount: `sessionService.getUserSessions()`
- Passes data to CalendarView and ProgressGraph child components
- Displays session list below calendar when date selected
- Empty state message when no sessions exist

**CalendarView.tsx**

- Monthly calendar grid (7 columns x 5-6 rows)
- Previous/next month navigation
- Highlights current date
- Marks dates with sessions using colored dots
- Shows total distance per day
- onClick handler for date selection

**ProgressGraph.tsx**

- Line chart using recharts library
- X-axis: dates, Y-axis: distance in meters
- Time range selector: Last 7/30/90 Days, All Time
- Hover tooltip showing date and distance
- Blue color scheme matching app design

**SessionDetail.tsx**

- Reuses layout from upload results page
- Fetches session by ID: `sessionService.getSessionById(sessionId)`
- Displays: session summary, splits table, HR zones card (if available), coaching tips, ability assessment (if available), training plan (if available)
- "Back to History" navigation link

#### 4. Visualization Components

**HRZonesCard.tsx**

- Displays HR zones data in card layout
- Zone list: zone number, HR range, time (seconds), percentage
- Horizontal bar chart with zone colors:
  - Zone 1: light blue (#60a5fa)
  - Zone 2: green (#34d399)
  - Zone 3: yellow (#fbbf24)
  - Zone 4: orange (#fb923c)
  - Zone 5: red (#ef4444)
- Handles zero-time zones (display with 0 width)
- Empty state: "Heart rate data was not found in your FIT file"

**AbilityAssessmentCard.tsx**

- Card layout with four sections:
  - Percentile Ranking
  - Local Ranking
  - National Ranking
  - Competitive Analysis
- Only rendered when ability assessment exists in response

#### 5. Layout Components

**Header.tsx**

- Left: App logo
- Center: Navigation links (Upload, History, Profile)
- Right: User email, profile avatar (40px circular), logout button
- Profile avatar click navigates to `/profile`
- Logout button clears localStorage and redirects to `/login`
- Default avatar icon when no profile picture exists

## Error Handling

### Backend Error Responses

**Authentication Errors:**

- `401 Unauthorized`: Invalid credentials, missing token, expired token
- `409 Conflict`: Email already registered
- Format: `{"error": "descriptive message"}`

**Validation Errors:**

- `400 Bad Request`: Invalid input (age out of range, malformed email, etc.)
- `413 Payload Too Large`: Profile picture exceeds 2 MB
- `422 Unprocessable Entity`: FIT file parse error, missing metrics, HR zone calculation failure

**Storage Errors:**

- `404 Not Found`: Profile or session doesn't exist
- `500 Internal Server Error`: DynamoDB or S3 operation failure
- `502 Bad Gateway`: Bedrock invocation failure

### Frontend Error Handling

**Authentication Flow:**

- Login/register failures display error message from backend
- Token verification failures clear localStorage and redirect to `/login`
- Network errors show generic "Service unavailable" message

**Upload Flow:**

- FIT parse errors display specific message from backend
- HR zone calculation failures show message but still display coaching results
- Session save failures logged but don't block response

**Profile and History:**

- Profile save failures display error message
- Profile picture upload failures display specific error (format, size)
- Session history load failures show "Unable to load history" message
- Individual session load failures redirect to `/history` with error toast

## Testing Strategy

This feature combines pure logic suitable for property-based testing (HR zone calculations, authentication operations, data serialization) with infrastructure components (AWS services, UI rendering) that require integration and example-based testing.

**Unit Tests (Example-Based):**

- Specific edge cases for HR zone boundaries
- Password validation rules (min length, special characters)
- Email format validation
- Profile picture file type validation
- Date range filtering edge cases
- Error message formatting

**Integration Tests:**

- DynamoDB table operations (Users, UserProfiles, Sessions)
- S3 profile picture upload and retrieval
- JWT token generation and verification with real keys
- End-to-end authentication flow (register → login → verify)
- Session persistence and retrieval
- Full upload pipeline with authentication

**Property-Based Tests (100+ iterations):**

Property-based tests focus on pure functions and data transformations where universal properties hold across randomized inputs. Each test references its design property and validates the specified requirements.

**Configuration:**

- Minimum 100 iterations per property test
- Use Hypothesis library for Python backend tests
- Use fast-check library for TypeScript frontend tests (if applicable)
- Each property test tagged with: **Feature: hr-zones-user-profile, Property {N}: {property_text}**

### Property-Based Test Scope

The following correctness properties will be implemented as property-based tests. Infrastructure operations (DynamoDB, S3, JWT with external libraries) will use integration tests with 1-3 examples instead.


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

The following properties focus on pure logic and data transformations in the heart rate zone calculations, data validation, and serialization components. Infrastructure operations (AWS services, UI rendering) are covered by integration tests rather than property-based tests.

### Property 1: HR Data Extraction Format Invariant

*For any* FIT file with heart rate data, the extracted HR samples SHALL be a list where each element is a 2-tuple containing a datetime object and an integer heart rate value.

**Validates: Requirements 1.2**

### Property 2: HR Data Filtering Correctness

*For any* list of heart rate values (including invalid ones), filtering SHALL exclude all values that are zero, negative, or greater than or equal to 221 bpm, while preserving all valid values in their original order.

**Validates: Requirements 1.4**

### Property 3: HR Data NaN/Inf Handling

*For any* list of heart rate values containing NaN or Inf values at random positions, processing SHALL skip invalid values and preserve all finite, valid heart rate values in their original sequence.

**Validates: Requirements 1.5**

### Property 4: Invalid Age Rejection

*For any* age value less than 1 or greater than 120, the max heart rate calculation SHALL raise an error or return an error indication.

**Validates: Requirements 2.1**

### Property 5: Max Heart Rate Calculation

*For any* valid age between 1 and 120 (inclusive), the maximum heart rate SHALL equal 220 minus the age.

**Validates: Requirements 2.2**

### Property 6: HR Zone Boundary Calculation

*For any* maximum heart rate value, the five zone boundaries SHALL be calculated as:
- Zone 1: [round(0.50 * max_hr), round(0.60 * max_hr))
- Zone 2: [round(0.60 * max_hr), round(0.70 * max_hr))
- Zone 3: [round(0.70 * max_hr), round(0.80 * max_hr))
- Zone 4: [round(0.80 * max_hr), round(0.90 * max_hr))
- Zone 5: [round(0.90 * max_hr), round(1.00 * max_hr)]

**Validates: Requirements 2.3, 2.4, 2.5, 2.6, 2.7**

### Property 7: HR Sample Validation

*For any* heart rate value, validation SHALL classify it as valid if and only if the value is greater than 0 and less than or equal to 300 beats per minute.

**Validates: Requirements 2.8**

### Property 8: Zone Time Conservation

*For any* set of valid heart rate samples with timestamps, the sum of time in seconds across all five zones SHALL equal the total session time (derived from first to last timestamp) within a tolerance of 1 second.

**Validates: Requirements 2.12**

### Property 9: Zone Percentage Calculation

*For any* set of valid heart rate samples, the calculated percentage for each zone SHALL equal (zone_time_seconds / total_time_seconds) * 100, rounded to one decimal place, and the sum of all five percentages SHALL be between 99.0% and 101.0% (accounting for rounding).

**Validates: Requirements 2.11**

### Property 10: UserProfile Validation - Age Range

*For any* UserProfile where age is less than 10 or greater than 100, the __post_init__ validation SHALL raise a ValueError.

**Validates: Requirements 6.2**

### Property 11: UserProfile Validation - Ability Level

*For any* string that is not one of "beginner", "intermediate", "advanced", or "elite" (case-insensitive), the UserProfile __post_init__ validation SHALL raise a ValueError.

**Validates: Requirements 6.3**

### Property 12: UserProfile Validation - String Lengths

*For any* UserProfile where nationality is an empty string or exceeds 100 characters, OR locality is an empty string or exceeds 100 characters, the __post_init__ validation SHALL raise a ValueError.

**Validates: Requirements 6.4, 6.5**

### Property 13: UserProfile Serialization Round-Trip

*For any* valid UserProfile object, serializing to JSON and then deserializing SHALL produce a UserProfile where age, nationality, locality, and ability_level exactly match the original values, preserving types (age as int, strings as strings, empty strings as empty strings).

**Validates: Requirements 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7**

### Property 14: AbilityAssessment Validation

*For any* AbilityAssessment object where percentile_estimate is empty or exceeds 100 characters, OR local_ranking is empty or exceeds 200 characters, OR national_ranking is empty or exceeds 200 characters, OR competitive_analysis is empty or exceeds 800 characters, the __post_init__ validation SHALL raise a ValueError.

**Validates: Requirements 8.4, 8.5, 8.6, 8.7**

### Property 15: Daily Distance Aggregation

*For any* list of sessions with session_date and total_distance_meters fields, grouping by date and summing distances SHALL produce a result where the sum of all daily distances equals the sum of all individual session distances.

**Validates: Requirements 18.4 (aggregation logic)**

### Property 16: Password Hash Verification Round-Trip

*For any* valid password string (minimum 8 characters), hashing the password with bcrypt and then verifying the original password against the hash SHALL return True, while verifying any different password SHALL return False.

**Validates: Requirements 21.6, 21.14 (bcrypt logic)**

### Property 17: Profile Picture Validation - File Size

*For any* file where size exceeds 2 MB (2,097,152 bytes), the profile picture validation SHALL reject the file.

**Validates: Requirements 23.2, 23.7**

### Property 18: Profile Picture Validation - File Type

*For any* file that does not have JPEG, PNG, or GIF magic bytes in its header, the profile picture validation SHALL reject the file as invalid format.

**Validates: Requirements 23.2, 23.5**

## Testing Strategy Summary

**Property-Based Tests** (focused on pure logic):
- HR zone calculations and data filtering
- UserProfile and AbilityAssessment validation
- Serialization round-trips
- Password hashing verification
- File validation logic
- Data aggregation calculations

Minimum 100 iterations per property test using Hypothesis (Python backend).

**Integration Tests** (focused on infrastructure and services):
- DynamoDB operations (Users, UserProfiles, Sessions tables)
- S3 profile picture upload and retrieval
- JWT token generation with real keys
- Bedrock AI invocation for coaching and assessments
- End-to-end authentication flows
- Full upload pipeline with session persistence

**Example-Based Unit Tests** (focused on specific cases):
- Edge cases for zone boundaries
- Empty HR data handling
- Missing profile scenarios
- Error message formatting
- Specific validation rules

**UI Tests** (focused on frontend components):
- Component rendering with different props
- Form validation behavior
- Navigation and routing
- Calendar and chart display
- Profile picture upload UI flow

