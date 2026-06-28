import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Navigation } from './Navigation';

const renderNavigation = (initialRoute = '/', onProfileClick = vi.fn()) => {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <Navigation onProfileClick={onProfileClick} />
    </MemoryRouter>
  );
};

describe('Navigation', () => {
  it('renders the app name and SVG logo', () => {
    renderNavigation();
    expect(screen.getByText('AI Swim Coach')).toBeInTheDocument();
    expect(screen.getByRole('img', { name: 'AI Swim Coach' })).toBeInTheDocument();
  });

  it('renders Dashboard and Training Plans nav links', () => {
    renderNavigation();
    expect(screen.getByRole('link', { name: 'Dashboard' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Training Plans' })).toBeInTheDocument();
  });

  it('renders Profile as a button (not a link)', () => {
    renderNavigation();
    const profileBtn = screen.getByRole('button', { name: /Profile/ });
    expect(profileBtn).toBeInTheDocument();
    // Verify it's not a link
    expect(screen.queryByRole('link', { name: /Profile/ })).not.toBeInTheDocument();
  });

  it('applies active class to Dashboard link when on /', () => {
    renderNavigation('/');
    const dashboardLink = screen.getByRole('link', { name: 'Dashboard' });
    expect(dashboardLink).toHaveClass('nav__link--active');
  });

  it('applies active class to Training Plans link when on /plans', () => {
    renderNavigation('/plans');
    const plansLink = screen.getByRole('link', { name: 'Training Plans' });
    expect(plansLink).toHaveClass('nav__link--active');
  });

  it('does not apply active class to Dashboard when on /plans', () => {
    renderNavigation('/plans');
    const dashboardLink = screen.getByRole('link', { name: 'Dashboard' });
    expect(dashboardLink).not.toHaveClass('nav__link--active');
  });

  it('calls onProfileClick when Profile button is clicked', () => {
    const onProfileClick = vi.fn();
    renderNavigation('/', onProfileClick);
    const profileBtn = screen.getByRole('button', { name: /Profile/ });
    fireEvent.click(profileBtn);
    // Clicking opens the dropdown; click "Edit Profile" to trigger onProfileClick
    const editProfileItem = screen.getByRole('menuitem', { name: 'Edit Profile' });
    fireEvent.click(editProfileItem);
    expect(onProfileClick).toHaveBeenCalledTimes(1);
  });

  it('has an accessible navigation landmark', () => {
    renderNavigation();
    expect(screen.getByRole('navigation', { name: 'Main navigation' })).toBeInTheDocument();
  });
});
