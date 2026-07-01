import { ApiError } from '../types';

// --- Interfaces ---

export interface Comment {
  comment_id: string;
  user_id: string;
  display_name: string;
  text: string;
  created_at: string;
}

export interface InteractionsData {
  comments: Comment[];
  kudos_count: number;
  user_has_kudos: boolean;
}

export interface KudosToggleResult {
  action: 'added' | 'removed';
  kudos_count: number;
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
    case 403:
      return bodyText || 'You do not have permission to perform this action.';
    case 404:
      return 'Resource not found.';
    case 429:
      return 'Too many requests. Please try again in a moment.';
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

export async function getInteractions(sessionId: string): Promise<InteractionsData> {
  const url = `${BASE()}/sessions/${encodeURIComponent(sessionId)}/interactions`;
  const response = await authFetch(url, { method: 'GET' });
  const data = await response.json();
  return data as InteractionsData;
}

export async function addComment(sessionId: string, text: string): Promise<Comment> {
  const url = `${BASE()}/sessions/${encodeURIComponent(sessionId)}/comments`;
  const response = await authFetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
  const data = await response.json();
  return data as Comment;
}

export async function deleteComment(sessionId: string, commentId: string): Promise<void> {
  const url = `${BASE()}/sessions/${encodeURIComponent(sessionId)}/comments/${encodeURIComponent(commentId)}`;
  await authFetch(url, { method: 'DELETE' });
}

export async function toggleKudos(sessionId: string): Promise<KudosToggleResult> {
  const url = `${BASE()}/sessions/${encodeURIComponent(sessionId)}/kudos`;
  const response = await authFetch(url, { method: 'POST' });
  const data = await response.json();
  return data as KudosToggleResult;
}
