import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import './AbilityAssessmentPage.css';

interface Assessment {
  percentile_estimate: string;
  local_ranking: string;
  national_ranking: string;
  competitive_analysis: string;
}

interface TimeStandard {
  event: string;
  national: string;
  regional: string;
  county: string;
  club: string;
}

/**
 * Ability Assessment page — shows the user's competitive assessment
 * (updated after each upload based on last 10 sessions) and time standards.
 */
export function AbilityAssessmentPage() {
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [standards, setStandards] = useState<{ british: TimeStandard[]; scottish: TimeStandard[] } | null>(null);
  const [ageGroup, setAgeGroup] = useState<string>('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      const token = localStorage.getItem('auth_token');
      if (!token) { setLoading(false); return; }

      try {
        // Fetch assessment and standards from profile
        const response = await fetch(`${import.meta.env.VITE_API_ENDPOINT}/profile/assessment`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (response.ok) {
          const data = await response.json();
          if (data.assessment) setAssessment(data.assessment);
          if (data.standards) setStandards(data.standards);
          if (data.age_group) setAgeGroup(data.age_group);
        }
      } catch {
        // Non-critical
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="ability-page">
      <Link to="/" className="ability-page__back">← Back to Dashboard</Link>
      <h1 className="ability-page__heading">Competitive Ability Assessment</h1>
      <p className="ability-page__subtitle">
        Based on your last 10 sessions. Updated after each upload.
      </p>

      {loading && <p className="ability-page__loading">Loading assessment…</p>}

      {!loading && !assessment && (
        <div className="ability-page__empty">
          <p>No assessment available yet.</p>
          <p>Upload a FIT file with a completed profile (date of birth, nationality, locality, ability level) to generate your competitive assessment.</p>
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

      {!loading && standards && (
        <div className="ability-page__standards">
          <h2>Time Standards — {ageGroup} Male</h2>
          <p className="ability-page__standards-note">
            Source: British Masters Swimming & Scottish Swimming (2024/2025 season).
            Updated annually.
          </p>

          <h3>British Masters Standards</h3>
          <table className="ability-page__table">
            <thead>
              <tr>
                <th>Event</th>
                <th>National</th>
                <th>Regional</th>
                <th>County</th>
                <th>Club</th>
              </tr>
            </thead>
            <tbody>
              {standards.british.map(s => (
                <tr key={s.event}>
                  <td className="ability-page__event-cell">{s.event}</td>
                  <td>{s.national}</td>
                  <td>{s.regional}</td>
                  <td>{s.county}</td>
                  <td>{s.club}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h3>Scottish Masters Standards</h3>
          <table className="ability-page__table">
            <thead>
              <tr>
                <th>Event</th>
                <th>National</th>
                <th>Regional</th>
                <th>County</th>
                <th>Club</th>
              </tr>
            </thead>
            <tbody>
              {standards.scottish.map(s => (
                <tr key={s.event}>
                  <td className="ability-page__event-cell">{s.event}</td>
                  <td>{s.national}</td>
                  <td>{s.regional}</td>
                  <td>{s.county}</td>
                  <td>{s.club}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
