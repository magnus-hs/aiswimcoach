# Implementation Plan: AI Swim Coach

## Overview

Implement a serverless web application where swimmers upload a Garmin `.fit` file and receive three AI-generated improvement tips and one drill. The backend is a Python Lambda orchestrating S3, fitparse, Amazon Bedrock, and DynamoDB. The frontend is a React/TypeScript SPA hosted on AWS Amplify.

Implementation is ordered as follows: project scaffolding → backend pipeline stages (multipart parsing, FIT parsing, Bedrock client, DynamoDB writer, Lambda handler) → frontend (validation, API client, UI components) → infrastructure wiring (API Gateway, Amplify config).

---

## Tasks

- [x] 1. Set up project structure, shared types, and testing frameworks
  - Create `backend/` directory with `handler.py`, `models.py`, `requirements.txt`, and `tests/` sub-directory
  - Create `frontend/` directory with standard Vite + React/TypeScript scaffold (`src/`, `src/api/`, `src/components/`)
  - Add `pytest` and `hypothesis` to `backend/requirements-dev.txt`; add `vitest`, `@vitest/coverage-v8`, `@testing-library/react`, `@testing-library/user-event`, and `fast-check` to `frontend/package.json`
  - Define the `Metrics` dataclass and `CoachingResponse` dataclass in `backend/models.py` with their documented invariants
  - Define the `CoachingResponse` TypeScript interface in `frontend/src/types.ts`
  - _Requirements: 4.5, 5.3, 7.2_

- [x] 2. Implement multipart body parser
  - [x] 2.1 Implement `parse_multipart(event) -> bytes` in `backend/multipart_parser.py`
    - Base64-decode `event["body"]` when `event.get("isBase64Encoded")` is `True`
    - Use `python-multipart` / `email.parser` stdlib to locate the part with `name="file"` and return its raw bytes
    - Raise a `ParseError` (returning HTTP 400) when no `file` part is found
    - _Requirements: 3.4_
  - [ ]* 2.2 Write unit tests for multipart parser
    - Test: valid body with file part → correct bytes returned
    - Test: body missing file part → `ParseError` raised
    - Test: empty body → `ParseError` raised
    - _Requirements: 3.4_

- [x] 3. Implement FIT file parser and metric extraction
  - [x] 3.1 Implement `parse_fit(fit_bytes: bytes) -> Metrics` in `backend/fit_parser.py`
    - Wrap `FitFile(fit_bytes)` in a try/except; raise `ParseError` (HTTP 422) on exception
    - Iterate `length` records first, then `lap` records as fallback; accumulate pace (from `avg_speed` → seconds per 100 m), SWOLF (`avg_stroke_count + length_m / avg_speed`), and stroke rate (`avg_swimming_cadence`)
    - Collect missing metric names and raise `MetricsMissingError(missing)` (HTTP 422) if any are absent
    - Return `Metrics(pace=average(...), swolf=average(...), stroke_rate=average(...))`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_
  - [ ]* 3.2 Write property test for Metrics finiteness invariant (Property 1)
    - **Property 1: Metrics finiteness invariant**
    - **Validates: Requirements 4.5**
    - Use `hypothesis` to generate triples of finite floats for raw metric values; feed through metric computation; assert all output fields satisfy `math.isfinite`
  - [ ]* 3.3 Write property test for missing-metric error (Property 2)
    - **Property 2: Missing-metric error identifies all absent fields**
    - **Validates: Requirements 4.3**
    - Use `hypothesis` to generate subsets of `{"pace", "swolf", "stroke_rate"}` as the absent set; construct synthetic data dicts; assert the raised `MetricsMissingError` identifies exactly those absent names
  - [ ]* 3.4 Write property test for per-length / per-lap fallback equivalence (Property 10)
    - **Property 10: Per-length and per-lap fallback produce equivalent metrics**
    - **Validates: Requirements 4.2**
    - Use `hypothesis` to generate metric value sets; build synthetic `length` and `lap` records encoding the same values; assert `parse_fit` returns equivalent `Metrics` from both
  - [ ]* 3.5 Write unit tests for FIT parser
    - Test: well-formed file with all metrics → `Metrics` returned with expected values
    - Test: file missing each metric individually → correct field name in error
    - Test: malformed binary input → `ParseError` raised with descriptive message
    - Test: SWOLF computation with known pace + stroke count inputs → expected SWOLF value
    - _Requirements: 4.1, 4.3, 4.4_

