/**
 * Personal Best grouping utilities.
 *
 * Groups PBs by stroke type and merges manual/derived entries for side-by-side comparison.
 *
 * Validates: Requirements 4.1, 4.3, 4.4, 4.6
 */

import { PersonalBest } from '../api/planService';

export interface EventEntry {
  event: string;
  distance: number;
  manual?: PersonalBest;
  derived?: PersonalBest;
}

export interface StrokeGroup {
  stroke: string;
  events: EventEntry[];
}

/**
 * Parse stroke type from event string.
 * "100m Freestyle" → "Freestyle"
 */
export function parseStrokeFromEvent(event: string): string {
  const match = event.match(/^\d+m\s+(.+)$/);
  return match ? match[1] : 'Other';
}

/**
 * Parse distance from event string.
 * "100m Freestyle" → 100
 */
export function parseDistanceFromEvent(event: string): number {
  const match = event.match(/^(\d+)m/);
  return match ? parseInt(match[1], 10) : 0;
}

/**
 * Group personal bests by stroke, merging manual and derived entries for the same event.
 *
 * - Builds a map: stroke → event → {manual?, derived?}
 * - Sorts strokes alphabetically
 * - Sorts events within each stroke by distance ascending
 * - Omits stroke groups with zero entries
 */
export function groupPersonalBests(pbs: PersonalBest[]): StrokeGroup[] {
  // Build map: stroke → event → EventEntry
  const strokeMap = new Map<string, Map<string, EventEntry>>();

  for (const pb of pbs) {
    const stroke = parseStrokeFromEvent(pb.event);
    const distance = parseDistanceFromEvent(pb.event);

    if (!strokeMap.has(stroke)) {
      strokeMap.set(stroke, new Map());
    }

    const eventMap = strokeMap.get(stroke)!;
    if (!eventMap.has(pb.event)) {
      eventMap.set(pb.event, { event: pb.event, distance });
    }

    const entry = eventMap.get(pb.event)!;
    if (pb.source === 'manual') {
      entry.manual = pb;
    } else if (pb.source === 'derived') {
      entry.derived = pb;
    }
  }

  // Convert to array, sort, and filter
  const groups: StrokeGroup[] = [];

  const sortedStrokes = Array.from(strokeMap.keys()).sort();

  for (const stroke of sortedStrokes) {
    const eventMap = strokeMap.get(stroke)!;
    const events = Array.from(eventMap.values()).sort((a, b) => a.distance - b.distance);

    if (events.length > 0) {
      groups.push({ stroke, events });
    }
  }

  return groups;
}

/**
 * Calculate and format the time difference between manual and derived PBs.
 *
 * Returns the absolute difference rounded to 1 decimal place,
 * labeled "faster" when manual < derived, "slower" when manual >= derived.
 */
export function formatTimeDiff(
  manualSeconds: number,
  derivedSeconds: number,
): { diff: string; label: 'faster' | 'slower' } {
  const difference = Math.abs(manualSeconds - derivedSeconds);
  const rounded = difference.toFixed(1);
  const label = manualSeconds < derivedSeconds ? 'faster' : 'slower';
  return { diff: rounded, label };
}
