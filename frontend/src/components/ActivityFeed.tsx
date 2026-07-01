import { useState, useEffect, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { SessionSummary } from '../api/sessionService';
import { getFriendsActivities, FriendActivity } from '../api/friendsService';
import { ActivityCard } from './ActivityCard';
import { ErrorBanner } from './ErrorBanner';
import './ActivityFeed.css';

const INITIAL_COUNT = 7;
const LOAD_MORE_STEP = 5;

export interface ActivityFeedProps {
  /** Session summaries to render as ActivityCards. */
  sessions: SessionSummary[];
  /** Whether session data is currently loading. */
  loading: boolean;
  /** Optional error message to display. */
  error?: string;
  /** Optional retry callback for recoverable errors. */
  onRetry?: () => void;
}

/**
 * Renders a list of ActivityCards in descending session date order.
 * Handles loading (skeleton cards), empty state (CTA), and error state (ErrorBanner + retry).
 * Includes tabs for "My Activities" and "Friends' Activities".
 *
 * Validates: Requirements 3.5, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 8.4, 8.5, 8.6, 12.1, 12.2, 12.4
 */
export function ActivityFeed({ sessions, loading, error, onRetry }: ActivityFeedProps) {
  const [visibleCount, setVisibleCount] = useState(INITIAL_COUNT);
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const [activeTab, setActiveTab] = useState<'my' | 'friends'>('my');

  // Friends' activities state
  const [friendsActivities, setFriendsActivities] = useState<FriendActivity[]>([]);
  const [friendsLoading, setFriendsLoading] = useState(false);
  const [friendsError, setFriendsError] = useState('');
  const [friendsFetched, setFriendsFetched] = useState(false);

  const loadFriendsActivities = useCallback(async () => {
    setFriendsLoading(true);
    setFriendsError('');
    try {
      const data = await getFriendsActivities();
      setFriendsActivities(data);
      setFriendsFetched(true);
    } catch (err: unknown) {
      setFriendsError(err instanceof Error ? err.message : 'Failed to load friends\' activities.');
    } finally {
      setFriendsLoading(false);
    }
  }, []);

  // Load friends activities when switching to that tab
  useEffect(() => {
    if (activeTab === 'friends' && !friendsFetched && !friendsLoading) {
      loadFriendsActivities();
    }
  }, [activeTab, friendsFetched, friendsLoading, loadFriendsActivities]);

  // Sort sessions by date descending (API should already be sorted, but ensure correctness)
  const sorted = [...sessions].sort((a, b) => {
    return new Date(b.session_date).getTime() - new Date(a.session_date).getTime();
  });
  const hasMore = visibleCount < sorted.length;
  const visible = sorted.slice(0, visibleCount);

  // Reveal more activities as the sentinel scrolls into view.
  useEffect(() => {
    if (!hasMore) return;
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          setVisibleCount((c) => Math.min(c + LOAD_MORE_STEP, sorted.length));
        }
      },
      { rootMargin: '200px' },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [hasMore, sorted.length, visibleCount]);

  // Sort friends activities by date descending
  const sortedFriendsActivities = [...friendsActivities].sort((a, b) => {
    return new Date(b.session_date).getTime() - new Date(a.session_date).getTime();
  });

  const renderMyActivities = () => {
    // Error state
    if (error) {
      return (
        <div className="activity-feed activity-feed--error">
          <ErrorBanner message={error} onRetry={onRetry} />
        </div>
      );
    }

    // Loading state — 3 skeleton placeholder cards
    if (loading) {
      return (
        <div className="activity-feed activity-feed--loading" aria-busy="true" aria-label="Loading sessions">
          {[0, 1, 2].map((i) => (
            <div key={i} className="activity-feed__skeleton" aria-hidden="true">
              <div className="activity-feed__skeleton-header" />
              <div className="activity-feed__skeleton-body" />
              <div className="activity-feed__skeleton-footer" />
            </div>
          ))}
        </div>
      );
    }

    // Empty state — CTA to upload first session
    if (sessions.length === 0) {
      return (
        <div className="activity-feed activity-feed--empty">
          <p className="activity-feed__empty-message">No sessions yet. Upload your first swim to get started!</p>
          <Link to="/activity/new" className="activity-feed__cta">
            Upload First Session
          </Link>
        </div>
      );
    }

    return (
      <div className="activity-feed">
        {visible.map((session) => (
          <ActivityCard
            key={session.session_id}
            sessionId={session.session_id}
            sessionDate={session.session_date}
            strokeType={session.stroke_type}
            totalDistanceMeters={session.total_distance_meters}
            totalTimeSeconds={session.total_time_seconds}
            averagePacePer100m={session.average_pace_per_100m}
            swolfScore={session.swolf_score}
            strokeBreakdown={session.stroke_breakdown}
            splits={session.splits}
            poolLengthMeters={session.pool_length_meters}
            kudosCount={(session as unknown as Record<string, unknown>).kudos ? ((session as unknown as Record<string, unknown>).kudos as unknown[]).length : 0}
          />
        ))}

        {hasMore && (
          <div ref={sentinelRef} className="activity-feed__more">
            <button
              type="button"
              className="activity-feed__more-btn"
              onClick={() => setVisibleCount((c) => Math.min(c + LOAD_MORE_STEP, sorted.length))}
            >
              Show more activities
            </button>
          </div>
        )}
      </div>
    );
  };

  const renderFriendsActivities = () => {
    if (friendsLoading) {
      return (
        <div className="activity-feed activity-feed--loading" aria-busy="true" aria-label="Loading friends' activities">
          {[0, 1, 2].map((i) => (
            <div key={i} className="activity-feed__skeleton" aria-hidden="true">
              <div className="activity-feed__skeleton-header" />
              <div className="activity-feed__skeleton-body" />
              <div className="activity-feed__skeleton-footer" />
            </div>
          ))}
        </div>
      );
    }

    if (friendsError) {
      return (
        <div className="activity-feed activity-feed--error">
          <ErrorBanner
            message={friendsError}
            onRetry={() => {
              setFriendsFetched(false);
              loadFriendsActivities();
            }}
          />
        </div>
      );
    }

    if (sortedFriendsActivities.length === 0) {
      return (
        <div className="activity-feed activity-feed--empty">
          <p className="activity-feed__empty-message">
            No friends' activities to show. Connect with more swimmers or ask friends to share their activities.
          </p>
        </div>
      );
    }

    return (
      <div className="activity-feed">
        {sortedFriendsActivities.map((activity) => (
          <div key={activity.session_id} className="activity-feed__friend-card">
            <span className="activity-feed__friend-name">{activity.friend_display_name}</span>
            <ActivityCard
              sessionId={activity.session_id}
              sessionDate={activity.session_date}
              strokeType={activity.stroke_type}
              totalDistanceMeters={activity.total_distance_meters}
              totalTimeSeconds={activity.total_time_seconds}
              averagePacePer100m={activity.average_pace_per_100m}
              swolfScore={activity.swolf_score}
              kudosCount={(activity as unknown as Record<string, unknown>).kudos ? ((activity as unknown as Record<string, unknown>).kudos as unknown[]).length : 0}
            />
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="activity-feed-wrapper">
      <div className="activity-feed__tabs">
        <button
          type="button"
          className={`activity-feed__tab ${activeTab === 'my' ? 'activity-feed__tab--active' : ''}`}
          onClick={() => setActiveTab('my')}
        >
          My Activities
        </button>
        <button
          type="button"
          className={`activity-feed__tab ${activeTab === 'friends' ? 'activity-feed__tab--active' : ''}`}
          onClick={() => setActiveTab('friends')}
        >
          Friends' Activities
        </button>
      </div>

      {activeTab === 'my' ? renderMyActivities() : renderFriendsActivities()}
    </div>
  );
}
