import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import './Header.css';

/**
 * Header component with sidebar navigation for authenticated pages.
 * 
 * Displays:
 * - Top bar: App logo (left), user email and profile avatar (right)
 * - Left sidebar: Navigation links with icons (Upload, History, Profile, Logout)
 * 
 * Features:
 * - Loads profile picture from Users table via GET /auth/user endpoint
 * - Shows default avatar icon if no profile picture exists
 * - Profile avatar click navigates to /profile
 * - Logout clears localStorage and redirects to /login
 * - Sidebar navigation with icons following Strava/Garmin pattern
 * 
 * Validates: Requirements 22.6-22.8, 24.1-24.6, 25.3, 25.9
 */
export function Header() {
  const { email, logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [profilePictureUrl, setProfilePictureUrl] = useState<string | null>(null);
  const [loadingPicture, setLoadingPicture] = useState(true);

  // Don't show authenticated layout on public routes
  const isPublicRoute = location.pathname === '/login' || location.pathname === '/register';

  useEffect(() => {
    // Only fetch user info when authenticated and not on public route
    if (!isAuthenticated || isPublicRoute) {
      setLoadingPicture(false);
      return;
    }

    // Fetch user info including profile picture URL
    const fetchUserInfo = async () => {
      try {
        const token = localStorage.getItem('auth_token');
        if (!token) {
          setLoadingPicture(false);
          return;
        }

        const response = await fetch(import.meta.env.VITE_API_ENDPOINT + '/auth/user', {
          method: 'GET',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (response.ok) {
          const data = await response.json();
          setProfilePictureUrl(data.profile_picture_url || null);
        }
      } catch (error) {
        console.error('Failed to load user info:', error);
      } finally {
        setLoadingPicture(false);
      }
    };

    fetchUserInfo();
  }, [isAuthenticated, isPublicRoute]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleAvatarClick = () => {
    navigate('/profile');
  };

  // Show simple header on public routes
  if (!isAuthenticated || isPublicRoute) {
    return (
      <header className="app-header">
        <div className="app-header__inner">
          <span className="app-header__icon" aria-hidden="true">🏊</span>
          <h1 className="app-header__title">AI Swim Coach</h1>
        </div>
      </header>
    );
  }

  // Show full header with sidebar navigation for authenticated routes
  return (
    <>
      {/* Top Header Bar */}
      <header className="app-header">
        <div className="app-header__inner app-header__inner--with-sidebar">
          <div className="app-header__left">
            <span className="app-header__icon" aria-hidden="true">🏊</span>
            <h1 className="app-header__title">AI Swim Coach</h1>
          </div>
          <div className="app-header__right">
            <span className="app-header__user-email">{email}</span>
            
            {/* Profile avatar - 40px circular */}
            <button
              type="button"
              className="app-header__avatar"
              onClick={handleAvatarClick}
              aria-label="View profile"
              title="View profile"
            >
              {loadingPicture ? (
                <span className="app-header__avatar-placeholder" aria-hidden="true">⏳</span>
              ) : profilePictureUrl ? (
                <img
                  src={profilePictureUrl}
                  alt="Profile"
                  className="app-header__avatar-image"
                />
              ) : (
                <span className="app-header__avatar-placeholder" aria-hidden="true">👤</span>
              )}
            </button>
          </div>
        </div>
      </header>

      {/* Left Sidebar Navigation */}
      <nav className="sidebar-nav" aria-label="Main navigation">
        <ul className="sidebar-nav__list">
          <li className="sidebar-nav__item">
            <Link
              to="/upload"
              className={`sidebar-nav__link ${location.pathname === '/upload' ? 'sidebar-nav__link--active' : ''}`}
            >
              <span className="sidebar-nav__icon" aria-hidden="true">📤</span>
              <span className="sidebar-nav__label">Upload</span>
            </Link>
          </li>
          <li className="sidebar-nav__item">
            <Link
              to="/history"
              className={`sidebar-nav__link ${location.pathname === '/history' || location.pathname.startsWith('/session/') ? 'sidebar-nav__link--active' : ''}`}
            >
              <span className="sidebar-nav__icon" aria-hidden="true">📊</span>
              <span className="sidebar-nav__label">History</span>
            </Link>
          </li>
          <li className="sidebar-nav__item">
            <Link
              to="/profile"
              className={`sidebar-nav__link ${location.pathname === '/profile' ? 'sidebar-nav__link--active' : ''}`}
            >
              <span className="sidebar-nav__icon" aria-hidden="true">⚙️</span>
              <span className="sidebar-nav__label">Profile</span>
            </Link>
          </li>
          <li className="sidebar-nav__item sidebar-nav__item--bottom">
            <button
              type="button"
              className="sidebar-nav__link sidebar-nav__link--button"
              onClick={handleLogout}
            >
              <span className="sidebar-nav__icon" aria-hidden="true">🚪</span>
              <span className="sidebar-nav__label">Logout</span>
            </button>
          </li>
        </ul>
      </nav>
    </>
  );
}
