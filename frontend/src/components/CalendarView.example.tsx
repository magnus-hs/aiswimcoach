/**
 * Example usage of CalendarView component
 *
 * This file demonstrates how to integrate the CalendarView component
 * with session data from the API.
 */

import { useState, useEffect } from 'react';
import { CalendarView } from './CalendarView';
import { getUserSessions, SessionSummary } from '../api/sessionService';

/**
 * Example component showing CalendarView integration
 */
export function HistoryPageExample() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [selectedDate, setSelectedDate] = useState<string | undefined>(undefined);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch user sessions on mount
    async function fetchSessions() {
      try {
        const data = await getUserSessions();
        setSessions(data);
      } catch (error) {
        console.error('Failed to load sessions:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchSessions();
  }, []);

  // Handle date selection
  const handleDateSelect = (date: string) => {
    setSelectedDate(date);
    console.log('Selected date:', date);

    // Filter sessions for the selected date
    const sessionsForDate = sessions.filter(
      (session) => session.session_date.split('T')[0] === date
    );

    console.log('Sessions for date:', sessionsForDate);
  };

  if (loading) {
    return <div>Loading sessions...</div>;
  }

  return (
    <div style={{ padding: '2rem' }}>
      <h1>Session History</h1>

      {/* Calendar showing all sessions */}
      <CalendarView
        sessions={sessions}
        onDateSelect={handleDateSelect}
        selectedDate={selectedDate}
      />

      {/* Display sessions for selected date */}
      {selectedDate && (
        <div style={{ marginTop: '2rem' }}>
          <h2>Sessions on {selectedDate}</h2>
          {sessions
            .filter((session) => session.session_date.split('T')[0] === selectedDate)
            .map((session) => (
              <div
                key={session.session_id}
                style={{
                  padding: '1rem',
                  border: '1px solid #e2e8f0',
                  borderRadius: '0.5rem',
                  marginBottom: '1rem',
                }}
              >
                <p>
                  <strong>Distance:</strong> {session.total_distance_meters}m
                </p>
                <p>
                  <strong>Stroke:</strong> {session.stroke_type}
                </p>
                <p>
                  <strong>Time:</strong> {Math.floor(session.total_time_seconds / 60)}m{' '}
                  {session.total_time_seconds % 60}s
                </p>
                <p>
                  <strong>Pace:</strong> {session.average_pace_per_100m}s/100m
                </p>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
