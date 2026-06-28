import './Sidebar.css';

export interface SidebarProps {
  profilePictureUrl: string | null;
  displayName: string;
  memberSince: string;
  totalSessions: number;
  totalDistanceMeters: number;
  currentStreakDays: number;
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
  currentStreakDays,
}: SidebarProps) {
  const formattedDistance = formatDistance(totalDistanceMeters);

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

      <div className="sidebar__stats" role="list" aria-label="Training statistics">
        <div className="sidebar__stat" role="listitem">
          <span className="sidebar__stat-value">{totalSessions}</span>
          <span className="sidebar__stat-label">Sessions</span>
        </div>
        <div className="sidebar__stat" role="listitem">
          <span className="sidebar__stat-value">{formattedDistance}</span>
          <span className="sidebar__stat-label">Total Distance</span>
        </div>
        <div className="sidebar__stat" role="listitem">
          <span className="sidebar__stat-value">{currentStreakDays}</span>
          <span className="sidebar__stat-label">Day Streak</span>
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
