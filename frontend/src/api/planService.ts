import { ApiError } from '../types';

/**
 * Structured multi-week training plan.
 */
export interface StructuredPlan {
  plan_id: string;
  created_at: string;
  status: 'draft' | 'active' | 'archived';
  status_updated_at: string;
  goal: { event: string; target_time: string; personal_best_seconds: number | null };
  duration_weeks: number;
  sessions_per_week: number;
  weeks?: WeekBlock[];
}

/**
 * A single week within a structured plan.
 */
export interface WeekBlock {
  week_number: number;
  sessions: SessionTemplate[];
}

/**
 * Individual session within a week block.
 */
export interface SessionTemplate {
  session_title: string;
  session_type: 'endurance' | 'speed' | 'technique' | 'threshold';
  warm_up: string[];
  main_set: string[];
  cool_down: string[];
  total_distance: number;
  focus_notes: string;
}

/**
 * Personal best record.
 */
export interface PersonalBest {
  event: string;
  time_seconds: number;
  source: 'manual' | 'derived';
  updated_at: string;
  session_id?: string;
}

/**
 * Get the JWT token from localStorage.
 */
function getAuthToken(): string {
  const token = localStorage.getItem('auth_token');
  if (!token) {
    throw new Error('No authentication token found. Please log in.');
  }
  return token;
}

/**
 * Base URL for the API.
 */
function baseUrl(): string {
  return import.meta.env.VITE_API_ENDPOINT;
}

/**
 * Generate a multi-week structured training plan.
 */
export async function generateStructuredPlan(params: {
  event: string;
  target_time: string;
  weeks: number;
  sessions_per_week?: number;
}): Promise<StructuredPlan> {
  const token = getAuthToken();

  let response: Response;
  try {
    response = await fetch(`${baseUrl()}/plans/generate`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(params),
    });
  } catch {
    throw new ApiError(0, 'Could not reach the server. Check your connection and retry.');
  }

  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(response.status, text || 'Failed to generate plan.');
  }

  return response.json() as Promise<StructuredPlan>;
}

/**
 * Retrieve all structured plans for the current user.
 */
export async function getStructuredPlans(): Promise<StructuredPlan[]> {
  const token = getAuthToken();

  let response: Response;
  try {
    response = await fetch(`${baseUrl()}/plans/structured`, {
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
    throw new ApiError(response.status, text || 'Failed to load plans.');
  }

  const data = await response.json();
  return (data.plans ?? data) as StructuredPlan[];
}

/**
 * Retrieve a single structured plan by ID (includes full week/session data).
 */
export async function getPlanById(planId: string): Promise<StructuredPlan> {
  const token = getAuthToken();

  let response: Response;
  try {
    response = await fetch(`${baseUrl()}/plans/${planId}`, {
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
    throw new ApiError(response.status, text || 'Failed to load plan.');
  }

  return response.json() as Promise<StructuredPlan>;
}

/**
 * Update the status of a structured plan (activate or archive).
 */
export async function updatePlanStatus(
  planId: string,
  status: 'active' | 'archived',
): Promise<void> {
  const token = getAuthToken();

  let response: Response;
  try {
    response = await fetch(`${baseUrl()}/plans/${planId}/status`, {
      method: 'PATCH',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ status }),
    });
  } catch {
    throw new ApiError(0, 'Could not reach the server. Check your connection and retry.');
  }

  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(response.status, text || 'Failed to update plan status.');
  }
}

/**
 * Save a manual personal best entry.
 */
export async function savePersonalBest(
  event: string,
  timeSeconds: number,
): Promise<void> {
  const token = getAuthToken();

  let response: Response;
  try {
    response = await fetch(`${baseUrl()}/personal-bests`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ event, time_seconds: timeSeconds }),
    });
  } catch {
    throw new ApiError(0, 'Could not reach the server. Check your connection and retry.');
  }

  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(response.status, text || 'Failed to save personal best.');
  }
}

/**
 * Retrieve all personal bests (manual + derived) for the current user.
 */
export async function getPersonalBests(): Promise<PersonalBest[]> {
  const token = getAuthToken();

  let response: Response;
  try {
    response = await fetch(`${baseUrl()}/personal-bests`, {
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
    throw new ApiError(response.status, text || 'Failed to load personal bests.');
  }

  const data = await response.json();
  return (data.personal_bests ?? data) as PersonalBest[];
}

/**
 * Delete a personal best entry by event name.
 */
export async function deletePersonalBest(event: string): Promise<void> {
  const token = getAuthToken();

  let response: Response;
  try {
    response = await fetch(`${baseUrl()}/personal-bests`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ event }),
    });
  } catch {
    throw new ApiError(0, 'Could not reach the server. Check your connection and retry.');
  }

  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(response.status, text || 'Failed to delete personal best.');
  }
}

/**
 * Reject (dismiss) a derived personal best so it won't appear again.
 */
export async function rejectDerivedPB(event: string): Promise<void> {
  const token = getAuthToken();

  let response: Response;
  try {
    response = await fetch(`${baseUrl()}/personal-bests/reject`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ event }),
    });
  } catch {
    throw new ApiError(0, 'Could not reach the server. Check your connection and retry.');
  }

  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(response.status, text || 'Failed to reject derived PB.');
  }
}
