# Requirements Document

## Introduction

Bulk Import enables users to upload multiple FIT files (up to 1000) in a single operation from the existing Activities upload page. Files are queued and uploaded sequentially with real-time progress indication. To keep costs low, bulk imports skip the Bedrock AI coaching analysis while still performing FIT parsing, S3 storage, session metric extraction, personal best derivation, and DynamoDB persistence. The feature handles failures gracefully by skipping problematic files and continuing with the rest, presenting a summary at completion.

## Glossary

- **Bulk_Import_Queue**: The client-side queue of FIT files awaiting sequential upload during a bulk import operation
- **Upload_Handler**: The backend Lambda function at POST /upload that processes FIT file uploads
- **FileDropZone**: The existing frontend drag-and-drop component that accepts FIT files
- **Progress_Indicator**: The frontend UI element displaying the current upload count, percentage, and status
- **Import_Summary**: The final report shown after all files in a bulk import have been processed or skipped
- **Skip_Coaching_Flag**: The `skip_coaching` parameter sent to the Upload_Handler to bypass Bedrock AI invocation

## Requirements

### Requirement 1: Multi-File Selection

**User Story:** As a swimmer, I want to drop or select multiple FIT files at once, so that I can import my entire training history without uploading files one by one.

#### Acceptance Criteria

1. WHEN the user drops multiple FIT files onto the FileDropZone, THE FileDropZone SHALL accept all valid FIT files and add them to the Bulk_Import_Queue
2. WHEN the user selects multiple FIT files via the file picker dialog, THE FileDropZone SHALL accept all valid FIT files and add them to the Bulk_Import_Queue
3. THE FileDropZone SHALL accept up to 1000 FIT files in a single bulk import operation
4. IF the user drops more than 1000 files, THEN THE FileDropZone SHALL reject the entire batch and display an error message stating the maximum file limit
5. IF any file in the batch is not a valid .fit file, THEN THE FileDropZone SHALL exclude that file from the Bulk_Import_Queue and include it in a rejected files count

### Requirement 2: Sequential Upload Queue

**User Story:** As a swimmer, I want my bulk files uploaded one at a time in sequence, so that the server is not overwhelmed and each file is processed reliably.

#### Acceptance Criteria

1. WHEN the Bulk_Import_Queue contains files, THE Bulk_Import_Queue SHALL upload files sequentially, one at a time, to the Upload_Handler
2. WHILE an upload is in progress, THE Bulk_Import_Queue SHALL wait for the current upload to complete or fail before starting the next file
3. WHEN a file upload completes successfully, THE Bulk_Import_Queue SHALL increment the success counter and proceed to the next file
4. WHEN a file upload fails, THE Bulk_Import_Queue SHALL increment the failure counter, record the filename and error reason, and proceed to the next file
5. THE Bulk_Import_Queue SHALL send the Skip_Coaching_Flag with each upload request during a bulk import operation

### Requirement 3: Progress Indication

**User Story:** As a swimmer, I want to see real-time progress during bulk upload, so that I know how many files have been processed and how much remains.

#### Acceptance Criteria

1. WHILE a bulk import is in progress, THE Progress_Indicator SHALL display the current file number out of the total count (e.g., "Uploading 45/1000")
2. WHILE a bulk import is in progress, THE Progress_Indicator SHALL display the completion percentage rounded to one decimal place
3. WHILE a bulk import is in progress, THE Progress_Indicator SHALL display a visual progress bar reflecting the completion percentage
4. WHEN a file upload completes or fails, THE Progress_Indicator SHALL update immediately to reflect the new count
5. WHILE a bulk import is in progress, THE FileDropZone SHALL be disabled to prevent additional file drops

### Requirement 4: Skip Coaching on Bulk Import

**User Story:** As a swimmer, I want bulk imports to skip AI coaching analysis, so that the import completes quickly and at minimal cost.

#### Acceptance Criteria

1. WHEN the Upload_Handler receives a request with the Skip_Coaching_Flag set to true, THE Upload_Handler SHALL skip the Bedrock AI coaching invocation
2. WHEN the Upload_Handler receives a request with the Skip_Coaching_Flag set to true, THE Upload_Handler SHALL still parse the FIT file and extract session metrics
3. WHEN the Upload_Handler receives a request with the Skip_Coaching_Flag set to true, THE Upload_Handler SHALL still store the FIT file in S3
4. WHEN the Upload_Handler receives a request with the Skip_Coaching_Flag set to true, THE Upload_Handler SHALL still save the session record to DynamoDB
5. WHEN the Upload_Handler receives a request with the Skip_Coaching_Flag set to true, THE Upload_Handler SHALL still derive and update personal bests from the session data
6. WHEN the Upload_Handler receives a request with the Skip_Coaching_Flag set to true, THE Upload_Handler SHALL skip the ability assessment generation
7. WHEN the Upload_Handler receives a request with the Skip_Coaching_Flag set to true, THE Upload_Handler SHALL return a response containing session info, splits, and metrics but with a null coaching field

### Requirement 5: Failure Handling

**User Story:** As a swimmer, I want failed uploads to be skipped gracefully, so that one bad file does not prevent the rest of my training history from being imported.

#### Acceptance Criteria

1. IF a file upload returns an HTTP error status, THEN THE Bulk_Import_Queue SHALL record the filename and error message and continue processing the remaining files
2. IF a file upload encounters a network timeout or connection error, THEN THE Bulk_Import_Queue SHALL record the filename with a timeout error and continue processing the remaining files
3. THE Bulk_Import_Queue SHALL never abort the entire bulk import due to a single file failure
4. WHILE processing continues after a failure, THE Progress_Indicator SHALL distinguish between successful and failed uploads in the running count

### Requirement 6: Import Summary

**User Story:** As a swimmer, I want a clear summary after bulk import completes, so that I know how many files succeeded, how many failed, and which ones had problems.

#### Acceptance Criteria

1. WHEN all files in the Bulk_Import_Queue have been processed, THE Import_Summary SHALL display the total number of files that succeeded
2. WHEN all files in the Bulk_Import_Queue have been processed, THE Import_Summary SHALL display the total number of files that failed
3. IF any files failed during the bulk import, THEN THE Import_Summary SHALL display a list of failed filenames with their error reasons
4. WHEN the Import_Summary is displayed, THE Import_Summary SHALL provide an option to dismiss the summary and return to the normal upload page state
5. WHEN the Import_Summary is displayed, THE FileDropZone SHALL be re-enabled to allow new uploads

### Requirement 7: Cancellation

**User Story:** As a swimmer, I want to cancel a bulk import in progress, so that I can stop the operation if I made a mistake or no longer need it.

#### Acceptance Criteria

1. WHILE a bulk import is in progress, THE Progress_Indicator SHALL display a cancel button
2. WHEN the user clicks the cancel button, THE Bulk_Import_Queue SHALL stop uploading after the currently in-progress file completes
3. WHEN a bulk import is cancelled, THE Import_Summary SHALL display showing results for files processed before cancellation
4. WHEN a bulk import is cancelled, THE Import_Summary SHALL indicate that the import was cancelled and show how many files were not processed
