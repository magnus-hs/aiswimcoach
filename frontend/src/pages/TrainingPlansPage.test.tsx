import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { TrainingPlansPage } from './TrainingPlansPage';
import * as planService from '../api/planService';

vi.mock('../api/planService');

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
    vi.mocked(planService.getStructuredPlans).mockResolvedValue([]);
  });

  it('renders the page heading', () => {
    renderPage();
    expect(screen.getByRole('heading', { level: 1, name: /training plans/i })).toBeInTheDocument();
  });

  it('renders create new plan link', () => {
    renderPage();
    expect(screen.getByRole('link', { name: /create new plan/i })).toBeInTheDocument();
  });

  it('renders personal bests link', () => {
    renderPage();
    expect(screen.getByRole('link', { name: /personal bests/i })).toBeInTheDocument();
  });

  it('shows loading state initially', () => {
    vi.mocked(planService.getStructuredPlans).mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByText('Loading plans…')).toBeInTheDocument();
  });

  it('shows empty state when no plans exist', async () => {
    vi.mocked(planService.getStructuredPlans).mockResolvedValue([]);
    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/no structured plans yet/i)).toBeInTheDocument();
    });
  });

  it('displays error message when plan loading fails', async () => {
    vi.mocked(planService.getStructuredPlans).mockRejectedValue(
      new Error('No authentication token found. Please log in.'),
    );

    renderPage();

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(
        'No authentication token found. Please log in.',
      );
    });
  });
});
