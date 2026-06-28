import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import './AbilityAssessmentPage.css';

interface Assessment {
  percentile_estimate: string;
  local_ranking: string;
  national_ranking: string;
  competitive_analysis: string;
}

/**
 * Standalone page showing the user's competitive ability assessment.
 * Accessible from Profile menu.
 */
export function AbilityAssessmentPage() {
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadAssessment() {
      try {
        const token = localStorage.getItem('auth_token');
        if (!token) return;
        const response = await fetch(`${import.meta.env.VITE_API_ENDPOINT}/sessions`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (response.ok) {
          const data = await response.json();
          const sessions = data.sessions ?? data;
          for (const session of sessions) {
            if (session.ability_assessment) {
              setAssessment(session.ability_assessment);
              break;
            }
          }
        }
      } catch {
        // Non-critical
      } finally {
        setLoading(false);
      }
    }
    loadAssessment();
  }, []);

  return (
    <div className="ability-page">
      <Link to="/" className="ability-page__back">← Back to Dashboard</Link>
      <h1 className="ability-page__heading">Competitive Ability Assessment</h1>

      {loading && <p className="ability-page__loading">Loading assessment…</p>}

      {!loading && !assessment && (
        <div className="ability-page__empty">
          <p>No assessment available yet.</p>
          <p>Upload a FIT file with a completed profile (age, nationality, locality, ability level) to generate your competitive assessment.</p>
        </div>
      )}

      {!loading && assessment && (
        <div className="ability-page__content">
          <div className="ability-page__card">
            <span className="ability-page__label">Percentile Ranking</span>
            <p className="ability-page__value">{assessment.percentile_estimate}</p>
          </div>
          <div className="ability-page__card">
            <span className="ability-page__label">Local Ranking</span>
            <p className="ability-page__value">{assessment.local_ranking}</p>
          </div>
          <div className="ability-page__card">
            <span className="ability-page__label">National Ranking</span>
            <p className="ability-page__value">{assessment.national_ranking}</p>
          </div>
          <div className="ability-page__card ability-page__card--full">
            <span className="ability-page__label">Competitive Analysis</span>
            <p className="ability-page__analysis">{assessment.competitive_analysis}</p>
          </div>
        </div>
      )}
    </div>
  );
}
