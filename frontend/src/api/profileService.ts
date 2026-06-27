import { ApiError } from '../types';

/**
 * User profile data structure.
 */
export interface UserProfile {
  age: number;
  nationality: string;
  locality: string;
  ability_level: 'beginner' | 'intermediate' | 'advanced' | 'elite';
}

/**
 * Response from profile picture upload.
 */
export interface UploadProfilePictureResponse {
  profile_picture_url: string;
}

/**
 * Maps HTTP status codes to user-facing error messages for profile operations.
 */
function errorMessageForStatus(status: number, bodyText: string): string {
  switch (status) {
    case 400:
      return bodyText || 'Invalid profile data. Please check your input.';
    case 401:
      return 'Authentication required. Please log in again.';
    case 404:
      return 'Profile not found.';
    case 413:
      return 'Profile picture is too large. Maximum size is 2 MB.';
    case 422:
      return bodyText || 'Profile picture format is invalid. Use JPEG, PNG, or GIF.';
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
 * Save or update user profile.
 *
 * @param profile - User profile data.
 * @throws {ApiError} When the server returns a non-2xx response.
 */
export async function saveProfile(profile: UserProfile): Promise<void> {
  const token = getAuthToken();

  let response: Response;
  try {
    response = await fetch(import.meta.env.VITE_API_ENDPOINT + '/profile', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(profile),
    });
  } catch {
    throw new ApiError(0, 'Could not reach the server. Check your connection and retry.');
  }

  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(response.status, errorMessageForStatus(response.status, text));
  }
}

/**
 * Retrieve user profile.
 *
 * @returns User profile data or null if profile doesn't exist.
 * @throws {ApiError} When the server returns a non-2xx response (except 404).
 */
export async function getProfile(): Promise<UserProfile | null> {
  const token = getAuthToken();

  let response: Response;
  try {
    response = await fetch(import.meta.env.VITE_API_ENDPOINT + '/profile', {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  } catch {
    throw new ApiError(0, 'Could not reach the server. Check your connection and retry.');
  }

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(response.status, errorMessageForStatus(response.status, text));
  }

  return response.json() as Promise<UserProfile>;
}

/**
 * Upload profile picture to S3 and update user record.
 *
 * @param imageFile - Image file (JPEG, PNG, or GIF, max 2 MB).
 * @returns S3 URL of uploaded image.
 * @throws {ApiError} When the upload fails (invalid format, too large, etc.).
 */
export async function uploadProfilePicture(imageFile: File): Promise<string> {
  const token = getAuthToken();

  const formData = new FormData();
  formData.append('file', imageFile);

  let response: Response;
  try {
    response = await fetch(import.meta.env.VITE_API_ENDPOINT + '/profile/picture', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });
  } catch {
    throw new ApiError(0, 'Could not reach the server. Check your connection and retry.');
  }

  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(response.status, errorMessageForStatus(response.status, text));
  }

  const result = (await response.json()) as UploadProfilePictureResponse;
  return result.profile_picture_url;
}
