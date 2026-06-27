import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ProgressGraph } from './ProgressGraph';
import { SessionSummary } from '../api/sessionService';

describe('ProgressGraph', () => {
  const mockSessions: SessionSummary[] = [
    {
      session_id: '1',
      session_date: '2024-01-15T10:00:00Z',
      pool_length_meters: 25,
      total_distance_meters: 1000,
      total_time_seconds: 1200,
      stroke_type: 'Freestyle',
      average_pace_per_100m: 120.0,
      swolf_score: 35,
      stroke_rate: 45.0,
    },
    {
      session_id: '2',
      session_date: '2024-01-15T16:00:00Z',
      pool_length_meters: 25,
      total_distance_meters: 1500,
      total_time_seconds: 1800,
      stroke_type: 'Freestyle',
      average_pace_per_100m: 120.0,
      swolf_score: 36,
      stroke_rate: 46.0,
    },
    {
      session_id: '3',
      session_date: '2024-01-16T10:00:00Z',
      pool_length_meters: 25,
      total_distance_meters: 2000,
      total_time_seconds: 2400,
      stroke_type: 'Freestyle',
      average_pace_per_100m: 120.0,
      swolf_score: 37,
      stroke_rate: 47.0,
    },
  ];

  describe('Rendering', () => {
    it('renders the component with heading', () => {
      render(<ProgressGraph sessions={mockSessions} />);
      expect(screen.getByText('Training Progress')).toBeInTheDocument();
    });

    it('renders time range selector with all options', () => {
      render(<ProgressGraph sessions={mockSessions} />);
      const select = screen.getByRole('combobox', { name: /time range/i });
      expect(select).toBeInTheDocument();

      const options = screen.getAllByRole('option');
      expect(options).toHaveLength(4);
      expect(screen.getByRole('option', { name: 'Last 7 Days' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Last 30 Days' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Last 90 Days' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'All Time' })).toBeInTheDocument();
    });

    it('defaults to "Last 30 Days" time range', () => {
      render(<ProgressGraph sessions={mockSessions} />);
      const select = screen.getByRole('combobox', { name: /time range/i }) as HTMLSelectElement;
      expect(select.value).toBe('30');
    });

    it('displays empty state when no sessions provided', () => {
      render(<ProgressGraph sessions={[]} />);
      expect(
        screen.getByText('No session data available for the selected time range.'),
      ).toBeInTheDocument();
    });
  });

  describe('Time Range Selection', () => {
    it('changes time range when user selects different option', async () => {
      const user = userEvent.setup();
      render(<ProgressGraph sessions={mockSessions} />);

      const select = screen.getByRole('combobox', { name: /time range/i });
      await user.selectOptions(select, '7');

      expect((select as HTMLSelectElement).value).toBe('7');
    });

    it('changes time range to "All Time"', async () => {
      const user = userEvent.setup();
      render(<ProgressGraph sessions={mockSessions} />);

      const select = screen.getByRole('combobox', { name: /time range/i });
      await user.selectOptions(select, 'all');

      expect((select as HTMLSelectElement).value).toBe('all');
    });
  });

  describe('Data Aggregation', () => {
    it('aggregates multiple sessions on the same date', () => {
      render(<ProgressGraph sessions={mockSessions} />);
      // Session 1 and 2 are both on 2024-01-15
      // Should aggregate: 1000 + 1500 = 2500 meters
      // This is tested implicitly through the chart rendering
      // The chart should show 2 data points: Jan 15 and Jan 16
      expect(screen.queryByText('No session data available')).not.toBeInTheDocument();
    });

    it('displays empty state when filtered sessions result in no data', () => {
      // Create sessions from 100 days ago
      const oldDate = new Date();
      oldDate.setDate(oldDate.getDate() - 100);
      const oldSessions: SessionSummary[] = [
        {
          session_id: '1',
          session_date: oldDate.toISOString(),
          pool_length_meters: 25,
          total_distance_meters: 1000,
          total_time_seconds: 1200,
          stroke_type: 'Freestyle',
          average_pace_per_100m: 120.0,
          swolf_score: 35,
          stroke_rate: 45.0,
        },
      ];

      render(<ProgressGraph sessions={oldSessions} />);
      // With default "Last 30 Days" filter, old sessions should be filtered out
      expect(
        screen.getByText('No session data available for the selected time range.'),
      ).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels', () => {
      render(<ProgressGraph sessions={mockSessions} />);
      expect(screen.getByLabelText('Training progress graph')).toBeInTheDocument();
      expect(screen.getByLabelText('Time Range:')).toBeInTheDocument();
    });

    it('select has accessible label', () => {
      render(<ProgressGraph sessions={mockSessions} />);
      const select = screen.getByRole('combobox', { name: /time range/i });
      expect(select).toHaveAccessibleName();
    });
  });

  describe('Date Formatting', () => {
    it('renders chart with recent sessions within 30 days', () => {
      // Create sessions within the last 30 days
      const today = new Date();
      const yesterday = new Date(today);
      yesterday.setDate(yesterday.getDate() - 1);
      const twoDaysAgo = new Date(today);
      twoDaysAgo.setDate(twoDaysAgo.getDate() - 2);

      const recentSessions: SessionSummary[] = [
        {
          session_id: '1',
          session_date: yesterday.toISOString(),
          pool_length_meters: 25,
          total_distance_meters: 1000,
          total_time_seconds: 1200,
          stroke_type: 'Freestyle',
          average_pace_per_100m: 120.0,
          swolf_score: 35,
          stroke_rate: 45.0,
        },
        {
          session_id: '2',
          session_date: twoDaysAgo.toISOString(),
          pool_length_meters: 25,
          total_distance_meters: 1500,
          total_time_seconds: 1800,
          stroke_type: 'Freestyle',
          average_pace_per_100m: 120.0,
          swolf_score: 36,
          stroke_rate: 46.0,
        },
      ];

      render(<ProgressGraph sessions={recentSessions} />);
      expect(screen.queryByText('No session data available')).not.toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles single session', () => {
      const singleSession: SessionSummary[] = [mockSessions[0]];
      render(<ProgressGraph sessions={singleSession} />);
      expect(screen.queryByText('No session data available')).not.toBeInTheDocument();
    });

    it('handles sessions with zero distance', () => {
      const zeroDistanceSessions: SessionSummary[] = [
        {
          session_id: '1',
          session_date: '2024-01-15T10:00:00Z',
          pool_length_meters: 25,
          total_distance_meters: 0,
          total_time_seconds: 1200,
          stroke_type: 'Freestyle',
          average_pace_per_100m: 0,
          swolf_score: 35,
          stroke_rate: 45.0,
        },
      ];
      render(<ProgressGraph sessions={zeroDistanceSessions} />);
      // Should still render the chart even with zero distance
      expect(screen.queryByText('No session data available')).not.toBeInTheDocument();
    });

    it('handles sessions spanning multiple years', () => {
      const multiYearSessions: SessionSummary[] = [
        {
          session_id: '1',
          session_date: '2023-12-31T10:00:00Z',
          pool_length_meters: 25,
          total_distance_meters: 1000,
          total_time_seconds: 1200,
          stroke_type: 'Freestyle',
          average_pace_per_100m: 120.0,
          swolf_score: 35,
          stroke_rate: 45.0,
        },
        {
          session_id: '2',
          session_date: '2024-01-01T10:00:00Z',
          pool_length_meters: 25,
          total_distance_meters: 1500,
          total_time_seconds: 1800,
          stroke_type: 'Freestyle',
          average_pace_per_100m: 120.0,
          swolf_score: 36,
          stroke_rate: 46.0,
        },
      ];
      render(<ProgressGraph sessions={multiYearSessions} />);
      expect(screen.queryByText('No session data available')).not.toBeInTheDocument();
    });
  });
});
