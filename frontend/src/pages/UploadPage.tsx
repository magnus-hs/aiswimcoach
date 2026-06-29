import { useState, useCallback, useRef } from 'react';
import { FileDropZone } from '../components/FileDropZone';
import { LoadingIndicator } from '../components/LoadingIndicator';
import { SessionSummary } from '../components/SessionSummary';
import { GroupedSplitsTable } from '../components/GroupedSplitsTable';
import { HRZonesCard } from '../components/HRZonesCard';
import { CoachingResult } from '../components/CoachingResult';
import { AbilityAssessmentCard } from '../components/AbilityAssessmentCard';
import { TrainingGoalForm } from '../components/TrainingGoalForm';
import { TrainingPlanResult } from '../components/TrainingPlanResult';
import { ErrorBanner } from '../components/ErrorBanner';
import { uploadFitFile, generateTrainingPlan } from '../api/upload';
import { ApiError, FullResponse, TrainingGoal, TrainingPlan } from '../types';

type PageState = 'idle' | 'uploading' | 'result' | 'error';

/**
 * Main upload page orchestrating the file upload flow.
 *
 * States:
 *   idle      → FileDropZone active
 *   uploading → LoadingIndicator shown, FileDropZone disabled
 *   result    → SessionSummary + SplitsTable + CoachingResult + TrainingGoalForm rendered
 *   error     → ErrorBanner rendered (with retry for network/5xx)
 */
export function UploadPage() {
  const [state, setState] = useState<PageState>('idle');
  const [result, setResult] = useState<FullResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [canRetry, setCanRetry] = useState(false);
  const [rejectionMessage, setRejectionMessage] = useState('');

  // Training plan state
  const [trainingPlan, setTrainingPlan] = useState<TrainingPlan | null>(null);
  const [planLoading, setPlanLoading] = useState(false);
  const [planError, setPlanError] = useState('');

  // Keep a ref to the last file so retry can re-upload it
  const lastFileRef = useRef<File | null>(null);

  const handleUpload = useCallback(async (file: File) => {
    lastFileRef.current = file;
    setRejectionMessage('');
    setState('uploading');
    setResult(null);
    setErrorMessage('');
    setCanRetry(false);
    setTrainingPlan(null);
    setPlanError('');

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

  const handleGoalSubmit = useCallback(
    async (goal: TrainingGoal) => {
      if (!result) return;

      setPlanLoading(true);
      setPlanError('');
      setTrainingPlan(null);

      try {
        const plan = await generateTrainingPlan(result.metrics, goal);
        setTrainingPlan(plan);
      } catch (err: unknown) {
        if (err instanceof ApiError) {
          setPlanError(err.serverMessage);
        } else if (err instanceof Error) {
          setPlanError(err.message);
        } else {
          setPlanError('Failed to generate training plan.');
        }
      } finally {
        setPlanLoading(false);
      }
    },
    [result],
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
          {!result.hr_zones && (
            <div className="upload-page__profile-prompt">
              Complete your <a href="/profile">profile</a> to enable heart rate zone analysis.
            </div>
          )}
          
          <SessionSummary session={result.session} />
          <GroupedSplitsTable splits={result.splits} poolLengthM={result.session.pool_length_m} />
          <HRZonesCard hrZones={result.hr_zones} />
          <CoachingResult tips={result.coaching.tips} drill={result.coaching.drill} />
          <AbilityAssessmentCard assessment={result.ability_assessment} />
          
          {result.session_id && (
            <div className="upload-page__success-message">
              Session saved! <a href="/history">View your training history</a> to track progress.
            </div>
          )}
          
          <TrainingGoalForm onSubmit={handleGoalSubmit} loading={planLoading} />
          {planError && <ErrorBanner message={planError} />}
          {trainingPlan && <TrainingPlanResult plan={trainingPlan} />}
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
