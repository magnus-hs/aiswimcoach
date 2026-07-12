import { ApiError } from '../types';

// --- Helpers ---

function getAuthToken(): string {
  const token = localStorage.getItem('auth_token');
  if (!token) {
    throw new Error('No authentication token found. Please log in.');
  }
  return token;
}

function errorMessageForStatus(status: number, bodyText: string): string {
  switch (status) {
    case 401:
      return 'Authentication required. Please log in again.';
    case 400:
      return bodyText || 'Invalid request. Please check your input.';
    default:
      if (status >= 500 && status <= 599) {
        return 'A server error occurred. Please try again in a moment.';
      }
      return bodyText || 'An unexpected error occurred.';
  }
}

async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const token = getAuthToken();
  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        Authorization: `Bearer ${token}`,
      },
    });
  } catch {
    throw new ApiError(0, 'Could not reach the server. Check your connection and retry.');
  }

  if (!response.ok) {
    const text = await response.text();
    let message = text;
    try {
      const json = JSON.parse(text);
      message = json.error || json.message || text;
    } catch {
      // use raw text
    }
    throw new ApiError(response.status, errorMessageForStatus(response.status, message));
  }

  return response;
}

const BASE = () => import.meta.env.VITE_API_ENDPOINT;

// --- API Functions ---

/**
 * Export all of the authenticated user's data (GDPR data export).
 *
 * @returns A Blob containing the JSON export, suitable for triggering a download.
 * @throws {ApiError} When the server returns a non-2xx response
 * @throws {Error} When a network error prevents the request from completing
 */
export async function exportMyData(): Promise<Blob> {
  const url = `${BASE()}/account/export`;
  const response = await authFetch(url, { method: 'GET' });
  return response.blob();
}

/**
 * Permanently delete the authenticated user's account and all associated data.
 *
 * Requires explicit confirmation, which is sent as {confirm: "DELETE"} in the body.
 *
 * @throws {ApiError} When the server returns a non-2xx response
 * @throws {Error} When a network error prevents the request from completing
 */
export async function deleteMyAccount(): Promise<void> {
  const url = `${BASE()}/account`;
  await authFetch(url, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ confirm: 'DELETE' }),
  });
}
