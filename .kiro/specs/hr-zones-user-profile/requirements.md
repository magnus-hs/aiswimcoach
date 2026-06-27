# Requirements Document

## Introduction

This document specifies the requirements for adding heart rate zone analysis, user profile management, and AI-powered ability assessment to the AI Swim Coach web application. The feature enables swimmers to understand their training intensity distribution, track personal information, and receive context-aware assessments of their competitive ability.

## Glossary

- **System**: The AI Swim Coach web application (backend + frontend)
- **Backend**: AWS Lambda functions (Python) handling FIT file processing, data storage, and AI invocation
- **Frontend**: React application (TypeScript) providing the user interface
- **FIT_Parser**: Component that extracts data from Garmin FIT files using the fitparse library
- **Heart_Rate_Zone**: One of five intensity ranges (Zone 1-5) calculated from maximum heart rate
- **Max_Heart_Rate**: Maximum heart rate calculated as 220 minus the user's age
- **User_Profile**: Collection of user attributes including age, nationality, locality, and ability level
- **Ability_Assessment**: AI-generated evaluation of swimmer's competitive level considering age, metrics, and population context
- **Bedrock_Client**: Component that invokes Amazon Bedrock (Claude) for AI-powered analysis
- **HR_Zones_Data**: Calculated time and percentage spent in each heart rate zone
- **Profile_Store**: DynamoDB table storing user profile information
- **Session_Metrics**: Performance data extracted from FIT files (pace, SWOLF, stroke rate, heart rate)
- **Sessions_Store**: DynamoDB table storing historical swim session data
- **Users_Store**: DynamoDB table storing user authentication credentials and profile information
- **JWT**: JSON Web Token used for authenticating API requests
- **Profile_Picture_Store**: S3 bucket storing user profile picture images

## Requirements

### Requirement 1: Extract Heart Rate Data from FIT Files

**User Story:** As a swimmer, I want the system to extract heart rate data from my FIT file, so that I can analyze my training intensity.

#### Acceptance Criteria

1. WHEN a FIT file containing heart rate data in record messages is uploaded, THE FIT_Parser SHALL extract all heart rate values with their associated timestamps from record messages
2. WHEN heart rate values are extracted, THE FIT_Parser SHALL return a list of tuples where each tuple contains a timestamp and a heart rate value in beats per minute
3. WHEN a FIT file contains no heart rate data in record messages, THE FIT_Parser SHALL return an empty list
4. WHEN heart rate values are present, THE FIT_Parser SHALL filter out values that are zero, negative, or greater than or equal to 221 bpm
5. IF a heart rate field contains non-numeric data or non-finite values, THEN THE FIT_Parser SHALL skip that value and continue processing remaining records

### Requirement 2: Calculate Heart Rate Zones

**User Story:** As a swimmer, I want to see which heart rate zones I trained in, so that I can understand my workout intensity distribution.

#### Acceptance Criteria

1. WHEN the user provides their age, IF the age is less than 1 or greater than 120, THEN THE System SHALL return an error message indicating invalid age
2. WHEN the user provides their age, IF the age is between 1 and 120 inclusive, THEN THE System SHALL calculate maximum heart rate as 220 minus age
3. THE System SHALL define Zone 1 as 50% (inclusive) to 60% (exclusive) of maximum heart rate, where zone boundaries are rounded to the nearest whole number
4. THE System SHALL define Zone 2 as 60% (inclusive) to 70% (exclusive) of maximum heart rate, where zone boundaries are rounded to the nearest whole number
5. THE System SHALL define Zone 3 as 70% (inclusive) to 80% (exclusive) of maximum heart rate, where zone boundaries are rounded to the nearest whole number
6. THE System SHALL define Zone 4 as 80% (inclusive) to 90% (exclusive) of maximum heart rate, where zone boundaries are rounded to the nearest whole number
7. THE System SHALL define Zone 5 as 90% (inclusive) to 100% (inclusive) of maximum heart rate, where zone boundaries are rounded to the nearest whole number
8. THE System SHALL classify a heart rate sample as valid if the value is greater than 0 and less than or equal to 300 beats per minute
9. WHEN heart rate data contains one or more valid samples, THE System SHALL calculate the time in seconds spent in each zone
10. IF the FIT file contains no valid heart rate samples, THEN THE System SHALL return an error message indicating missing heart rate data
11. WHEN heart rate data contains one or more valid samples, THE System SHALL calculate the percentage of total session time spent in each zone, rounded to one decimal place
12. THE System SHALL ensure the sum of time across all zones equals the total session time with valid heart rate data within a tolerance of 1 second

