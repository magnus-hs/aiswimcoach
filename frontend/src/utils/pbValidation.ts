/**
 * Personal Best validation and construction utilities.
 *
 * Validates: Requirements 3.5, 3.6, 3.7, 3.8, 3.9
 */

export type StrokeType = 'Freestyle' | 'Backstroke' | 'Breaststroke' | 'Butterfly' | 'IM';
export type DistanceOption = '50' | '100' | '200' | '400' | '800' | '1500' | 'Custom';

export const STROKES: StrokeType[] = ['Freestyle', 'Backstroke', 'Breaststroke', 'Butterfly', 'IM'];
export const DISTANCES: DistanceOption[] = ['50', '100', '200', '400', '800', '1500', 'Custom'];
export const CUSTOM_DISTANCE_MIN = 25;
export const CUSTOM_DISTANCE_MAX = 5000;

/**
 * Validates a time input in M:SS or MM:SS format.
 *
 * - Minutes must be 0–59
 * - Seconds must be 00–59
 * - Returns the total seconds (minutes * 60 + seconds) when valid
 */
export function validateTimeInput(input: string): { valid: boolean; seconds?: number; error?: string } {
  const match = input.trim().match(/^(\d{1,2}):(\d{2})$/);
  if (!match) {
    return { valid: false, error: 'Enter time as M:SS (e.g., 1:05)' };
  }
  const minutes = parseInt(match[1], 10);
  const seconds = parseInt(match[2], 10);
  if (minutes < 0 || minutes > 59) {
    return { valid: false, error: 'Minutes must be 0-59' };
  }
  if (seconds < 0 || seconds > 59) {
    return { valid: false, error: 'Seconds must be 00-59' };
  }
  return { valid: true, seconds: minutes * 60 + seconds };
}

/**
 * Validates a custom distance input.
 *
 * - Must be a whole number (integer)
 * - Must be between 25 and 5000 inclusive
 */
export function validateCustomDistance(input: string): { valid: boolean; error?: string } {
  const trimmed = input.trim();
  if (trimmed === '') {
    return { valid: false, error: 'Distance must be a whole number' };
  }
  const num = Number(trimmed);
  if (isNaN(num) || !Number.isInteger(num)) {
    return { valid: false, error: 'Distance must be a whole number' };
  }
  if (num < CUSTOM_DISTANCE_MIN || num > CUSTOM_DISTANCE_MAX) {
    return { valid: false, error: `Distance must be between ${CUSTOM_DISTANCE_MIN} and ${CUSTOM_DISTANCE_MAX} meters` };
  }
  return { valid: true };
}

/**
 * Constructs an event name from stroke, distance, and optional custom distance.
 *
 * Format: "{distance}m {stroke}" (e.g., "100m Freestyle", "350m Backstroke")
 */
export function buildEventName(stroke: StrokeType, distance: DistanceOption, customDistance: string): string {
  const dist = distance === 'Custom' ? customDistance : distance;
  return `${dist}m ${stroke}`;
}
