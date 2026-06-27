import { useState, useCallback, useRef } from 'react';
import { FileDropZone } from '../components/FileDropZone';
import { LoadingIndicator } from '../components/LoadingIndicator';
import { SessionSummary } from '../components/SessionSummary';
import { SplitsTable } from '../components/SplitsTable';
import { CoachingResult } from '../components/CoachingResult';
import { ErrorBanner } from '../components/ErrorBanner';
import { uploadFitFile } from '../api/upload';
import { ApiError, FullResponse } from '../types';

type PageState = 'idle' | 'uploading' | 'result' | 'error';

/**
 * Main upload page orchestrating the file upload flow.
 *
 * States:
 *   idle      → FileDropZone active
 *   uploading → LoadingIndicator shown, FileDropZone disabled
 *   result    → SessionSummary + SplitsTable + CoachingResult rendered
 *   error     → ErrorBanner rendered (with retry for network/5xx)
 */
export function UploadPage() {
  const [state, setState] = useState<PageState>('idle');
  const [result, setResult] = useState<FullResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [canRetry, setCanRetry] = useState(false);
  const [rejectionMessage, setRejectionMessage] = useState('');

  // Keep a ref to the last file so retry can re-upload it
  const lastFileRef = useRef<File | null>(null);

  const handleUpload = useCallback(async (file: File) => {
    lastFileRef.current = file;
    setRejectionMessage('');
    setState('uploading');
    setResult(null);
    setErrorMessage('');
    setCanRetry(false);

    try {
      const response = await uploadFitFile(file);
      setResult(response);
      setState('result');
    } catch (err: unknown) {
      let message = 'An unexpected error occurred.';
      let retryable = false;

      if (err instanceof ApiError) {
        message = err.serverMessage;
        // Network errors (status 0) and server errors (5xx) are retryable
        retryable = err.status === 0 || err.status >= 500;
      } else if (err instanceof Error) {
        message = err.message;
        retryable = true; // Unexpected errors are treated as retryable
      }

      setErrorMessage(message);
      setCanRetry(retryable);
      setState('error');
    }
  }, []);

  const handleRetry = useCallback(() => {
    if (lastFileRef.current) {
      handleUpload(lastFileRef.current);
    }
  }, [handleUpload]);

  const handleFileRejected = useCallback((reason: string) => {
    setRejectionMessage(reason);
  }, []);

  const handleFileAccepted = useCallback(
    (file: File) => {
      setRejectionMessage('');
      handleUpload(file);
    },
    [handleUpload],
  );

  return (
    <div className="upload-page">
      <FileDropZone
        onFileAccepted={handleFileAccepted}
        onFileRejected={handleFileRejected}
        disabled={state === 'uploading'}
      />

      {rejectionMessage && state !== 'uploading' && (
        <ErrorBanner message={rejectionMessage} />
      )}

      {state === 'uploading' && <LoadingIndicator />}

      {state === 'result' && result && (
        <div className="upload-page__results">
          <SessionSummary session={result.session} />
          <SplitsTable splits={result.splits} />
          <CoachingResult tips={result.coaching.tips} drill={result.coaching.drill} />
        </div>
      )}

      {state === 'error' && (
        <ErrorBanner
          message={errorMessage}
          onRetry={canRetry ? handleRetry : undefined}
        />
      )}
    </div>
  );
}
