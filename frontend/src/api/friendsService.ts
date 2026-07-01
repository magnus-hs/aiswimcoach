import { ApiError } from '../types';

// --- Interfaces ---

export interface UserSearchResult {
  user_id: string;
  display_name: string;
  email_prefix: string;
  relationship_status: 'none' | 'pending_sent' | 'pending_received' | 'friends';
}

export interface FriendRequest {
  request_id: string;
  from_user_id: string;
  from_display_name: string;
  created_at: string;
}

export interface Friend {
  user_id: string;
  display_name: string;
  since: string;
}

export interface FriendActivity {
  session_id: string;
  session_date: string;
  total_distance_meters: number;
  total_time_seconds: number;
  stroke_type: string;
  average_pace_per_100m: number;
  swolf_score: number;
  friend_display_name: string;
  friend_user_id: string;
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
    case 404:
      return 'Resource not found.';
    case 409:
      return bodyText || 'Conflict: the operation could not be completed.';
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

export async function searchUsers(query: string): Promise<UserSearchResult[]> {
  const url = `${BASE()}/friends/search?q=${encodeURIComponent(query)}`;
  const response = await authFetch(url, { method: 'GET' });
  const data = await response.json();
  return (data.results ?? data) as UserSearchResult[];
}

export async function sendFriendRequest(targetUserId: string): Promise<void> {
  const url = `${BASE()}/friends/request`;
  await authFetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target_user_id: targetUserId }),
  });
}

export async function getPendingRequests(): Promise<FriendRequest[]> {
  const url = `${BASE()}/friends/requests`;
  const response = await authFetch(url, { method: 'GET' });
  const data = await response.json();
  return (data.requests ?? data) as FriendRequest[];
}

export async function acceptRequest(requestId: string): Promise<void> {
  const url = `${BASE()}/friends/requests/${encodeURIComponent(requestId)}/accept`;
  await authFetch(url, { method: 'POST' });
}

export async function declineRequest(requestId: string): Promise<void> {
  const url = `${BASE()}/friends/requests/${encodeURIComponent(requestId)}/decline`;
  await authFetch(url, { method: 'POST' });
}

export async function getFriends(): Promise<Friend[]> {
  const url = `${BASE()}/friends`;
  const response = await authFetch(url, { method: 'GET' });
  const data = await response.json();
  return (data.friends ?? data) as Friend[];
}

export async function removeFriend(friendUserId: string): Promise<void> {
  const url = `${BASE()}/friends/${encodeURIComponent(friendUserId)}`;
  await authFetch(url, { method: 'DELETE' });
}

export async function getFriendsActivities(): Promise<FriendActivity[]> {
  const url = `${BASE()}/friends/activities`;
  const response = await authFetch(url, { method: 'GET' });
  const data = await response.json();
  return (data.activities ?? data) as FriendActivity[];
}

export async function getActivityVisibility(): Promise<boolean> {
  const url = `${BASE()}/friends/visibility`;
  const response = await authFetch(url, { method: 'GET' });
  const data = await response.json();
  return data.visible === true || data.visibility === 'shared';
}

export async function updateActivityVisibility(visible: boolean): Promise<void> {
  const url = `${BASE()}/friends/visibility`;
  await authFetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ visible }),
  });
}
