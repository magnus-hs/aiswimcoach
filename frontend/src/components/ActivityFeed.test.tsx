import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ActivityFeed, ActivityFeedProps } from './ActivityFeed';
import { SessionSummary } from '../api/sessionService';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

function makeSummary(overrides: Partial<SessionSummary> = {}): SessionSummary {
  return {
    session_id: 'session-1',
    session_date: '2024-06-15T10:00:00Z',
    pool_length_meters: 25,
    total_distance_meters: 2000,
    total_time_seconds: 1800,
    stroke_type: 'freestyle',
    average_pace_per_100m: 90,
    swolf_score: 42,
    stroke_rate: 30,
    ...overrides,
  };
}

function renderFeed(props: Partial<ActivityFeedProps> = {}) {
  const defaultProps: ActivityFeedProps = {
    sessions: [],
    loading: false,
    ...props,
  };
  return render(
    <MemoryRouter>
      <ActivityFeed {...defaultProps} />
    </MemoryRouter>
  );
}

describe('ActivityFeed', () => {
  describe('loading state', () => {
    it('renders 3 skeleton placeholders when loading', () => {
      const { container } = renderFeed({ loading: true });
      const skeletons = container.querySelectorAll('.activity-feed__skeleton');
      expect(skeletons).toHaveLength(3);
    });

    it('sets aria-busy on loading container', () => {
      renderFeed({ loading: true });
      const feed = screen.getByLabelText('Loading sessions');
      expect(feed).toHaveAttribute('aria-busy', 'true');
    });
  });

  describe('empty state', () => {
    it('renders empty message when sessions array is empty', () => {
      renderFeed({ sessions: [] });
      expect(screen.getByText(/No sessions yet/)).toBeInTheDocument();
    });

    it('renders CTA link to /activity/new', () => {
      renderFeed({ sessions: [] });
      const link = screen.getByRole('link', { name: /Upload First Session/ });
      expect(link).toHaveAttribute('href', '/activity/new');
    });
  });

  describe('error state', () => {
    it('renders ErrorBanner with error message', () => {
      renderFeed({ error: 'Network error occurred' });
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText('Network error occurred')).toBeInTheDocument();
    });

    it('renders retry button when onRetry is provided', () => {
      const onRetry = vi.fn();
      renderFeed({ error: 'Server error', onRetry });
      const retryBtn = screen.getByRole('button', { name: /Try Again/ });
      expect(retryBtn).toBeInTheDocument();
    });

    it('does not render retry button when onRetry is absent', () => {
      renderFeed({ error: 'Server error' });
      expect(screen.queryByRole('button', { name: /Try Again/ })).not.toBeInTheDocument();
    });
  });

  describe('sessions rendering', () => {
    it('renders ActivityCards for each session', () => {
      const sessions = [
        makeSummary({ session_id: 's1', session_date: '2024-06-15T10:00:00Z' }),
        makeSummary({ session_id: 's2', session_date: '2024-06-14T10:00:00Z' }),
      ];
      renderFeed({ sessions });
      const cards = screen.getAllByRole('button');
      expect(cards).toHaveLength(2);
    });

    it('renders cards in descending date order', () => {
      const sessions = [
        makeSummary({ session_id: 's-old', session_date: '2024-01-01T10:00:00Z', stroke_type: 'backstroke' }),
        makeSummary({ session_id: 's-new', session_date: '2024-06-15T10:00:00Z', stroke_type: 'freestyle' }),
        makeSummary({ session_id: 's-mid', session_date: '2024-03-10T10:00:00Z', stroke_type: 'butterfly' }),
      ];
      renderFeed({ sessions });
      const cards = screen.getAllByRole('button');
      // First card should be the newest (freestyle - Jun 15)
      expect(cards[0]).toHaveAttribute('aria-label', expect.stringContaining('freestyle'));
      // Last card should be the oldest (backstroke - Jan 1)
      expect(cards[2]).toHaveAttribute('aria-label', expect.stringContaining('backstroke'));
    });
  });
});
