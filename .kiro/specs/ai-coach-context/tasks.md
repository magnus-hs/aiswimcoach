# Implementation Plan: AI Coach Context

## Overview

This plan implements conversational memory (S3 chat history) and personal training notes (DynamoDB) for the AI Swim Coach. Backend modules are built and tested first, then integrated into the handler, followed by frontend components and deployment.

## Tasks

- [x] 1. Infrastructure and project setup
  - [x] 1.1 Create DynamoDB table and update IAM policy
    - Create the `ai-swim-coach-notes` DynamoDB table with `user_id` (partition key, String) and `note_id` (sort key, String)
    - Update the `ai-swim-coach-lambda-permissions` IAM inline policy to add `dynamodb:PutItem`, `dynamodb:Query`, `dynamodb:DeleteItem` on `arn:aws:dynamodb:*:562535532900:table/ai-swim-coach-notes`
    - Verify S3 bucket `ai-swim-coach-data-562535532900` already has GetObject/PutObject for the Lambda role (no change needed, new `chat-history/` prefix is covered)
    - _Requirements: 3.7, 1.1_

- [x] 2. Implement chat history store
  - [x] 2.1 Create `backend/chat_history_store.py`
    - Implement `QAEntry` dataclass with `user_prompt` (max 2000 chars), `ai_response`, and `timestamp` (ISO 8601 UTC) fields
    - Implement `get_history(user_id)` — reads `chat-history/{user_id}/history.json` from S3, returns `[]` on missing key or read failure
    - Implement `save_history(user_id, history)` — writes full history list to S3, enforces 50-entry cap by dropping oldest
    - Implement `append_entry(user_id, entry)` — read-modify-write: append entry, enforce 50-cap, persist
    - Use existing `S3_BUCKET` env var and boto3 S3 client pattern from `s3_store.py`
    - _Requirements: 1.1, 1.2, 1.7, 6.1, 6.2_

  - [x] 2.2 Write property test: chat history round-trip (Property 1)
    - **Property 1: Chat history round-trip**
    - For any list of valid QAEntry objects, serialize to JSON and deserialize back, assert equivalence
    - **Validates: Requirements 1.2, 1.8**

  - [x] 2.3 Write property test: history size bounded at 50 (Property 2)
    - **Property 2: History size bounded at 50**
    - For any sequence of N appends (N ≥ 1), assert stored history ≤ 50 entries, and when N > 50, oldest N-50 entries are discarded
    - **Validates: Requirements 1.7, 6.1, 6.2**

- [x] 3. Implement notes service
  - [x] 3.1 Create `backend/notes_service.py`
    - Implement `TrainingNote` dataclass with `user_id`, `note_id` (UUID v4), `text` (1–500 chars trimmed), `timestamp` (ISO 8601 UTC)
    - Implement `create_note(user_id, text)` — validate text, generate UUID + timestamp, PutItem to DynamoDB, return TrainingNote
    - Implement `get_notes(user_id, limit=200)` — Query DynamoDB by partition key, return notes ordered by timestamp descending, capped at limit
    - Implement `delete_note(user_id, note_id)` — Delete note if it belongs to user, raise NotFoundError otherwise
    - Use `NOTES_TABLE` env var (default: `ai-swim-coach-notes`)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

  - [x] 3.2 Write property test: note text validation (Property 6)
    - **Property 6: Note text validation**
    - For any string input, assert acceptance iff trimmed length is between 1 and 500 chars inclusive
    - **Validates: Requirements 3.2, 3.3**

  - [x] 3.3 Write property test: note deletion ownership (Property 7)
    - **Property 7: Note deletion ownership**
    - For any note belonging to user A and delete request from user B, assert success iff A == B
    - **Validates: Requirements 3.5, 3.6**

  - [x] 3.4 Write property test: notes retrieval ordering and bound (Property 8)
    - **Property 8: Notes retrieval ordering and bound**
    - For any set of notes for a user, assert response ordered by timestamp descending and contains ≤ 200 entries
    - **Validates: Requirements 3.4**