- [x] 4. Implement S3 storage module
  - [x] 4.1 Implement `store_in_s3(fit_bytes: bytes) -> str` in `backend/s3_store.py`
    - Generate a UUID v4 key `uploads/{uuid}.fit` using Python's `uuid` module
    - Call `boto3` S3 `put_object`; re-raise as a storage exception (HTTP 500) on failure
    - Return the generated S3 key string
    - _Requirements: 3.1, 3.2, 3.3_
  - [ ]* 4.2 Write property test for S3 key uniqueness and format (Property 4)
    - **Property 4: S3 key uniqueness and format**
    - **Validates: Requirements 3.2**
    - Use `hypothesis` to drive N independent calls to the key-generation function; assert all keys are distinct and match `^uploads/[0-9a-f-]{36}\.fit$`

- [x] 5. Implement Bedrock client
  - [x] 5.1 Implement `invoke_bedrock(metrics: Metrics) -> CoachingResponse` in `backend/bedrock_client.py`
    - Define `TOOL_SCHEMA` and `SYSTEM_PROMPT` as documented in the design
    - Call `bedrock_runtime.invoke_model` with `tool_choice={"type": "tool", "name": "submit_coaching_response"}`
    - On non-2xx or network exception → raise `BedrockError` (HTTP 502) immediately
    - On HTTP 200 but schema-invalid response → retry once; if second attempt also invalid → raise `BedrockError` (HTTP 502)
    - Parse tool-use input from response and construct `CoachingResponse`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_
  - [ ]* 5.2 Write property test for CoachingResponse structural invariant (Property 3)
    - **Property 3: CoachingResponse structural invariant**
    - **Validates: Requirements 5.3, 7.2**
    - Use `hypothesis` to generate arbitrary tool-use JSON payloads with 3 tips (varying strings ≤ 300 chars) and 1 drill (≤ 500 chars); parse via the response-builder; assert `len(tips) == 3`, all tips non-empty and ≤ 300 chars, drill non-empty and ≤ 500 chars
  - [ ]* 5.3 Write unit tests for Bedrock client
    - Test: mocked `invoke_model` returning valid tool-use response → `CoachingResponse` returned
    - Test: mocked `invoke_model` returning malformed response → retry occurs once → HTTP 502 on second failure
    - Test: mocked `invoke_model` returning non-2xx → HTTP 502 immediately (no retry)
    - _Requirements: 5.1, 5.3, 5.4, 5.5_

- [x] 6. Checkpoint — Ensure all backend unit and property tests pass
  - Run `pytest backend/tests/ -v`; ensure all tests pass. Ask the user if questions arise.

- [x] 7. Implement DynamoDB writer
  - [x] 7.1 Implement `save_to_dynamodb(s3_key: str, metrics: Metrics, coaching: CoachingResponse) -> None` in `backend/dynamo_writer.py`
    - Compose the DynamoDB item: `file_key=s3_key`, `created_at=<ISO 8601 UTC ms>`, `pace`, `swolf`, `stroke_rate`, `tips`, `drill`
    - Call `dynamodb.put_item` using the `coaching-sessions` table name from an environment variable
    - Raise the original exception on failure (caller handles best-effort logging)
    - _Requirements: 6.1, 6.2_
  - [ ]* 7.2 Write property test for DynamoDB record schema (Property 11)
    - **Property 11: DynamoDB record uses S3 key as partition key with ISO 8601 sort key**
    - **Validates: Requirements 6.2**
    - Use `hypothesis` to generate arbitrary UUID-based S3 key strings; invoke `save_to_dynamodb` with a mocked `put_item`; assert the captured item's `file_key` equals the input key and `created_at` matches the regex `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$`
  - [ ]* 7.3 Write unit test for DynamoDB best-effort failure
    - Test: `put_item` raises an exception → exception propagates (so handler can catch and log)
    - _Requirements: 6.3_

- [x] 8. Implement Lambda handler
  - [x] 8.1 Implement `handler(event, context)` in `backend/handler.py`
    - Wire the pipeline: `parse_multipart` → `store_in_s3` → `parse_fit` → `invoke_bedrock` → `save_to_dynamodb` (best-effort, catch + log) → `http_200(coaching)`
    - Map each custom exception type to its documented HTTP status code and JSON error body
    - Set Lambda timeout to 28 seconds (configured in infrastructure; document in `README`)
    - _Requirements: 2.2, 2.3, 3.1, 3.3, 3.4, 4.1, 5.1, 6.1, 6.3, 7.1_
  - [ ]* 8.2 Write property test for DynamoDB failure resilience (Property 5)
    - **Property 5: DynamoDB write failure does not suppress the coaching response**
    - **Validates: Requirements 6.3**
    - Use `hypothesis` to generate valid `CoachingResponse` objects; inject a `put_item` exception; invoke `handler`; assert `statusCode == 200` and body equals the full `CoachingResponse` JSON
  - [ ]* 8.3 Write unit tests for Lambda handler pipeline
    - Test: happy path with all mocks succeeding → HTTP 200 with coaching JSON
    - Test: missing file part → HTTP 400
    - Test: S3 failure → HTTP 500, no further calls made
    - Test: malformed FIT → HTTP 422
    - Test: Bedrock failure → HTTP 502
    - _Requirements: 2.2, 2.3, 3.3, 3.4, 4.4, 5.4_

