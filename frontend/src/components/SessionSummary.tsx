import { SessionInfo } from '../types';
import { StrokeBreakdownEntry } from '../api/sessionService';
import { formatStrokeBreakdown } from '../utils/strokeBreakdown';
import './SessionSummary.css';

interface SessionSummaryProps {
  session: SessionInfo;
  strokeBreakdown?: StrokeBreakdownEntry[];
}

function formatTime(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = Math.round(totalSeconds % 60);
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

function formatDate(isoString: string): string {
  if (!isoString) return '—';
  try {
    const date = new Date(isoString);
    return date.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoString;
  }
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/**
 * Displays a summary card with key session information.
 * Key metrics (distance, time) are displayed with large bold numbers per Strava/Garmin pattern.
 * Validates: Requirements 25.1, 25.2
 */
export function SessionSummary({ session, strokeBreakdown }: SessionSummaryProps) {
  const strokeDisplay =
    strokeBreakdown && strokeBreakdown.length > 0
      ? formatStrokeBreakdown(strokeBreakdown)
      : capitalize(session.stroke);
  return (
    <section className="session-summary" aria-label="Session summary">
      <h2 className="session-summary__heading">Session Summary</h2>
      <div className="session-summary__grid">
        <div className="session-summary__item session-summary__item--primary">
          <span className="session-summary__label">Distance</span>
          <span className="session-summary__value session-summary__value--large">{session.total_distance_m}m</span>
        </div>
        <div className="session-summary__item session-summary__item--primary">
          <span className="session-summary__label">Total Time</span>
          <span className="session-summary__value session-summary__value--large">{formatTime(session.total_time_seconds)}</span>
        </div>
        <div className="session-summary__item">
          <span className="session-summary__label">Date</span>
          <span className="session-summary__value">{formatDate(session.start_time)}</span>
        </div>
        <div className="session-summary__item">
          <span className="session-summary__label">Pool Size</span>
          <span className="session-summary__value">{session.pool_length_m}m</span>
        </div>
        <div className="session-summary__item">
          <span className="session-summary__label">Stroke</span>
          <span className="session-summary__value">{strokeDisplay}</span>
        </div>
        <div className="session-summary__item">
          <span className="session-summary__label">Lengths</span>
          <span className="session-summary__value">{session.num_lengths}</span>
        </div>
      </div>
    </section>
  );
}
