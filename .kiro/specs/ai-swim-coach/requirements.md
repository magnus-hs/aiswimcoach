# Requirements Document

## Introduction

AI Swim Coach is a web application that allows swimmers to upload Garmin `.fit` files from their workouts and receive personalized coaching feedback powered by AI. The system parses swim metrics (pace, SWOLF, stroke rate) from the uploaded file, sends them to an AI model acting as an elite swim coach, and returns three actionable tips and one drill to the user. The backend is fully serverless on AWS, and the frontend is a React application hosted via AWS Amplify.

## Glossary

- **User**: A swimmer who interacts with the AI Swim Coach web application.
- **FIT_File**: A binary file in the Garmin `.fit` format containing recorded swim workout data.
- **API_Gateway**: The AWS API Gateway endpoint that accepts file upload requests from the frontend.
- **Lambda**: The AWS Lambda function (Python) that orchestrates file storage, parsing, AI invocation, and persistence.
- **S3**: The AWS S3 bucket where raw FIT files are stored.
- **Parser**: The component within Lambda that uses the `fitparse` library to extract swim metrics from a FIT file.
- **Metrics**: The extracted swim data — pace, SWOLF score, and stroke rate — derived from the FIT file.
- **Bedrock_Client**: The component within Lambda that sends Metrics to Amazon Bedrock (Anthropic Claude 3.5 Sonnet) using a custom system prompt.
- **Coaching_Response**: The AI-generated output containing exactly three improvement tips and one drill recommendation.
- **DynamoDB**: The AWS DynamoDB table used to persist Coaching_Responses.
- **Frontend**: The React application hosted via AWS Amplify through which users interact with the system.
- **System_Prompt**: A predefined instruction set sent to Bedrock that instructs the model to act as an elite swim coach.

---

## Requirements

### Requirement 1: File Upload

**User Story:** As a swimmer, I want to upload my Garmin `.fit` file through the web app, so that the system can analyse my workout data.

#### Acceptance Criteria

1. THE Frontend SHALL provide a file upload control that accepts only files with the `.fit` extension and rejects all other file types before submission.
2. WHEN a User selects a file that does not have a `.fit` extension, THE Frontend SHALL display an error message indicating that only `.fit` files are accepted, and SHALL NOT submit the file.
3. WHEN a User selects a `.fit` file larger than 100 MB, THE Frontend SHALL display an error message stating the file exceeds the maximum allowed size and SHALL NOT submit the file.
4. WHEN a User submits a valid `.fit` file of 100 MB or less, THE Frontend SHALL send the file to the API_Gateway endpoint via an HTTP POST request with the file as multipart/form-data.
5. WHILE a file upload is in progress, THE Frontend SHALL display a loading indicator to the User and SHALL disable the upload control to prevent duplicate submissions.
6. WHEN the Frontend receives a successful HTTP 200 response, THE Frontend SHALL hide the loading indicator and display the Coaching_Response to the User.
7. IF the HTTP POST request fails due to a network error, THEN THE Frontend SHALL hide the loading indicator, display an error message describing the failure, and present a retry action to the User.
8. IF the Frontend receives an HTTP 4xx or 5xx response, THEN THE Frontend SHALL hide the loading indicator and display a descriptive error message corresponding to the HTTP status code.

---

### Requirement 2: API Gateway Routing

**User Story:** As a system operator, I want all upload requests routed to the correct Lambda function, so that the backend processes every request consistently.

#### Acceptance Criteria

1. THE API_Gateway SHALL expose a single POST endpoint at `/upload` that accepts multipart/form-data payloads.
2. WHEN a POST request is received at `/upload`, THE API_Gateway SHALL invoke the Lambda function synchronously and return the Lambda's response to the caller within 29 seconds.
3. IF the Lambda function returns an error response, THEN THE API_Gateway SHALL forward that error response with its HTTP status code unchanged to the caller.
4. THE API_Gateway SHALL enforce a maximum request payload size of 10 MB and SHALL return HTTP 413 for any request that exceeds this limit.
5. WHEN a request is received at `/upload` using any HTTP method other than POST, THE API_Gateway SHALL return HTTP 405.

---

### Requirement 3: Raw File Storage

**User Story:** As a system operator, I want every uploaded FIT file stored in S3, so that raw workout data is preserved for auditing and reprocessing.

#### Acceptance Criteria

1. WHEN the Lambda function is invoked with a FIT_File payload between 1 byte and 6 MB in size, THE Lambda SHALL store the FIT_File in S3 without modification before performing any other processing.
2. WHEN the Lambda stores a FIT_File in S3, THE Lambda SHALL assign it a unique key composed of a UUID (e.g., `uploads/{uuid}.fit`) so that concurrent uploads do not overwrite each other.
3. IF the S3 write operation fails, THEN THE Lambda SHALL return an HTTP 500 response to the API_Gateway and halt further processing without attempting to parse or invoke Bedrock.
4. IF the incoming request payload does not contain a FIT_File, THEN THE Lambda SHALL return an HTTP 400 response and halt further processing.

---

### Requirement 4: FIT File Parsing

