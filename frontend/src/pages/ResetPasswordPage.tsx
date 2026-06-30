import { useState, FormEvent } from 'react';
import { Link } from 'react-router-dom';

/**
 * Reset password page — enter email to request a password reset,
 * then enter new password with the reset token.
 */
export function ResetPasswordPage() {
  const [email, setEmail] = useState('');
  const [token, setToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [step, setStep] = useState<'request' | 'reset'>('request');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleRequest = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await fetch(`${import.meta.env.VITE_API_ENDPOINT}/auth/reset-request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to request reset');
      }

      const data = await response.json();
      if (data.token) {
        setToken(data.token);
      }
      setStep('reset');
      setSuccess('A reset token has been sent to your email. Enter it below with your new password.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await fetch(`${import.meta.env.VITE_API_ENDPOINT}/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, token, new_password: newPassword }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to reset password');
      }

      setSuccess('Password reset successfully! You can now log in with your new password.');
      setStep('request');
      setEmail('');
      setToken('');
      setNewPassword('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Reset failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-card__header">
          <span className="auth-card__icon" aria-hidden="true">🔑</span>
          <h1 className="auth-card__title">Reset Password</h1>
          <p className="auth-card__subtitle">
            {step === 'request'
              ? 'Enter your email to receive a reset token'
              : 'Enter the reset token and your new password'}
          </p>
        </div>

        {success && (
          <div className="auth-form__success" role="status">{success}</div>
        )}
        {error && (
          <div className="auth-form__error" role="alert">{error}</div>
        )}

        {step === 'request' && (
          <form onSubmit={handleRequest} className="auth-form">
            <div className="auth-form__field">
              <label htmlFor="reset-email" className="auth-form__label">Email Address</label>
              <input
                id="reset-email"
                type="email"
                className="auth-form__input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                disabled={loading}
              />
            </div>
            <button type="submit" className="auth-form__submit" disabled={loading || !email}>
              {loading ? 'Sending...' : 'Request Reset Token'}
            </button>
          </form>
        )}

        {step === 'reset' && (
          <form onSubmit={handleReset} className="auth-form">
            <div className="auth-form__field">
              <label htmlFor="reset-token" className="auth-form__label">Reset Token</label>
              <input
                id="reset-token"
                type="text"
                className="auth-form__input"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="Enter the 6-digit token"
                required
                disabled={loading}
              />
            </div>
            <div className="auth-form__field">
              <label htmlFor="new-password" className="auth-form__label">New Password</label>
              <input
                id="new-password"
                type="password"
                className="auth-form__input"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Minimum 8 characters"
                required
                minLength={8}
                disabled={loading}
              />
            </div>
            <button type="submit" className="auth-form__submit" disabled={loading || !token || newPassword.length < 8}>
              {loading ? 'Resetting...' : 'Reset Password'}
            </button>
          </form>
        )}

        <div className="auth-card__footer">
          <p className="auth-card__footer-text">
            <Link to="/login" className="auth-card__link">← Back to Login</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