### Requirement 3: Display Heart Rate Zone Analysis

**User Story:** As a swimmer, I want to view a visual breakdown of my heart rate zones, so that I can quickly assess my training intensity.

#### Acceptance Criteria

1. WHEN the Frontend receives HR_Zones_Data with calculated zones, THE Frontend SHALL display time in whole seconds for each of the five zones
2. WHEN the Frontend receives HR_Zones_Data with calculated zones, THE Frontend SHALL display percentage of total time for each of the five zones, rounded to one decimal place
3. WHEN the Frontend receives HR_Zones_Data with calculated zones, THE Frontend SHALL render a horizontal bar chart showing the relative distribution across zones
4. WHEN the Frontend displays the horizontal bar chart, THE Frontend SHALL use distinct colors for each zone (Zone 1: light blue, Zone 2: green, Zone 3: yellow, Zone 4: orange, Zone 5: red)
5. WHEN no heart rate data is available in the uploaded FIT file, THE Frontend SHALL display the message "Heart rate data was not found in your FIT file"
6. WHEN HR_Zones_Data contains a zone with zero time, THE Frontend SHALL still display that zone with 0 seconds and 0.0% in the list and render it with zero width in the bar chart
7. THE Frontend SHALL label each displayed zone with its zone number and heart rate range in beats per minute

### Requirement 4: Capture User Profile Information

**User Story:** As a swimmer, I want to enter my personal information, so that the system can provide personalized coaching and assessments.

#### Acceptance Criteria

1. THE Frontend SHALL provide a user profile form with fields for age (integer input), nationality (text input with 100-character maximum), locality (text input with 100-character maximum), and ability level (dropdown selection)
2. THE Frontend SHALL require age as a mandatory integer field with client-side validation for values between 10 and 100 inclusive
3. THE Frontend SHALL provide nationality as an optional text field with a maximum length of 100 characters
4. THE Frontend SHALL provide locality as an optional text field with a maximum length of 100 characters
5. THE Frontend SHALL provide ability level as a mandatory dropdown with options: beginner, intermediate, advanced, elite, with no default selection
6. THE Frontend SHALL disable the submit button when age is empty, invalid, or outside the valid range (10-100), or when ability level is not selected
7. WHEN the user submits the profile form with valid data, THE Frontend SHALL send a POST request to /profile endpoint with JSON payload containing age, nationality, locality, and ability_level fields
8. WHEN the Backend responds with HTTP 200 to the profile submission, THE Frontend SHALL display a confirmation message indicating the profile was saved successfully
9. WHEN age validation fails, THE Frontend SHALL display an error message below the age field indicating the valid age range is 10-100

### Requirement 5: Store User Profile Data

**User Story:** As a swimmer, I want my profile saved, so that I don't have to re-enter it for future sessions.

#### Acceptance Criteria

1. WHEN the Backend receives a valid User_Profile, THE Profile_Store SHALL persist the profile with a unique user identifier formatted as a UUID version 4
2. THE Profile_Store SHALL store age as an integer
3. THE Profile_Store SHALL store nationality as a string with maximum length 100 characters
4. THE Profile_Store SHALL store locality as a string with maximum length 200 characters
5. THE Profile_Store SHALL store ability_level as a string with one of the following values: beginner, intermediate, advanced, elite
6. THE Profile_Store SHALL store an updated_at timestamp in ISO 8601 format with UTC timezone and millisecond precision
7. IF the Backend receives a User_Profile where age is not between 5 and 120 inclusive, or nationality exceeds 100 characters, or locality exceeds 200 characters, or ability_level is not one of the four enumerated values, THEN THE Backend SHALL reject the profile as invalid
8. WHEN a user submits an updated profile, IF the persistence to Profile_Store fails, THEN THE Backend SHALL return HTTP 500 with error message indicating profile storage failure
9. WHEN the Frontend requests user profile data for a user identifier that does not exist in Profile_Store, THE Backend SHALL return HTTP 404 with error message indicating profile not found
10. WHEN the Frontend requests user profile data and the Profile_Store query fails, THE Backend SHALL return HTTP 500 with error message indicating profile retrieval failure

### Requirement 6: Parse User Profile in Backend Models

**User Story:** As a developer, I want a UserProfile data model, so that profile data is validated and type-safe throughout the backend.