**User Story:** As a swimmer, I want my swim metrics extracted from my FIT file, so that the AI coach has accurate data to base its feedback on.

#### Acceptance Criteria

1. WHEN a FIT_File has been successfully stored in S3, THE Parser SHALL parse the FIT_File using the `fitparse` library to attempt extraction of pace, SWOLF, and stroke rate values.
2. THE Parser SHALL extract per-length metric values when present in the FIT_File; WHERE per-length values are absent, THE Parser SHALL fall back to per-lap values.
3. IF the FIT_File does not contain at least one of pace, SWOLF, or stroke rate, THEN THE Lambda SHALL return an HTTP 422 response whose body identifies each missing metric by name.
4. IF the FIT_File is malformed or raises an exception during `fitparse` parsing, THEN THE Lambda SHALL return an HTTP 422 response with a descriptive error message and SHALL NOT proceed to Bedrock invocation.
5. FOR ALL FIT_Files that the `fitparse` library parses without error and that contain pace, SWOLF, and stroke rate, THE Parser SHALL produce a Metrics object whose pace, SWOLF, and stroke rate fields each contain only finite numeric values (integers or floats, excluding NaN and Infinity).

---

### Requirement 5: AI Coaching Feedback

**User Story:** As a swimmer, I want AI-generated coaching advice based on my swim metrics, so that I receive personalised, actionable guidance to improve my technique.

#### Acceptance Criteria

1. WHEN a Metrics object containing pace, SWOLF, and stroke rate has been successfully produced by the Parser, THE Bedrock_Client SHALL send those Metrics to Amazon Bedrock using the `anthropic.claude-3-5-sonnet-20240620-v1:0` model ID together with the System_Prompt.
2. THE System_Prompt SHALL instruct the model to act as an elite swim coach and to respond with a structured output containing exactly three improvement tips and one drill recommendation, with no additional top-level fields.
3. WHEN the Bedrock API returns a 200 response, THE Bedrock_Client SHALL parse the response body and construct a Coaching_Response containing a `tips` list of exactly three non-empty strings and a `drill` non-empty string.
4. IF the Amazon Bedrock API returns a non-2xx HTTP status code or raises a network exception, THEN THE Lambda SHALL return an HTTP 502 response to the API_Gateway without retrying.
5. IF the Bedrock response body cannot be parsed or does not yield exactly three tips and one drill, THEN THE Lambda SHALL retry the Bedrock_Client invocation exactly once with the same inputs; IF the retry also fails to produce a valid Coaching_Response, THEN THE Lambda SHALL return an HTTP 502 response.

---

### Requirement 6: Coaching Response Persistence

**User Story:** As a system operator, I want coaching responses stored in DynamoDB, so that previous sessions can be retrieved and audited.

#### Acceptance Criteria

1. WHEN a Coaching_Response containing exactly three tips and one drill has been constructed, THE Lambda SHALL attempt to write the Coaching_Response to DynamoDB before returning the response to the API_Gateway.
2. THE Lambda SHALL store each Coaching_Response record in DynamoDB using the S3 file key as the partition key and an ISO 8601 UTC millisecond-precision timestamp as the sort key, together with the Metrics object and the full Coaching_Response.
3. IF the DynamoDB write operation fails, THEN THE Lambda SHALL record an error entry in the system log containing the S3 file key and the error detail, and SHALL still return the Coaching_Response to the Frontend with HTTP 200 so that the User receives their feedback.

---

### Requirement 7: Response Delivery to Frontend

**User Story:** As a swimmer, I want to see my AI coaching tips and drill on screen after uploading my file, so that I can act on the feedback immediately.

#### Acceptance Criteria

1. WHEN Lambda processing completes successfully, THE API_Gateway SHALL return an HTTP 200 response whose body is a JSON object containing the Coaching_Response.
2. THE Coaching_Response JSON SHALL include a `tips` array of exactly three non-empty strings each no longer than 300 characters, and a `drill` non-empty string no longer than 500 characters.
3. WHEN the Frontend receives an HTTP 200 response, THE Frontend SHALL display three individually labelled tips and a visually distinct drill section, all visible without any additional user interaction.
4. IF the Frontend receives an HTTP 4xx response, THEN THE Frontend SHALL display a descriptive error message that identifies the nature of the client-side error (e.g., unsupported file, payload too large).
5. IF the Frontend receives an HTTP 5xx response, THEN THE Frontend SHALL display a descriptive error message indicating a server-side failure and advising the User to try again.

---

### Requirement 8: Frontend Hosting and Accessibility

**User Story:** As a swimmer, I want to access the AI Swim Coach application from any modern browser, so that I can use it without installing software.

#### Acceptance Criteria

1. THE Frontend SHALL be deployed and served via AWS Amplify such that the application is reachable via a public HTTPS URL.
2. THE Frontend SHALL be a React application that, on the current stable major version of Chrome (≥ 125), Firefox (≥ 126), Safari (≥ 17), and Edge (≥ 125), loads without JavaScript errors, renders all interactive elements as operable, and presents no broken layout.
3. THE Frontend SHALL meet WCAG 2.1 Level AA accessibility requirements for all interactive elements.
