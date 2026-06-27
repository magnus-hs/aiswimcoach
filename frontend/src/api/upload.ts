import { ApiError, CoachingResponse } from '../types';

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
 * Uploads a .fit file to the backend and returns the AI coaching response.
 *
 * @param file - The .fit file selected by the user.
 * @returns The coaching response containing tips and a drill.
 * @throws {ApiError} When the server returns a non-2xx response.
 * @throws {Error} When a network error prevents the request from completing.
 */
export async function uploadFitFile(file: File): Promise<CoachingResponse> {
  const formData = new FormData();
  formData.append('file', file);

  let response: Response;
  try {
    response = await fetch(import.meta.env.VITE_API_ENDPOINT + '/upload', {
      method: 'POST',
      body: formData,
    });
  } catch {
    throw new ApiError(0, 'Could not reach the server. Check your connection and retry.');
  }

  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(response.status, errorMessageForStatus(response.status, text));
  }

  return response.json() as Promise<CoachingResponse>;
}
