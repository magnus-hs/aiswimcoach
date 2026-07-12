import { useState } from 'react';
import { createCheckoutSession } from '../api/billingService';
import './UpgradePrompt.css';

interface UpgradePromptProps {
  /** Optional custom message to display above the upgrade CTA */
  message?: string;
}

/**
 * Displays a paywall prompt encouraging the user to subscribe to AI Coach Premium.
 * Clicking the button creates a Stripe Checkout session and redirects.
 */
export function UpgradePrompt({ message }: UpgradePromptProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleUpgrade = async () => {
    setLoading(true);
    setError('');
    try {
      const url = await createCheckoutSession();
      window.location.href = url;
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Please try again.');
      setLoading(false);
    }
  };

  return (
    <div className="upgrade-prompt" role="alert">
      <div className="upgrade-prompt__icon" aria-hidden="true">🏊‍♂️</div>
      <h3 className="upgrade-prompt__title">Unlock AI Coach Premium</h3>
      <p className="upgrade-prompt__description">
        {message || 'AI coaching, training plans, and ability assessments are premium features. Subscribe for £3/month to unlock everything.'}
      </p>
      <ul className="upgrade-prompt__features">
        <li>Unlimited AI coaching conversations</li>
        <li>Personalised training plans</li>
        <li>Competitive ability assessments</li>
        <li>Post-swim AI analysis on every upload</li>
      </ul>
      {error && <p className="upgrade-prompt__error">{error}</p>}
      <button
        className="upgrade-prompt__button"
        onClick={handleUpgrade}
        disabled={loading}
        aria-busy={loading}
      >
        {loading ? 'Redirecting…' : 'Upgrade Now — £3/month'}
      </button>
    </div>
  );
}
