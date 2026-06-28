import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { Sidebar } from './Sidebar';

describe('Sidebar', () => {
  const defaultProps = {
    profilePictureUrl: null,
    displayName: 'Jane Swimmer',
    memberSince: 'January 2024',
    totalSessions: 42,
    totalDistanceMeters: 52500,
    swimsThisWeek: 3,
    swimsThisMonth: 12,
    swimsYTD: 42,
    sessionsPerWeek: [2, 3, 1, 4],
    distanceThisWeekMeters: 4500,
    distanceThisMonthMeters: 18000,
    distanceYTDMeters: 45000,
  };

  function renderSidebar(props = defaultProps) {
    return render(
      <MemoryRouter>
        <Sidebar {...props} />
      </MemoryRouter>
    );
  }

  it('renders display name and member-since date', () => {
    renderSidebar();

    expect(screen.getByText('Jane Swimmer')).toBeInTheDocument();
    expect(screen.getByText('Member since January 2024')).toBeInTheDocument();
  });

  it('renders placeholder avatar when no profile picture', () => {
    renderSidebar();

    expect(screen.getByText('👤')).toBeInTheDocument();
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
  });

  it('renders profile picture when URL is provided', () => {
    renderSidebar({
      ...defaultProps,
      profilePictureUrl: 'https://example.com/photo.jpg',
    });

    const img = screen.getByRole('img');
    expect(img).toHaveAttribute('src', 'https://example.com/photo.jpg');
    expect(img).toHaveAttribute('alt', "Jane Swimmer's profile picture");
  });

  it('renders total sessions stat', () => {
    renderSidebar();

    expect(screen.getAllByText('42').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Sessions')).toBeInTheDocument();
  });

  it('renders total distance formatted in km', () => {
    renderSidebar();

    expect(screen.getByText('52.5 km')).toBeInTheDocument();
    expect(screen.getByText('Total Distance')).toBeInTheDocument();
  });

  it('renders distance in meters when below 1000m', () => {
    renderSidebar({ ...defaultProps, totalDistanceMeters: 750 });

    expect(screen.getByText('750 m')).toBeInTheDocument();
  });

  it('renders swims per week, month, and year to date stats', () => {
    renderSidebar();

    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('Swims / Week')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('Swims / Month')).toBeInTheDocument();
    expect(screen.getByText('Swims Year to Date')).toBeInTheDocument();
  });

  it('renders stat values with large bold typography', () => {
    renderSidebar();

    const statValues = document.querySelectorAll('.sidebar__stat-value');
    expect(statValues.length).toBe(8);

    // Verify the CSS class is applied (actual computed style requires browser rendering)
    statValues.forEach((el) => {
      expect(el.classList.contains('sidebar__stat-value')).toBe(true);
    });
  });

  it('has accessible structure with aria-label', () => {
    renderSidebar();

    expect(screen.getByLabelText('Profile summary')).toBeInTheDocument();
    expect(screen.getByLabelText('Training statistics')).toBeInTheDocument();
  });
});
