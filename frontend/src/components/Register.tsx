import { useState, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import * as authService from '../api/authService';
import { ApiError } from '../types';

/**
 * Register component for creating new user accounts.
 * 
 * Features:
 * - Email, password, and confirm password form with validation
 * - Validates email format using standard HTML5 pattern
 * - Validates password length (minimum 8 characters)
 * - Validates password match between password and confirm password fields
 * - Calls authService.register() on submit
 * - Redirects to /login with success message on successful registration
 * - Displays error messages from backend
 * 
 * Validates: Requirements 21.1-21.9
 */
export function Register() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  // Email validation using standard HTML5 email pattern
  const isValidEmail = (email: string): boolean => {
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailPattern.test(email);
  };

  // Password validation - minimum 8 characters
  const isValidPassword = (password: string): boolean => {
    return password.length >= 8;
  };

  // Check if passwords match
  const doPasswordsMatch = (): boolean => {
    return password === confirmPassword && password.length > 0;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');

    // Client-side validation
    if (!isValidEmail(email)) {
      setError('Please enter a valid email address');
      return;
    }

    if (!isValidPassword(password)) {
      setError('Password must be at least 8 characters long');
      return;
    }

    if (!doPasswordsMatch()) {
      setError('Passwords do not match');
      return;
    }

    setIsLoading(true);

    try {
      await authService.register(email, password);
      
      // Redirect to login page with success message
      navigate('/login', { state: { message: 'Registration successful! Please sign in.' } });
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
          <h1 className="auth-card__title">Create Account</h1>
          <p className="auth-card__subtitle">Join AI Swim Coach to track your progress</p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
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
              placeholder="Enter your password (min 8 characters)"
              required
              autoComplete="new-password"
              minLength={8}
              disabled={isLoading}
            />
          </div>

          <div className="auth-form__field">
            <label htmlFor="confirmPassword" className="auth-form__label">
              Confirm Password
            </label>
            <input
              id="confirmPassword"
              type="password"
              className="auth-form__input"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Re-enter your password"
              required
              autoComplete="new-password"
              minLength={8}
              disabled={isLoading}
            />
          </div>

          <button
            type="submit"
            className="auth-form__submit"
            disabled={isLoading}
          >
            {isLoading ? 'Creating account...' : 'Create Account'}
          </button>
        </form>

        <div className="auth-card__footer">
          <p className="auth-card__footer-text">
            Already have an account?{' '}
            <a href="/login" className="auth-card__link">
              Sign in
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