- [x] 9. Checkpoint — Ensure full backend test suite passes
  - Run `pytest backend/tests/ -v --tb=short`; ensure all tests pass. Ask the user if questions arise.

- [x] 10. Implement frontend file validation
  - [x] 10.1 Implement `validateFile(file: File): { valid: true } | { valid: false; reason: string }` in `frontend/src/utils/validateFile.ts`
    - Reject any file whose name does not end with `.fit` (case-insensitive); return reason `"Only .fit files are accepted."`
    - Reject any file whose `size > 104_857_600` bytes; return reason `"File exceeds the 100 MB limit."`
    - Return `{ valid: true }` otherwise
    - _Requirements: 1.1, 1.2, 1.3_
  - [ ]* 10.2 Write property test for non-.fit file rejection (Property 6)
    - **Property 6: Client-side rejection of non-.fit files**
    - **Validates: Requirements 1.1, 1.2**
    - Use `fast-check` to generate arbitrary filename strings not ending in `.fit`; assert `validateFile` returns `{ valid: false }`
  - [ ]* 10.3 Write property test for oversized file rejection (Property 7)
    - **Property 7: Client-side rejection of oversized files**
    - **Validates: Requirements 1.3**
    - Use `fast-check` to generate integers > 104,857,600; assert `validateFile` returns `{ valid: false }`

- [x] 11. Implement frontend API client
  - [x] 11.1 Implement `uploadFitFile(file: File): Promise<CoachingResponse>` in `frontend/src/api/upload.ts`
    - Build a `FormData` with the file appended as `"file"`
    - `fetch` POST to `import.meta.env.VITE_API_ENDPOINT + "/upload"`
    - On non-ok response: parse body text and throw `ApiError(status, text)` with the status-to-message mapping from the design
    - Return `response.json()` cast to `CoachingResponse`
    - _Requirements: 1.4, 7.1_
  - [ ]* 11.2 Write unit tests for API client error mapping
    - Test each HTTP status (400, 413, 422, 502, 500) using mocked `fetch` → correct `ApiError` message thrown
    - Test network error (fetch rejects) → connection error message thrown
    - _Requirements: 1.7, 1.8, 7.4, 7.5_

- [x] 12. Implement frontend React components
  - [x] 12.1 Implement `<FileDropZone>` in `frontend/src/components/FileDropZone.tsx`
    - Use `react-dropzone` with `accept={{ "application/octet-stream": [".fit"] }}`
    - On drop: call `validateFile`; emit `onFileAccepted(file)` if valid, emit `onFileRejected(reason)` otherwise
    - Include ARIA label and live region announcement for screen readers
    - _Requirements: 1.1, 1.2, 1.3, 8.3_
  - [x] 12.2 Implement `<CoachingResult>` in `frontend/src/components/CoachingResult.tsx`
    - Accept `{ tips: string[]; drill: string }` props
    - Render each tip as a numbered list item with a heading label (`Tip 1`, `Tip 2`, `Tip 3`)
    - Render the drill in a visually distinct card/section (different background or border)
    - _Requirements: 1.6, 7.3_
  - [x] 12.3 Implement `<ErrorBanner>` in `frontend/src/components/ErrorBanner.tsx`
    - Accept `{ message: string; onRetry?: () => void }` props
    - Show retry button only when `onRetry` is provided (for network and 5xx errors)
    - _Requirements: 1.7, 1.8, 7.4, 7.5_
  - [x] 12.4 Implement `<UploadPage>` in `frontend/src/pages/UploadPage.tsx`
    - Maintain state: `idle | uploading | result | error`
    - In `uploading` state: show `<LoadingIndicator>` and disable upload control
    - On success: transition to `result` state, render `<CoachingResult>`
    - On error: transition to `error` state, render `<ErrorBanner>` with retry for network/5xx, no retry for 4xx
    - _Requirements: 1.4, 1.5, 1.6, 1.7, 1.8_

- [x] 13. Checkpoint — Ensure frontend compiles without errors
  - Run `npm run build` inside `frontend/`; resolve any TypeScript or compilation errors. Ask the user if questions arise.

