import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getSessionById, SessionDetail } from '../api/sessionService';
import { ApiError } from '../types';
import { LoadingIndicator } from '../components/LoadingIndicator';
import { SessionSummary } from '../components/SessionSummary';
import { GroupedSplitsTable } from '../components/GroupedSplitsTable';
import { HRZonesCard } from '../components/HRZonesCard';
import { CoachingResult } from '../components/CoachingResult';
import { AbilityAssessmentCard } from '../components/AbilityAssessmentCard';
import { TrainingPlanResult } from '../components/TrainingPlanResult';
import { ErrorBanner } from '../components/ErrorBanner';

type PageState = 'loading' | 'loaded' | 'error';

/**
 * SessionDetailPage - Displays detailed results for a past swim session.
 * 
 * Fetches session by ID and reuses the same layout as the upload results page:
 * - Session summary
 * - Splits table
 * - Heart rate zones (if available)
 * - Coaching tips
 * - Ability assessment (if available)
 * - Training plan (if available)
 * 
 * Validates: Requirements 19.1-19.8
 */
export function SessionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [state, setState] = useState<PageState>('loading');
  const [sessionDetail, setSessionDetail] = useState<SessionDetail | null>(null);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    if (!id) {
      setErrorMessage('Session ID is required');
      setState('error');
      return;
    }

    const fetchSession = async () => {
      setState('loading');
      setErrorMessage('');

      try {
        const detail = await getSessionById(id);
        setSessionDetail(detail);
        setState('loaded');
      } catch (err: unknown) {
        let message = 'Failed to load session details.';

        if (err instanceof ApiError) {
          message = err.serverMessage;
        } else if (err instanceof Error) {
          message = err.message;
        }

        setErrorMessage(message);
        setState('error');
      }
    };

    fetchSession();
  }, [id]);

  if (state === 'loading') {
    return (
      <div className="session-detail-page" style={{ padding: '2rem' }}>
        <LoadingIndicator />
      </div>
    );
  }

  if (state === 'error') {
    return (
      <div className="session-detail-page" style={{ padding: '2rem' }}>
        <div style={{ marginBottom: '1.5rem' }}>
          <Link to="/history" style={{ color: '#3b82f6', textDecoration: 'none' }}>
            ← Back to History
          </Link>
        </div>
        <ErrorBanner message={errorMessage} />
      </div>
    );
  }

  if (!sessionDetail) {
    return (
      <div className="session-detail-page" style={{ padding: '2rem' }}>
        <ErrorBanner message="Session data not available" />
      </div>
    );
  }

  return (
    <div className="session-detail-page" style={{ padding: '2rem' }}>
      <div style={{ marginBottom: '1.5rem' }}>
        <Link to="/history" style={{ color: '#3b82f6', textDecoration: 'none', fontSize: '1rem' }}>
          ← Back to History
        </Link>
      </div>

      <div className="session-detail-page__results">
        <SessionSummary session={sessionDetail.session} />
        <GroupedSplitsTable splits={sessionDetail.splits} poolLengthM={sessionDetail.session.pool_length_m} strokeRate={sessionDetail.metrics?.stroke_rate} />
        <HRZonesCard hrZones={sessionDetail.hr_zones} />
        <CoachingResult tips={sessionDetail.coaching.tips} drill={sessionDetail.coaching.drill} />
        <AbilityAssessmentCard assessment={sessionDetail.ability_assessment} />
        
        {sessionDetail.training_plan && (
          <TrainingPlanResult plan={sessionDetail.training_plan} />
        )}
      </div>
    </div>
  );
}
