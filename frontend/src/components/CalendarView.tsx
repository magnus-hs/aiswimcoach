import './CalendarView.css';
import { SessionSummary } from '../api/sessionService';
import { useState } from 'react';

export interface CalendarViewProps {
  /** List of session summaries to display on the calendar */
  sessions: SessionSummary[];
  /** Callback when a date is selected */
  onDateSelect: (date: string) => void;
  /** Currently selected date (ISO 8601 format) */
  selectedDate?: string;
}

/**
 * Monthly calendar component displaying swim sessions.
 *
 * Features:
 * - Monthly calendar grid (7 columns x 5-6 rows)
 * - Previous/next month navigation
 * - Marks dates with sessions using colored dots
 * - Displays total distance per date
 * - Highlights current date
 * - Handles date selection
 *
 * Validates: Requirements 17.1-17.8
 */
export function CalendarView({ sessions, onDateSelect, selectedDate }: CalendarViewProps) {
  const [currentDate, setCurrentDate] = useState(new Date());

  // Get calendar data for current month
  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  // First day of the month
  const firstDayOfMonth = new Date(year, month, 1);
  const firstDayWeekday = firstDayOfMonth.getDay(); // 0 = Sunday, 6 = Saturday

  // Last day of the month
  const lastDayOfMonth = new Date(year, month + 1, 0);
  const daysInMonth = lastDayOfMonth.getDate();

  // Calculate total distance for each date
  const distanceByDate = new Map<string, number>();
  const sessionsHaveData = new Map<string, boolean>();

  sessions.forEach((session) => {
    // Extract date portion (YYYY-MM-DD) from session_date
    const dateStr = session.session_date.split('T')[0];
    const currentDistance = distanceByDate.get(dateStr) || 0;
    distanceByDate.set(dateStr, currentDistance + session.total_distance_meters);
    sessionsHaveData.set(dateStr, true);
  });

  // Get today's date string for highlighting
  const today = new Date();
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

  // Navigate to previous month
  const handlePreviousMonth = () => {
    setCurrentDate(new Date(year, month - 1, 1));
  };

  // Navigate to next month
  const handleNextMonth = () => {
    setCurrentDate(new Date(year, month + 1, 1));
  };

  // Handle date click
  const handleDateClick = (day: number) => {
    const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    onDateSelect(dateStr);
  };

  // Generate calendar cells
  const calendarCells: JSX.Element[] = [];

  // Add empty cells for days before the first day of the month
  for (let i = 0; i < firstDayWeekday; i++) {
    calendarCells.push(
      <div key={`empty-${i}`} className="calendar-view__cell calendar-view__cell--empty" />
    );
  }

  // Add cells for each day of the month
  for (let day = 1; day <= daysInMonth; day++) {
    const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    const hasSession = sessionsHaveData.has(dateStr);
    const distance = distanceByDate.get(dateStr);
    const isToday = dateStr === todayStr;
    const isSelected = dateStr === selectedDate;

    calendarCells.push(
      <div
        key={day}
        className={`calendar-view__cell ${isToday ? 'calendar-view__cell--today' : ''} ${isSelected ? 'calendar-view__cell--selected' : ''} ${hasSession ? 'calendar-view__cell--has-session' : ''}`}
        onClick={() => handleDateClick(day)}
        role="button"
        tabIndex={0}
        aria-label={`${dateStr}${hasSession ? `, ${distance}m swum` : ''}`}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleDateClick(day);
          }
        }}
      >
        <div className="calendar-view__day-number">{day}</div>
        {hasSession && (
          <>
            <div className="calendar-view__session-indicator" aria-hidden="true" />
            <div className="calendar-view__distance">{distance}m</div>
          </>
        )}
      </div>
    );
  }

  // Month names
  const monthNames = [
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
  ];

  // Weekday names
  const weekdayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  return (
    <section className="calendar-view" aria-label="Session calendar">
      {/* Calendar header with navigation */}
      <div className="calendar-view__header">
        <button
          className="calendar-view__nav-button"
          onClick={handlePreviousMonth}
          aria-label="Previous month"
        >
          ←
        </button>
        <h2 className="calendar-view__title">
          {monthNames[month]} {year}
        </h2>
        <button
          className="calendar-view__nav-button"
          onClick={handleNextMonth}
          aria-label="Next month"
        >
          →
        </button>
      </div>

      {/* Weekday headers */}
      <div className="calendar-view__weekdays">
        {weekdayNames.map((name) => (
          <div key={name} className="calendar-view__weekday">
            {name}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div className="calendar-view__grid">{calendarCells}</div>
    </section>
  );
}
