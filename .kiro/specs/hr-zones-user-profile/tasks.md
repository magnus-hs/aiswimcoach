# Implementation Plan: Heart Rate Zones, User Profile, and Authentication

## Overview

This implementation extends the AI Swim Coach with user authentication (JWT-based), profile management, heart rate zone analysis, and session history tracking. The work is organized into backend modules (authentication, HR zones, session history, profile management), frontend components (login, registration, profile, history views), and infrastructure setup (DynamoDB tables, S3 bucket).

## Tasks

### Backend Infrastructure Setup

- [x] 1. Set up DynamoDB tables and S3 bucket
  - Create Users table (partition key: user_id, GSI: email-index)
  - Create UserProfiles table (partition key: user_id)
  - Create Sessions table (partition key: user_id, sort key: session_date, GSI: session_id-index)
  - Create S3 bucket for profile pictures with public read access
  - Add environment variables: JWT_SECRET, PROFILE_PICTURES_BUCKET, USERS_TABLE, PROFILES_TABLE, SESSIONS_TABLE
  - _Requirements: 5.1-5.6, 15.1-15.12, 23.9-23.11_

### Backend Data Models

- [x] 2. Extend models.py with new dataclasses
  - [x] 2.1 Create UserProfile dataclass
    - Add fields: age (int), nationality (str), locality (str), ability_level (str)
    - Implement __post_init__ validation for age range (10-100)
    - Implement __post_init__ validation for ability_level enum
    - Implement __post_init__ validation for nationality/locality string lengths
    - _Requirements: 6.1-6.5_
  
  - [x]* 2.2 Write property tests for UserProfile validation
    - **Property 10: UserProfile Validation - Age Range**
    - **Property 11: UserProfile Validation - Ability Level**
    - **Property 12: UserProfile Validation - String Lengths**
    - **Validates: Requirements 6.2, 6.3, 6.4, 6.5**
  
  - [x] 2.3 Create HRZonesData dataclass
    - Add fields for zone times (seconds), percentages, max_hr, zone_boundaries
    - Implement field validation (non-negative times, percentages sum to ~100%)
    - _Requirements: 2.9, 2.11_
  
  - [x] 2.4 Create AbilityAssessment dataclass
    - Add fields: percentile_estimate, local_ranking, national_ranking, competitive_analysis
    - Implement __post_init__ validation for string length constraints
    - _Requirements: 8.1, 8.4-8.7_
  
  - [x]* 2.5 Write property tests for AbilityAssessment validation
    - **Property 14: AbilityAssessment Validation**
    - **Validates: Requirements 8.4, 8.5, 8.6, 8.7**
  
  - [x] 2.6 Create Session dataclass
    - Add all fields from requirements: session_id, user_id, session_date, metrics, hr_zones (optional), ability_assessment (optional)
    - _Requirements: 15.2-15.12_
  
  - [x] 2.7 Extend FullResponse dataclass
    - Add optional fields: hr_zones, ability_assessment, session_id
    - _Requirements: 12.4_
  
  - [x] 2.8 Extend TrainingPlan dataclass
    - Add goal_likelihood field (str, max 300 chars)
    - _Requirements: 11.1-11.2_
  
  - [x]* 2.9 Write property test for UserProfile serialization round-trip
    - **Property 13: UserProfile Serialization Round-Trip**
    - **Validates: Requirements 14.1-14.7**

- [x] 3. Checkpoint - Ensure all data model tests pass
  - Ensure all tests pass, ask the user if questions arise.

### Backend Authentication Module

- [x] 4. Implement authentication module (auth.py)
  - [x] 4.1 Implement password hashing functions
    - Write hash_password() using bcrypt with cost factor 12
    - Write verify_password() using bcrypt verification
    - _Requirements: 21.6, 21.14_
  
  - [x]* 4.2 Write property test for password hash round-trip
    - **Property 16: Password Hash Verification Round-Trip**
    - **Validates: Requirements 21.6, 21.14**
  
  - [x] 4.3 Implement JWT token generation
    - Write generate_jwt_token() with claims: user_id, email, iat, exp (7 days)
    - Sign with JWT_SECRET from environment
    - _Requirements: 21.16-21.17_
  
  - [x] 4.4 Implement JWT token verification
    - Write verify_token() to extract and validate JWT claims
    - Handle expired and invalid tokens
    - _Requirements: 21.21-21.22_
  
  - [x] 4.5 Implement user registration
    - Write register_user() to create user in Users table
    - Check for existing email using email-index GSI
    - Return 409 if email exists, 201 with user_id if successful
    - _Requirements: 21.5-21.9_
  
  - [x] 4.6 Implement user login
    - Write login_user() to authenticate and return JWT token
    - Query Users table by email, verify password, generate token
    - Return 401 for invalid credentials, 200 with token if successful
    - _Requirements: 21.11-21.18_
  
  - [x]* 4.7 Write integration tests for authentication flow
    - Test registration with duplicate email
    - Test login with invalid credentials
    - Test token generation and verification
    - Test expired token handling
    - _Requirements: 21.1-21.22_

