import { useState, FormEvent, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import * as authService from '../api/authService';
import { ApiError } from '../types';

/**
 * Login component with email and password authentication.
 * 
 * Features:
 * - Email and password input fields with validation
 * - Calls authService.login() on submit
 * - Stores token and updates auth context
 * - Redirects to /upload on success
 * - Displays error messages from backend
 * - Displays success message when redirected from registration
 * 
 * Validates: Requirements 21.10-21.19
 */
export function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Check for success message from registration
  useEffect(() => {
    const state = location.state as { message?: string } | null;
    if (state?.message) {
      setSuccessMessage(state.message);
      // Clear the state so message doesn't reappear on refresh
      navigate(location.pathname, { replace: true, state: {} });
    }
  }, [location, navigate]);

  // Email validation using standard HTML5 email pattern
  const isValidEmail = (email: string): boolean => {
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailPattern.test(email);
  };

  // Check if form is valid
  const isFormValid = isValidEmail(email) && password.length >= 8;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');

    if (!isFormValid) {
      setError('Please enter a valid email and password (minimum 8 characters)');
      return;
    }

    setIsLoading(true);

    try {
      const response = await authService.login(email, password);
      
      // Store token and update auth context
      login(response.token);
      
      // Redirect to upload page
      navigate('/upload');
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.serverMessage);
      } else {
        setError('An unexpected error occurred. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-card__header">
          <span className="auth-card__icon" aria-hidden="true">🏊</span>
          <h1 className="auth-card__title">Welcome Back</h1>
          <p className="auth-card__subtitle">Sign in to continue to AI Swim Coach</p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {successMessage && (
            <div className="auth-form__success" role="status">
              {successMessage}
            </div>
          )}
          
          {error && (
            <div className="auth-form__error" role="alert">
              {error}
            </div>
          )}

          <div className="auth-form__field">
            <label htmlFor="email" className="auth-form__label">
              Email Address
            </label>
            <input
              id="email"
              type="email"
              className="auth-form__input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              autoComplete="email"
              disabled={isLoading}
            />
          </div>

          <div className="auth-form__field">
            <label htmlFor="password" className="auth-form__label">
              Password
            </label>
            <input
              id="password"
              type="password"
              className="auth-form__input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              required
              autoComplete="current-password"
              minLength={8}
              disabled={isLoading}
            />
          </div>

          <button
            type="submit"
            className="auth-form__submit"
            disabled={!isFormValid || isLoading}
          >
            {isLoading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="auth-card__footer">
          <p className="auth-card__footer-text">
            <a href="/reset-password" className="auth-card__link">
              Forgot your password?
            </a>
          </p>
          <p className="auth-card__footer-text">
            Don't have an account?{' '}
            <a href="/register" className="auth-card__link">
              Sign up
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
