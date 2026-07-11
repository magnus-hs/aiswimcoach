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

const STROKES = ['Freestyle', 'Backstroke', 'Breaststroke', 'Butterfly', 'IM'];
const POOL_DISTANCES = ['50m', '100m', '200m', '400m', '800m', '1500m'];
const OPEN_WATER_DISTANCES = ['1 mile', '2km', '3km', '5km', '10km'];

type Category = 'pool' | 'openwater';

/**
 * Ability Assessment page — shows competitive assessment, time standards by stroke/distance,
 * and open water standards.
 */
export function AbilityAssessmentPage() {
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [allStandards, setAllStandards] = useState<any>(null);
  const [ageGroup, setAgeGroup] = useState<string>('');
  const [loading, setLoading] = useState(true);

  // Filter state
  const [category, setCategory] = useState<Category>('pool');
  const [stroke, setStroke] = useState('Freestyle');
  const [distance, setDistance] = useState('100m');

  useEffect(() => {
    async function loadData() {
      const token = localStorage.getItem('auth_token');
      if (!token) { setLoading(false); return; }
      try {
        const response = await fetch(`${import.meta.env.VITE_API_ENDPOINT}/profile/assessment`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (response.ok) {
          const data = await response.json();
          if (data.assessment) setAssessment(data.assessment);
          if (data.standards) setAllStandards(data.standards);
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

  // Get the specific standard for selected stroke + distance
  const getStandard = (): TimeStandard | null => {
    if (!allStandards) return null;
    const eventName = `${distance} ${stroke}`;
    const british = allStandards.british?.find((s: TimeStandard) => s.event === eventName);
    return british || null;
  };

  const getScottishStandard = (): TimeStandard | null => {
    if (!allStandards) return null;
    const eventName = `${distance} ${stroke}`;
    const scottish = allStandards.scottish?.find((s: TimeStandard) => s.event === eventName);
    return scottish || null;
  };

  const getOpenWaterStandard = (): TimeStandard | null => {
    if (!allStandards) return null;
    const eventName = `Open Water ${distance}`;
    const ow = allStandards.openwater?.find((s: TimeStandard) => s.event === eventName);
    return ow || null;
  };

  const selectedStandard = category === 'pool' ? getStandard() : getOpenWaterStandard();
  const scottishStandard = category === 'pool' ? getScottishStandard() : null;

  return (
    <div className="ability-page">
      <Link to="/" className="ability-page__back">← Back to Dashboard</Link>
      <h1 className="ability-page__heading">Competitive Ability Assessment</h1>
      <p className="ability-page__subtitle">
        Based on your last 10 sessions. Updated after each upload.
      </p>

      {loading && <p className="ability-page__loading">Loading…</p>}

      {!loading && !assessment && (
        <div className="ability-page__empty">
          <p>No assessment available yet.</p>
          <p>Upload a FIT file with a completed profile to generate your competitive assessment.</p>
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

      {!loading && allStandards && (
        <div className="ability-page__standards">
          <h2>Time Standards — {ageGroup} Male</h2>
          <p className="ability-page__standards-note">
            Source: British Masters Swimming & Scottish Swimming (2024/2025 season).
            Updated annually. Data sourced from{' '}
            <a href="https://www.swimming.org/masters/results-archive/" target="_blank" rel="noopener noreferrer">
              Swim England Masters Results Archive
            </a>{' '}
            and{' '}
            <a href="https://www.swimmingresults.org/mastersdata/results/" target="_blank" rel="noopener noreferrer">
              swimmingresults.org
            </a>.
          </p>

          <div className="ability-page__filters">
            <div className="ability-page__filter-group">
              <label>Category</label>
              <div className="ability-page__toggle">
                <button
                  className={`ability-page__toggle-btn ${category === 'pool' ? 'ability-page__toggle-btn--active' : ''}`}
                  onClick={() => setCategory('pool')}
                >
                  Pool
                </button>
                <button
                  className={`ability-page__toggle-btn ${category === 'openwater' ? 'ability-page__toggle-btn--active' : ''}`}
                  onClick={() => setCategory('openwater')}
                >
                  Open Water
                </button>
              </div>
            </div>

            {category === 'pool' && (
              <>
                <div className="ability-page__filter-group">
                  <label>Stroke</label>
                  <select
                    className="ability-page__select"
                    value={stroke}
                    onChange={(e) => setStroke(e.target.value)}
                  >
                    {STROKES.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div className="ability-page__filter-group">
                  <label>Distance</label>
                  <select
                    className="ability-page__select"
                    value={distance}
                    onChange={(e) => setDistance(e.target.value)}
                  >
                    {POOL_DISTANCES.map(d => <option key={d} value={d}>{d}</option>)}
                  </select>
                </div>
              </>
            )}

            {category === 'openwater' && (
              <div className="ability-page__filter-group">
                <label>Distance</label>
                <select
                  className="ability-page__select"
                  value={distance}
                  onChange={(e) => setDistance(e.target.value)}
                >
                  {OPEN_WATER_DISTANCES.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
            )}
          </div>

          {selectedStandard ? (
            <div className="ability-page__standard-result">
              <h3>{category === 'pool' ? `${distance} ${stroke}` : `Open Water ${distance}`}</h3>
              <table className="ability-page__table">
                <thead>
                  <tr>
                    <th>Organisation</th>
                    <th>National</th>
                    <th>Regional</th>
                    <th>County</th>
                    <th>Club</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td className="ability-page__event-cell">British Masters</td>
                    <td>{selectedStandard.national}</td>
                    <td>{selectedStandard.regional}</td>
                    <td>{selectedStandard.county}</td>
                    <td>{selectedStandard.club}</td>
                  </tr>
                  {scottishStandard && (
                    <tr>
                      <td className="ability-page__event-cell">Scottish Swimming</td>
                      <td>{scottishStandard.national}</td>
                      <td>{scottishStandard.regional}</td>
                      <td>{scottishStandard.county}</td>
                      <td>{scottishStandard.club}</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="ability-page__no-standard">
              No standards available for this combination. Try a different stroke or distance.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
