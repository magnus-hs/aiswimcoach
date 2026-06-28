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
          viewBox="0 0 56 28"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Swim goggles silhouette */}
          <ellipse cx="18" cy="14" rx="10" ry="8" fill="none" stroke="#ffffff" strokeWidth="2" />
          <ellipse cx="38" cy="14" rx="10" ry="8" fill="none" stroke="#ffffff" strokeWidth="2" />
          {/* Bridge between lenses */}
          <path d="M28 12 C29 10, 27 10, 28 12" stroke="#ffffff" strokeWidth="2" fill="none" />
          <path d="M28 14 Q28 10, 28 14" stroke="#ffffff" strokeWidth="1.5" fill="none" />
          <line x1="26" y1="11" x2="30" y2="11" stroke="#ffffff" strokeWidth="1.5" strokeLinecap="round" />
          {/* Strap */}
          <path d="M8 13 Q4 14, 4 14" stroke="hsla(200,60%,75%,0.7)" strokeWidth="1.5" strokeLinecap="round" fill="none" />
          <path d="M48 13 Q52 14, 52 14" stroke="hsla(200,60%,75%,0.7)" strokeWidth="1.5" strokeLinecap="round" fill="none" />
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