#### Acceptance Criteria

1. THE Backend SHALL define a UserProfile dataclass with fields: age (int), nationality (str with max length 100 characters), locality (str with max length 100 characters), ability_level (str)
2. IF age is less than 10 or greater than 100, THEN THE UserProfile.__post_init__ method SHALL raise a ValueError with message "age must be between 10 and 100"
3. IF ability_level (case-insensitive) is not one of: beginner, intermediate, advanced, elite, THEN THE UserProfile.__post_init__ method SHALL raise a ValueError with message "ability_level must be one of: beginner, intermediate, advanced, elite"
4. IF nationality is an empty string or exceeds 100 characters, THEN THE UserProfile.__post_init__ method SHALL raise a ValueError with message "nationality must be 1-100 characters if provided"
5. IF locality is an empty string or exceeds 100 characters, THEN THE UserProfile.__post_init__ method SHALL raise a ValueError with message "locality must be 1-100 characters if provided"

### Requirement 7: Generate AI-Powered Ability Assessment

**User Story:** As a swimmer, I want an AI assessment of my competitive ability, so that I understand how I compare to others in my age group and region.

#### Acceptance Criteria

1. IF the user has a User_Profile with age, nationality, locality, and ability_level all populated, AND Session_Metrics with pace, swolf, and stroke_rate all finite numbers, THEN THE System SHALL invoke the Bedrock_Client to generate an Ability_Assessment
2. IF the User_Profile is missing any required field (age, nationality, locality, ability_level), THEN THE System SHALL skip ability assessment generation and return no Ability_Assessment in the response
3. IF Session_Metrics contains any non-finite value for pace, swolf, or stroke_rate, THEN THE System SHALL skip ability assessment generation and return no Ability_Assessment in the response
4. THE Ability_Assessment prompt sent to Bedrock_Client SHALL include the swimmer's age as an integer, nationality as a string, locality as a string, and ability level as a string
5. THE Ability_Assessment prompt sent to Bedrock_Client SHALL include current pace in seconds per 100 m, SWOLF score, and stroke rate in strokes per minute from Session_Metrics
6. THE Bedrock_Client SHALL request the AI to estimate the swimmer's percentile ranking within their age group (e.g., "top 25%")
7. THE Bedrock_Client SHALL request the AI to estimate local competition ranking relative to other swimmers in the specified locality
8. THE Bedrock_Client SHALL request the AI to estimate national competition ranking relative to other swimmers in the specified nationality
9. THE Bedrock_Client SHALL request the AI to assess how competitive the swimmer is for their stated age and population context
10. IF the Bedrock invocation fails with a network error or HTTP non-2xx status, THEN THE System SHALL retry the invocation once
11. IF the Bedrock invocation fails after one retry, THEN THE System SHALL return a BedrockError with message "AI coach unavailable for ability assessment"
12. THE Ability_Assessment returned SHALL contain structured text with a minimum length of 1 character and a maximum length of 800 characters

### Requirement 8: Parse and Validate Ability Assessment Response

**User Story:** As a developer, I want structured ability assessment data, so that the frontend can reliably display the assessment.

#### Acceptance Criteria

1. THE Backend SHALL define an AbilityAssessment dataclass with fields: percentile_estimate (str), local_ranking (str), national_ranking (str), competitive_analysis (str)
2. WHEN the Backend receives an AI response containing ability assessment data, THE Backend SHALL parse the tool-use input into the AbilityAssessment structure
3. WHEN the AI response cannot be parsed into valid AbilityAssessment structure after one retry, THE Backend SHALL return a BedrockError
4. THE AbilityAssessment dataclass SHALL validate in __post_init__ that percentile_estimate is non-empty and does not exceed 100 characters
5. THE AbilityAssessment dataclass SHALL validate in __post_init__ that local_ranking is non-empty and does not exceed 200 characters
6. THE AbilityAssessment dataclass SHALL validate in __post_init__ that national_ranking is non-empty and does not exceed 200 characters
7. THE AbilityAssessment dataclass SHALL validate in __post_init__ that competitive_analysis is non-empty and does not exceed 800 characters

### Requirement 9: Display Ability Assessment

**User Story:** As a swimmer, I want to see my ability assessment, so that I can understand my competitive standing.

#### Acceptance Criteria

