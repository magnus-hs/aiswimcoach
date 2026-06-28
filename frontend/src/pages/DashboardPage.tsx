import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { getUserSessions, SessionSummary } from '../api/sessionService';
import { Sidebar } from '../components/Sidebar';
import { ActivityFeed } from '../components/ActivityFeed';
import { computeStreak } from '../utils/computeStreak';
import './DashboardPage.css';

/**
 * Dashboard page — two-column layout with Sidebar (profile + stats) and ActivityFeed.
 * Fetches sessions on mount, computes aggregate stats, and passes data to children.
 * Read-only feed with no inline upload capability.
 *
 * Validates: Requirements 3.1, 3.6, 3.7, 3.8
 */
export function DashboardPage() {
  const { email } = useAuth();

  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | undefined>(undefined);

  const fetchSessions = useCallback(async () => {
    setLoading(true);
    setError(undefined);
    try {
      const data = await getUserSessions();
      setSessions(data);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Failed to load sessions. Please try again.';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  // Compute aggregate stats from sessions
  const totalSessions = sessions.length;
  const totalDistance = sessions.reduce((sum, s) => sum + s.total_distance_meters, 0);
  const streak = computeStreak(sessions.map((s) => s.session_date));

  // Derive display name from email (use part before @)
  const displayName = email ? email.split('@')[0] : 'Swimmer';

  return (
    <div className="dashboard">
      <aside className="dashboard__sidebar">
        <Sidebar
          profilePictureUrl={null}
          displayName={displayName}
          memberSince=""
          totalSessions={totalSessions}
          totalDistanceMeters={totalDistance}
          currentStreakDays={streak}
        />
      </aside>
      <section className="dashboard__feed">
        <div className="dashboard__feed-header">
          <h1>Activity Feed</h1>
          <Link to="/activity/new" className="dashboard__new-activity-btn">
            + New Activity
          </Link>
        </div>
        <ActivityFeed
          sessions={sessions}
          loading={loading}
          error={error}
          onRetry={fetchSessions}
        />
      </section>
    </div>
  );
}
