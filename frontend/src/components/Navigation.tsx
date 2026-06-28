import { NavLink } from 'react-router-dom';
import './Navigation.css';

interface NavigationProps {
  onProfileClick?: () => void;
  profileButtonRef?: React.RefObject<HTMLElement>;
}

/**
 * Top navigation bar with route links and active indicator.
 *
 * Renders app name/logo on the left and nav links on the right.
 * Uses react-router-dom NavLink for automatic active state detection.
 * Profile button triggers a modal (not a route navigation).
 *
 * Validates: Requirements 7.1, 7.2, 7.3, 7.5, 11.4
 */
export function Navigation({ onProfileClick, profileButtonRef }: NavigationProps) {
  return (
    <header className="nav">
      <div className="nav__left">
        <span className="nav__logo" aria-hidden="true">🏊</span>
        <span className="nav__app-name">AI Swim Coach</span>
      </div>
      <nav className="nav__links" aria-label="Main navigation">
        <NavLink
          to="/"
          end
          className={({ isActive }) =>
            `nav__link${isActive ? ' nav__link--active' : ''}`
          }
        >
          Dashboard
        </NavLink>
        <NavLink
          to="/plans"
          className={({ isActive }) =>
            `nav__link${isActive ? ' nav__link--active' : ''}`
          }
        >
          Training Plans
        </NavLink>
        <button
          type="button"
          className="nav__link nav__profile-btn"
          onClick={onProfileClick}
          ref={profileButtonRef as React.RefObject<HTMLButtonElement>}
        >
          Profile
        </button>
      </nav>
    </header>
  );
}
