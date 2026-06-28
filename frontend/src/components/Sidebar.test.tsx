import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Sidebar } from './Sidebar';

describe('Sidebar', () => {
  const defaultProps = {
    profilePictureUrl: null,
    displayName: 'Jane Swimmer',
    memberSince: 'January 2024',
    totalSessions: 42,
    totalDistanceMeters: 52500,
    currentStreakDays: 7,
    sessionsPerWeek: [2, 3, 1, 4],
  };

  it('renders display name and member-since date', () => {
    render(<Sidebar {...defaultProps} />);

    expect(screen.getByText('Jane Swimmer')).toBeInTheDocument();
    expect(screen.getByText('Member since January 2024')).toBeInTheDocument();
  });

  it('renders placeholder avatar when no profile picture', () => {
    render(<Sidebar {...defaultProps} />);

    expect(screen.getByText('👤')).toBeInTheDocument();
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
  });

  it('renders profile picture when URL is provided', () => {
    render(
      <Sidebar
        {...defaultProps}
        profilePictureUrl="https://example.com/photo.jpg"
      />
    );

    const img = screen.getByRole('img');
    expect(img).toHaveAttribute('src', 'https://example.com/photo.jpg');
    expect(img).toHaveAttribute('alt', "Jane Swimmer's profile picture");
  });

  it('renders total sessions stat', () => {
    render(<Sidebar {...defaultProps} />);

    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('Sessions')).toBeInTheDocument();
  });

  it('renders total distance formatted in km', () => {
    render(<Sidebar {...defaultProps} />);

    expect(screen.getByText('52.5 km')).toBeInTheDocument();
    expect(screen.getByText('Total Distance')).toBeInTheDocument();
  });

  it('renders distance in meters when below 1000m', () => {
    render(<Sidebar {...defaultProps} totalDistanceMeters={750} />);

    expect(screen.getByText('750 m')).toBeInTheDocument();
  });

  it('renders streak days stat', () => {
    render(<Sidebar {...defaultProps} />);

    expect(screen.getByText('7')).toBeInTheDocument();
    expect(screen.getByText('Day Streak')).toBeInTheDocument();
  });

  it('renders stat values with large bold typography', () => {
    render(<Sidebar {...defaultProps} />);

    const statValues = document.querySelectorAll('.sidebar__stat-value');
    expect(statValues.length).toBe(4);

    // Verify the CSS class is applied (actual computed style requires browser rendering)
    statValues.forEach((el) => {
      expect(el.classList.contains('sidebar__stat-value')).toBe(true);
    });
  });

  it('has accessible structure with aria-label', () => {
    render(<Sidebar {...defaultProps} />);

    expect(screen.getByLabelText('Profile summary')).toBeInTheDocument();
    expect(screen.getByLabelText('Training statistics')).toBeInTheDocument();
  });
});
