import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getUserSessions, SessionSummary } from '../api/sessionService';
import { ApiError } from '../types';

/**
 * HistoryPage - Container component for session history view.
 * 
 * Responsibilities:
 * - Fetch user's session history on mount
 * - Manage state for calendar, graph, and session list
 * - Handle empty state with user-friendly message
 * - Render clickable session summaries that navigate to detail view
 * 
 * Requirements: 16.1-16.10, 19.1-19.2
 */
export function HistoryPage() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const navigate = useNavigate();

  useEffect(() => {
    const fetchSessions = async () => {
      setLoading(true);
      setError('');
      
      try {
        const data = await getUserSessions();
        setSessions(data);
      } catch (err: unknown) {
        if (err instanceof ApiError) {
          setError(err.serverMessage);
        } else if (err instanceof Error) {
          setError(err.message);
        } else {
          setError('Failed to load session history.');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchSessions();
  }, []);

  /**
   * Navigate to session detail page.
   * Validates: Requirements 19.1-19.2
   */
  const handleSessionClick = (sessionId: string) => {
    navigate(`/session/${sessionId}`);
  };

  /**
   * Format session date for display.
   */
  const formatDate = (isoDate: string): string => {
    const date = new Date(isoDate);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  /**
   * Format time duration from seconds.
   */
  const formatTime = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  return (
    <div className="history-page">
      <div className="history-page__header">
        <h1 className="history-page__title">Training History</h1>
      </div>

      {loading && (
        <div className="history-page__loading">
          <p>Loading your training history...</p>
        </div>
      )}

      {error && (
        <div className="history-page__error">
          <p>{error}</p>
        </div>
      )}

      {!loading && !error && sessions.length === 0 && (
        <div className="history-page__empty">
          <p>No swim sessions found. Upload your first FIT file to get started!</p>
          <a href="/upload" className="history-page__upload-link">
            Go to Upload
          </a>
        </div>
      )}

      {!loading && !error && sessions.length > 0 && (
        <div className="history-page__content">
          <div className="history-page__session-list">
            {sessions.map((session) => (
              <div
                key={session.session_id}
                onClick={() => handleSessionClick(session.session_id)}
                className="session-summary-card"
                style={{
                  padding: '1.5rem',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  backgroundColor: '#ffffff',
                  marginBottom: '1rem',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = '#f9fafb';
                  e.currentTarget.style.borderColor = '#3b82f6';
                  e.currentTarget.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.1)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = '#ffffff';
                  e.currentTarget.style.borderColor = '#e5e7eb';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <h3 style={{ margin: '0 0 0.5rem 0', color: '#1f2937', fontSize: '1.125rem' }}>
                      {formatDate(session.session_date)}
                    </h3>
                    <p style={{ margin: '0.25rem 0', color: '#6b7280' }}>
                      {session.stroke_type}
                    </p>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <p style={{ margin: '0.25rem 0', fontSize: '1.5rem', fontWeight: 'bold', color: '#1f2937' }}>
                      {session.total_distance_meters}m
                    </p>
                    <p style={{ margin: '0.25rem 0', color: '#6b7280' }}>
                      {formatTime(session.total_time_seconds)}
                    </p>
                  </div>
                </div>
                
                <div style={{ marginTop: '1rem', display: 'flex', gap: '2rem', fontSize: '0.875rem', color: '#6b7280' }}>
                  <div>
                    <span style={{ fontWeight: '500' }}>Pace:</span> {session.average_pace_per_100m.toFixed(1)}s/100m
                  </div>
                  <div>
                    <span style={{ fontWeight: '500' }}>SWOLF:</span> {session.swolf_score}
                  </div>
                  <div>
                    <span style={{ fontWeight: '500' }}>Stroke Rate:</span> {session.stroke_rate.toFixed(1)} spm
                  </div>
                </div>
              </div>
            ))}
          </div>
          
          <div className="history-page__upcoming-features" style={{ marginTop: '2rem', padding: '1rem', backgroundColor: '#f3f4f6', borderRadius: '8px' }}>
            <p style={{ margin: '0', color: '#6b7280', fontSize: '0.875rem' }}>
              📅 Calendar view and progress graphs coming in tasks 19.2 and 19.3
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
