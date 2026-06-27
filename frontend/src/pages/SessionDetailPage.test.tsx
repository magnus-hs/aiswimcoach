import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { SessionDetailPage } from './SessionDetailPage';
import * as sessionService from '../api/sessionService';
import { ApiError } from '../types';

// Mock the session service
vi.mock('../api/sessionService');

// Helper function to render with router
function renderWithRouter(sessionId: string) {
  return render(
    <MemoryRouter initialEntries={[`/session/${sessionId}`]}>
      <Routes>
        <Route path="/session/:id" element={<SessionDetailPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('SessionDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock localStorage for auth token
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: vi.fn(() => 'mock-token'),
        setItem: vi.fn(),
        removeItem: vi.fn(),
      },
      writable: true,
    });
  });

  it('renders loading state initially', () => {
    vi.mocked(sessionService.getSessionById).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    renderWithRouter('test-session-id');

    // Check for loading indicator (can be text or any element indicating loading)
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('displays session details when loaded successfully', async () => {
    const mockSessionDetail: sessionService.SessionDetail = {
      session: {
        start_time: '2024-01-15T10:00:00Z',
        pool_length_m: 25,
        stroke: 'freestyle',
        total_distance_m: 2000,
        total_time_seconds: 1800,
        num_lengths: 80,
      },
      splits: [
        { length_number: 1, time_seconds: 22.5, stroke: 'freestyle', strokes: 12 },
        { length_number: 2, time_seconds: 23.0, stroke: 'freestyle', strokes: 13 },
      ],
      metrics: { pace: 90.0, swolf: 37, stroke_rate: 32 },
      coaching: {
        tips: ['Tip 1', 'Tip 2', 'Tip 3'],
        drill: 'Test drill',
      },
      session_id: 'test-session-id',
    };

    vi.mocked(sessionService.getSessionById).mockResolvedValue(mockSessionDetail);

    renderWithRouter('test-session-id');

    await waitFor(() => {
      expect(screen.getByText('Session Summary')).toBeInTheDocument();
    });

    // Check for key elements
    expect(screen.getByText('2000m')).toBeInTheDocument();
    expect(screen.getByText('Length Splits')).toBeInTheDocument();
    expect(screen.getByText('Your Coaching Tips')).toBeInTheDocument();
    expect(screen.getByText(/Back to History/)).toBeInTheDocument();
  });

  it('displays HR zones when available', async () => {
    const mockSessionDetail: sessionService.SessionDetail = {
      session: {
        start_time: '2024-01-15T10:00:00Z',
        pool_length_m: 25,
        stroke: 'freestyle',
        total_distance_m: 2000,
        total_time_seconds: 1800,
        num_lengths: 80,
      },
      splits: [],
      metrics: { pace: 90.0, swolf: 37, stroke_rate: 32 },
      coaching: {
        tips: ['Tip 1', 'Tip 2', 'Tip 3'],
        drill: 'Test drill',
      },
      hr_zones: {
        zone_1_seconds: 300,
        zone_2_seconds: 600,
        zone_3_seconds: 500,
        zone_4_seconds: 300,
        zone_5_seconds: 100,
        zone_1_percent: 16.7,
        zone_2_percent: 33.3,
        zone_3_percent: 27.8,
        zone_4_percent: 16.7,
        zone_5_percent: 5.5,
        max_hr: 190,
        zone_boundaries: {
          1: [95, 114],
          2: [114, 133],
          3: [133, 152],
          4: [152, 171],
          5: [171, 190],
        },
      },
      session_id: 'test-session-id',
    };

    vi.mocked(sessionService.getSessionById).mockResolvedValue(mockSessionDetail);

    renderWithRouter('test-session-id');

    await waitFor(() => {
      expect(screen.getByText('Heart Rate Zones')).toBeInTheDocument();
    });
  });

  it('displays ability assessment when available', async () => {
    const mockSessionDetail: sessionService.SessionDetail = {
      session: {
        start_time: '2024-01-15T10:00:00Z',
        pool_length_m: 25,
        stroke: 'freestyle',
        total_distance_m: 2000,
        total_time_seconds: 1800,
        num_lengths: 80,
      },
      splits: [],
      metrics: { pace: 90.0, swolf: 37, stroke_rate: 32 },
      coaching: {
        tips: ['Tip 1', 'Tip 2', 'Tip 3'],
        drill: 'Test drill',
      },
      ability_assessment: {
        percentile_estimate: 'Top 30%',
        local_ranking: 'Competitive at local level',
        national_ranking: 'Regional competitor',
        competitive_analysis: 'Strong performance for age group',
      },
      session_id: 'test-session-id',
    };

    vi.mocked(sessionService.getSessionById).mockResolvedValue(mockSessionDetail);

    renderWithRouter('test-session-id');

    await waitFor(() => {
      expect(screen.getByText('Competitive Ability Assessment')).toBeInTheDocument();
    });

    expect(screen.getByText('Top 30%')).toBeInTheDocument();
  });

  it('displays training plan when available', async () => {
    const mockSessionDetail: sessionService.SessionDetail = {
      session: {
        start_time: '2024-01-15T10:00:00Z',
        pool_length_m: 25,
        stroke: 'freestyle',
        total_distance_m: 2000,
        total_time_seconds: 1800,
        num_lengths: 80,
      },
      splits: [],
      metrics: { pace: 90.0, swolf: 37, stroke_rate: 32 },
      coaching: {
        tips: ['Tip 1', 'Tip 2', 'Tip 3'],
        drill: 'Test drill',
      },
      training_plan: {
        session_title: 'Speed Work Session',
        warm_up: ['400m easy'],
        main_set: ['8x100m fast'],
        cool_down: ['200m easy'],
        total_distance: 1400,
        focus_notes: 'Focus on technique',
      },
      session_id: 'test-session-id',
    };

    vi.mocked(sessionService.getSessionById).mockResolvedValue(mockSessionDetail);

    renderWithRouter('test-session-id');

    await waitFor(() => {
      expect(screen.getByText('Speed Work Session')).toBeInTheDocument();
    });

    expect(screen.getByText('400m easy')).toBeInTheDocument();
    expect(screen.getByText('8x100m fast')).toBeInTheDocument();
  });

  it('displays error message when session fetch fails', async () => {
    const apiError = new ApiError(404, 'Session not found');
    vi.mocked(sessionService.getSessionById).mockRejectedValue(apiError);

    renderWithRouter('nonexistent-session-id');

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });

    expect(screen.getByText('Session not found')).toBeInTheDocument();
    // Check for the link by searching for text that contains "Back to History"
    expect(screen.getByText(/Back to History/)).toBeInTheDocument();
  });

  it('handles authentication errors', async () => {
    const apiError = new ApiError(401, 'Authentication required. Please log in again.');
    vi.mocked(sessionService.getSessionById).mockRejectedValue(apiError);

    renderWithRouter('test-session-id');

    await waitFor(() => {
      expect(screen.getByText('Authentication required. Please log in again.')).toBeInTheDocument();
    });
  });

  it('has back to history link', async () => {
    const mockSessionDetail: sessionService.SessionDetail = {
      session: {
        start_time: '2024-01-15T10:00:00Z',
        pool_length_m: 25,
        stroke: 'freestyle',
        total_distance_m: 2000,
        total_time_seconds: 1800,
        num_lengths: 80,
      },
      splits: [],
      metrics: { pace: 90.0, swolf: 37, stroke_rate: 32 },
      coaching: {
        tips: ['Tip 1', 'Tip 2', 'Tip 3'],
        drill: 'Test drill',
      },
      session_id: 'test-session-id',
    };

    vi.mocked(sessionService.getSessionById).mockResolvedValue(mockSessionDetail);

    renderWithRouter('test-session-id');

    await waitFor(() => {
      const backLink = screen.getByText(/Back to History/);
      expect(backLink).toBeInTheDocument();
      expect(backLink).toHaveAttribute('href', '/history');
    });
  });
});