1. WHEN the Frontend receives an Ability_Assessment object, THE Frontend SHALL display the percentile estimate with label "Percentile Ranking"
2. WHEN the Frontend receives an Ability_Assessment object, THE Frontend SHALL display the local ranking estimate with label "Local Ranking"
3. WHEN the Frontend receives an Ability_Assessment object, THE Frontend SHALL display the national ranking estimate with label "National Ranking"
4. WHEN the Frontend receives an Ability_Assessment object, THE Frontend SHALL display the competitive analysis text with label "Competitive Analysis"
5. THE Frontend SHALL render the ability assessment in a dedicated card component positioned immediately below the coaching tips card
6. WHEN the Frontend receives a response with no Ability_Assessment object (because user profile is incomplete), THE Frontend SHALL not display the ability assessment card

### Requirement 10: Enhance Training Plan with Profile Context

**User Story:** As a swimmer, I want training plans that consider my profile, so that recommendations are realistic for my age and ability level.

#### Acceptance Criteria

1. WHEN generating a training plan with a complete User_Profile available, THE System SHALL include the user's age in the Bedrock prompt
2. WHEN generating a training plan with a complete User_Profile available, THE System SHALL include the user's ability level in the Bedrock prompt
3. WHEN generating a training plan with a complete User_Profile available, THE System SHALL include the user's locality in the Bedrock prompt
4. WHEN an Ability_Assessment exists for the current session, THE System SHALL include the competitive_analysis field from the Ability_Assessment in the training plan prompt
5. WHEN generating a training plan with no User_Profile available, THE System SHALL omit age, ability level, and locality from the Bedrock prompt
6. THE training plan prompt SHALL request the AI to evaluate likelihood of reaching the stated goal
7. THE training plan prompt SHALL request the AI to adjust interval targets by at least 5% based on the difference between current pace and goal pace
8. WHEN the generated training plan contains interval recommendations, THE System SHALL verify that at least one interval target differs from current pace by the requested adjustment

### Requirement 11: Add Likelihood Assessment to Training Plan

**User Story:** As a swimmer, I want to know if my goal is realistic, so that I can set achievable targets.

#### Acceptance Criteria

1. THE Backend SHALL extend the TrainingPlan dataclass to include a goal_likelihood field of type string with a maximum length of 300 characters
2. THE training plan tool schema SHALL include goal_likelihood as a required field with a minimum length of 1 character and a maximum length of 300 characters
3. THE goal_likelihood field SHALL contain the AI's assessment stating whether the swimmer's goal is achievable, challenging but achievable, or unrealistic based on current pace, SWOLF, stroke rate, stated timeframe, and user profile if available
4. IF the Bedrock response omits the goal_likelihood field or returns an empty string, THEN THE Backend SHALL retry the request once
5. IF the Bedrock response fails validation after one retry, THEN THE Backend SHALL return HTTP 502 with error message indicating invalid training plan response
6. WHEN a training plan is generated, THE Frontend SHALL display the goal likelihood assessment above the session plan title

### Requirement 12: Integrate Heart Rate Zones into Upload Flow

**User Story:** As a swimmer, I want heart rate zone analysis to appear automatically after upload, so that I can review intensity distribution alongside other metrics.

#### Acceptance Criteria

1. WHEN a FIT file with heart rate data is uploaded and a User_Profile with age exists, IF the heart rate zone calculation succeeds, THEN THE System SHALL include HR_Zones_Data in the response
2. WHEN a FIT file with heart rate data is uploaded and a User_Profile with age exists, IF the heart rate zone calculation fails, THEN THE Backend SHALL return HTTP 422 with error message describing the calculation failure reason
3. WHEN a FIT file is uploaded without a User_Profile or without an age field in the User_Profile, THE System SHALL omit HR_Zones_Data from the response
4. THE Backend SHALL include HR_Zones_Data as a separate field in the FullResponse JSON object alongside session, splits, metrics, and coaching
5. WHEN the Frontend receives a FullResponse containing HR_Zones_Data, THE Frontend SHALL display the heart rate zones card between the splits table and the coaching results card
6. WHEN the user has not provided their age, THE Frontend SHALL display the prompt "Complete your profile to enable heart rate zone analysis" above the file upload control
7. THE System SHALL use the age from the User_Profile most recently stored in Profile_Store at the time of FIT file upload

### Requirement 13: Handle Missing User Profile Gracefully

**User Story:** As a swimmer, I want the app to work without a profile, so that I can use basic features immediately.

#### Acceptance Criteria

