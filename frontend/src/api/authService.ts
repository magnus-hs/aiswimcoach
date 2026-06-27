import { ApiError } from '../types';

export interface LoginResponse {
  token: string;
  user_id: string;
  email: string;
}

export interface RegisterResponse {
  message: string;
}

/**
 * Maps HTTP status codes to user-facing error messages for authentication.
 */
function errorMessageForStatus(status: number, bodyText: string): string {
  switch (status) {
    case 401:
      return 'Invalid email or password.';
    case 409:
      return 'An account with this email already exists.';
    case 400:
      return bodyText || 'Invalid request. Please check your input.';
    default:
      if (status >= 500 && status <= 599) {
        return 'A server error occurred. Please try again in a moment.';
      }
      return bodyText || 'An unexpected error occurred.';
  }
}

/**
 * Register a new user with email and password.
 *
 * @param email - Valid email address
 * @param password - Password (minimum 8 characters)
 * @returns Success message
 * @throws {ApiError} When the server returns a non-2xx response
 * @throws {Error} When a network error prevents the request from completing
 */
export async function register(email: string, password: string): Promise<RegisterResponse> {
  let response: Response;
  try {
    response = await fetch(import.meta.env.VITE_API_ENDPOINT + '/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
  } catch {
    throw new ApiError(0, 'Could not reach the server. Check your connection and retry.');
  }

  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(response.status, errorMessageForStatus(response.status, text));
  }

  return response.json() as Promise<RegisterResponse>;
}

/**
 * Login with email and password.
 *
 * @param email - Registered email address
 * @param password - User password
 * @returns JWT token and user information
 * @throws {ApiError} When the server returns a non-2xx response
 * @throws {Error} When a network error prevents the request from completing
 */
export async function login(email: string, password: string): Promise<LoginResponse> {
  let response: Response;
  try {
    response = await fetch(import.meta.env.VITE_API_ENDPOINT + '/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
  } catch {
    throw new ApiError(0, 'Could not reach the server. Check your connection and retry.');
  }

  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(response.status, errorMessageForStatus(response.status, text));
  }

  return response.json() as Promise<LoginResponse>;
}

/**
 * Verify the current JWT token.
 *
 * @param token - JWT token to verify
 * @returns User information if token is valid
 * @throws {ApiError} When the server returns a non-2xx response
 * @throws {Error} When a network error prevents the request from completing
 */
export async function verifyToken(token: string): Promise<{ user_id: string; email: string }> {
  let response: Response;
  try {
    response = await fetch(import.meta.env.VITE_API_ENDPOINT + '/auth/verify', {
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

  return response.json() as Promise<{ user_id: string; email: string }>;
}