- [x] 4. Implement prompt assembler
  - [x] 4.1 Create `backend/prompt_assembler.py`
    - Implement `build_chat_messages(current_prompt, conversation_history, notes, max_exchanges=10, max_history_chars=4000, max_notes=20)`
    - Filter malformed history entries (missing role/content)
    - Order history chronologically (oldest first)
    - Truncate to max_exchanges (keep most recent)
    - Apply 4000-char budget (remove oldest until ≤ budget)
    - Format notes as "[timestamp]: [text]" lines in system prompt (max 20 notes, timestamp descending)
    - Include system instructions for continuity and notes context
    - Append current_prompt as final user message
    - Return `(system_prompt, messages_array)`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 5.1, 5.2, 5.3, 5.5, 6.3, 6.4, 6.5_

  - [x] 4.2 Write property test: prompt includes at most 10 recent exchanges (Property 3)
    - **Property 3: Prompt includes at most 10 most-recent exchanges**
    - For any history of N exchanges, assert output includes min(N, 10) exchanges and they are the most recent
    - **Validates: Requirements 1.4, 2.3**

  - [x] 4.3 Write property test: conversation history chronological ordering (Property 4)
    - **Property 4: Conversation history chronological ordering**
    - For any valid history entries, assert messages array is chronological (oldest first) with current prompt last
    - **Validates: Requirements 2.1, 2.2**

  - [x] 4.4 Write property test: malformed entries filtered (Property 5)
    - **Property 5: Malformed entries filtered**
    - For any mix of valid and malformed entries, assert output contains exactly valid entries and zero malformed
    - **Validates: Requirements 2.6**

  - [x] 4.5 Write property test: notes in prompt limited and formatted (Property 10)
    - **Property 10: Notes in prompt limited and formatted**
    - For any set of 0–200 notes, assert prompt includes ≤ 20 notes formatted as "[timestamp]: [text]" per line, ordered timestamp desc
    - **Validates: Requirements 5.2**

  - [x] 4.6 Write property test: character-budget truncation (Property 11)
    - **Property 11: Character-budget truncation**
    - For any history, assert total chars of included exchanges ≤ 4000 after truncation, and oldest entries removed first
    - **Validates: Requirements 6.3, 6.4**

- [x] 5. Checkpoint - Backend modules tested
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Integrate into handler
  - [x] 6.1 Add notes CRUD routes to `backend/handler.py`
    - Add `POST /notes` route → `_handle_create_note` calling `notes_service.create_note`, return 201
    - Add `GET /notes` route → `_handle_get_notes` calling `notes_service.get_notes`, return 200
    - Add `DELETE /notes/{note_id}` route → `_handle_delete_note` calling `notes_service.delete_note`, return 200 or 404
    - Handle validation errors (400), storage errors (500), auth errors (401)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.8_

  - [x] 6.2 Modify `_handle_ai_chat` to integrate history and notes
    - Import and use `chat_history_store.get_history` (best-effort, log ERROR on failure)
    - Import and use `notes_service.get_notes` (best-effort, log ERROR on failure)
    - Accept optional `conversation_history` array from request body
    - Delegate to `prompt_assembler.build_chat_messages()` for prompt construction
    - After successful Bedrock response, call `chat_history_store.append_entry` (best-effort, log ERROR on failure)
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 1.6, 2.1, 2.2, 2.3, 2.4, 5.1, 5.4_

  - [x] 6.3 Write unit tests for handler notes routes and chat integration
    - Test POST /notes success (201), validation failure (400), storage failure (500)
    - Test GET /notes success (200), storage failure (500)
    - Test DELETE /notes success (200), not found (404), wrong owner (404)
    - Test AI chat with history retrieval failure → still returns response
    - Test AI chat with notes retrieval failure → still returns response
    - Test AI chat with conversation_history in body → passes to prompt assembler
    - _Requirements: 1.5, 1.6, 3.1, 3.3, 3.5, 3.6, 3.8, 5.4_

