import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { getUserSessions, SessionSummary } from '../api/sessionService';
import { Sidebar } from '../components/Sidebar';
import { ActivityFeed } from '../components/ActivityFeed';
import './DashboardPage.css';

/**
 * Compute session counts for the last 4 ISO weeks (most recent last).
 */
function computeSessionsPerWeek(sessions: SessionSummary[]): number[] {
  const now = new Date();
  const weekCounts = [0, 0, 0, 0]; // 4 weeks: [3 weeks ago, 2 weeks ago, 1 week ago, this week]

  for (const session of sessions) {
    const sessionDate = new Date(session.session_date);
    const diffMs = now.getTime() - sessionDate.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    // Day of week (0=Monday, 6=Sunday) for calculating week start
    const todayDay = (now.getDay() + 6) % 7; // Convert Sun=0 to Mon=0
    const daysSinceThisWeekStart = todayDay;
    const daysIntoWeek = diffDays - daysSinceThisWeekStart;

    if (diffDays <= daysSinceThisWeekStart) {
      // Current week
      weekCounts[3]++;
    } else if (daysIntoWeek <= 7) {
      // 1 week ago
      weekCounts[2]++;
    } else if (daysIntoWeek <= 14) {
      // 2 weeks ago
      weekCounts[1]++;
    } else if (daysIntoWeek <= 21) {
      // 3 weeks ago
      weekCounts[0]++;
    }
  }

  return weekCounts;
}

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
  const [profilePictureUrl, setProfilePictureUrl] = useState<string | null>(null);
  const [memberSince, setMemberSince] = useState('');

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

  // Fetch user profile info (profile picture, member since)
  useEffect(() => {
    async function fetchUserInfo() {
      const token = localStorage.getItem('auth_token');
      if (!token) return;
      try {
        const response = await fetch(`${import.meta.env.VITE_API_ENDPOINT}/auth/user`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (response.ok) {
          const data = await response.json();
          if (data.profile_picture_url) {
            setProfilePictureUrl(data.profile_picture_url);
          }
          if (data.created_at) {
            const date = new Date(data.created_at);
            setMemberSince(date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' }));
          }
        }
      } catch {
        // Non-critical — silently ignore profile fetch failures
      }
    }
    fetchUserInfo();
  }, []);

  // Compute aggregate stats from sessions
  const totalSessions = sessions.length;
  const totalDistance = sessions.reduce((sum, s) => sum + s.total_distance_meters, 0);
  const sessionsPerWeek = computeSessionsPerWeek(sessions);

  // Compute swims this week, this month, and year to date
  const now = new Date();
  const startOfWeek = new Date(now);
  const dayOfWeek = (now.getDay() + 6) % 7; // Mon=0
  startOfWeek.setDate(now.getDate() - dayOfWeek);
  startOfWeek.setHours(0, 0, 0, 0);

  const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
  const startOfYear = new Date(now.getFullYear(), 0, 1);

  const swimsThisWeek = sessions.filter(s => new Date(s.session_date) >= startOfWeek).length;
  const swimsThisMonth = sessions.filter(s => new Date(s.session_date) >= startOfMonth).length;
  const swimsYTD = sessions.filter(s => new Date(s.session_date) >= startOfYear).length;

  // Compute distance this week, this month, and year to date
  const distanceThisWeek = sessions
    .filter(s => new Date(s.session_date) >= startOfWeek)
    .reduce((sum, s) => sum + s.total_distance_meters, 0);
  const distanceThisMonth = sessions
    .filter(s => new Date(s.session_date) >= startOfMonth)
    .reduce((sum, s) => sum + s.total_distance_meters, 0);
  const distanceYTD = sessions
    .filter(s => new Date(s.session_date) >= startOfYear)
    .reduce((sum, s) => sum + s.total_distance_meters, 0);

  // Derive display name from email (use part before @)
  const displayName = email ? email.split('@')[0] : 'Swimmer';

  return (
    <div className="dashboard">
      <aside className="dashboard__sidebar">
        <Sidebar
          profilePictureUrl={profilePictureUrl}
          displayName={displayName}
          memberSince={memberSince}
          totalSessions={totalSessions}
          totalDistanceMeters={totalDistance}
          swimsThisWeek={swimsThisWeek}
          swimsThisMonth={swimsThisMonth}
          swimsYTD={swimsYTD}
          sessionsPerWeek={sessionsPerWeek}
          distanceThisWeekMeters={distanceThisWeek}
          distanceThisMonthMeters={distanceThisMonth}
          distanceYTDMeters={distanceYTD}
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
