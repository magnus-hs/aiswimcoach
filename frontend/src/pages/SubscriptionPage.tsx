import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { createPortalSession } from '../api/billingService';
import { UpgradePrompt } from '../components/UpgradePrompt';
import './SubscriptionPage.css';

export function SubscriptionPage() {
  const [tier, setTier] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [portalLoading, setPortalLoading] = useState(false);

  useEffect(() => {
    async function loadTier() {
      try {
        const token = localStorage.getItem('auth_token');
        if (!token) { setLoading(false); return; }
        const resp = await fetch(`${import.meta.env.VITE_API_ENDPOINT}/profile`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (resp.ok) {
          const data = await resp.json();
          setTier(data.tier || 'free');
        } else {
          setTier('free');
        }
      } catch {
        setTier('free');
      } finally {
        setLoading(false);
      }
    }
    loadTier();
  }, []);

  const handleManage = async () => {
    setPortalLoading(true);
    try {
      const url = await createPortalSession();
      window.location.href = url;
    } catch {
      alert('Could not open subscription management. Please try again.');
      setPortalLoading(false);
    }
  };

  return (
    <div className="subscription-page">
      <Link to="/" className="subscription-page__back">← Back to Dashboard</Link>
      <h1 className="subscription-page__heading">Subscription</h1>

      {loading && <p className="subscription-page__loading">Loading…</p>}

      {!loading && tier === 'paid' && (
        <div className="subscription-page__active">
          <div className="subscription-page__badge">✓ Active</div>
          <h2>AI Swim Coach Premium</h2>
          <p className="subscription-page__price">£3/month</p>
          <p className="subscription-page__description">
            You have full access to AI coaching, training plans, and ability assessments.
          </p>
          <button
            className="subscription-page__manage-btn"
            onClick={handleManage}
            disabled={portalLoading}
          >
            {portalLoading ? 'Opening…' : 'Manage Subscription'}
          </button>
          <p className="subscription-page__manage-hint">
            Update payment method, view invoices, or cancel
          </p>
        </div>
      )}

      {!loading && tier !== 'paid' && (
        <UpgradePrompt />
      )}
    </div>
  );
}
