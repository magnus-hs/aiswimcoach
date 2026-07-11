import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { getUserSessions, SessionSummary } from '../api/sessionService';
import './StatisticsPage.css';

interface YearStats {
  year: number;
  sessions: number;
  totalDistanceM: number;
  totalTimeSeconds: number;
  avgPace: number;
  avgSwolf: number;
  avgStrokeRate: number;
  longestSessionM: number;
  shortestSessionM: number;
}

function formatTime(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
}

function formatDistance(meters: number): string {
  if (meters >= 1000) {
    return `${(meters / 1000).toFixed(1)}km`;
  }
  return `${meters}m`;
}

function formatPace(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}/100m`;
}

/**
 * Statistics page — shows yearly totals and averages across all sessions.
 * Accessible from the Profile dropdown at /statistics.
 */
export function StatisticsPage() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await getUserSessions();
        setSessions(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load sessions.');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const yearlyStats: YearStats[] = useMemo(() => {
    if (sessions.length === 0) return [];

    // Group sessions by year
    const byYear: Record<number, SessionSummary[]> = {};
    for (const s of sessions) {
      const year = new Date(s.session_date).getFullYear();
      if (!byYear[year]) byYear[year] = [];
      byYear[year].push(s);
    }

    // Compute stats per year
    return Object.entries(byYear)
      .map(([yearStr, yearSessions]) => {
        const year = parseInt(yearStr, 10);
        const totalDistanceM = yearSessions.reduce((sum, s) => sum + s.total_distance_meters, 0);
        const totalTimeSeconds = yearSessions.reduce((sum, s) => sum + s.total_time_seconds, 0);

        const paces = yearSessions.filter(s => s.average_pace_per_100m > 0).map(s => s.average_pace_per_100m);
        const swolfs = yearSessions.filter(s => s.swolf_score > 0).map(s => s.swolf_score);
        const rates = yearSessions.filter(s => s.stroke_rate > 0).map(s => s.stroke_rate);

        const avgPace = paces.length > 0 ? paces.reduce((a, b) => a + b, 0) / paces.length : 0;
        const avgSwolf = swolfs.length > 0 ? swolfs.reduce((a, b) => a + b, 0) / swolfs.length : 0;
        const avgStrokeRate = rates.length > 0 ? rates.reduce((a, b) => a + b, 0) / rates.length : 0;

        const distances = yearSessions.map(s => s.total_distance_meters);
        const longestSessionM = Math.max(...distances);
        const shortestSessionM = Math.min(...distances);

        return {
          year,
          sessions: yearSessions.length,
          totalDistanceM,
          totalTimeSeconds,
          avgPace,
          avgSwolf,
          avgStrokeRate,
          longestSessionM,
          shortestSessionM,
        };
      })
      .sort((a, b) => b.year - a.year); // Most recent year first
  }, [sessions]);

  // All-time totals
  const allTime = useMemo(() => {
    if (sessions.length === 0) return null;
    const totalDistanceM = sessions.reduce((sum, s) => sum + s.total_distance_meters, 0);
    const totalTimeSeconds = sessions.reduce((sum, s) => sum + s.total_time_seconds, 0);
    const firstDate = sessions.reduce((earliest, s) =>
      s.session_date < earliest ? s.session_date : earliest, sessions[0].session_date);
    return { totalDistanceM, totalTimeSeconds, sessions: sessions.length, since: firstDate };
  }, [sessions]);

  return (
    <div className="statistics-page">
      <Link to="/" className="statistics-page__back">← Back to Dashboard</Link>
      <h1 className="statistics-page__heading">Statistics</h1>
      <p className="statistics-page__subtitle">Your swimming history at a glance</p>

      {loading && <p className="statistics-page__loading">Loading…</p>}
      {error && <p className="statistics-page__error">{error}</p>}

      {!loading && !error && sessions.length === 0 && (
        <p className="statistics-page__empty">No sessions yet. Upload some swims to see your statistics.</p>
      )}

      {!loading && allTime && (
        <>
          {/* All-time summary */}
          <section className="statistics-page__all-time" aria-label="All-time statistics">
            <h2>All Time</h2>
            <div className="statistics-page__grid">
              <div className="statistics-page__stat">
                <span className="statistics-page__stat-value">{allTime.sessions}</span>
                <span className="statistics-page__stat-label">Sessions</span>
              </div>
              <div className="statistics-page__stat">
                <span className="statistics-page__stat-value">{formatDistance(allTime.totalDistanceM)}</span>
                <span className="statistics-page__stat-label">Total Distance</span>
              </div>
              <div className="statistics-page__stat">
                <span className="statistics-page__stat-value">{formatTime(allTime.totalTimeSeconds)}</span>
                <span className="statistics-page__stat-label">Total Time</span>
              </div>
              <div className="statistics-page__stat">
                <span className="statistics-page__stat-value">
                  {new Date(allTime.since).toLocaleDateString(undefined, { month: 'short', year: 'numeric' })}
                </span>
                <span className="statistics-page__stat-label">Swimming Since</span>
              </div>
            </div>
          </section>

          {/* Yearly breakdown */}
          <section className="statistics-page__yearly" aria-label="Yearly statistics">
            <h2>By Year</h2>
            <div className="statistics-page__years">
              {yearlyStats.map((ys) => (
                <div key={ys.year} className="statistics-page__year-card">
                  <h3 className="statistics-page__year-heading">{ys.year}</h3>
                  <div className="statistics-page__year-grid">
                    <div className="statistics-page__year-stat">
                      <span className="statistics-page__year-value">{ys.sessions}</span>
                      <span className="statistics-page__year-label">Sessions</span>
                    </div>
                    <div className="statistics-page__year-stat">
                      <span className="statistics-page__year-value">{formatDistance(ys.totalDistanceM)}</span>
                      <span className="statistics-page__year-label">Distance</span>
                    </div>
                    <div className="statistics-page__year-stat">
                      <span className="statistics-page__year-value">{formatTime(ys.totalTimeSeconds)}</span>
                      <span className="statistics-page__year-label">Time</span>
                    </div>
                    <div className="statistics-page__year-stat">
                      <span className="statistics-page__year-value">{ys.avgPace > 0 ? formatPace(ys.avgPace) : '—'}</span>
                      <span className="statistics-page__year-label">Avg Pace</span>
                    </div>
                    <div className="statistics-page__year-stat">
                      <span className="statistics-page__year-value">{ys.avgSwolf > 0 ? Math.round(ys.avgSwolf) : '—'}</span>
                      <span className="statistics-page__year-label">Avg SWOLF</span>
                    </div>
                    <div className="statistics-page__year-stat">
                      <span className="statistics-page__year-value">{ys.avgStrokeRate > 0 ? `${ys.avgStrokeRate.toFixed(1)}` : '—'}</span>
                      <span className="statistics-page__year-label">Avg SR (spm)</span>
                    </div>
                    <div className="statistics-page__year-stat">
                      <span className="statistics-page__year-value">{formatDistance(ys.longestSessionM)}</span>
                      <span className="statistics-page__year-label">Longest</span>
                    </div>
                    <div className="statistics-page__year-stat">
                      <span className="statistics-page__year-value">{formatDistance(ys.shortestSessionM)}</span>
                      <span className="statistics-page__year-label">Shortest</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