1. WHEN no User_Profile exists in Profile_Store for the current user, THE System SHALL process FIT files and generate exactly three coaching tips and one drill
2. WHEN no User_Profile exists in Profile_Store for the current user, THE System SHALL omit the hr_zones field from the JSON response
3. WHEN no User_Profile exists in Profile_Store for the current user, THE Frontend SHALL not display the heart rate zones card
4. WHEN no User_Profile exists in Profile_Store for the current user, THE System SHALL omit the ability_assessment field from the JSON response
5. WHEN no User_Profile exists in Profile_Store for the current user, THE Frontend SHALL not display the ability assessment card
6. WHEN generating a training plan and no User_Profile exists, THE System SHALL omit age, ability_level, and locality from the Bedrock prompt
7. WHEN the Frontend loads and no User_Profile exists, THE Frontend SHALL display the user profile form above the file upload control

### Requirement 14: Round-Trip Property for User Profile Serialization

**User Story:** As a developer, I want confidence that user profiles are preserved correctly, so that profile data integrity is maintained.

#### Acceptance Criteria

1. FOR ALL valid UserProfile objects, serializing to JSON then deserializing SHALL produce a UserProfile object where age, nationality, locality, and ability_level match the original values
2. THE serialization format SHALL preserve age as an integer (not a string or floating-point number)
3. THE serialization format SHALL preserve nationality as a string (empty string if not provided)
4. THE serialization format SHALL preserve locality as a string (empty string if not provided)
5. THE serialization format SHALL preserve ability_level as a string with one of the four enumerated values
6. WHEN a UserProfile is stored in Profile_Store and retrieved, ALL fields (age, nationality, locality, ability_level) SHALL match the original values exactly
7. IF a UserProfile contains an empty string for nationality or locality, THEN serialization followed by deserialization SHALL preserve the empty string (not convert to null or omit the field)

### Requirement 15: Store Multiple Session History

**User Story:** As a swimmer, I want to upload multiple FIT files over time, so that I can track my progress across multiple training sessions.

#### Acceptance Criteria

1. WHEN the Backend processes a FIT file upload successfully, THE System SHALL persist the session data to a Sessions_Store with a unique session identifier formatted as a UUID version 4
2. THE Sessions_Store SHALL store session_id as a unique string primary key
3. THE Sessions_Store SHALL store user_id as a string to associate the session with a specific user
4. THE Sessions_Store SHALL store session_date as an ISO 8601 datetime string with UTC timezone and second precision extracted from the FIT file
5. THE Sessions_Store SHALL store pool_length_meters as a positive integer
6. THE Sessions_Store SHALL store total_distance_meters as a positive integer
7. THE Sessions_Store SHALL store total_time_seconds as a positive integer
8. THE Sessions_Store SHALL store stroke_type as a string with maximum length 50 characters
9. THE Sessions_Store SHALL store average_pace_per_100m as a decimal number with two decimal places
10. THE Sessions_Store SHALL store swolf_score as an integer
11. THE Sessions_Store SHALL store stroke_rate as a decimal number with one decimal place
12. THE Sessions_Store SHALL store uploaded_at as an ISO 8601 datetime string with UTC timezone and second precision indicating when the file was uploaded
13. WHEN a session is stored successfully, THE Backend SHALL return the session_id in the response
14. IF the persistence to Sessions_Store fails, THEN THE Backend SHALL return HTTP 500 with error message indicating session storage failure

### Requirement 16: Retrieve Session History

**User Story:** As a swimmer, I want to view my past swim sessions, so that I can see my training history.

#### Acceptance Criteria

1. THE Frontend SHALL provide a "History" navigation link in the application header
2. WHEN the user clicks the History link, THE Frontend SHALL navigate to a /history route
3. WHEN the /history page loads, THE Frontend SHALL send a GET request to /sessions endpoint with the user identifier
4. WHEN the Backend receives a GET request to /sessions with a valid user identifier, THE Backend SHALL query Sessions_Store for all sessions belonging to that user
5. THE Backend SHALL return sessions ordered by session_date in descending order (most recent first)
6. THE Backend SHALL return a JSON array where each session object contains: session_id, session_date, pool_length_meters, total_distance_meters, total_time_seconds, stroke_type, average_pace_per_100m, swolf_score, stroke_rate
7. WHEN the Frontend receives the session history array, THE Frontend SHALL display a list of session summaries showing date, distance, time, and stroke type for each session
8. WHEN no sessions exist for the user, THE Backend SHALL return an empty array with HTTP 200
9. WHEN the Frontend receives an empty session history array, THE Frontend SHALL display the message "No swim sessions found. Upload your first FIT file to get started!"
10. IF the Sessions_Store query fails, THEN THE Backend SHALL return HTTP 500 with error message indicating session retrieval failure

