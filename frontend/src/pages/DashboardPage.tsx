import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { getUserSessions, SessionSummary } from '../api/sessionService';
import { Sidebar } from '../components/Sidebar';
import { DistanceChartPoint } from '../components/DistanceChart';
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
  const [dateFilter, setDateFilter] = useState<{ start: string; end: string; label: string } | null>(null);
  const [weeklyGoalM, setWeeklyGoalM] = useState<number | null>(null);
  const [monthlyGoalM, setMonthlyGoalM] = useState<number | null>(null);
  const [yearlyGoalM, setYearlyGoalM] = useState<number | null>(null);

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

  // Fetch the swimmer's weekly distance goal (if set).
  useEffect(() => {
    async function fetchGoals() {
      const token = localStorage.getItem('auth_token');
      if (!token) return;
      try {
        const response = await fetch(`${import.meta.env.VITE_API_ENDPOINT}/profile/goals`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (response.ok) {
          const data = await response.json();
          const wd = data.goals?.weekly_distance_m;
          if (wd) setWeeklyGoalM(wd);
          const md = data.goals?.monthly_distance_m;
          if (md) setMonthlyGoalM(md);
          const yd = data.goals?.yearly_distance_m;
          if (yd) setYearlyGoalM(yd);
        }
      } catch {
        // Non-critical
      }
    }
    fetchGoals();
  }, []);

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
  const totalTime = sessions.reduce((sum, s) => sum + s.total_time_seconds, 0);
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

  // Compute chart data: daily distances for the week (Mon–Sun)
  const weeklyDistanceChart = (() => {
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    return days.map((label, i) => {
      const dayStart = new Date(startOfWeek);
      dayStart.setDate(startOfWeek.getDate() + i);
      const dayEnd = new Date(dayStart);
      dayEnd.setDate(dayStart.getDate() + 1);
      const distance = sessions
        .filter(s => {
          const d = new Date(s.session_date);
          return d >= dayStart && d < dayEnd;
        })
        .reduce((sum, s) => sum + s.total_distance_meters, 0);
      return { label, distance, startDate: dayStart.toISOString(), endDate: dayEnd.toISOString() };
    });
  })();

  // Compute chart data: weekly distances for the month (Week 1, 2, 3, 4/5)
  const monthlyDistanceChart = (() => {
    const weeksInMonth: { label: string; start: Date; end: Date }[] = [];
    const d = new Date(startOfMonth);
    let weekNum = 1;
    while (d.getMonth() === now.getMonth()) {
      const weekStart = new Date(d);
      const weekEnd = new Date(d);
      weekEnd.setDate(d.getDate() + 7);
      if (weekEnd.getMonth() !== now.getMonth()) {
        weekEnd.setDate(1);
        weekEnd.setMonth(now.getMonth() + 1);
      }
      weeksInMonth.push({ label: `W${weekNum}`, start: weekStart, end: weekEnd });
      d.setDate(d.getDate() + 7);
      weekNum++;
    }
    return weeksInMonth.map(({ label, start, end }) => {
      const distance = sessions
        .filter(s => {
          const sd = new Date(s.session_date);
          return sd >= start && sd < end;
        })
        .reduce((sum, s) => sum + s.total_distance_meters, 0);
      return { label, distance, startDate: start.toISOString(), endDate: end.toISOString() };
    });
  })();

  // Compute chart data: monthly distances for the year (Jan–current month)
  const yearlyDistanceChart = (() => {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const currentMonth = now.getMonth();
    return months.slice(0, currentMonth + 1).map((label, i) => {
      const monthStart = new Date(now.getFullYear(), i, 1);
      const monthEnd = new Date(now.getFullYear(), i + 1, 1);
      const distance = sessions
        .filter(s => {
          const sd = new Date(s.session_date);
          return sd >= monthStart && sd < monthEnd;
        })
        .reduce((sum, s) => sum + s.total_distance_meters, 0);
      return { label, distance, startDate: monthStart.toISOString(), endDate: monthEnd.toISOString() };
    });
  })();

  // Derive display name from email (use part before @)
  const displayName = email ? email.split('@')[0] : 'Swimmer';

  // Handle bar click on distance charts — filter feed to that period
  const handleBarClick = useCallback((point: DistanceChartPoint) => {
    if (point.startDate && point.endDate && point.distance > 0) {
      setDateFilter({ start: point.startDate, end: point.endDate, label: point.label });
    }
  }, []);

  // Filter sessions by date range if a bar was clicked
  const filteredSessions = dateFilter
    ? sessions.filter(s => {
        const d = new Date(s.session_date);
        return d >= new Date(dateFilter.start) && d < new Date(dateFilter.end);
      })
    : sessions;

  return (
    <div className="dashboard">
      <aside className="dashboard__sidebar">
        <Sidebar
          profilePictureUrl={profilePictureUrl}
          displayName={displayName}
          memberSince={memberSince}
          totalSessions={totalSessions}
          totalDistanceMeters={totalDistance}
          totalTimeSeconds={totalTime}
          swimsThisWeek={swimsThisWeek}
          swimsThisMonth={swimsThisMonth}
          swimsYTD={swimsYTD}
          sessionsPerWeek={sessionsPerWeek}
          distanceThisWeekMeters={distanceThisWeek}
          distanceThisMonthMeters={distanceThisMonth}
          distanceYTDMeters={distanceYTD}
          weeklyDistanceChart={weeklyDistanceChart}
          monthlyDistanceChart={monthlyDistanceChart}
          yearlyDistanceChart={yearlyDistanceChart}
          onBarClick={handleBarClick}
          weeklyGoalMeters={weeklyGoalM}
          monthlyGoalMeters={monthlyGoalM}
          yearlyGoalMeters={yearlyGoalM}
        />
      </aside>
      <section className="dashboard__feed">
        <div className="dashboard__feed-header">
          <h1>Activity Feed</h1>
          <Link to="/activity/new" className="dashboard__new-activity-btn">
            + New Activity
          </Link>
        </div>
        {dateFilter && (
          <div className="dashboard__filter-bar">
            <span className="dashboard__filter-label">Showing: {dateFilter.label}</span>
            <button
              className="dashboard__filter-clear"
              onClick={() => setDateFilter(null)}
            >
              ✕ Clear
            </button>
          </div>
        )}
        <ActivityFeed
          sessions={filteredSessions}
          loading={loading}
          error={error}
          onRetry={fetchSessions}
        />
      </section>
    </div>
  );
}
