import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { ActivityCard, ActivityCardProps, formatTime, formatPace } from './ActivityCard';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const defaultProps: ActivityCardProps = {
  sessionId: 'session-123',
  sessionDate: '2024-06-15T10:30:00Z',
  strokeType: 'freestyle',
  totalDistanceMeters: 2000,
  totalTimeSeconds: 1800,
  averagePacePer100m: 90,
  swolfScore: 42,
};

function renderCard(props: Partial<ActivityCardProps> = {}) {
  return render(
    <MemoryRouter>
      <ActivityCard {...defaultProps} {...props} />
    </MemoryRouter>
  );
}

describe('ActivityCard', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
  });

  it('renders session date', () => {
    renderCard();
    // The date should be formatted (e.g., "Jun 15, 2024")
    expect(screen.getByText(/Jun/)).toBeInTheDocument();
    expect(screen.getByText(/2024/)).toBeInTheDocument();
  });

  it('renders stroke type', () => {
    renderCard();
    expect(screen.getByText('freestyle')).toBeInTheDocument();
  });

  it('renders total distance as primary metric', () => {
    renderCard();
    expect(screen.getByText('2000m')).toBeInTheDocument();
  });

  it('renders total time formatted as Xm Ys', () => {
    renderCard();
    expect(screen.getByText('30m 0s')).toBeInTheDocument();
  });

  it('renders pace formatted as M:SS /100m', () => {
    renderCard();
    expect(screen.getByText('1:30 /100m')).toBeInTheDocument();
  });

  it('renders SWOLF score', () => {
    renderCard();
    expect(screen.getByText('42')).toBeInTheDocument();
  });

  it('navigates to /activity/:id on click', async () => {
    const user = userEvent.setup();
    renderCard();
    const card = screen.getByRole('button');
    await user.click(card);
    expect(mockNavigate).toHaveBeenCalledWith('/activity/session-123');
  });

  it('navigates on Enter key press', async () => {
    const user = userEvent.setup();
    renderCard();
    const card = screen.getByRole('button');
    card.focus();
    await user.keyboard('{Enter}');
    expect(mockNavigate).toHaveBeenCalledWith('/activity/session-123');
  });

  it('navigates on Space key press', async () => {
    const user = userEvent.setup();
    renderCard();
    const card = screen.getByRole('button');
    card.focus();
    await user.keyboard(' ');
    expect(mockNavigate).toHaveBeenCalledWith('/activity/session-123');
  });

  it('has an accessible label', () => {
    renderCard();
    const card = screen.getByRole('button');
    expect(card).toHaveAttribute('aria-label');
    expect(card.getAttribute('aria-label')).toContain('freestyle');
    expect(card.getAttribute('aria-label')).toContain('2000 meters');
  });

  it('renders metric labels (Time, Pace, SWOLF)', () => {
    renderCard();
    expect(screen.getByText('Time')).toBeInTheDocument();
    expect(screen.getByText('Pace')).toBeInTheDocument();
    expect(screen.getByText('SWOLF')).toBeInTheDocument();
  });
});

describe('formatTime', () => {
  it('formats full minutes and seconds', () => {
    expect(formatTime(90)).toBe('1m 30s');
  });

  it('formats zero seconds', () => {
    expect(formatTime(60)).toBe('1m 0s');
  });

  it('formats zero time', () => {
    expect(formatTime(0)).toBe('0m 0s');
  });

  it('formats large values', () => {
    expect(formatTime(3661)).toBe('61m 1s');
  });
});

describe('formatPace', () => {
  it('formats pace with padded seconds', () => {
    expect(formatPace(65)).toBe('1:05 /100m');
  });

  it('formats pace with zero seconds', () => {
    expect(formatPace(120)).toBe('2:00 /100m');
  });

  it('formats pace under a minute', () => {
    expect(formatPace(45)).toBe('0:45 /100m');
  });
});
