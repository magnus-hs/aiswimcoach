import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import './StatisticsPage.css';

interface YearStats {
  year: number;
  sessions: number;
  total_distance_m: number;
  total_time_seconds: number;
  avg_pace: number;
  avg_swolf: number;
  longest_session_m: number;
}

interface AllTimeTotals {
  sessions: number;
  total_distance_m: number;
  total_time_seconds: number;
}

function formatTime(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
}

function formatPace(paceSeconds: number): string {
  const minutes = Math.floor(paceSeconds / 60);
  const seconds = Math.round(paceSeconds % 60);
  return `${minutes}:${seconds.toString().padStart(2, '0')}/100m`;
}

function formatDistance(meters: number): string {
  if (meters >= 1000) {
    return `${(meters / 1000).toFixed(1)}km`;
  }
  return `${meters}m`;
}

/**
 * Statistics page — shows yearly swim totals and trends.
 * Accessible from the Profile dropdown at /statistics.
 */
export function StatisticsPage() {
  const [yearStats, setYearStats] = useState<YearStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [allTimeTotals, setAllTimeTotals] = useState<AllTimeTotals | null>(null);

  useEffect(() => {
    async function loadStats() {
      try {
        const token = localStorage.getItem('auth_token');
        if (!token) { setLoading(false); return; }
        const response = await fetch(`${import.meta.env.VITE_API_ENDPOINT}/statistics`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!response.ok) throw new Error('Failed to load statistics');
        const data = await response.json();
        setAllTimeTotals(data.all_time);
        setYearStats(data.yearly);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load statistics.');
      } finally {
        setLoading(false);
      }
    }
    loadStats();
  }, []);

  return (
    <div className="statistics-page">
      <Link to="/" className="statistics-page__back">← Back to Dashboard</Link>
      <h1 className="statistics-page__heading">Statistics</h1>
      <p className="statistics-page__subtitle">Your swimming history by year</p>

      {loading && <p className="statistics-page__loading">Loading…</p>}
      {error && <p className="statistics-page__error">{error}</p>}

      {!loading && !error && allTimeTotals && (
        <>
          <section className="statistics-page__all-time" aria-label="All-time totals">
            <h2>All Time</h2>
            <div className="statistics-page__totals-grid">
              <div className="statistics-page__total-item">
                <span className="statistics-page__total-value">{allTimeTotals.sessions}</span>
                <span className="statistics-page__total-label">Sessions</span>
              </div>
              <div className="statistics-page__total-item">
                <span className="statistics-page__total-value">{formatDistance(allTimeTotals.total_distance_m)}</span>
                <span className="statistics-page__total-label">Distance</span>
              </div>
              <div className="statistics-page__total-item">
                <span className="statistics-page__total-value">{formatTime(allTimeTotals.total_time_seconds)}</span>
                <span className="statistics-page__total-label">Time in Pool</span>
              </div>
            </div>
          </section>

          <section className="statistics-page__years" aria-label="Yearly statistics">
            <h2>By Year</h2>
            {yearStats.length === 0 ? (
              <p className="statistics-page__empty">No session data available.</p>
            ) : (
              <div className="statistics-page__year-cards">
                {yearStats.map(year => (
                  <div key={year.year} className="statistics-page__year-card">
                    <h3 className="statistics-page__year-title">{year.year}</h3>
                    <div className="statistics-page__year-grid">
                      <div className="statistics-page__stat">
                        <span className="statistics-page__stat-value">{year.sessions}</span>
                        <span className="statistics-page__stat-label">Sessions</span>
                      </div>
                      <div className="statistics-page__stat">
                        <span className="statistics-page__stat-value">{formatDistance(year.total_distance_m)}</span>
                        <span className="statistics-page__stat-label">Distance</span>
                      </div>
                      <div className="statistics-page__stat">
                        <span className="statistics-page__stat-value">{formatTime(year.total_time_seconds)}</span>
                        <span className="statistics-page__stat-label">Time</span>
                      </div>
                      <div className="statistics-page__stat">
                        <span className="statistics-page__stat-value">{year.avg_pace > 0 ? formatPace(year.avg_pace) : '—'}</span>
                        <span className="statistics-page__stat-label">Avg Pace</span>
                      </div>
                      <div className="statistics-page__stat">
                        <span className="statistics-page__stat-value">{year.avg_swolf > 0 ? Math.round(year.avg_swolf) : '—'}</span>
                        <span className="statistics-page__stat-label">Avg SWOLF</span>
                      </div>
                      <div className="statistics-page__stat">
                        <span className="statistics-page__stat-value">{formatDistance(year.longest_session_m)}</span>
                        <span className="statistics-page__stat-label">Longest Swim</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
