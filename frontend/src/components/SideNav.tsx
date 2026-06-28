import { NavLink } from 'react-router-dom';
import './SideNav.css';

/**
 * Left sidebar navigation with links to main sections.
 */
export function SideNav() {
  return (
    <nav className="sidenav" aria-label="Side navigation">
      <NavLink
        to="/"
        end
        className={({ isActive }) =>
          `sidenav__link${isActive ? ' sidenav__link--active' : ''}`
        }
      >
        <span className="sidenav__icon">📊</span>
        <span className="sidenav__label">Dashboard</span>
      </NavLink>
      <NavLink
        to="/plans"
        className={({ isActive }) =>
          `sidenav__link${isActive ? ' sidenav__link--active' : ''}`
        }
      >
        <span className="sidenav__icon">📋</span>
        <span className="sidenav__label">Training Plans</span>
      </NavLink>
      <NavLink
        to="/activity/new"
        className={({ isActive }) =>
          `sidenav__link${isActive ? ' sidenav__link--active' : ''}`
        }
      >
        <span className="sidenav__icon">🏊</span>
        <span className="sidenav__label">Activities</span>
      </NavLink>
      <NavLink
        to="/personal-bests"
        className={({ isActive }) =>
          `sidenav__link${isActive ? ' sidenav__link--active' : ''}`
        }
      >
        <span className="sidenav__icon">🏆</span>
        <span className="sidenav__label">Personal Bests</span>
      </NavLink>
    </nav>
  );
}
