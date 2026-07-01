import { Link } from 'react-router-dom';
import { SessionSummary } from '../api/sessionService';
import { ActivityCard } from './ActivityCard';
import { ErrorBanner } from './ErrorBanner';
import './ActivityFeed.css';

export interface ActivityFeedProps {
  /** Session summaries to render as ActivityCards. */
  sessions: SessionSummary[];
  /** Whether session data is currently loading. */
  loading: boolean;
  /** Optional error message to display. */
  error?: string;
  /** Optional retry callback for recoverable errors. */
  onRetry?: () => void;
}

/**
 * Renders a list of ActivityCards in descending session date order.
 * Handles loading (skeleton cards), empty state (CTA), and error state (ErrorBanner + retry).
 *
 * Validates: Requirements 3.5, 12.1, 12.2, 12.4
 */
export function ActivityFeed({ sessions, loading, error, onRetry }: ActivityFeedProps) {
  // Error state
  if (error) {
    return (
      <div className="activity-feed activity-feed--error">
        <ErrorBanner message={error} onRetry={onRetry} />
      </div>
    );
  }

  // Loading state — 3 skeleton placeholder cards
  if (loading) {
    return (
      <div className="activity-feed activity-feed--loading" aria-busy="true" aria-label="Loading sessions">
        {[0, 1, 2].map((i) => (
          <div key={i} className="activity-feed__skeleton" aria-hidden="true">
            <div className="activity-feed__skeleton-header" />
            <div className="activity-feed__skeleton-body" />
            <div className="activity-feed__skeleton-footer" />
          </div>
        ))}
      </div>
    );
  }

  // Empty state — CTA to upload first session
  if (sessions.length === 0) {
    return (
      <div className="activity-feed activity-feed--empty">
        <p className="activity-feed__empty-message">No sessions yet. Upload your first swim to get started!</p>
        <Link to="/activity/new" className="activity-feed__cta">
          Upload First Session
        </Link>
      </div>
    );
  }

  // Sort sessions by date descending (API should already be sorted, but ensure correctness)
  const sorted = [...sessions].sort((a, b) => {
    return new Date(b.session_date).getTime() - new Date(a.session_date).getTime();
  });

  return (
    <div className="activity-feed">
      {sorted.map((session) => (
        <ActivityCard
          key={session.session_id}
          sessionId={session.session_id}
          sessionDate={session.session_date}
          strokeType={session.stroke_type}
          totalDistanceMeters={session.total_distance_meters}
          totalTimeSeconds={session.total_time_seconds}
          averagePacePer100m={session.average_pace_per_100m}
          swolfScore={session.swolf_score}
          strokeBreakdown={session.stroke_breakdown}
        />
      ))}
    </div>
  );
}