### Requirement 17: Display Session History in Calendar View

**User Story:** As a swimmer, I want to see my swim sessions on a calendar, so that I can visualize my training frequency.

#### Acceptance Criteria

1. THE Frontend SHALL display a calendar component on the /history page showing the current month by default
2. THE Frontend SHALL allow navigation to previous and next months using arrow buttons
3. WHEN the Frontend receives session history data, THE Frontend SHALL mark each date that has one or more sessions with a visual indicator (e.g., colored dot or badge)
4. WHEN a calendar date is marked with sessions, THE Frontend SHALL display the total distance in meters for that date below the date number
5. WHEN the user clicks on a marked date, THE Frontend SHALL display a list of sessions for that date below the calendar
6. WHEN multiple sessions exist on the same date, THE Frontend SHALL display each session separately with time of day, distance, and stroke type
7. WHEN a date has no sessions, clicking on it SHALL display no session details
8. THE calendar component SHALL highlight the current date with a distinct visual style

### Requirement 18: Display Progress Graph

**User Story:** As a swimmer, I want to see a graph of my total distance over time, so that I can track my training volume.

#### Acceptance Criteria

1. THE Frontend SHALL display a line chart on the /history page below the calendar showing total distance swum per day over the last 30 days
2. THE x-axis of the chart SHALL display dates in a readable format (e.g., "Jan 15", "Jan 22")
3. THE y-axis of the chart SHALL display distance in meters with appropriate scale (e.g., 0, 500, 1000, 1500, 2000)
4. WHEN multiple sessions exist on the same date, THE chart SHALL sum the total distance for that date
5. WHEN no sessions exist on a date within the 30-day range, THE chart SHALL display that date with zero distance
6. THE chart SHALL use a line connecting data points with markers indicating days with sessions
7. THE chart SHALL use the same blue color scheme consistent with the application's design (blue-500 for the line)
8. WHEN the user hovers over a data point, THE chart SHALL display a tooltip showing the exact date and total distance in meters
9. THE Frontend SHALL allow the user to change the time range using a dropdown with options: Last 7 Days, Last 30 Days, Last 90 Days, All Time
10. WHEN the time range is changed, THE Frontend SHALL update the chart to display data for the selected range

### Requirement 19: Link Session History to Detail View

**User Story:** As a swimmer, I want to view detailed results for a past session, so that I can review my performance and coaching feedback.

#### Acceptance Criteria

1. WHEN the Frontend displays a session summary in the history list or calendar, THE Frontend SHALL render the session as a clickable link
2. WHEN the user clicks on a session summary, THE Frontend SHALL navigate to a /session/:sessionId route
3. WHEN the /session/:sessionId page loads, THE Frontend SHALL send a GET request to /sessions/:sessionId endpoint
4. WHEN the Backend receives a GET request to /sessions/:sessionId with a valid session identifier, THE Backend SHALL retrieve the full session data including session metrics, splits, coaching tips, training plan (if generated), and ability assessment (if generated)
5. THE Backend SHALL return HTTP 200 with a JSON object containing all session details
6. WHEN the Frontend receives the full session data, THE Frontend SHALL display the same layout as the upload results page: session summary, splits table, heart rate zones (if available), coaching tips, ability assessment (if available), and training plan (if available)
7. WHEN the session identifier does not exist in Sessions_Store, THE Backend SHALL return HTTP 404 with error message indicating session not found
8. IF the Sessions_Store query fails, THEN THE Backend SHALL return HTTP 500 with error message indicating session retrieval failure

### Requirement 20: Update Upload Flow to Save Sessions

**User Story:** As a swimmer, I want my uploaded sessions to be automatically saved to history, so that I can review them later.

#### Acceptance Criteria

1. WHEN the Backend successfully processes a FIT file upload and generates coaching tips, THE Backend SHALL persist the session to Sessions_Store before returning the response
2. THE Backend SHALL extract the user_id from the authentication context JWT token in the Authorization header
3. IF no Authorization header is present or the JWT token is invalid, THE Backend SHALL return HTTP 401 with error message indicating authentication required
4. WHEN the session is saved successfully, THE response SHALL include a session_id field
5. WHEN the Frontend receives a response with a session_id, THE Frontend SHALL display a success message with a link to view the session in history
6. IF the session save fails, THE Backend SHALL log the error but still return the coaching results to the Frontend (session history feature should not block primary upload functionality)
7. THE success message SHALL include text: "Session saved! View your training history to track progress."

