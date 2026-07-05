# Requirements Document

## Introduction

This feature adds two capabilities to the AI Swim Coach: (1) persisting Q&A conversation history to S3 so the AI coach maintains context across follow-up questions, and (2) a personal notes system where swimmers can record training observations (e.g. injuries, group changes, illness) that the AI coach reads when generating answers to explain anomalies or context changes.

## Glossary

- **Chat_History_Store**: The S3-based storage layer responsible for persisting and retrieving per-user Q&A conversation history under the `ai-swim-coach-*` bucket.
- **AI_Chat_Endpoint**: The POST /ai/chat Lambda handler that receives user prompts, assembles context, and invokes Bedrock to generate coaching responses.
- **Notes_Store**: The DynamoDB-based storage layer responsible for persisting and retrieving user training notes.
- **Notes_API**: The backend API endpoints for creating, retrieving, and deleting user training notes.
- **Notes_UI**: The frontend component on the activity dashboard page that allows users to input and view personal training notes.
- **Conversation_Context**: The assembled collection of prior Q&A exchanges and user notes included in the AI prompt to provide conversational continuity.
- **User_ID**: The unique identifier for an authenticated user, extracted from the JWT auth token.

## Requirements

### Requirement 1: Persist Chat Q&A History to S3

**User Story:** As a swimmer, I want my AI coach conversations saved, so that when I ask follow-up questions the coach remembers what we previously discussed.

#### Acceptance Criteria

1. WHEN the AI_Chat_Endpoint returns a successful response, THE Chat_History_Store SHALL persist both the user prompt and the AI response as a Q&A entry to S3 under the key prefix `chat-history/{User_ID}/`.
2. THE Chat_History_Store SHALL store each conversation entry as a JSON object containing the fields: user prompt (string, maximum 2000 characters), AI response (string), and timestamp (ISO 8601 UTC format).
3. WHEN a new chat prompt is received, THE AI_Chat_Endpoint SHALL retrieve the user's prior Q&A history from the Chat_History_Store before invoking Bedrock.
4. THE AI_Chat_Endpoint SHALL include up to the 10 most recent Q&A exchanges, ordered by timestamp descending, in the Bedrock prompt as conversation context.
5. IF the Chat_History_Store retrieval fails, THEN THE AI_Chat_Endpoint SHALL continue processing the request without historical context and log the error at ERROR level with the user ID and failure reason.
6. IF the Chat_History_Store persistence fails, THEN THE AI_Chat_Endpoint SHALL still return the AI response to the user and log the error at ERROR level with the user ID and failure reason.
7. THE Chat_History_Store SHALL store all Q&A entries for a single user in a single JSON file at `chat-history/{User_ID}/history.json`, appending new entries to the end of the JSON array, retaining a maximum of 50 entries and discarding the oldest entries when the limit is exceeded.
8. FOR ALL Q&A entries containing a non-empty user prompt, a non-empty AI response, and a valid ISO 8601 timestamp, reading then writing then reading the history SHALL produce an equivalent list of entries (round-trip property).

### Requirement 2: Include Conversation History in AI Prompt

**User Story:** As a swimmer, I want the AI coach to reference my earlier questions and its previous answers, so that I get coherent follow-up analysis without repeating context.

#### Acceptance Criteria

1. WHEN the request body contains a conversation_history array with one or more exchanges (where one exchange is one user message paired with one assistant message), THE AI_Chat_Endpoint SHALL format those exchanges as alternating user/assistant message pairs in the Bedrock messages array.
2. THE AI_Chat_Endpoint SHALL order historical messages chronologically, with the oldest exchange first and the current user prompt appended as the final message in the array.
3. WHILE the conversation_history array contains more than 10 exchanges, THE AI_Chat_Endpoint SHALL include only the 10 most recent exchanges preceding the current prompt and discard older exchanges.
4. IF the request body does not contain a conversation_history field or the array is empty, THEN THE AI_Chat_Endpoint SHALL send only the current user prompt in the messages array without any historical context.
5. THE AI_Chat_Endpoint SHALL prepend a system-level instruction stating that prior conversation context is included and that the model should maintain continuity with previous answers.
6. IF any entry in the conversation_history array is missing a required role or content field, THEN THE AI_Chat_Endpoint SHALL omit that malformed entry from the messages array and process the remaining valid entries.

### Requirement 3: Personal Training Notes Storage

**User Story:** As a swimmer, I want to record personal training notes (e.g. "shoulder felt tight", "changed training group"), so that relevant context is available for the AI coach to explain anomalies in my data.

#### Acceptance Criteria

