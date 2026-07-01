import { useState, useEffect, useCallback, useRef } from 'react';
import {
  searchUsers,
  sendFriendRequest,
  getPendingRequests,
  acceptRequest,
  declineRequest,
  getFriends,
  removeFriend,
  getActivityVisibility,
  updateActivityVisibility,
  UserSearchResult,
  FriendRequest,
  Friend,
} from '../api/friendsService';
import './FriendsPage.css';

export function FriendsPage() {
  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<UserSearchResult[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState('');
  const [searchExecuted, setSearchExecuted] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Pending requests state
  const [pendingRequests, setPendingRequests] = useState<FriendRequest[]>([]);
  const [pendingLoading, setPendingLoading] = useState(true);
  const [pendingError, setPendingError] = useState('');

  // Friends state
  const [friends, setFriends] = useState<Friend[]>([]);
  const [friendsLoading, setFriendsLoading] = useState(true);
  const [friendsError, setFriendsError] = useState('');

  // Privacy state
  const [visibilityLoading, setVisibilityLoading] = useState(true);
  const [activityVisible, setActivityVisible] = useState(false);
  const [visibilityError, setVisibilityError] = useState('');
  const [visibilitySuccess, setVisibilitySuccess] = useState('');

  // Remove confirmation
  const [confirmRemoveId, setConfirmRemoveId] = useState<string | null>(null);

  // Action errors
  const [actionError, setActionError] = useState('');

  // Load pending requests
  const loadPendingRequests = useCallback(async () => {
    setPendingLoading(true);
    setPendingError('');
    try {
      const data = await getPendingRequests();
      setPendingRequests(data);
    } catch (err: unknown) {
      setPendingError(err instanceof Error ? err.message : 'Failed to load pending requests.');
    } finally {
      setPendingLoading(false);
    }
  }, []);

  // Load friends
  const loadFriends = useCallback(async () => {
    setFriendsLoading(true);
    setFriendsError('');
    try {
      const data = await getFriends();
      setFriends(data);
    } catch (err: unknown) {
      setFriendsError(err instanceof Error ? err.message : 'Failed to load friends.');
    } finally {
      setFriendsLoading(false);
    }
  }, []);

  // Load visibility
  const loadVisibility = useCallback(async () => {
    setVisibilityLoading(true);
    setVisibilityError('');
    try {
      const visible = await getActivityVisibility();
      setActivityVisible(visible);
    } catch (err: unknown) {
      setVisibilityError(err instanceof Error ? err.message : 'Failed to load visibility setting.');
    } finally {
      setVisibilityLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPendingRequests();
    loadFriends();
    loadVisibility();
  }, [loadPendingRequests, loadFriends, loadVisibility]);

  // Debounced search
  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    if (searchQuery.trim().length < 2) {
      setSearchResults([]);
      setSearchExecuted(false);
      setSearchError('');
      return;
    }

    debounceRef.current = setTimeout(async () => {
      setSearchLoading(true);
      setSearchError('');
      setSearchExecuted(true);
      try {
        const results = await searchUsers(searchQuery.trim());
        setSearchResults(results);
      } catch (err: unknown) {
        setSearchError(err instanceof Error ? err.message : 'Search failed. Please try again.');
        setSearchResults([]);
      } finally {
        setSearchLoading(false);
      }
    }, 300);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [searchQuery]);

  // Handle send friend request
  const handleSendRequest = async (userId: string) => {
    setActionError('');
    try {
      await sendFriendRequest(userId);
      // Update search results to reflect sent status
      setSearchResults((prev) =>
        prev.map((r) =>
          r.user_id === userId ? { ...r, relationship_status: 'pending_sent' as const } : r
        )
      );
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Failed to send friend request.');
    }
  };

  // Handle accept request
  const handleAccept = async (requestId: string) => {
    setActionError('');
    try {
      await acceptRequest(requestId);
      setPendingRequests((prev) => prev.filter((r) => r.request_id !== requestId));
      // Refresh friends list
      loadFriends();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Failed to accept request.');
    }
  };

  // Handle decline request
  const handleDecline = async (requestId: string) => {
    setActionError('');
    try {
      await declineRequest(requestId);
      setPendingRequests((prev) => prev.filter((r) => r.request_id !== requestId));
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Failed to decline request.');
    }
  };

  // Handle remove friend
  const handleRemove = async (friendUserId: string) => {
    setActionError('');
    try {
      await removeFriend(friendUserId);
      setFriends((prev) => prev.filter((f) => f.user_id !== friendUserId));
      setConfirmRemoveId(null);
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Failed to remove friend.');
      setConfirmRemoveId(null);
    }
  };

  // Handle visibility toggle
  const handleVisibilityToggle = async () => {
    const previous = activityVisible;
    const newValue = !activityVisible;
    setActivityVisible(newValue);
    setVisibilityError('');
    setVisibilitySuccess('');
    try {
      await updateActivityVisibility(newValue);
      setVisibilitySuccess(newValue ? 'Activities are now shared with friends.' : 'Activities are now private.');
      setTimeout(() => setVisibilitySuccess(''), 3000);
    } catch (err: unknown) {
      setActivityVisible(previous);
      setVisibilityError(err instanceof Error ? err.message : 'Failed to update visibility.');
    }
  };

  const retrySearch = () => {
    setSearchError('');
    const query = searchQuery.trim();
    if (query.length >= 2) {
      setSearchLoading(true);
      setSearchExecuted(true);
      searchUsers(query)
        .then((results) => setSearchResults(results))
        .catch((err) => setSearchError(err instanceof Error ? err.message : 'Search failed.'))
        .finally(() => setSearchLoading(false));
    }
  };

  return (
    <div className="friends-page">
      <h1 className="friends-page__heading">Friends</h1>
      <p className="friends-page__intro">
        Connect with fellow swimmers, manage your friends, and control activity sharing.
      </p>

      {actionError && (
        <div className="friends-page__error-banner" role="alert">
          {actionError}
          <button className="friends-page__dismiss" onClick={() => setActionError('')}>×</button>
        </div>
      )}

      {/* Search Section */}
      <section className="friends-page__card">
        <h2>Find Swimmers</h2>
        <input
          type="text"
          className="friends-page__search-input"
          placeholder="Search by name or email"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          aria-label="Search by name or email"
        />

        {searchLoading && (
          <div className="friends-page__loading">Searching...</div>
        )}

        {searchError && (
          <div className="friends-page__error-banner" role="alert">
            {searchError}
            <button className="friends-page__retry-btn" onClick={retrySearch}>Retry</button>
          </div>
        )}

        {!searchLoading && !searchError && searchExecuted && searchResults.length === 0 && (
          <p className="friends-page__empty">No users found</p>
        )}

        {searchResults.length > 0 && (
          <ul className="friends-page__search-results">
            {searchResults.map((user) => (
              <li key={user.user_id} className="friends-page__search-item">
                <div className="friends-page__user-row">
                  <span className="friends-page__avatar">
                    {user.profile_picture_url ? (
                      <img src={user.profile_picture_url} alt="" className="friends-page__avatar-img" />
                    ) : (
                      <svg viewBox="0 0 48 24" xmlns="http://www.w3.org/2000/svg" className="friends-page__avatar-logo">
                        <ellipse cx="14" cy="12" rx="9" ry="7" fill="none" stroke="var(--color-primary)" strokeWidth="2.5"/>
                        <ellipse cx="34" cy="12" rx="9" ry="7" fill="none" stroke="var(--color-primary)" strokeWidth="2.5"/>
                        <path d="M23 10 C24 8, 24 8, 25 10" stroke="var(--color-primary)" strokeWidth="2" fill="none" strokeLinecap="round"/>
                      </svg>
                    )}
                  </span>
                  <div className="friends-page__user-info">
                    <span className="friends-page__user-name">{user.display_name}</span>
                    <span className="friends-page__user-email">{user.email_prefix}</span>
                  </div>
                </div>
                {user.relationship_status === 'none' && (
                  <button
                    className="friends-page__btn friends-page__btn--primary"
                    onClick={() => handleSendRequest(user.user_id)}
                  >
                    Add Friend
                  </button>
                )}
                {user.relationship_status === 'pending_sent' && (
                  <button className="friends-page__btn friends-page__btn--disabled" disabled>
                    Request Sent
                  </button>
                )}
                {user.relationship_status === 'pending_received' && (
                  <button className="friends-page__btn friends-page__btn--disabled" disabled>
                    Pending
                  </button>
                )}
                {user.relationship_status === 'friends' && (
                  <button className="friends-page__btn friends-page__btn--disabled" disabled>
                    Already Friends
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Pending Requests Section */}
      <section className="friends-page__card">
        <h2>Pending Requests</h2>
        {pendingLoading && <div className="friends-page__loading">Loading...</div>}
        {pendingError && (
          <div className="friends-page__error-banner" role="alert">
            {pendingError}
            <button className="friends-page__retry-btn" onClick={loadPendingRequests}>Retry</button>
          </div>
        )}
        {!pendingLoading && !pendingError && pendingRequests.length === 0 && (
          <p className="friends-page__empty">No pending requests</p>
        )}
        {pendingRequests.length > 0 && (
          <ul className="friends-page__list">
            {pendingRequests.map((req) => (
              <li key={req.request_id} className="friends-page__list-item">
                <div className="friends-page__user-info">
                  <span className="friends-page__user-name">{req.from_display_name}</span>
                  <span className="friends-page__user-meta">
                    {new Date(req.created_at).toLocaleDateString()}
                  </span>
                </div>
                <div className="friends-page__actions">
                  <button
                    className="friends-page__btn friends-page__btn--primary"
                    onClick={() => handleAccept(req.request_id)}
                  >
                    Accept
                  </button>
                  <button
                    className="friends-page__btn friends-page__btn--secondary"
                    onClick={() => handleDecline(req.request_id)}
                  >
                    Decline
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* My Friends Section */}
      <section className="friends-page__card">
        <h2>My Friends</h2>
        {friendsLoading && <div className="friends-page__loading">Loading...</div>}
        {friendsError && (
          <div className="friends-page__error-banner" role="alert">
            {friendsError}
            <button className="friends-page__retry-btn" onClick={loadFriends}>Retry</button>
          </div>
        )}
        {!friendsLoading && !friendsError && friends.length === 0 && (
          <p className="friends-page__empty">No friends yet. Search for swimmers to connect!</p>
        )}
        {friends.length > 0 && (
          <ul className="friends-page__list">
            {friends.map((friend) => (
              <li key={friend.user_id} className="friends-page__list-item">
                <div className="friends-page__user-info">
                  <span className="friends-page__user-name">{friend.display_name}</span>
                  <span className="friends-page__user-meta">
                    Friends since {new Date(friend.since).toLocaleDateString()}
                  </span>
                </div>
                {confirmRemoveId === friend.user_id ? (
                  <div className="friends-page__confirm">
                    <span className="friends-page__confirm-text">Remove?</span>
                    <button
                      className="friends-page__btn friends-page__btn--danger"
                      onClick={() => handleRemove(friend.user_id)}
                    >
                      Yes
                    </button>
                    <button
                      className="friends-page__btn friends-page__btn--secondary"
                      onClick={() => setConfirmRemoveId(null)}
                    >
                      No
                    </button>
                  </div>
                ) : (
                  <button
                    className="friends-page__btn friends-page__btn--secondary"
                    onClick={() => setConfirmRemoveId(friend.user_id)}
                  >
                    Remove
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Activity Sharing Section */}
      <section className="friends-page__card">
        <h2>Activity Sharing</h2>
        <p className="friends-page__hint">
          Control whether your swim activities are visible to your friends.
        </p>
        {visibilityLoading ? (
          <div className="friends-page__loading">Loading...</div>
        ) : (
          <div className="friends-page__toggle-row">
            <label className="friends-page__toggle-label" htmlFor="visibility-toggle">
              Share my activities with friends
            </label>
            <button
              id="visibility-toggle"
              type="button"
              role="switch"
              aria-checked={activityVisible}
              className={`friends-page__toggle ${activityVisible ? 'friends-page__toggle--active' : ''}`}
              onClick={handleVisibilityToggle}
            >
              <span className="friends-page__toggle-knob" />
            </button>
          </div>
        )}
        {visibilityError && (
          <p className="friends-page__error" role="alert">{visibilityError}</p>
        )}
        {visibilitySuccess && (
          <p className="friends-page__success">{visibilitySuccess}</p>
        )}
      </section>

      {/* Invite Section */}
      <section className="friends-page__card">
        <h2>Invite a Friend</h2>
        <p className="friends-page__hint">
          Know someone who'd enjoy AI Swim Coach? Share a link and invite them to join.
        </p>
        <div className="friends-page__invite-row">
          <input
            type="text"
            className="friends-page__search-input"
            readOnly
            value="https://main.d3qbayea55l8tl.amplifyapp.com/register"
            onClick={(e) => (e.target as HTMLInputElement).select()}
          />
          <button
            className="friends-page__btn friends-page__btn--primary"
            onClick={() => {
              navigator.clipboard.writeText('https://main.d3qbayea55l8tl.amplifyapp.com/register');
              setActionError('');
              setVisibilitySuccess('Invite link copied!');
              setTimeout(() => setVisibilitySuccess(''), 3000);
            }}
          >
            Copy Link
          </button>
        </div>
        {typeof navigator.share === 'function' && (
          <button
            className="friends-page__btn friends-page__btn--secondary"
            style={{ marginTop: 'var(--space-3)' }}
            onClick={() => {
              navigator.share({
                title: 'Join AI Swim Coach',
                text: 'Track your swims, get AI coaching, and compare with friends!',
                url: 'https://main.d3qbayea55l8tl.amplifyapp.com/register',
              }).catch(() => {});
            }}
          >
            Share via…
          </button>
        )}
      </section>
    </div>
  );
}