### Requirement 21: User Authentication with Email and Password

**User Story:** As a swimmer, I want to create an account and log in, so that my data is private and accessible across sessions.

#### Acceptance Criteria

1. THE Frontend SHALL provide a registration form with fields: email (email input), password (password input with minimum 8 characters), and confirm password (password input)
2. THE Frontend SHALL validate that email is in valid email format before enabling the submit button
3. THE Frontend SHALL validate that password is at least 8 characters before enabling the submit button
4. THE Frontend SHALL validate that password and confirm password match before enabling the submit button
5. WHEN the user submits the registration form with valid data, THE Frontend SHALL send a POST request to /auth/register endpoint with JSON payload containing email and password fields
6. WHEN the Backend receives a registration request, THE Backend SHALL hash the password using bcrypt with a cost factor of 12
7. WHEN the Backend receives a registration request, THE Backend SHALL check if the email already exists in the Users_Store
8. IF the email already exists in Users_Store, THEN THE Backend SHALL return HTTP 409 with error message "Email already registered"
9. IF the email does not exist, THE Backend SHALL create a new user record in Users_Store with user_id (UUID v4), email, hashed_password, created_at (ISO 8601 UTC timestamp), and return HTTP 201 with a success message
10. THE Frontend SHALL provide a login form with fields: email (email input) and password (password input)
11. WHEN the user submits the login form, THE Frontend SHALL send a POST request to /auth/login endpoint with JSON payload containing email and password fields
12. WHEN the Backend receives a login request, THE Backend SHALL retrieve the user record from Users_Store by email
13. IF no user exists with the provided email, THEN THE Backend SHALL return HTTP 401 with error message "Invalid email or password"
14. IF the user exists, THE Backend SHALL verify the password against the stored hashed_password using bcrypt
15. IF the password does not match, THEN THE Backend SHALL return HTTP 401 with error message "Invalid email or password"
16. IF the password matches, THE Backend SHALL generate a JWT token with claims: user_id, email, issued_at (iat), expiration (exp set to 7 days from now)
17. THE Backend SHALL sign the JWT token using a secret key stored in environment variable JWT_SECRET
18. THE Backend SHALL return HTTP 200 with a JSON payload containing the JWT token and user information (user_id, email)
19. WHEN the Frontend receives a successful login response, THE Frontend SHALL store the JWT token in localStorage under key "auth_token"
20. WHEN the Frontend makes authenticated API requests, THE Frontend SHALL include the JWT token in the Authorization header as "Bearer <token>"
21. WHEN the Backend receives a request with an Authorization header, THE Backend SHALL extract and verify the JWT token
22. IF the JWT token is expired or invalid, THE Backend SHALL return HTTP 401 with error message "Invalid or expired token"

### Requirement 22: Protected Routes and Navigation

**User Story:** As a swimmer, I want to access my data only after logging in, so that my information is secure.

#### Acceptance Criteria

1. WHEN the Frontend application loads, THE Frontend SHALL check for an auth_token in localStorage
2. IF no auth_token exists, THE Frontend SHALL redirect the user to the /login route
3. IF an auth_token exists, THE Frontend SHALL attempt to verify it by sending a GET request to /auth/verify endpoint with the token in the Authorization header
4. IF the token verification fails (HTTP 401), THE Frontend SHALL remove the token from localStorage and redirect to /login
5. IF the token verification succeeds (HTTP 200), THE Frontend SHALL allow access to protected routes (/upload, /history, /profile, /session/:id)
6. THE Frontend SHALL display a "Logout" button in the application header when the user is authenticated
7. WHEN the user clicks the Logout button, THE Frontend SHALL remove the auth_token from localStorage and redirect to /login
8. THE Frontend SHALL display the user's email address in the application header when authenticated
9. WHEN the user is on the /login page and already has a valid token, THE Frontend SHALL redirect to /upload page
10. THE Backend SHALL require a valid JWT token for all endpoints except /auth/register, /auth/login, and /auth/verify

### Requirement 23: Upload Profile Picture

