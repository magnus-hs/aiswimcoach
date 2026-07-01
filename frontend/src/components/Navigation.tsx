import { useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import './Navigation.css';

interface NavigationProps {
  onProfileClick?: () => void;
  profileButtonRef?: React.RefObject<HTMLElement>;
}

/**
 * Top navigation bar with route links, profile dropdown menu, and logo.
 */
export function Navigation({ onProfileClick, profileButtonRef }: NavigationProps) {
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);
  const navigate = useNavigate();
  const { logout } = useAuth();

  return (
    <header className="nav">
      <Link to="/" className="nav__left">
        <svg
          className="nav__logo-img"
          role="img"
          aria-label="AI Swim Coach"
          viewBox="0 0 48 24"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Left lens */}
          <ellipse cx="14" cy="12" rx="9" ry="7" fill="none" stroke="var(--color-primary)" strokeWidth="2.5" />
          {/* Right lens */}
          <ellipse cx="34" cy="12" rx="9" ry="7" fill="none" stroke="var(--color-primary)" strokeWidth="2.5" />
          {/* Bridge */}
          <path d="M23 10 C24 8, 24 8, 25 10" stroke="var(--color-primary)" strokeWidth="2" fill="none" strokeLinecap="round" />
          {/* Left strap */}
          <line x1="5" y1="11" x2="2" y2="11" stroke="var(--color-primary-light)" strokeWidth="2" strokeLinecap="round" />
          {/* Right strap */}
          <line x1="43" y1="11" x2="46" y2="11" stroke="var(--color-primary-light)" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <span className="nav__app-name">AI Swim Coach</span>
      </Link>
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
        <NavLink
          to="/ai-coach"
          className={({ isActive }) =>
            `nav__link${isActive ? ' nav__link--active' : ''}`
          }
        >
          AI Coach
        </NavLink>
        <div className="nav__profile-menu">
          <button
            type="button"
            className="nav__link nav__profile-btn"
            onClick={() => setProfileMenuOpen(!profileMenuOpen)}
            ref={profileButtonRef as React.RefObject<HTMLButtonElement>}
            aria-expanded={profileMenuOpen}
            aria-haspopup="true"
          >
            Profile ▾
          </button>
          {profileMenuOpen && (
            <div className="nav__dropdown" role="menu">
              <button
                className="nav__dropdown-item"
                role="menuitem"
                onClick={() => { setProfileMenuOpen(false); navigate('/ability'); }}
              >
                Ability Assessment
              </button>
              <button
                className="nav__dropdown-item"
                role="menuitem"
                onClick={() => { setProfileMenuOpen(false); navigate('/personal-bests'); }}
              >
                Personal Bests
              </button>
              <button
                className="nav__dropdown-item"
                role="menuitem"
                onClick={() => { setProfileMenuOpen(false); navigate('/goals'); }}
              >
                Goals
              </button>
              <button
                className="nav__dropdown-item"
                role="menuitem"
                onClick={() => { setProfileMenuOpen(false); navigate('/css'); }}
              >
                Critical Swim Speed
              </button>
              <button
                className="nav__dropdown-item"
                role="menuitem"
                onClick={() => { setProfileMenuOpen(false); onProfileClick?.(); }}
              >
                Edit Profile
              </button>
              <button
                className="nav__dropdown-item nav__dropdown-item--logout"
                role="menuitem"
                onClick={() => { setProfileMenuOpen(false); logout(); navigate('/login'); }}
              >
                Log Out
              </button>
            </div>
          )}
        </div>
      </nav>
    </header>
  );
}
