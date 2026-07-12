import { ApiError, FullResponse, TrainingGoal, TrainingPlan } from '../types';

/**
 * Maps HTTP status codes to user-facing error messages.
 * 422 uses the server body directly (identifies missing metrics).
 */
function errorMessageForStatus(status: number, bodyText: string): string {
  switch (status) {
    case 400:
      return 'The file could not be read — please try a different .fit file.';
    case 413:
      return 'The file is too large for this endpoint (max 10 MB).';
    case 422:
      return bodyText;
    case 502:
      return 'Our AI coach is temporarily unavailable. Please try again.';
    default:
      if (status >= 500 && status <= 599) {
        return 'A server error occurred. Please try again in a moment.';
      }
      return bodyText;
  }
}

/**
 * Uploads a .fit file to the backend and returns the full response
 * including session info, splits, metrics, and coaching.
 *
 * @param file - The .fit file selected by the user.
 * @returns The full response from the backend.
 * @throws {ApiError} When the server returns a non-2xx response.
 * @throws {Error} When a network error prevents the request from completing.
 */
export async function uploadFitFile(file: File): Promise<FullResponse> {
  const formData = new FormData();
  formData.append('file', file);

  // Get JWT token from localStorage
  const token = localStorage.getItem('auth_token');
  const headers: HeadersInit = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(import.meta.env.VITE_API_ENDPOINT + '/upload', {
      method: 'POST',
      headers,
      body: formData,
    });
  } catch {
    throw new ApiError(0, 'Could not reach the server. Check your connection and retry.');
  }

  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(response.status, errorMessageForStatus(response.status, text));
  }

  const data = await response.json();
  if (data.duplicate) {
    throw new ApiError(409, data.message || 'This swim was already uploaded.');
  }
  return data as FullResponse;
}


/**
 * Uploads a .fit file in bulk-import mode (skips AI coaching).
 * Returns session info, splits, and metrics but with coaching=null.
 *
 * @param file - The .fit file to upload.
 * @returns The full response from the backend (coaching will be null).
 * @throws {ApiError} When the server returns a non-2xx response.
 * @throws {Error} When a network error prevents the request from completing.
 */
export async function uploadFitFileBulk(file: File): Promise<FullResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const token = localStorage.getItem('auth_token');
  const headers: HeadersInit = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(import.meta.env.VITE_API_ENDPOINT + '/upload?skip_coaching=true', {
      method: 'POST',
      headers,
      body: formData,
    });
  } catch {
    throw new ApiError(0, 'Could not reach the server. Check your connection and retry.');
  }

  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(response.status, errorMessageForStatus(response.status, text));
  }

  return response.json() as Promise<FullResponse>;
}


/**
 * Generates a training plan from current metrics and a training goal.
 *
 * @param metrics - Current swim performance metrics.
 * @param goal - The swimmer's training goal.
 * @returns A structured training plan.
 * @throws {ApiError} When the server returns a non-2xx response.
 * @throws {Error} When a network error prevents the request from completing.
 */
export async function generateTrainingPlan(
  metrics: { pace: number; swolf: number; stroke_rate: number },
  goal: TrainingGoal,
): Promise<TrainingPlan> {
  // Get JWT token from localStorage
  const token = localStorage.getItem('auth_token');
  const headers: HeadersInit = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(import.meta.env.VITE_API_ENDPOINT + '/upload', {
      method: 'POST',
      headers,
      body: JSON.stringify({
        action: 'training_plan',
        metrics,
        goal,
      }),
    });
  } catch {
    throw new ApiError(0, 'Could not reach the server. Check your connection and retry.');
  }

  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(response.status, errorMessageForStatus(response.status, text));
  }

  return response.json() as Promise<TrainingPlan>;
}
