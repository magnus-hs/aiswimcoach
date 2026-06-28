import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
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
      <div className="nav__left">
        <img src="/logo.png" alt="AI Swim Coach" className="nav__logo-img" />
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
