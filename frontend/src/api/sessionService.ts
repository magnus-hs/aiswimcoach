import { ApiError, SessionInfo, LengthSplit, CoachingResponse } from '../types';
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
  percentile_estimate: string;
  local_ranking: string;
  national_ranking: string;
  competitive_analysis: string;
}

/**
 * Training plan with goal likelihood.
 */
export interface TrainingPlan {
  session_title: string;
  warm_up: string[];
  main_set: string[];
  cool_down: string[];
  total_distance: number;
  focus_notes: string;
  goal_likelihood?: string;
}

/**
 * Complete session record.
 */
export interface Session {
  session_id: string;
  user_id: string;
  session_date: string;
  pool_length_meters: number;
  total_distance_meters: number;
  total_time_seconds: number;
  stroke_type: string;
  average_pace_per_100m: number;
  swolf_score: number;
  stroke_rate: number;
  uploaded_at: string;
  s3_key: string;
  hr_zones?: HRZonesData;
  ability_assessment?: AbilityAssessment;
}

/**
 * Per-stroke percentage breakdown entry.
 */
export interface StrokeBreakdownEntry {
  stroke: string;
  lengths: number;
  percent: number;
}

/**
 * Session summary for history list.
 */
export interface SessionSummary {
  session_id: string;
  session_date: string;
  pool_length_meters: number;
  total_distance_meters: number;
  total_time_seconds: number;
  stroke_type: string;
  average_pace_per_100m: number;
  swolf_score: number;
  stroke_rate: number;
  stroke_breakdown?: StrokeBreakdownEntry[];
  splits?: LengthSplit[];
  kudos?: { user_id: string; created_at: string }[];
  comments?: { comment_id: string; user_id: string; display_name: string; text: string; created_at: string }[];
}

/**
 * Full session details with splits, metrics, and coaching.
 */
export interface SessionDetail {
  session: SessionInfo;
  splits: LengthSplit[];
  metrics: { pace: number; swolf: number; stroke_rate: number };
  coaching: CoachingResponse;
  hr_zones?: HRZonesData;
  ability_assessment?: AbilityAssessment;
  training_plan?: TrainingPlan;
  session_id: string;
  hr_timeseries?: { t: number; hr: number }[] | null;
  stroke_breakdown?: StrokeBreakdownEntry[];
}

/**
 * Maps HTTP status codes to user-facing error messages for session operations.
 */
function errorMessageForStatus(status: number, bodyText: string): string {
  switch (status) {
    case 401:
      return 'Authentication required. Please log in again.';
    case 404:
      return 'Session not found.';
    case 500:
      return bodyText || 'Unable to load session history. Please try again.';
    default:
      if (status >= 500 && status <= 599) {
        return 'A server error occurred. Please try again in a moment.';
      }
      return bodyText || 'An unexpected error occurred.';
  }
}

/**
 * Get the JWT token from localStorage.
 * @throws {Error} If no token is found.
 */
function getAuthToken(): string {
  const token = localStorage.getItem('auth_token');
  if (!token) {
    throw new Error('No authentication token found. Please log in.');
  }
  return token;
}

/**
 * Retrieve user's session history.
 *
 * @param startDate - Optional ISO 8601 date filter (inclusive).
 * @param endDate - Optional ISO 8601 date filter (inclusive).
 * @returns List of session summaries ordered by session_date descending.
 * @throws {ApiError} When the server returns a non-2xx response.
 */

// --- Session cache (5-minute TTL) ---
let _sessionsCache: { data: SessionSummary[]; ts: number; key: string } | null = null;
const CACHE_TTL_MS = 5 * 60 * 1000;

/** Clear the sessions cache (call after new upload). */
export function invalidateSessionsCache(): void {
  _sessionsCache = null;
}

function isValidSessionDate(dateStr: string): boolean {
  if (!dateStr) return false;
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return false;
  const year = d.getFullYear();
  return year >= 1990 && year <= 2030;
}

export async function getUserSessions(
  startDate?: string,
  endDate?: string,
  options?: { all?: boolean },
): Promise<SessionSummary[]> {
  const fetchAll = options?.all ?? false;
  const cacheKey = `${startDate || ''}_${endDate || ''}_${fetchAll ? 'all' : ''}`;

  // Return cached if fresh
  if (_sessionsCache && _sessionsCache.key === cacheKey && (Date.now() - _sessionsCache.ts) < CACHE_TTL_MS) {
    return _sessionsCache.data;
  }

  const token = getAuthToken();

  const queryParams = new URLSearchParams();
  if (startDate) {
    queryParams.append('start_date', startDate);
  }
  if (endDate) {
    queryParams.append('end_date', endDate);
  }
  if (fetchAll) {
    queryParams.append('all', 'true');
  }

  const url = `${import.meta.env.VITE_API_ENDPOINT}/sessions${
    queryParams.toString() ? `?${queryParams.toString()}` : ''
  }`;

  let response: Response;
  try {
    response = await fetch(url, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  } catch {
    throw new ApiError(0, 'Could not reach the server. Check your connection and retry.');
  }

  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(response.status, errorMessageForStatus(response.status, text));
  }

  const data = await response.json();
  const sessions = ((data.sessions ?? data) as SessionSummary[])
    .filter(s => isValidSessionDate(s.session_date));

  _sessionsCache = { data: sessions, ts: Date.now(), key: cacheKey };
  return sessions;
}

/**
 * Saved training plan from the backend.
 */
export interface SavedPlan {
  plan_id: string;
  created_at: string;
  goal: { event: string; target_time: string; volume_meters: number; timeframe: string };
  plan: { session_title: string; warm_up: string[]; main_set: string[]; cool_down: string[]; total_distance: number; focus_notes: string; goal_likelihood?: string };
}

/**
 * Retrieve single session by ID with full details.
 *
 * @param sessionId - Session identifier (UUID v4).
 * @returns Session details including splits, metrics, coaching, and optional HR zones/assessment.
 * @throws {ApiError} When the session doesn't exist or server returns a non-2xx response.
 */
export async function getSessionById(sessionId: string): Promise<SessionDetail> {
  const token = getAuthToken();

  let response: Response;
  try {
    response = await fetch(import.meta.env.VITE_API_ENDPOINT + `/sessions/${sessionId}`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  } catch {
    throw new ApiError(0, 'Could not reach the server. Check your connection and retry.');
  }

  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(response.status, errorMessageForStatus(response.status, text));
  }

  return response.json() as Promise<SessionDetail>;
}


/**
 * Retrieve user's saved training plans.
 *
 * @returns List of saved plans ordered by created_at descending.
 * @throws {ApiError} When the server returns a non-2xx response.
 */
export async function getUserPlans(): Promise<SavedPlan[]> {
  const token = getAuthToken();

  let response: Response;
  try {
    response = await fetch(`${import.meta.env.VITE_API_ENDPOINT}/plans`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  } catch {
    throw new ApiError(0, 'Could not reach the server. Check your connection and retry.');
  }

  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(response.status, errorMessageForStatus(response.status, text));
  }

  const data = await response.json();
  return (data.plans ?? []) as SavedPlan[];
}
