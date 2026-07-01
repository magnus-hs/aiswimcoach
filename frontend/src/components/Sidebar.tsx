import { useState } from 'react';
import { DistanceChart, DistanceChartPoint } from './DistanceChart';
import './Sidebar.css';

export interface SidebarProps {
  profilePictureUrl: string | null;
  displayName: string;
  memberSince: string;
  totalSessions: number;
  totalDistanceMeters: number;
  totalTimeSeconds: number;
  swimsThisWeek: number;
  swimsThisMonth: number;
  swimsYTD: number;
  sessionsPerWeek: number[];
  distanceThisWeekMeters: number;
  distanceThisMonthMeters: number;
  distanceYTDMeters: number;
  weeklyDistanceChart: DistanceChartPoint[];
  monthlyDistanceChart: DistanceChartPoint[];
  yearlyDistanceChart: DistanceChartPoint[];
  onBarClick?: (point: DistanceChartPoint) => void;
  /** Optional weekly distance goal in metres (from the swimmer's Goals). */
  weeklyGoalMeters?: number | null;
}

/**
 * Sidebar component displaying user profile summary and aggregate stats.
 *
 * Shows profile picture (or placeholder avatar), display name, member-since date,
 * and key stats (total sessions, total distance, streak) with large bold typography.
 *
 * Validates: Requirements 3.2, 3.3, 3.4
 */
export function Sidebar({
  profilePictureUrl,
  displayName,
  memberSince,
  totalSessions,
  totalDistanceMeters,
  totalTimeSeconds,
  swimsThisWeek,
  swimsThisMonth,
  swimsYTD,
  distanceThisWeekMeters,
  distanceThisMonthMeters,
  distanceYTDMeters,
  weeklyDistanceChart,
  monthlyDistanceChart,
  yearlyDistanceChart,
  onBarClick,
  weeklyGoalMeters,
}: SidebarProps) {
  const formattedDistance = formatDistance(totalDistanceMeters);
  const formattedTime = formatDuration(totalTimeSeconds);
  const [mobileExpanded, setMobileExpanded] = useState(false);

  // Weekly distance goal progress (if a goal is set).
  const weeklyGoalPct =
    weeklyGoalMeters && weeklyGoalMeters > 0
      ? Math.round((distanceThisWeekMeters / weeklyGoalMeters) * 100)
      : null;
  const weeklyGoalRemaining =
    weeklyGoalMeters && weeklyGoalMeters > 0
      ? Math.max(0, weeklyGoalMeters - distanceThisWeekMeters)
      : 0;

  return (
    <aside className="sidebar" aria-label="Profile summary">
      <div className="sidebar__profile">
        <div className="sidebar__avatar">
          {profilePictureUrl ? (
            <img
              src={profilePictureUrl}
              alt={`${displayName}'s profile picture`}
              className="sidebar__avatar-image"
            />
          ) : (
            <span className="sidebar__avatar-placeholder" aria-hidden="true">
              👤
            </span>
          )}
        </div>
        <h2 className="sidebar__name">{displayName}</h2>
        <p className="sidebar__member-since">Member since {memberSince}</p>
      </div>

      <button
        className="sidebar__mobile-toggle"
        onClick={() => setMobileExpanded(!mobileExpanded)}
        aria-expanded={mobileExpanded}
      >
        <span className={`sidebar__mobile-arrow ${mobileExpanded ? 'sidebar__mobile-arrow--open' : ''}`}>▶</span>
        {mobileExpanded ? 'Hide stats' : 'Show stats & charts'}
      </button>

      <div className={`sidebar__collapsible ${mobileExpanded ? 'sidebar__collapsible--open' : ''}`}>

      <div className="sidebar__chart-section">
        <h3 className="sidebar__section-title">Distance This Week</h3>
        <span className="sidebar__section-value">{formatDistance(distanceThisWeekMeters)}</span>
        <DistanceChart data={weeklyDistanceChart} height={90} onBarClick={onBarClick} />
      </div>

      <div className="sidebar__chart-section">
        <h3 className="sidebar__section-title">Distance This Month</h3>
        <span className="sidebar__section-value">{formatDistance(distanceThisMonthMeters)}</span>
        <DistanceChart data={monthlyDistanceChart} height={90} onBarClick={onBarClick} />
      </div>

      <div className="sidebar__chart-section">
        <h3 className="sidebar__section-title">Distance Year to Date</h3>
        <span className="sidebar__section-value">{formatDistance(distanceYTDMeters)}</span>
        <DistanceChart data={yearlyDistanceChart} height={90} onBarClick={onBarClick} />
      </div>

      {weeklyGoalPct != null && (
        <p className="sidebar__goal-indicator">
          {weeklyGoalPct >= 100
            ? `🎯 Weekly goal smashed — ${weeklyGoalPct}% of ${formatDistance(weeklyGoalMeters!)}`
            : `🎯 ${weeklyGoalPct}% of your ${formatDistance(weeklyGoalMeters!)} weekly goal — ${formatDistance(weeklyGoalRemaining)} to go`}
        </p>
      )}

      <div className="sidebar__stats" role="list" aria-label="Training statistics">
        <div className="sidebar__stat" role="listitem">
          <span className="sidebar__stat-value">{totalSessions}</span>
          <span className="sidebar__stat-label">Sessions</span>
        </div>
        <div className="sidebar__stat" role="listitem">
          <span className="sidebar__stat-value">{swimsThisWeek}</span>
          <span className="sidebar__stat-label">Swims / Week</span>
        </div>
        <div className="sidebar__stat" role="listitem">
          <span className="sidebar__stat-value">{swimsThisMonth}</span>
          <span className="sidebar__stat-label">Swims / Month</span>
        </div>
        <div className="sidebar__stat" role="listitem">
          <span className="sidebar__stat-value">{swimsYTD}</span>
          <span className="sidebar__stat-label">Swims Year to Date</span>
        </div>
      </div>

      <div className="sidebar__totals">
        <div className="sidebar__total">
          <span className="sidebar__total-value">{formattedDistance}</span>
          <span className="sidebar__total-label">Total Distance</span>
        </div>
        <div className="sidebar__total">
          <span className="sidebar__total-value">{formattedTime}</span>
          <span className="sidebar__total-label">Total Time</span>
        </div>
      </div>
      </div>
    </aside>
  );
}

/**
 * Format distance in meters to a human-readable string.
 * Displays in km if >= 1000m, otherwise in meters.
 */
function formatDistance(meters: number): string {
  if (meters >= 1000) {
    const km = meters / 1000;
    return `${km % 1 === 0 ? km.toFixed(0) : km.toFixed(1)} km`;
  }
  return `${meters} m`;
}

/**
 * Format total time in seconds to a human-readable string.
 * Shows hours and minutes (e.g., "12h 45m" or "45m").
 */
function formatDuration(seconds: number): string {
  if (seconds <= 0) return '0m';
  const hours = Math.floor(seconds / 3600);
  const mins = Math.round((seconds % 3600) / 60);
  if (hours > 0) {
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
  }
  return `${mins}m`;
}
