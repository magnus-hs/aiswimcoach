import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getUserSessions, SessionSummary } from '../api/sessionService';
import './StatisticsPage.css';

interface YearStats {
  year: number;
  sessions: number;
  totalDistanceM: number;
  totalTimeS: number;
  avgPace: number;
  avgSwolf: number;
  longestSessionM: number;
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
  const [allTimeTotals, setAllTimeTotals] = useState<{
    sessions: number;
    distance: number;
    time: number;
  } | null>(null);

  useEffect(() => {
    async function loadStats() {
      try {
        const sessions = await getUserSessions();
        const byYear = new Map<number, SessionSummary[]>();

        for (const session of sessions) {
          const year = new Date(session.session_date).getFullYear();
          if (!byYear.has(year)) byYear.set(year, []);
          byYear.get(year)!.push(session);
        }

        const stats: YearStats[] = [];
        for (const [year, yearSessions] of byYear) {
          const totalDist = yearSessions.reduce((s, sess) => s + sess.total_distance_meters, 0);
          const totalTime = yearSessions.reduce((s, sess) => s + sess.total_time_seconds, 0);
          const paces = yearSessions
            .filter(s => s.average_pace_per_100m > 0)
            .map(s => s.average_pace_per_100m);
          const swolfs = yearSessions
            .filter(s => s.swolf_score > 0)
            .map(s => s.swolf_score);
          const longest = Math.max(...yearSessions.map(s => s.total_distance_meters));

          stats.push({
            year,
            sessions: yearSessions.length,
            totalDistanceM: totalDist,
            totalTimeS: totalTime,
            avgPace: paces.length > 0 ? paces.reduce((a, b) => a + b, 0) / paces.length : 0,
            avgSwolf: swolfs.length > 0 ? swolfs.reduce((a, b) => a + b, 0) / swolfs.length : 0,
            longestSessionM: longest,
          });
        }

        // Sort by year descending (most recent first)
        stats.sort((a, b) => b.year - a.year);
        setYearStats(stats);

        // All-time totals
        setAllTimeTotals({
          sessions: sessions.length,
          distance: sessions.reduce((s, sess) => s + sess.total_distance_meters, 0),
          time: sessions.reduce((s, sess) => s + sess.total_time_seconds, 0),
        });
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
                <span className="statistics-page__total-value">{formatDistance(allTimeTotals.distance)}</span>
                <span className="statistics-page__total-label">Distance</span>
              </div>
              <div className="statistics-page__total-item">
                <span className="statistics-page__total-value">{formatTime(allTimeTotals.time)}</span>
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
                        <span className="statistics-page__stat-value">{formatDistance(year.totalDistanceM)}</span>
                        <span className="statistics-page__stat-label">Distance</span>
                      </div>
                      <div className="statistics-page__stat">
                        <span className="statistics-page__stat-value">{formatTime(year.totalTimeS)}</span>
                        <span className="statistics-page__stat-label">Time</span>
                      </div>
                      <div className="statistics-page__stat">
                        <span className="statistics-page__stat-value">{year.avgPace > 0 ? formatPace(year.avgPace) : '—'}</span>
                        <span className="statistics-page__stat-label">Avg Pace</span>
                      </div>
                      <div className="statistics-page__stat">
                        <span className="statistics-page__stat-value">{year.avgSwolf > 0 ? Math.round(year.avgSwolf) : '—'}</span>
                        <span className="statistics-page__stat-label">Avg SWOLF</span>
                      </div>
                      <div className="statistics-page__stat">
                        <span className="statistics-page__stat-value">{formatDistance(year.longestSessionM)}</span>
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
