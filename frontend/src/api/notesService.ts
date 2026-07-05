import { ApiError } from '../types';

// --- Interfaces ---

export interface TrainingNote {
  note_id: string;
  text: string;
  timestamp: string;
}

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
    case 404:
      return 'Note not found.';
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
 * Create a new training note.
 *
 * @param text - Note text (1–500 characters)
 * @returns The created training note with generated note_id and timestamp
 * @throws {ApiError} When the server returns a non-2xx response
 * @throws {Error} When a network error prevents the request from completing
 */
export async function createNote(text: string): Promise<TrainingNote> {
  const url = `${BASE()}/notes`;
  const response = await authFetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
  return response.json() as Promise<TrainingNote>;
}

/**
 * Retrieve all training notes for the authenticated user.
 *
 * @returns Array of training notes ordered by timestamp descending
 * @throws {ApiError} When the server returns a non-2xx response
 * @throws {Error} When a network error prevents the request from completing
 */
export async function getNotes(): Promise<TrainingNote[]> {
  const url = `${BASE()}/notes`;
  const response = await authFetch(url, { method: 'GET' });
  const data = await response.json();
  return (data.notes ?? data) as TrainingNote[];
}

/**
 * Delete a training note by ID.
 *
 * @param noteId - The ID of the note to delete
 * @throws {ApiError} When the server returns a non-2xx response (404 if not found)
 * @throws {Error} When a network error prevents the request from completing
 */
export async function deleteNote(noteId: string): Promise<void> {
  const url = `${BASE()}/notes/${encodeURIComponent(noteId)}`;
  await authFetch(url, { method: 'DELETE' });
}