- [x] 5. Checkpoint - Ensure authentication tests pass
  - Ensure all tests pass, ask the user if questions arise.

### Backend Heart Rate Zones Module

- [x] 6. Implement HR zones module (hr_zones.py)
  - [x] 6.1 Implement HR data extraction
    - Write extract_heart_rate_data() to parse FIT file record messages
    - Extract (timestamp, hr_bpm) tuples
    - Filter out zero, negative, and >= 221 bpm values
    - Skip NaN and Inf values
    - _Requirements: 1.1-1.5_
  
  - [ ]* 6.2 Write property tests for HR data extraction and filtering
    - **Property 1: HR Data Extraction Format Invariant**
    - **Property 2: HR Data Filtering Correctness**
    - **Property 3: HR Data NaN/Inf Handling**
    - **Validates: Requirements 1.2, 1.4, 1.5**
  
  - [x] 6.3 Implement max HR calculation
    - Write calculate_max_hr() as 220 - age
    - Validate age range (1-120)
    - _Requirements: 2.1-2.2_
  
  - [ ]* 6.4 Write property tests for max HR calculation
    - **Property 4: Invalid Age Rejection**
    - **Property 5: Max Heart Rate Calculation**
    - **Validates: Requirements 2.1, 2.2**
  
  - [x] 6.5 Implement zone boundary calculation
    - Write calculate_zone_boundaries() for 5 zones
    - Zone boundaries: 50-60%, 60-70%, 70-80%, 80-90%, 90-100% of max HR
    - Round boundaries to nearest whole number
    - _Requirements: 2.3-2.7_
  
  - [ ]* 6.6 Write property test for zone boundary calculation
    - **Property 6: HR Zone Boundary Calculation**
    - **Validates: Requirements 2.3, 2.4, 2.5, 2.6, 2.7**
  
  - [x] 6.7 Implement HR sample validation
    - Write is_valid_hr_sample() checking 0 < hr <= 300
    - _Requirements: 2.8_
  
  - [ ]* 6.8 Write property test for HR sample validation
    - **Property 7: HR Sample Validation**
    - **Validates: Requirements 2.8**
  
  - [x] 6.9 Implement zone time calculation
    - Write calculate_hr_zones() to compute time in each zone
    - Calculate seconds and percentages for each zone
    - Ensure sum of times equals total session time (within 1 second tolerance)
    - _Requirements: 2.9-2.12_
  
  - [ ]* 6.10 Write property tests for zone calculations
    - **Property 8: Zone Time Conservation**
    - **Property 9: Zone Percentage Calculation**
    - **Validates: Requirements 2.11, 2.12**
  
  - [ ]* 6.11 Write unit tests for edge cases
    - Test empty HR data returns error
    - Test single HR sample
    - Test all samples in one zone
    - _Requirements: 1.3, 2.10_

- [x] 7. Checkpoint - Ensure HR zones tests pass
  - Ensure all tests pass, ask the user if questions arise.

### Backend Profile Management Module

- [x] 8. Implement profile manager module (profile_manager.py)
  - [x] 8.1 Implement profile storage
    - Write save_profile() to persist UserProfile to UserProfiles table
    - Include updated_at timestamp in ISO 8601 format
    - _Requirements: 5.1-5.6_
  
  - [x] 8.2 Implement profile retrieval
    - Write get_profile() to fetch UserProfile by user_id
    - Return None if profile doesn't exist
    - _Requirements: 5.9_
  
  - [x] 8.3 Implement profile picture validation
    - Write validate_image_file() checking magic bytes for JPEG/PNG/GIF
    - Write validate_file_size() checking max 2 MB
    - _Requirements: 23.2, 23.5-23.7_
  
  - [ ]* 8.4 Write property tests for file validation
    - **Property 17: Profile Picture Validation - File Size**
    - **Property 18: Profile Picture Validation - File Type**
    - **Validates: Requirements 23.2, 23.5, 23.7**
  
  - [x] 8.5 Implement profile picture upload
    - Write upload_profile_picture() to upload to S3
    - Generate unique filename: {user_id}_{timestamp}.{extension}
    - Update Users table with profile_picture_url
    - _Requirements: 23.8-23.11_
  
  - [ ]* 8.6 Write integration tests for profile operations
    - Test profile save and retrieval
    - Test profile update
    - Test profile picture upload and URL storage
    - _Requirements: 5.1-5.10, 23.1-23.15_

