import { LengthSplit } from '../types';

export interface SplitGroup {
  id: number;
  splits: LengthSplit[];
  totalDistance: number;
  totalTime: number;
  stroke: string;
  avgPacePer100m: number;
  restAfter: number | null;
}

/**
 * Group consecutive same-stroke splits into reps/sets.
 * A new group starts when:
 * - The stroke type changes
 * - The previous split has a rest_after_seconds value (rest between sets)
 */
export function groupSplits(splits: LengthSplit[], poolLengthM: number): SplitGroup[] {
  if (splits.length === 0) return [];

  const groups: SplitGroup[] = [];
  let currentSplits: LengthSplit[] = [splits[0]];

  for (let i = 1; i < splits.length; i++) {
    const prev = splits[i - 1];
    const curr = splits[i];

    // Break into new group if rest after previous OR stroke change
    if (prev.rest_after_seconds != null || curr.stroke !== currentSplits[0].stroke) {
      groups.push(buildGroup(groups.length, currentSplits, poolLengthM));
      currentSplits = [curr];
    } else {
      currentSplits.push(curr);
    }
  }

  // Emit final group
  if (currentSplits.length > 0) {
    groups.push(buildGroup(groups.length, currentSplits, poolLengthM));
  }

  return groups;
}

function buildGroup(id: number, splits: LengthSplit[], poolLengthM: number): SplitGroup {
  const totalDistance = splits.length * poolLengthM;
  const totalTime = splits.reduce((sum, s) => sum + s.time_seconds, 0);
  const avgPacePer100m = totalDistance > 0 ? (totalTime / totalDistance) * 100 : 0;
  const lastSplit = splits[splits.length - 1];
  const restAfter = lastSplit.rest_after_seconds ?? null;

  return {
    id,
    splits,
    totalDistance,
    totalTime,
    stroke: splits[0].stroke,
    avgPacePer100m,
    restAfter,
  };
}

/** Format seconds as M:SS.d (e.g., "1:32.5") */
export function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins > 0) {
    return `${mins}:${secs.toFixed(1).padStart(4, '0')}`;
  }
  return `${secs.toFixed(1)}s`;
}

/** Format rest duration: "15s" for ≤60s, "1:30" for >60s */
export function formatRest(seconds: number): string {
  if (seconds <= 60) {
    return `${Math.round(seconds)}s`;
  }
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}
