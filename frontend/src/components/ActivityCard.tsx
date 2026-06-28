import { useNavigate } from 'react-router-dom';
import './ActivityCard.css';

export interface ActivityCardProps {
  sessionId: string;
  sessionDate: string;
  strokeType: string;
  totalDistanceMeters: number;
  totalTimeSeconds: number;
  averagePacePer100m: number;
  swolfScore: number;
}

/**
 * Format seconds into "Xm Ys" display string.
 */
export function formatTime(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = Math.round(totalSeconds % 60);
  return `${minutes}m ${seconds}s`;
}

/**
 * Format pace (in seconds per 100m) into "M:SS /100m" display string.
 */
export function formatPace(paceSeconds: number): string {
  const minutes = Math.floor(paceSeconds / 60);
  const seconds = Math.round(paceSeconds % 60);
  return `${minutes}:${seconds.toString().padStart(2, '0')} /100m`;
}

/**
 * Format a date string into a readable short format.
 */
function formatDate(isoString: string): string {
  if (!isoString) return '—';
  try {
    const date = new Date(isoString);
    return date.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return isoString;
  }
}

/**
 * Clickable card displaying session metrics in a Strava-inspired layout.
 * Distance is the hero metric (large bold), secondary metrics below.
 * Navigates to /activity/:id on click.
 *
 * Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5
 */
export function ActivityCard({
  sessionId,
  sessionDate,
  strokeType,
  totalDistanceMeters,
  totalTimeSeconds,
  averagePacePer100m,
  swolfScore,
}: ActivityCardProps) {
  const navigate = useNavigate();

  const handleClick = () => {
    navigate(`/activity/${sessionId}`);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      navigate(`/activity/${sessionId}`);
    }
  };

  return (
    <article
      className="activity-card"
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
      aria-label={`${strokeType} session on ${formatDate(sessionDate)}, ${totalDistanceMeters} meters`}
    >
      <div className="activity-card__header">
        <span className="activity-card__date">{formatDate(sessionDate)}</span>
        <span className="activity-card__stroke">{strokeType}</span>
      </div>

      <div className="activity-card__distance">
        {totalDistanceMeters}m
      </div>

      <div className="activity-card__metrics">
        <div className="activity-card__metric">
          <span className="activity-card__metric-label">Time</span>
          <span className="activity-card__metric-value">{formatTime(totalTimeSeconds)}</span>
        </div>
        <div className="activity-card__metric">
          <span className="activity-card__metric-label">Pace</span>
          <span className="activity-card__metric-value">{formatPace(averagePacePer100m)}</span>
        </div>
        <div className="activity-card__metric">
          <span className="activity-card__metric-label">SWOLF</span>
          <span className="activity-card__metric-value">{swolfScore}</span>
        </div>
      </div>
    </article>
  );
}
