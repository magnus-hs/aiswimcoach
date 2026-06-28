import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { TrainingPlansPage } from './TrainingPlansPage';
import * as uploadApi from '../api/upload';
import * as sessionService from '../api/sessionService';

vi.mock('../api/upload');
vi.mock('../api/sessionService');

function renderPage() {
  return render(
    <MemoryRouter>
      <TrainingPlansPage />
    </MemoryRouter>,
  );
}

describe('TrainingPlansPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(sessionService.getUserSessions).mockResolvedValue([]);
  });

  it('renders the page heading', () => {
    renderPage();
    expect(screen.getByRole('heading', { level: 1, name: /training plans/i })).toBeInTheDocument();
  });

  it('renders the TrainingGoalForm', () => {
    renderPage();
    expect(screen.getByRole('heading', { name: /set your training goal/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/target event/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/target time/i)).toBeInTheDocument();
  });

  it('does not render TrainingPlanResult initially', () => {
    renderPage();
    expect(screen.queryByLabelText(/training plan/i)).not.toBeInTheDocument();
  });

  it('displays generated plan after form submission', async () => {
    const user = userEvent.setup();
    const mockPlan = {
      session_title: 'Speed Endurance Session',
      warm_up: ['400m easy swim'],
      main_set: ['8x100m at threshold pace'],
      cool_down: ['200m easy'],
      total_distance: 1800,
      focus_notes: 'Focus on consistent splits.',
    };

    vi.mocked(uploadApi.generateTrainingPlan).mockResolvedValue(mockPlan);

    renderPage();

    // Fill target time and submit
    const timeInput = screen.getByLabelText(/target time/i);
    await user.clear(timeInput);
    await user.type(timeInput, '1:05');

    const submitButton = screen.getByRole('button', { name: /generate training plan/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Speed Endurance Session')).toBeInTheDocument();
    });

    expect(screen.getByText('400m easy swim')).toBeInTheDocument();
    expect(screen.getByText('8x100m at threshold pace')).toBeInTheDocument();
    expect(screen.getByText('200m easy')).toBeInTheDocument();
    expect(screen.getByText('1800m total')).toBeInTheDocument();
  });

  it('displays error message when plan generation fails', async () => {
    const user = userEvent.setup();
    vi.mocked(uploadApi.generateTrainingPlan).mockRejectedValue(
      new Error('AI coach is temporarily unavailable'),
    );

    renderPage();

    const timeInput = screen.getByLabelText(/target time/i);
    await user.clear(timeInput);
    await user.type(timeInput, '1:00');

    const submitButton = screen.getByRole('button', { name: /generate training plan/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(
        'AI coach is temporarily unavailable',
      );
    });
  });

  it('loads metrics from latest session', async () => {
    const mockSessions = [
      {
        session_id: 's1',
        session_date: '2024-01-15',
        pool_length_meters: 25,
        total_distance_meters: 2000,
        total_time_seconds: 1800,
        stroke_type: 'freestyle',
        average_pace_per_100m: 95,
        swolf_score: 35,
        stroke_rate: 28,
      },
    ];

    vi.mocked(sessionService.getUserSessions).mockResolvedValue(mockSessions);

    const user = userEvent.setup();
    renderPage();

    // Wait for sessions to load
    await waitFor(() => {
      expect(sessionService.getUserSessions).toHaveBeenCalled();
    });

    vi.mocked(uploadApi.generateTrainingPlan).mockResolvedValue({
      session_title: 'Test',
      warm_up: ['warm'],
      main_set: ['main'],
      cool_down: ['cool'],
      total_distance: 2000,
      focus_notes: 'notes',
    });

    const timeInput = screen.getByLabelText(/target time/i);
    await user.clear(timeInput);
    await user.type(timeInput, '0:55');

    const submitButton = screen.getByRole('button', { name: /generate training plan/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(uploadApi.generateTrainingPlan).toHaveBeenCalledWith(
        { pace: 95, swolf: 35, stroke_rate: 28 },
        expect.objectContaining({ target_time: '0:55' }),
      );
    });
  });
});
