import { LengthSplit } from '../types';
import { groupSplits } from '../utils/groupSplits';
import './SetSummary.css';

interface SetSummaryProps {
  splits: LengthSplit[];
  poolLengthM: number;
}

/**
 * Compact summary of what was swum: e.g., "4×100m, 8×50m, 4×25m"
 */
export function SetSummary({ splits, poolLengthM }: SetSummaryProps) {
  if (splits.length === 0) return null;

  const groups = groupSplits(splits, poolLengthM);

  // Count distances: how many sets of each distance
  const distanceCounts = new Map<number, number>();
  for (const group of groups) {
    const dist = group.totalDistance;
    distanceCounts.set(dist, (distanceCounts.get(dist) || 0) + 1);
  }

  // Sort by distance descending
  const entries = Array.from(distanceCounts.entries()).sort((a, b) => b[0] - a[0]);

  const summary = entries.map(([dist, count]) => `${count}×${dist}m`).join(', ');
  const totalDist = groups.reduce((sum, g) => sum + g.totalDistance, 0);

  return (
    <div className="set-summary">
      <span className="set-summary__label">Session:</span>
      <span className="set-summary__text">{summary}</span>
      <span className="set-summary__total">({totalDist}m total)</span>
    </div>
  );
}
