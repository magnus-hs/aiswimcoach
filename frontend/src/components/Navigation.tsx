import { useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
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

  return (
    <header className="nav">
      <Link to="/" className="nav__left">
        <svg
          className="nav__logo-img"
          role="img"
          aria-label="AI Swim Coach"
          viewBox="0 0 48 36"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Lane lines */}
          <rect y="8" width="48" height="2" fill="hsla(0,0%,100%,0.25)" rx="1" />
          <rect y="16" width="48" height="2" fill="hsla(0,0%,100%,0.25)" rx="1" />
          <rect y="24" width="48" height="2" fill="hsla(0,0%,100%,0.25)" rx="1" />
          {/* Swimmer silhouette / wave */}
          <path
            d="M6 18 C12 14, 18 22, 24 18 C30 14, 36 22, 42 18"
            stroke="#ffffff"
            strokeWidth="2.5"
            fill="none"
            strokeLinecap="round"
          />
          {/* Water accent */}
          <path
            d="M2 30 C8 27, 14 33, 20 30 C26 27, 32 33, 38 30 C44 27, 46 30, 48 30"
            stroke="hsla(200,60%,75%,0.8)"
            strokeWidth="1.5"
            fill="none"
            strokeLinecap="round"
          />
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
                onClick={() => { setProfileMenuOpen(false); onProfileClick?.(); }}
              >
                Edit Profile
              </button>
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
            </div>
          )}
        </div>
      </nav>
    </header>
  );
}