- [ ] 14. Write frontend component tests
  - [ ]* 14.1 Write property test for CoachingResult rendering (Property 8)
    - **Property 8: Frontend renders all content from any valid CoachingResponse**
    - **Validates: Requirements 1.6, 7.3**
    - Use `fast-check` to generate random `CoachingResponse` objects (3 tips, 1 drill, varying string content); render `<CoachingResult>` with React Testing Library; assert all three tip strings and the drill string appear in the output
  - [ ]* 14.2 Write property test for error UI on 4xx/5xx responses (Property 9)
    - **Property 9: Frontend displays error UI for any 4xx or 5xx response**
    - **Validates: Requirements 1.8, 7.4, 7.5**
    - Use `fast-check` to generate integers in [400–499] and [500–599]; mock `fetch` to return each; render `<UploadPage>` and trigger an upload; assert error message visible and `<CoachingResult>` absent; assert 5xx messages include retry advice
  - [ ]* 14.3 Write unit tests for FileDropZone validation behaviour
    - Test: `.fit` file of valid size → `onFileAccepted` called, no network call
    - Test: non-`.fit` file → `onFileRejected` called with appropriate reason, no network call
    - Test: `.fit` file > 100 MB → `onFileRejected` called, no network call
    - _Requirements: 1.1, 1.2, 1.3_
  - [ ]* 14.4 Write unit tests for UploadPage state transitions
    - Test: successful upload → loading indicator visible during upload, hidden after; `<CoachingResult>` rendered
    - Test: API returns 400 → error banner shown, coaching result absent
    - Test: API returns 502 → error banner shown with retry button
    - Test: network error → error banner shown with retry button
    - _Requirements: 1.5, 1.6, 1.7, 1.8_

- [x] 15. Checkpoint — Ensure all frontend tests pass
  - Run `npx vitest run` inside `frontend/`; ensure all tests pass. Ask the user if questions arise.

- [x] 16. Wire infrastructure as Terraform
  - [x] 16.1 Create Terraform configuration for API Gateway in `infra/api_gateway.tf`
    - REST API (aws_api_gateway_rest_api), resource `POST /upload`, binary media type `multipart/form-data`, Lambda proxy integration (aws_api_gateway_integration), 29-second timeout, CORS headers (aws_api_gateway_method_response / aws_api_gateway_integration_response), HTTP 413 on oversize via gateway response, HTTP 405 on wrong method via gateway response
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_
  - [x] 16.2 Create Terraform configuration for Amplify hosting in `infra/amplify.tf`
    - aws_amplify_app and aws_amplify_branch resources pointing to `frontend/`, environment variable `VITE_API_ENDPOINT` mapped to the API Gateway invoke URL output
    - _Requirements: 8.1, 8.2_
  - [x] 16.3 Create Terraform configuration for Lambda, S3, DynamoDB, and IAM in `infra/lambda.tf`, `infra/s3.tf`, `infra/dynamodb.tf`, `infra/iam.tf`
    - Lambda: aws_lambda_function (Python 3.12, timeout 28 s), aws_lambda_permission for API Gateway invocation
    - S3: aws_s3_bucket for raw FIT file uploads
    - DynamoDB: aws_dynamodb_table `coaching-sessions` with `file_key` (String, HASH) and `created_at` (String, RANGE)
    - IAM: aws_iam_role + aws_iam_role_policy granting s3:PutObject, bedrock:InvokeModel, dynamodb:PutItem; environment variables S3_BUCKET, DYNAMODB_TABLE, AWS_REGION wired via aws_lambda_function environment block
    - _Requirements: 3.1, 5.1, 6.1_
  - [x] 16.4 Create `infra/main.tf` with provider configuration and `infra/outputs.tf` exposing the API Gateway invoke URL
    - terraform block with required_providers (aws), provider "aws" with region variable, output "api_gateway_url" from aws_api_gateway_deployment invoke_url

- [x] 17. Final checkpoint — Full test suite and build verification
  - Run `pytest backend/tests/ -v` and `npx vitest run` inside `frontend/`; confirm all tests pass and `npm run build` succeeds. Ask the user if questions arise.

---

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Checkpoints (tasks 6, 9, 13, 15, 17) provide incremental validation gates
- Property tests validate universal correctness properties (Properties 1–11 from the design document)
- Unit tests validate specific examples and edge cases
- Backend property tests use `hypothesis`; frontend property tests use `fast-check`
- The model MUST NOT implement sub-tasks postfixed with `*`; it MUST implement all others

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1"] },
    { "id": 1, "tasks": ["2.1", "3.1", "4.1", "5.1", "7.1", "10.1", "11.1"] },
    { "id": 2, "tasks": ["2.2", "3.2", "3.3", "3.4", "3.5", "4.2", "5.2", "5.3", "7.2", "7.3", "10.2", "10.3", "11.2"] },
    { "id": 3, "tasks": ["8.1", "12.1", "12.2", "12.3"] },
    { "id": 4, "tasks": ["8.2", "8.3", "12.4"] },
    { "id": 5, "tasks": ["14.1", "14.2", "14.3", "14.4"] },
    { "id": 6, "tasks": ["16.1", "16.2", "16.3", "16.4"] }
  ]
}
```