**User Story:** As a swimmer, I want to upload a profile picture, so that I can personalize my account.

#### Acceptance Criteria

1. THE Frontend SHALL provide a profile picture upload control on the user profile page with an image preview area showing the current profile picture or a placeholder avatar
2. THE Frontend SHALL accept image files with extensions .jpg, .jpeg, .png, and .gif with a maximum file size of 2 MB
3. WHEN the user selects a valid image file, THE Frontend SHALL display a preview of the image before upload
4. WHEN the user clicks the "Save Profile Picture" button, THE Frontend SHALL send a POST request to /profile/picture endpoint with the image file as multipart/form-data
5. WHEN the Backend receives a profile picture upload, THE Backend SHALL validate that the file is an image (JPEG, PNG, or GIF) by checking the file header magic bytes
6. IF the file is not a valid image, THEN THE Backend SHALL return HTTP 400 with error message "Invalid image file format"
7. IF the file size exceeds 2 MB, THEN THE Backend SHALL return HTTP 413 with error message "Image file size exceeds 2 MB limit"
8. WHEN the Backend validates the image successfully, THE Backend SHALL generate a unique filename using the format: {user_id}_{timestamp}.{extension}
9. THE Backend SHALL upload the image to an S3 bucket named ai-swim-coach-profile-pictures with the generated filename
10. THE Backend SHALL store the S3 object key in the Users_Store under the profile_picture_url field for the authenticated user
11. THE Backend SHALL return HTTP 200 with a JSON payload containing the profile_picture_url field with the full S3 URL
12. WHEN the Frontend receives a successful upload response, THE Frontend SHALL update the profile picture preview with the new image URL
13. WHEN the Frontend displays the user profile, THE Frontend SHALL fetch the profile picture from the profile_picture_url field and display it in a circular avatar format with 120px diameter
14. IF no profile picture exists, THE Frontend SHALL display a default avatar icon
15. THE S3 bucket SHALL be configured with public read access for profile pictures

### Requirement 24: Display Profile Picture in Header

**User Story:** As a swimmer, I want to see my profile picture in the header, so that I know I'm logged into my account.

#### Acceptance Criteria

1. WHEN the user is authenticated, THE Frontend SHALL display the user's profile picture in the application header next to the email address
2. THE profile picture in the header SHALL be displayed in a circular avatar format with 40px diameter
3. IF the user has not uploaded a profile picture, THE Frontend SHALL display a default avatar icon in the header
4. WHEN the user clicks on the profile picture in the header, THE Frontend SHALL navigate to the /profile page
5. THE profile picture SHALL load asynchronously and display a loading spinner while the image is being fetched
6. IF the profile picture fails to load, THE Frontend SHALL fall back to displaying the default avatar icon

### Requirement 25: Strava/Garmin-Inspired UI Layout

**User Story:** As a swimmer familiar with fitness tracking apps, I want the interface to follow familiar patterns from Strava and Garmin, so that navigation and data presentation feel intuitive.

#### Acceptance Criteria

1. THE Frontend SHALL use a card-based layout for displaying session data, with each metric group (session summary, splits, heart rate zones, coaching) in a separate white card with subtle shadow
2. THE Frontend SHALL display the session summary at the top of the page with large, bold numbers for key metrics (distance, time, pace)
3. THE Frontend SHALL use a left sidebar navigation menu with icons and labels for: Dashboard, Upload, History, Profile, Logout
4. THE Frontend SHALL display activity cards in the history view with: date/time as header, distance and duration as primary metrics, stroke type and pool length as secondary details
5. THE Frontend SHALL use orange/red accent colors for intense zones (Zone 4, Zone 5) and blue/green for recovery zones (Zone 1, Zone 2) in the heart rate zone visualization
6. THE Frontend SHALL display the progress graph with a clean grid background and prominent data points, following the visual style of Strava's training log charts
7. THE calendar view SHALL use a month grid layout with activity indicators (colored dots or badges) on days with sessions, similar to Garmin Connect's calendar
8. THE profile page SHALL display the profile picture in a large circular format at the top center, with profile details in organized sections below
9. THE Frontend SHALL use a consistent header bar with app logo on the left, navigation items in the center, and user profile/avatar on the right
10. THE Frontend SHALL use a cohesive color scheme: dark navy (#1e293b) for headers/sidebar, white (#ffffff) for card backgrounds, blue-500 (#3b82f6) for primary actions, and gray-100 (#f1f5f9) for page backgrounds

