import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CalendarView } from './CalendarView';
import { SessionSummary } from '../api/sessionService';

describe('CalendarView', () => {
  // Use current month for test data to ensure tests work reliably
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, '0');

  const mockSessions: SessionSummary[] = [
    {
      session_id: '1',
      session_date: `${year}-${month}-15T10:00:00Z`,
      pool_length_meters: 25,
      total_distance_meters: 2000,
      total_time_seconds: 1800,
      stroke_type: 'freestyle',
      average_pace_per_100m: 90,
      swolf_score: 45,
      stroke_rate: 30,
    },
    {
      session_id: '2',
      session_date: `${year}-${month}-15T14:00:00Z`,
      pool_length_meters: 25,
      total_distance_meters: 1500,
      total_time_seconds: 1200,
      stroke_type: 'backstroke',
      average_pace_per_100m: 80,
      swolf_score: 42,
      stroke_rate: 28,
    },
    {
      session_id: '3',
      session_date: `${year}-${month}-20T10:00:00Z`,
      pool_length_meters: 50,
      total_distance_meters: 3000,
      total_time_seconds: 2400,
      stroke_type: 'freestyle',
      average_pace_per_100m: 80,
      swolf_score: 40,
      stroke_rate: 32,
    },
  ];

  it('renders calendar with month and year', () => {
    const onDateSelect = vi.fn();
    render(<CalendarView sessions={[]} onDateSelect={onDateSelect} />);

    // Should display a month name and year
    const header = screen.getByRole('heading');
    expect(header.textContent).toMatch(/\w+ \d{4}/);
  });

  it('renders previous and next month navigation buttons', () => {
    const onDateSelect = vi.fn();
    render(<CalendarView sessions={[]} onDateSelect={onDateSelect} />);

    const prevButton = screen.getByLabelText('Previous month');
    const nextButton = screen.getByLabelText('Next month');

    expect(prevButton).toBeInTheDocument();
    expect(nextButton).toBeInTheDocument();
  });

  it('displays weekday headers', () => {
    const onDateSelect = vi.fn();
    render(<CalendarView sessions={[]} onDateSelect={onDateSelect} />);

    expect(screen.getByText('Sun')).toBeInTheDocument();
    expect(screen.getByText('Mon')).toBeInTheDocument();
    expect(screen.getByText('Tue')).toBeInTheDocument();
    expect(screen.getByText('Wed')).toBeInTheDocument();
    expect(screen.getByText('Thu')).toBeInTheDocument();
    expect(screen.getByText('Fri')).toBeInTheDocument();
    expect(screen.getByText('Sat')).toBeInTheDocument();
  });

  it('displays total distance for dates with sessions', () => {
    const onDateSelect = vi.fn();
    render(<CalendarView sessions={mockSessions} onDateSelect={onDateSelect} />);

    // Should show 3500m for Jan 15 (2000 + 1500)
    expect(screen.getByText('3500m')).toBeInTheDocument();

    // Should show 3000m for Jan 20
    expect(screen.getByText('3000m')).toBeInTheDocument();
  });

  it('calls onDateSelect when a date is clicked', () => {
    const onDateSelect = vi.fn();
    render(<CalendarView sessions={mockSessions} onDateSelect={onDateSelect} />);

    // Find and click a date cell (e.g., day 15)
    const dateCell = screen.getByText('15').closest('[role="button"]');
    expect(dateCell).toBeInTheDocument();

    if (dateCell) {
      fireEvent.click(dateCell);

      // Should call onDateSelect with the date string
      expect(onDateSelect).toHaveBeenCalledTimes(1);
      expect(onDateSelect.mock.calls[0][0]).toMatch(/\d{4}-\d{2}-15/);
    }
  });

  it('highlights selected date', () => {
    const onDateSelect = vi.fn();
    const selectedDate = `${year}-${month}-15`;
    render(
      <CalendarView
        sessions={mockSessions}
        onDateSelect={onDateSelect}
        selectedDate={selectedDate}
      />
    );

    // Find the cell with day 15
    const dateCell = screen.getByText('15').closest('[role="button"]');
    expect(dateCell).toHaveClass('calendar-view__cell--selected');
  });

  it('marks dates with sessions using visual indicator', () => {
    const onDateSelect = vi.fn();
    const { container } = render(
      <CalendarView sessions={mockSessions} onDateSelect={onDateSelect} />
    );

    // Check for session indicator elements
    const indicators = container.querySelectorAll('.calendar-view__session-indicator');
    expect(indicators.length).toBeGreaterThan(0);
  });

  it('navigates to previous month when prev button clicked', () => {
    const onDateSelect = vi.fn();
    render(<CalendarView sessions={[]} onDateSelect={onDateSelect} />);

    const currentMonth = screen.getByRole('heading').textContent;
    const prevButton = screen.getByLabelText('Previous month');

    fireEvent.click(prevButton);

    const newMonth = screen.getByRole('heading').textContent;
    expect(newMonth).not.toBe(currentMonth);
  });

  it('navigates to next month when next button clicked', () => {
    const onDateSelect = vi.fn();
    render(<CalendarView sessions={[]} onDateSelect={onDateSelect} />);

    const currentMonth = screen.getByRole('heading').textContent;
    const nextButton = screen.getByLabelText('Next month');

    fireEvent.click(nextButton);

    const newMonth = screen.getByRole('heading').textContent;
    expect(newMonth).not.toBe(currentMonth);
  });

  it('handles keyboard navigation with Enter key', () => {
    const onDateSelect = vi.fn();
    render(<CalendarView sessions={mockSessions} onDateSelect={onDateSelect} />);

    const dateCell = screen.getByText('15').closest('[role="button"]');
    expect(dateCell).toBeInTheDocument();

    if (dateCell) {
      fireEvent.keyDown(dateCell, { key: 'Enter', code: 'Enter' });

      expect(onDateSelect).toHaveBeenCalledTimes(1);
      expect(onDateSelect.mock.calls[0][0]).toMatch(/\d{4}-\d{2}-15/);
    }
  });

  it('handles keyboard navigation with Space key', () => {
    const onDateSelect = vi.fn();
    render(<CalendarView sessions={mockSessions} onDateSelect={onDateSelect} />);

    const dateCell = screen.getByText('20').closest('[role="button"]');
    expect(dateCell).toBeInTheDocument();

    if (dateCell) {
      fireEvent.keyDown(dateCell, { key: ' ', code: 'Space' });

      expect(onDateSelect).toHaveBeenCalledTimes(1);
      expect(onDateSelect.mock.calls[0][0]).toMatch(/\d{4}-\d{2}-20/);
    }
  });

  it('displays empty calendar when no sessions provided', () => {
    const onDateSelect = vi.fn();
    const { container } = render(<CalendarView sessions={[]} onDateSelect={onDateSelect} />);

    // Should not have any session indicators
    const indicators = container.querySelectorAll('.calendar-view__session-indicator');
    expect(indicators.length).toBe(0);

    // Should not have any distance labels
    const distances = container.querySelectorAll('.calendar-view__distance');
    expect(distances.length).toBe(0);
  });
});