- [x] 9. Checkpoint - Ensure profile management tests pass
  - Ensure all tests pass, ask the user if questions arise.

### Backend Session History Module

- [x] 10. Implement session history module (session_history.py)
  - [x] 10.1 Implement session storage
    - Write save_session() to persist Session to Sessions table
    - Generate session_id as UUID v4
    - Include all session fields, optional hr_zones and ability_assessment
    - _Requirements: 15.1-15.13_
  
  - [x] 10.2 Implement session retrieval by user
    - Write get_user_sessions() querying by user_id (partition key)
    - Support optional start_date and end_date filters using sort key
    - Return sessions ordered by session_date descending
    - _Requirements: 16.4-16.6_
  
  - [x] 10.3 Implement session retrieval by ID
    - Write get_session_by_id() querying session_id-index GSI
    - Return full Session object with all details
    - Return 404 if session doesn't exist
    - _Requirements: 19.4-19.5_
  
  - [x] 10.4 Implement daily distance aggregation
    - Write aggregate_daily_distances() grouping sessions by date
    - Sum total_distance_meters for each date
    - _Requirements: 18.4_
  
  - [ ]* 10.5 Write property test for distance aggregation
    - **Property 15: Daily Distance Aggregation**
    - **Validates: Requirements 18.4**
  
  - [ ]* 10.6 Write integration tests for session operations
    - Test session save and retrieval
    - Test user sessions query with date filters
    - Test session by ID retrieval
    - Test empty session history
    - _Requirements: 15.1-15.13, 16.1-16.10, 19.1-19.8_

- [x] 11. Checkpoint - Ensure session history tests pass
  - Ensure all tests pass, ask the user if questions arise.

### Backend Middleware and Route Integration

- [x] 12. Implement authentication middleware (middleware.py)
  - [x] 12.1 Create require_auth decorator
    - Extract JWT from Authorization header
    - Verify token using verify_token()
    - Inject auth_context with user_id and email into event
    - Return 401 if token missing, invalid, or expired
    - _Requirements: 20.2-20.3, 21.20-21.22_
  
  - [ ]* 12.2 Write unit tests for middleware
    - Test with valid token
    - Test with missing token
    - Test with expired token
    - Test with invalid token
    - _Requirements: 21.20-21.22_

- [x] 13. Extend handler.py with new routes
  - [x] 13.1 Add route dispatcher
    - Implement route mapping for httpMethod and path
    - Support routes: POST /auth/register, POST /auth/login, GET /auth/verify
    - Support routes: POST /profile, GET /profile, POST /profile/picture
    - Support routes: GET /sessions, GET /sessions/:id
    - Maintain existing multipart and JSON training plan routes
    - _Requirements: 21.5, 21.11, 22.4, 4.7, 16.3, 19.3_
  
  - [x] 13.2 Implement authentication endpoints
    - POST /auth/register: call register_user()
    - POST /auth/login: call login_user()
    - GET /auth/verify: call verify_token()
    - _Requirements: 21.5-21.22_
  
  - [x] 13.3 Implement profile endpoints
    - POST /profile: call save_profile() (requires auth)
    - GET /profile: call get_profile() (requires auth)
    - POST /profile/picture: call upload_profile_picture() (requires auth)
    - _Requirements: 4.7, 23.4, 23.11_
  
  - [x] 13.4 Implement session endpoints
    - GET /sessions: call get_user_sessions() (requires auth)
    - GET /sessions/:id: call get_session_by_id() (requires auth)
    - _Requirements: 16.3, 19.3_
  
  - [x] 13.5 Modify upload handler to integrate HR zones
    - Check if user has profile with age
    - If age exists, call extract_heart_rate_data() and calculate_hr_zones()
    - Include hr_zones in FullResponse if calculation succeeds
    - Handle hr_zones calculation failure gracefully (omit from response)
    - _Requirements: 12.1-12.7_
  
  - [x] 13.6 Modify upload handler to integrate ability assessment
    - Check if user has complete profile (age, nationality, locality, ability_level)
    - If profile complete, enhance Bedrock prompt with profile data
    - Parse ability assessment from Bedrock response
    - Include ability_assessment in FullResponse if available
    - _Requirements: 7.1-7.12, 9.1-9.6_
  
  - [x] 13.7 Modify upload handler to save session
    - Extract user_id from auth_context (requires auth)
    - Call save_session() after generating coaching results
    - Include session_id in FullResponse
    - Log error if session save fails but still return coaching results (best-effort)
    - _Requirements: 20.1-20.7_
  
  - [x] 13.8 Update training plan handler to include profile context
    - Check if user has profile
    - Include age, ability_level, locality in Bedrock prompt if available
    - Include ability assessment competitive_analysis if exists
    - Add goal_likelihood field to TrainingPlan response
    - _Requirements: 10.1-10.8, 11.1-11.6_
  
  - [ ]* 13.9 Write integration tests for extended upload flow
    - Test upload with user profile (includes HR zones and ability assessment)
    - Test upload without user profile (omits HR zones and ability assessment)
    - Test upload with profile but no age (omits HR zones only)
    - Test session save success and failure scenarios
    - _Requirements: 12.1-12.7, 13.1-13.7, 20.1-20.7_

