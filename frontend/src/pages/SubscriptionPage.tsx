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

      {!loading && (
        <section className="subscription-page__comparison">
          <h2>Feature Comparison</h2>
          <table className="subscription-page__table">
            <thead>
              <tr>
                <th>Feature</th>
                <th>Free</th>
                <th>Premium (£3/mo)</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Upload & track swim sessions</td>
                <td>✓</td>
                <td>✓</td>
              </tr>
              <tr>
                <td>Session splits & stroke breakdown</td>
                <td>✓</td>
                <td>✓</td>
              </tr>
              <tr>
                <td>Heart rate zones</td>
                <td>✓</td>
                <td>✓</td>
              </tr>
              <tr>
                <td>Personal bests (manual & derived)</td>
                <td>✓</td>
                <td>✓</td>
              </tr>
              <tr>
                <td>Statistics & yearly totals</td>
                <td>✓</td>
                <td>✓</td>
              </tr>
              <tr>
                <td>Friends & social features</td>
                <td>✓</td>
                <td>✓</td>
              </tr>
              <tr>
                <td>Training notes</td>
                <td>✓</td>
                <td>✓</td>
              </tr>
              <tr>
                <td>Goals & distance targets</td>
                <td>✓</td>
                <td>✓</td>
              </tr>
              <tr className="subscription-page__table-row--premium">
                <td>AI Coach chat</td>
                <td>—</td>
                <td>✓</td>
              </tr>
              <tr className="subscription-page__table-row--premium">
                <td>AI coaching tips on uploads</td>
                <td>—</td>
                <td>✓</td>
              </tr>
              <tr className="subscription-page__table-row--premium">
                <td>AI training plan generation</td>
                <td>—</td>
                <td>✓</td>
              </tr>
              <tr className="subscription-page__table-row--premium">
                <td>Competitive ability assessment</td>
                <td>—</td>
                <td>✓</td>
              </tr>
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
