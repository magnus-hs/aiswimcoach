import { ApiError } from '../types';

/**
 * Retrieve the stored auth token.
 */
function getAuthToken(): string {
  const token = localStorage.getItem('auth_token');
  if (!token) throw new Error('Not authenticated');
  return token;
}

/**
 * Create a Stripe Checkout session for the AI Coach Premium subscription.
 * Returns the Stripe-hosted checkout URL to redirect the user to.
 */
export async function createCheckoutSession(): Promise<string> {
  let response: Response;
  try {
    response = await fetch(`${import.meta.env.VITE_API_ENDPOINT}/billing/checkout`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${getAuthToken()}` },
    });
  } catch {
    throw new ApiError(0, 'Could not reach the server. Check your connection and retry.');
  }

  if (!response.ok) {
    const text = await response.text().catch(() => '');
    throw new ApiError(response.status, text || 'Failed to start checkout');
  }

  const data = await response.json();
  return data.url;
}

/**
 * Create a Stripe Billing Portal session for managing the existing subscription.
 * Returns the portal URL to redirect the user to.
 */
export async function createPortalSession(): Promise<string> {
  let response: Response;
  try {
    response = await fetch(`${import.meta.env.VITE_API_ENDPOINT}/billing/portal`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${getAuthToken()}` },
    });
  } catch {
    throw new ApiError(0, 'Could not reach the server. Check your connection and retry.');
  }

  if (!response.ok) {
    const text = await response.text().catch(() => '');
    throw new ApiError(response.status, text || 'Failed to open billing portal');
  }

  const data = await response.json();
  return data.url;
}
