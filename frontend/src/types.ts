/**
 * Shared TypeScript types for the AI Swim Coach frontend.
 */

export interface LengthSplit {
  length_number: number;
  time_seconds: number;
  stroke: string;
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

export interface FullResponse {
  session: SessionInfo;
  splits: LengthSplit[];
  metrics: { pace: number; swolf: number; stroke_rate: number };
  coaching: CoachingResponse;
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