- [x] 7. Checkpoint - Backend fully integrated
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Frontend notes API service
  - [x] 8.1 Create `frontend/src/api/notesService.ts`
    - Define `TrainingNote` interface (`note_id`, `text`, `timestamp`)
    - Implement `createNote(text: string): Promise<TrainingNote>` — POST /notes
    - Implement `getNotes(): Promise<TrainingNote[]>` — GET /notes
    - Implement `deleteNote(noteId: string): Promise<void>` — DELETE /notes/{noteId}
    - Follow existing API service patterns (authService.ts, friendsService.ts)
    - _Requirements: 3.1, 3.4, 3.5_

- [x] 9. Frontend TrainingNotes component
  - [x] 9.1 Create `frontend/src/utils/relativeTime.ts`
    - Implement `formatRelativeTime(timestamp: string): string`
    - Return "just now" for < 60s, "N minutes ago" for < 3600s, "N hours ago" for < 86400s, "N days ago" otherwise
    - _Requirements: 4.7_

  - [x] 9.2 Write property test for relative timestamp formatting (Property 9)
    - **Property 9: Relative timestamp formatting**
    - Use fast-check to generate timestamp/now pairs and assert correct threshold-based formatting
    - Create `frontend/src/utils/relativeTime.test.ts`
    - **Validates: Requirements 4.7**

  - [x] 9.3 Create `frontend/src/components/TrainingNotes.tsx` and `TrainingNotes.css`
    - Multi-line textarea with placeholder "Add a training note..." and 500-char max
    - Submit button disabled when empty/whitespace or loading
    - Loading indicator during submission
    - Display up to 50 notes in reverse chronological order with relative timestamps
    - Delete button on each note
    - Optimistic UI: add note immediately, rollback on failure with error message
    - Optimistic delete: remove note immediately, rollback on failure with error message
    - Error message on submission failure, retain text in input
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9_

  - [x] 9.4 Add TrainingNotes component to the dashboard page
    - Import and render `TrainingNotes` on the activity dashboard page
    - _Requirements: 4.1_

- [x] 10. Frontend AI coach chat history
  - [x] 10.1 Modify `frontend/src/components/AICoachChat.tsx` to send conversation history
    - Add local `conversationHistory` state (array of `{role, content}` pairs)
    - On submit, include `conversation_history` in POST body alongside `prompt`
    - On successful response, append user message and AI response to local state
    - _Requirements: 2.1, 2.2_

- [x] 11. Checkpoint - Frontend complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Deploy
  - [x] 12.1 Deploy backend Lambda
    - Run `bash build-lambda.sh && aws lambda update-function-code --function-name ai-swim-coach --zip-file fileb://backend.zip --region us-east-1`
    - Verify Lambda function updated successfully
    - _Requirements: 1.1, 3.1_

  - [x] 12.2 Deploy frontend via git push
    - Run `cd frontend && npm run build` to verify build succeeds
    - Commit and push to trigger Amplify deployment
    - _Requirements: 4.1_

- [x] 13. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Backend uses Python 3.12, frontend uses TypeScript/React
- Hypothesis is already installed for backend property tests
- Infrastructure (DynamoDB table, IAM) must be set up before backend integration tests can run against real AWS

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1", "3.1", "4.1", "8.1", "9.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "3.2", "3.3", "3.4", "4.2", "4.3", "4.4", "4.5", "4.6", "9.2", "9.3"] },
    { "id": 3, "tasks": ["6.1", "6.2", "9.4", "10.1"] },
    { "id": 4, "tasks": ["6.3"] },
    { "id": 5, "tasks": ["12.1", "12.2"] }
  ]
}
```