- [x] 14. Checkpoint - Ensure backend integration tests pass
  - Ensure all tests pass, ask the user if questions arise.

### Frontend Infrastructure Setup

- [x] 15. Set up frontend routing and authentication context
  - [x] 15.1 Install dependencies
    - Add react-router-dom for routing
    - Add recharts for progress graph
    - Add axios for API calls
    - _Requirements: 16.2, 18.1_
  
  - [x] 15.2 Create authentication context hook (useAuth.tsx)
    - Manage auth state: token, user_id, email, isAuthenticated
    - Provide login, logout, and register functions
    - Store/retrieve token from localStorage
    - _Requirements: 21.19, 22.1-22.2_
  
  - [x] 15.3 Create API service modules
    - Create authService.ts with register, login, verifyToken functions
    - Create profileService.ts with saveProfile, getProfile, uploadProfilePicture functions
    - Create sessionService.ts with getUserSessions, getSessionById functions
    - Include JWT token in Authorization header for authenticated requests
    - _Requirements: 21.20, 4.7, 16.3, 19.3_
  
  - [x] 15.4 Set up routing with ProtectedRoute
    - Create ProtectedRoute component checking auth state
    - Redirect to /login if not authenticated
    - Set up route structure: /, /login, /register, /upload, /profile, /history, /session/:id
    - _Requirements: 22.1-22.5, 16.2, 19.2_

### Frontend Authentication Components

- [x] 16. Implement authentication UI components
  - [x] 16.1 Create Login component (Login.tsx)
    - Email and password form with validation
    - Call authService.login() on submit
    - Store token in localStorage and update auth context
    - Redirect to /upload on success
    - Display error messages
    - _Requirements: 21.10-21.19_
  
  - [x] 16.2 Create Register component (Register.tsx)
    - Email, password, confirm password form with validation
    - Validate email format and password length (min 8 chars)
    - Validate password match
    - Call authService.register() on submit
    - Redirect to /login with success message
    - Display error messages
    - _Requirements: 21.1-21.9_
  
  - [ ]* 16.3 Write component tests for authentication UI
    - Test form validation
    - Test successful login flow
    - Test successful registration flow
    - Test error handling
    - _Requirements: 21.1-21.22_

### Frontend Profile Components

- [x] 17. Implement profile management UI
  - [x] 17.1 Create ProfilePage component (ProfilePage.tsx)
    - User profile form: age, nationality, locality, ability_level
    - Client-side validation (age 10-100, ability_level required)
    - Profile picture upload with preview
    - Call profileService.saveProfile() and uploadProfilePicture()
    - Load existing profile on mount
    - Display success/error messages
    - _Requirements: 4.1-4.9, 23.1-23.4, 23.12_
  
  - [ ]* 17.2 Write component tests for profile page
    - Test form validation
    - Test profile save
    - Test profile picture upload
    - Test loading existing profile
    - _Requirements: 4.1-4.9, 23.1-23.15_

### Frontend Upload Results Enhancement

- [x] 18. Extend upload results to display HR zones and ability assessment
  - [x] 18.1 Create HRZonesCard component (HRZonesCard.tsx)
    - Display zone list with zone number, HR range, time, percentage
    - Render horizontal bar chart with zone colors
    - Handle empty state: "Heart rate data was not found in your FIT file"
    - _Requirements: 3.1-3.7_
  
  - [x] 18.2 Create AbilityAssessmentCard component (AbilityAssessmentCard.tsx)
    - Display four sections: percentile, local, national, competitive analysis
    - Only render if ability_assessment exists in response
    - _Requirements: 9.1-9.6_
  
  - [x] 18.3 Update upload results page layout
    - Insert HRZonesCard between splits table and coaching results
    - Insert AbilityAssessmentCard below coaching results
    - Display prompt "Complete your profile to enable heart rate zone analysis" if no age
    - Display session saved message with link to history
    - _Requirements: 12.5-12.6, 20.5-20.7_
  
  - [ ]* 18.4 Write component tests for enhanced upload results
    - Test HR zones card rendering
    - Test ability assessment card rendering
    - Test conditional rendering based on profile completeness
    - _Requirements: 3.1-3.7, 9.1-9.6, 12.1-12.7_

