import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import './NotificationBell.css';

interface Notification {
  type: 'kudos' | 'comment';
  from_display_name: string;
  session_id: string;
  text?: string;
  created_at: string;
}

function relativeTime(isoString: string): string {
  const diffMs = Date.now() - new Date(isoString).getTime();
  if (diffMs < 60_000) return 'just now';
  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

/**
 * Notification bell — sits in the top-right of the nav bar.
 * Shows a badge when there are unread notifications.
 * Click opens a dropdown with recent kudos/comment notifications.
 */
export function NotificationBell() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const bellRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const fetchNotifications = useCallback(async () => {
    const token = localStorage.getItem('auth_token');
    if (!token) return;
    setLoading(true);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_ENDPOINT}/notifications`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setNotifications(data.notifications ?? []);
      }
    } catch {
      // Non-critical
    } finally {
      setLoading(false);
    }
  }, []);

  // Poll on mount and every 60s
  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 60_000);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  // Close dropdown on click outside
  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (bellRef.current && !bellRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open]);

  const handleClear = async () => {
    const token = localStorage.getItem('auth_token');
    if (!token) return;
    try {
      await fetch(`${import.meta.env.VITE_API_ENDPOINT}/notifications`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      setNotifications([]);
    } catch {
      // Non-critical
    }
  };

  const handleNotificationClick = (sessionId: string) => {
    setOpen(false);
    navigate(`/activity/${sessionId}`);
  };

  const count = notifications.length;

  return (
    <div className="notification-bell" ref={bellRef}>
      <button
        type="button"
        className="notification-bell__btn"
        onClick={() => setOpen(!open)}
        aria-label={`Notifications${count > 0 ? ` (${count} new)` : ''}`}
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
        {count > 0 && <span className="notification-bell__badge">{count > 9 ? '9+' : count}</span>}
      </button>

      {open && (
        <div className="notification-bell__dropdown">
          <div className="notification-bell__header">
            <span className="notification-bell__title">Notifications</span>
            {count > 0 && (
              <button className="notification-bell__clear" onClick={handleClear}>Clear all</button>
            )}
          </div>
          {loading && count === 0 && (
            <div className="notification-bell__empty">Loading…</div>
          )}
          {!loading && count === 0 && (
            <div className="notification-bell__empty">No notifications</div>
          )}
          {count > 0 && (
            <ul className="notification-bell__list">
              {notifications.slice(0, 20).map((n, i) => (
                <li
                  key={i}
                  className="notification-bell__item"
                  onClick={() => handleNotificationClick(n.session_id)}
                >
                  <span className="notification-bell__icon">
                    {n.type === 'kudos' ? '👍' : '💬'}
                  </span>
                  <span className="notification-bell__text">
                    <strong>{n.from_display_name}</strong>
                    {n.type === 'kudos' ? ' gave kudos to your swim' : ` commented: "${(n.text || '').slice(0, 40)}${(n.text || '').length > 40 ? '…' : ''}"`}
                  </span>
                  <span className="notification-bell__time">{relativeTime(n.created_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
