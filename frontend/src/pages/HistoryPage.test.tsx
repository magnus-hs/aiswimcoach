import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import userEvent from '@testing-library/user-event';
import { HistoryPage } from './HistoryPage';
import * as sessionService from '../api/sessionService';
import { ApiError } from '../types';

// Mock react-router-dom's useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock the sessionService module
vi.mock('../api/sessionService', () => ({
  getUserSessions: vi.fn(),
}));

describe('HistoryPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockClear();
  });

  const renderHistoryPage = () => {
    return render(
      <BrowserRouter>
        <HistoryPage />
      </BrowserRouter>
    );
  };

  it('renders page title', () => {
    vi.mocked(sessionService.getUserSessions).mockResolvedValue([]);
    renderHistoryPage();

    expect(screen.getByRole('heading', { name: /training history/i })).toBeInTheDocument();
  });

  it('displays loading state while fetching sessions', async () => {
    // Create a promise that we control
    let resolveSessions: (value: any) => void;
    const sessionsPromise = new Promise((resolve) => {
      resolveSessions = resolve;
    });
    
    vi.mocked(sessionService.getUserSessions).mockReturnValue(sessionsPromise);
    renderHistoryPage();

    // Check loading state
    expect(screen.getByText(/loading your training history/i)).toBeInTheDocument();

    // Resolve the promise
    resolveSessions!([]);

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText(/loading your training history/i)).not.toBeInTheDocument();
    });
  });

  it('displays empty state message when no sessions exist', async () => {
    vi.mocked(sessionService.getUserSessions).mockResolvedValue([]);
    renderHistoryPage();

    await waitFor(() => {
      expect(screen.getByText(/no swim sessions found\. upload your first fit file to get started!/i)).toBeInTheDocument();
    });

    // Should have a link to upload page
    const uploadLink = screen.getByRole('link', { name: /go to upload/i });
    expect(uploadLink).toHaveAttribute('href', '/upload');
  });

  it('displays session cards when sessions exist', async () => {
    const mockSessions = [
      {
        session_id: 'session-1',
        session_date: '2024-01-15T10:00:00Z',
        pool_length_meters: 25,
        total_distance_meters: 2000,
        total_time_seconds: 1800,
        stroke_type: 'Freestyle',
        average_pace_per_100m: 90,
        swolf_score: 45,
        stroke_rate: 30,
      },
      {
        session_id: 'session-2',
        session_date: '2024-01-16T10:00:00Z',
        pool_length_meters: 25,
        total_distance_meters: 1500,
        total_time_seconds: 1500,
        stroke_type: 'Freestyle',
        average_pace_per_100m: 100,
        swolf_score: 50,
        stroke_rate: 28,
      },
    ];

    vi.mocked(sessionService.getUserSessions).mockResolvedValue(mockSessions);
    renderHistoryPage();

    await waitFor(() => {
      expect(screen.getByText('2000m')).toBeInTheDocument();
      expect(screen.getByText('1500m')).toBeInTheDocument();
    });

    // Should not show empty state
    expect(screen.queryByText(/no swim sessions found/i)).not.toBeInTheDocument();
    
    // Should show both session cards with Freestyle
    const freestyleElements = screen.getAllByText('Freestyle');
    expect(freestyleElements).toHaveLength(2);
  });

  it('displays session card when one session exists', async () => {
    const mockSessions = [
      {
        session_id: 'session-1',
        session_date: '2024-01-15T10:00:00Z',
        pool_length_meters: 25,
        total_distance_meters: 2000,
        total_time_seconds: 1800,
        stroke_type: 'Freestyle',
        average_pace_per_100m: 90,
        swolf_score: 45,
        stroke_rate: 30,
      },
    ];

    vi.mocked(sessionService.getUserSessions).mockResolvedValue(mockSessions);
    renderHistoryPage();

    await waitFor(() => {
      expect(screen.getByText('2000m')).toBeInTheDocument();
    });
    
    expect(screen.getByText('Freestyle')).toBeInTheDocument();
  });

  it('displays error message when session fetch fails with ApiError', async () => {
    const errorMessage = 'Unable to load session history. Please try again.';
    vi.mocked(sessionService.getUserSessions).mockRejectedValue(
      new ApiError(500, errorMessage)
    );

    renderHistoryPage();

    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });

    // Should not show loading or empty state
    expect(screen.queryByText(/loading your training history/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/no swim sessions found/i)).not.toBeInTheDocument();
  });

  it('displays error message when session fetch fails with network error', async () => {
    const errorMessage = 'Network connection failed';
    vi.mocked(sessionService.getUserSessions).mockRejectedValue(
      new Error(errorMessage)
    );

    renderHistoryPage();

    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });
  });

  it('displays generic error message for unknown error types', async () => {
    vi.mocked(sessionService.getUserSessions).mockRejectedValue('Unknown error');

    renderHistoryPage();

    await waitFor(() => {
      expect(screen.getByText(/failed to load session history/i)).toBeInTheDocument();
    });
  });

  it('calls getUserSessions on mount', async () => {
    vi.mocked(sessionService.getUserSessions).mockResolvedValue([]);
    renderHistoryPage();

    await waitFor(() => {
      expect(sessionService.getUserSessions).toHaveBeenCalledTimes(1);
    });
  });

  /**
   * Test for Requirement 19.1-19.2: Session summaries should be clickable and navigate to detail view
   */
  it('navigates to session detail page when session card is clicked', async () => {
    const user = userEvent.setup();
    const mockSessions = [
      {
        session_id: 'test-session-123',
        session_date: '2024-01-15T10:00:00Z',
        pool_length_meters: 25,
        total_distance_meters: 2000,
        total_time_seconds: 1800,
        stroke_type: 'Freestyle',
        average_pace_per_100m: 90,
        swolf_score: 45,
        stroke_rate: 30,
      },
    ];

    vi.mocked(sessionService.getUserSessions).mockResolvedValue(mockSessions);
    renderHistoryPage();

    // Wait for session card to appear
    await waitFor(() => {
      expect(screen.getByText('2000m')).toBeInTheDocument();
    });

    // Find and click the session card
    const sessionCard = screen.getByText('2000m').closest('.session-summary-card');
    expect(sessionCard).toBeInTheDocument();
    
    await user.click(sessionCard!);

    // Verify navigation was called with correct session ID
    expect(mockNavigate).toHaveBeenCalledWith('/session/test-session-123');
    expect(mockNavigate).toHaveBeenCalledTimes(1);
  });

  it('navigates to correct session when multiple sessions are displayed', async () => {
    const user = userEvent.setup();
    const mockSessions = [
      {
        session_id: 'session-1',
        session_date: '2024-01-15T10:00:00Z',
        pool_length_meters: 25,
        total_distance_meters: 2000,
        total_time_seconds: 1800,
        stroke_type: 'Freestyle',
        average_pace_per_100m: 90,
        swolf_score: 45,
        stroke_rate: 30,
      },
      {
        session_id: 'session-2',
        session_date: '2024-01-16T10:00:00Z',
        pool_length_meters: 25,
        total_distance_meters: 1500,
        total_time_seconds: 1500,
        stroke_type: 'Backstroke',
        average_pace_per_100m: 100,
        swolf_score: 50,
        stroke_rate: 28,
      },
    ];

    vi.mocked(sessionService.getUserSessions).mockResolvedValue(mockSessions);
    renderHistoryPage();

    // Wait for both session cards to appear
    await waitFor(() => {
      expect(screen.getByText('2000m')).toBeInTheDocument();
      expect(screen.getByText('1500m')).toBeInTheDocument();
    });

    // Click the second session (Backstroke)
    const backstrokeCard = screen.getByText('Backstroke').closest('.session-summary-card');
    expect(backstrokeCard).toBeInTheDocument();
    
    await user.click(backstrokeCard!);

    // Verify navigation was called with session-2
    expect(mockNavigate).toHaveBeenCalledWith('/session/session-2');
    expect(mockNavigate).toHaveBeenCalledTimes(1);
  });
});