### Frontend Session History Components

- [x] 19. Implement session history UI
  - [x] 19.1 Create HistoryPage component (HistoryPage.tsx)
    - Container managing calendar, graph, and session list state
    - Fetch sessions on mount: sessionService.getUserSessions()
    - Handle empty state: "No swim sessions found. Upload your first FIT file to get started!"
    - _Requirements: 16.1-16.10_
  
  - [x] 19.2 Create CalendarView component (CalendarView.tsx)
    - Monthly calendar grid (7 columns x 5-6 rows)
    - Previous/next month navigation
    - Mark dates with sessions using colored dots
    - Display total distance per date
    - Highlight current date
    - onClick handler for date selection
    - _Requirements: 17.1-17.8_
  
  - [x] 19.3 Create ProgressGraph component (ProgressGraph.tsx)
    - Line chart using recharts library
    - X-axis: dates, Y-axis: distance in meters
    - Time range selector: Last 7/30/90 Days, All Time
    - Hover tooltip showing date and distance
    - Blue color scheme (blue-500)
    - Use aggregate_daily_distances for data
    - _Requirements: 18.1-18.10_
  
  - [x] 19.4 Create SessionDetail component (SessionDetail.tsx)
    - Reuse upload results layout
    - Fetch session by ID: sessionService.getSessionById()
    - Display: session summary, splits, HR zones (if available), coaching, ability assessment (if available), training plan (if available)
    - "Back to History" link
    - _Requirements: 19.1-19.8_
  
  - [x] 19.5 Add session links in calendar and history list
    - Make session summaries clickable
    - Navigate to /session/:sessionId on click
    - _Requirements: 19.1-19.2_
  
  - [ ]* 19.6 Write component tests for history UI
    - Test calendar rendering and date selection
    - Test progress graph rendering
    - Test session detail page
    - Test empty state handling
    - _Requirements: 16.1-16.10, 17.1-17.8, 18.1-18.10, 19.1-19.8_

### Frontend Layout and Navigation

- [x] 20. Implement app layout and navigation
  - [x] 20.1 Create Header component (Header.tsx)
    - Left: app logo
    - Center: navigation links (Upload, History, Profile)
    - Right: user email, profile avatar (40px), logout button
    - Load profile picture from Users table
    - Default avatar icon if no picture
    - Profile avatar click navigates to /profile
    - Logout clears localStorage and redirects to /login
    - _Requirements: 22.6-22.8, 24.1-24.6, 25.3, 25.9_
  
  - [x] 20.2 Apply Strava/Garmin-inspired styling
    - Card-based layout for data sections
    - Large bold numbers for key metrics
    - Left sidebar navigation with icons
    - Orange/red for intense zones, blue/green for recovery zones
    - Consistent color scheme: dark navy headers, white cards, blue-500 actions, gray-100 backgrounds
    - _Requirements: 25.1-25.10_
  
  - [ ]* 20.3 Write component tests for header and layout
    - Test navigation links
    - Test logout functionality
    - Test profile picture display
    - _Requirements: 22.6-22.10, 24.1-24.6_

- [x] 21. Final checkpoint - Ensure all frontend tests pass
  - Ensure all tests pass, ask the user if questions arise.

### End-to-End Integration Testing

- [ ]* 22. Write end-to-end integration tests
  - Test complete user flow: register → login → upload profile → upload FIT file → view results → view history
  - Test authenticated API calls with JWT tokens
  - Test profile picture upload and display
  - Test HR zones appearing in results when profile has age
  - Test ability assessment appearing when profile is complete
  - Test session history and calendar views
  - _Requirements: All requirements 1-25_

## Notes

- Tasks marked with `*` are optional property-based and integration tests that can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation throughout implementation
- Property tests validate universal correctness properties with 100+ iterations
- Integration tests verify AWS service interactions and component integration
- Authentication is required for all endpoints except /auth/register, /auth/login, and /auth/verify
- Session storage is best-effort and should not block the primary upload response
- HR zones and ability assessment are optional enhancements that gracefully degrade when profile is incomplete