1. WHEN a user submits a note via POST /notes, THE Notes_API SHALL persist the note in the Notes_Store with the User_ID, a system-generated note_id, the note text, and an ISO 8601 timestamp, and return HTTP 201 with the created note object.
2. THE Notes_API SHALL validate that the note text contains between 1 and 500 characters after trimming leading and trailing whitespace.
3. IF the note text is empty, contains only whitespace, or exceeds 500 characters after trimming, THEN THE Notes_API SHALL return HTTP 400 with an error message indicating the validation failure reason.
4. WHEN a user requests GET /notes, THE Notes_API SHALL return up to 200 notes for that User_ID ordered by timestamp descending.
5. WHEN a user requests DELETE /notes/{note_id}, THE Notes_API SHALL remove the specified note only if it belongs to the authenticated User_ID and return HTTP 200 on success.
6. IF a user attempts to delete a note that does not exist or belongs to another user, THEN THE Notes_API SHALL return HTTP 404.
7. THE Notes_Store SHALL use the DynamoDB table with User_ID as the partition key and note_id as the sort key.
8. IF the Notes_Store persistence or retrieval operation fails, THEN THE Notes_API SHALL return HTTP 500 with an error message indicating a storage failure.

### Requirement 4: Display Notes on Activity Dashboard

**User Story:** As a swimmer, I want a notes input box on my activity dashboard, so that I can quickly jot down observations about my training without leaving the page.

#### Acceptance Criteria

1. THE Notes_UI SHALL display a multi-line text input area on the activity dashboard page with placeholder text "Add a training note..." and a maximum input length of 500 characters.
2. WHEN the user submits a note containing at least 1 non-whitespace character, THE Notes_UI SHALL send the note text to POST /notes and display the saved note at the top of the notes list.
3. THE Notes_UI SHALL display up to 50 existing notes in reverse chronological order below the input area.
4. WHEN the user clicks a delete button on a note, THE Notes_UI SHALL call DELETE /notes/{note_id} and remove the note from the displayed list.
5. WHILE a note submission is in progress, THE Notes_UI SHALL disable the submit button and show a loading indicator.
6. IF a note submission fails, THEN THE Notes_UI SHALL display an error message indicating the note was not saved and retain the note text in the input area.
7. THE Notes_UI SHALL display the timestamp of each note in a relative format using thresholds: "just now" for under 60 seconds, "N minutes ago" for under 60 minutes, "N hours ago" for under 24 hours, and "N days ago" for 1 day or more.
8. IF the user attempts to submit an empty or whitespace-only note, THEN THE Notes_UI SHALL keep the submit button disabled and not send a request.
9. IF a note deletion fails, THEN THE Notes_UI SHALL display an error message indicating the note was not deleted and restore the note in the displayed list.

### Requirement 5: Include User Notes in AI Coach Context

**User Story:** As a swimmer, I want the AI coach to read my personal notes when answering questions, so that the coach can explain sudden changes in performance or training patterns.

#### Acceptance Criteria

1. WHEN the AI_Chat_Endpoint processes a prompt, THE AI_Chat_Endpoint SHALL retrieve the user's notes from the Notes_Store ordered by timestamp descending.
2. THE AI_Chat_Endpoint SHALL include up to the 20 most recent notes in the Bedrock prompt as contextual information, where each note is formatted as "[ISO 8601 timestamp]: [note text]" on a separate line.
3. IF the user has zero notes in the Notes_Store, THEN THE AI_Chat_Endpoint SHALL proceed with prompt assembly without a notes context section.
4. IF the Notes_Store retrieval fails, THEN THE AI_Chat_Endpoint SHALL continue processing without notes context, return a successful AI response to the user, and log the error.
5. THE AI_Chat_Endpoint SHALL include a system instruction informing the AI model that user-provided training notes are included as context and that the model should reference relevant notes when explaining sudden changes, anomalies, or gaps in the swimmer's training data.

### Requirement 6: Chat History Size Management

**User Story:** As a system operator, I want conversation history to be bounded in size, so that S3 storage costs remain predictable and prompt sizes stay within model limits.

#### Acceptance Criteria

1. THE Chat_History_Store SHALL retain a maximum of 50 Q&A entries per user.
2. WHEN a new entry would exceed the 50-entry limit, THE Chat_History_Store SHALL remove the oldest entry before appending the new one.
3. WHEN assembling conversation context for a Bedrock prompt, THE AI_Chat_Endpoint SHALL calculate the total character count of all included Q&A exchanges (user prompts and AI responses combined).
4. IF the total character count of the conversation history exceeds 4000 characters, THEN THE AI_Chat_Endpoint SHALL remove the oldest Q&A exchanges one at a time until the remaining history is within the 4000-character limit.
5. IF all prior Q&A exchanges are removed due to truncation, THEN THE AI_Chat_Endpoint SHALL still include the current user prompt and proceed with the Bedrock invocation without historical context.
