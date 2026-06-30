import { LengthSplit } from '../types';
import './SessionStatsBlock.css';

interface SessionStatsBlockProps {
  splits: LengthSplit[];
  poolLengthM: number;
  totalDistanceM: number;
  totalTimeSeconds: number;
}

/**
 * Compact stats block showing key session metrics.
 */
export function SessionStatsBlock({ splits, poolLengthM, totalDistanceM, totalTimeSeconds }: SessionStatsBlockProps) {
  const validSplits = splits.filter(s => s.strokes > 0 && s.time_seconds > 0);

  // Average SWOLF
  const avgSwolf = validSplits.length > 0
    ? Math.round(validSplits.reduce((sum, s) => sum + s.time_seconds + s.strokes, 0) / validSplits.length)
    : 0;

  // Average HR
  const hrsWithData = splits.filter(s => s.avg_hr != null);
  const avgHr = hrsWithData.length > 0
    ? Math.round(hrsWithData.reduce((sum, s) => sum + s.avg_hr!, 0) / hrsWithData.length)
    : null;

  // Average distance per stroke
  const avgDps = validSplits.length > 0
    ? (validSplits.reduce((sum, s) => sum + (poolLengthM / s.strokes), 0) / validSplits.length).toFixed(2)
    : '—';

  // Format time
  const formatDuration = (seconds: number): string => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.round((seconds % 3600) / 60);
    if (hrs > 0) return `${hrs}h ${mins}m`;
    return `${mins}m`;
  };

  // Swim time (excluding rest)
  const swimTime = splits.reduce((sum, s) => sum + s.time_seconds, 0);

  return (
    <div className="session-stats-block">
      <div className="session-stats-block__item">
        <span className="session-stats-block__value">{totalDistanceM}m</span>
        <span className="session-stats-block__label">Distance</span>
      </div>
      <div className="session-stats-block__item">
        <span className="session-stats-block__value">{avgSwolf || '—'}</span>
        <span className="session-stats-block__label">Avg SWOLF</span>
      </div>
      {avgHr && (
        <div className="session-stats-block__item">
          <span className="session-stats-block__value">{avgHr} bpm</span>
          <span className="session-stats-block__label">Avg HR</span>
        </div>
      )}
      <div className="session-stats-block__item">
        <span className="session-stats-block__value">{avgDps}m</span>
        <span className="session-stats-block__label">Dist/Stroke</span>
      </div>
      <div className="session-stats-block__item">
        <span className="session-stats-block__value">{formatDuration(swimTime)}</span>
        <span className="session-stats-block__label">Swim Time</span>
      </div>
      <div className="session-stats-block__item">
        <span className="session-stats-block__value">{formatDuration(totalTimeSeconds)}</span>
        <span className="session-stats-block__label">Total Time</span>
      </div>
    </div>
  );
}
