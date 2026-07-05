import { StrokeBreakdownEntry } from '../api/sessionService';
import { LengthSplit } from '../types';

/**
 * Returns the CSS variable for a stroke category color.
 * Drill gets a distinct orange to stand out from swimming stroke colors.
 */
export function strokeColor(stroke: string): string {
  const s = (stroke || '').toLowerCase();
  switch (s) {
    case 'freestyle':
      return 'var(--color-stroke-freestyle)';
    case 'backstroke':
      return 'var(--color-stroke-backstroke)';
    case 'breaststroke':
      return 'var(--color-stroke-breaststroke)';
    case 'butterfly':
      return 'var(--color-stroke-butterfly)';
    case 'im':
    case 'medley':
      return 'var(--color-stroke-im)';
    case 'mixed':
      return 'var(--color-stroke-mixed)';
    case 'drill':
      return 'var(--color-stroke-drill)';
    default:
      return 'var(--color-text)';
  }
}

/** Short, readable label for a stroke name. */
export function strokeLabel(stroke: string): string {
  const s = (stroke || '').toLowerCase();
  switch (s) {
    case 'freestyle':
      return 'Free';
    case 'backstroke':
      return 'Back';
    case 'breaststroke':
      return 'Breast';
    case 'butterfly':
      return 'Fly';
    case 'im':
    case 'medley':
      return 'IM';
    case 'mixed':
      return 'Mixed';
    case 'drill':
      return 'Drill';
    default:
      return stroke ? stroke.charAt(0).toUpperCase() + stroke.slice(1) : 'Unknown';
  }
}

/**
 * Compute a per-stroke percentage breakdown from per-length splits.
 * Used as a client-side fallback when the backend has not supplied one.
 * Each length counts as an equal unit.
 */
export function computeBreakdownFromSplits(splits: LengthSplit[]): StrokeBreakdownEntry[] {
  if (!splits || splits.length === 0) return [];
  const counts = new Map<string, number>();
  for (const s of splits) {
    const stroke = s.stroke || 'unknown';
    counts.set(stroke, (counts.get(stroke) ?? 0) + 1);
  }
  const total = splits.length;
  const entries: StrokeBreakdownEntry[] = [...counts.entries()].map(([stroke, lengths]) => ({
    stroke,
    lengths,
    percent: Math.round((lengths * 1000) / total) / 10,
  }));
  entries.sort((a, b) => b.lengths - a.lengths || a.stroke.localeCompare(b.stroke));
  return entries;
}

/**
 * Format a stroke breakdown into a compact string.
 * e.g. "95% Free · 5% Breast". Rounds to whole percents for display.
 */
export function formatStrokeBreakdown(breakdown: StrokeBreakdownEntry[]): string {
  if (!breakdown || breakdown.length === 0) return '';
  return breakdown
    .map((b) => `${Math.round(b.percent)}% ${strokeLabel(b.stroke)}`)
    .join(' · ');
}
