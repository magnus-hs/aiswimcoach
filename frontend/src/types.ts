/**
 * Shared TypeScript types for the AI Swim Coach frontend.
 */

export interface LengthSplit {
  length_number: number;
  time_seconds: number;
  stroke: string;
  strokes: number;
  rest_after_seconds?: number | null;
}

export interface SessionInfo {
  start_time: string;
  pool_length_m: number;
  stroke: string;
  total_distance_m: number;
  total_time_seconds: number;
  num_lengths: number;
}

/**
 * AI-generated coaching response returned by the backend.
 *
 * Invariants (enforced by the backend):
 *   - tips contains exactly 3 items
 *   - each tip is a non-empty string of ≤ 300 characters
 *   - drill is a non-empty string of ≤ 500 characters
 */
export interface CoachingResponse {
  /** Exactly three concise, actionable improvement tips. */
  tips: [string, string, string];
  /** One specific drill recommendation targeting the swimmer's weakest area. */
  drill: string;
}

/**
 * Heart rate zone distribution data.
 */
export interface HRZonesData {
  zone_1_seconds: number;
  zone_2_seconds: number;
  zone_3_seconds: number;
  zone_4_seconds: number;
  zone_5_seconds: number;
  zone_1_percent: number;
  zone_2_percent: number;
  zone_3_percent: number;
  zone_4_percent: number;
  zone_5_percent: number;
  max_hr: number;
  zone_boundaries: Record<number, [number, number]>;
}

/**
 * AI-generated competitive ability assessment.
 */
export interface AbilityAssessment {
  /** Estimated percentile ranking within age group (e.g., "top 25%"). */
  percentile_estimate: string;
  /** Estimated local competition ranking in specified locality. */
  local_ranking: string;
  /** Estimated national competition ranking in specified nationality. */
  national_ranking: string;
  /** Assessment of competitiveness for age and population context. */
  competitive_analysis: string;
}

export interface FullResponse {
  session: SessionInfo;
  splits: LengthSplit[];
  metrics: { pace: number; swolf: number; stroke_rate: number };
  coaching: CoachingResponse;
  hr_zones?: HRZonesData;
  ability_assessment?: AbilityAssessment;
  session_id?: string;
}

/**
 * Application error thrown by the API client when the server returns a
 * non-ok HTTP response.
 */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly serverMessage: string,
  ) {
    super(`HTTP ${status}: ${serverMessage}`);
    this.name = 'ApiError';
  }
}

export interface TrainingGoal {
  event: string;
  target_time: string;
  volume_meters: number;
  timeframe: string;
}

export interface TrainingPlan {
  session_title: string;
  warm_up: string[];
  main_set: string[];
  cool_down: string[];
  total_distance: number;
  focus_notes: string;
}

