import { LengthSplit } from '../types';
import './DrillSummary.css';

interface DrillSummaryProps {
  splits: LengthSplit[];
  poolLengthM: number;
}

export interface DrillStats {
  count: number;
  totalDistance: number;
  totalTime: number;
}

/**
 * Compute aggregated drill statistics from splits.
 * Returns null when no drill splits exist.
 */
export function computeDrillStats(splits: LengthSplit[], poolLengthM: number): DrillStats | null {
  const drillSplits = splits.filter(s => s.stroke === 'drill');
  if (drillSplits.length === 0) return null;
  return {
    count: drillSplits.length,
    totalDistance: drillSplits.length * poolLengthM,
    totalTime: drillSplits.reduce((sum, s) => sum + s.time_seconds, 0),
  };
}

/**
 * Format seconds into a readable time string (e.g., "2:30").
 */
function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Displays a summary of drill work in the session: count, distance, and time.
 * Returns null when the session contains no drill splits (Req 3.5).
 */
export function DrillSummary({ splits, poolLengthM }: DrillSummaryProps) {
  const stats = computeDrillStats(splits, poolLengthM);
  if (!stats) return null;

  return (
    <section className="drill-summary" aria-label="Drill summary">
      <h3 className="drill-summary__title">Drill Work</h3>
      <div className="drill-summary__grid">
        <div className="drill-summary__item">
          <span className="drill-summary__value">{stats.count}</span>
          <span className="drill-summary__label">Lengths</span>
        </div>
        <div className="drill-summary__item">
          <span className="drill-summary__value">{stats.totalDistance}m</span>
          <span className="drill-summary__label">Distance</span>
        </div>
        <div className="drill-summary__item">
          <span className="drill-summary__value">{formatTime(stats.totalTime)}</span>
          <span className="drill-summary__label">Time</span>
        </div>
      </div>
    </section>
  );
}
