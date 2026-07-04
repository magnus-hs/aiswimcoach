import { Link } from 'react-router-dom';
import { SwimSlider } from '../components/SwimSlider';
import './LandingPage.css';

const FEATURES: { icon: string; title: string; description: string }[] = [
  {
    icon: '📊',
    title: 'Deep Session Analysis',
    description:
      'Upload your Garmin .fit files and get accurate set breakdowns, rest intervals, SWOLF, distance per stroke, and heart rate zones — all derived from real lap data, not guesswork.',
  },
  {
    icon: '🤖',
    title: 'AI Coaching',
    description:
      'Chat with an AI coach that knows your full training history. Get trend analysis, personalised drills, and honest answers about where you stand.',
  },
  {
    icon: '📈',
    title: 'Training Load & CSS',
    description:
      'Calculate your Critical Swim Speed and see every set categorised by energy system — sprint, threshold, or aerobic — with rest-adjusted load scoring.',
  },
  {
    icon: '🎯',
    title: 'Goals That Matter',
    description:
      'Set weekly, monthly, and yearly distance targets, plus a target race time. Watch your progress bars fill as your AI coach tracks the gap.',
  },
  {
    icon: '🏆',
    title: 'Personal Bests, Verified',
    description:
      'Derived PBs only count if you actually swam that distance continuously — no estimates, no inflated numbers. Just the times you really hit.',
  },
  {
    icon: '👥',
    title: 'Swim With Friends',
    description:
      'Connect with other swimmers, share your sessions, and trade kudos and comments. Training is better with a bit of friendly competition.',
  },
];

const STEPS: { number: string; title: string; description: string }[] = [
  { number: '1', title: 'Upload your swim', description: 'Drop in a .fit file from your Garmin or compatible watch.' },
  { number: '2', title: 'Get instant analysis', description: 'Pace, SWOLF, heart rate, splits, and training load — automatically.' },
  { number: '3', title: 'Train smarter', description: 'Follow AI-guided plans, track goals, and improve with every session.' },
];

/**
 * Public landing page — showcases what AI Swim Coach can do to entice sign-ups.
 * Shown at "/" for unauthenticated visitors; authenticated users see the Dashboard instead.
 */
export function LandingPage() {
  return (
    <div className="landing">
      <span className="landing__beta-badge">Beta</span>
      {/* Header */}
      <header className="landing__header">
        <div className="landing__header-inner">
          <div className="landing__brand">
            <svg
              className="landing__logo"
              viewBox="0 0 48 24"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <ellipse cx="14" cy="12" rx="9" ry="7" fill="none" stroke="var(--color-primary)" strokeWidth="2.5" />
              <ellipse cx="34" cy="12" rx="9" ry="7" fill="none" stroke="var(--color-primary)" strokeWidth="2.5" />
              <path d="M23 10 C24 8, 24 8, 25 10" stroke="var(--color-primary)" strokeWidth="2" fill="none" strokeLinecap="round" />
              <line x1="5" y1="11" x2="2" y2="11" stroke="var(--color-primary-light)" strokeWidth="2" strokeLinecap="round" />
              <line x1="43" y1="11" x2="46" y2="11" stroke="var(--color-primary-light)" strokeWidth="2" strokeLinecap="round" />
            </svg>
            <span className="landing__brand-name">AI Swim Coach</span>
          </div>
          <nav className="landing__header-actions">
            <Link to="/login" className="landing__nav-link">Log In</Link>
            <Link to="/register" className="landing__nav-cta">Get Started Free</Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="landing__hero">
        <div className="landing__hero-content">
          <h1 className="landing__hero-title">
            Swim training analysis that actually understands your data.
          </h1>
          <p className="landing__hero-subtitle">
            Upload your swim files, get real set-by-set analysis, AI coaching tailored to your history,
            and training load insights other apps just don't offer. Built by swimmers, for swimmers.
          </p>
          <div className="landing__hero-actions">
            <Link to="/register" className="landing__btn landing__btn--primary">
              Start Training Smarter
            </Link>
            <Link to="/login" className="landing__btn landing__btn--secondary">
              I already have an account
            </Link>
          </div>
          <p className="landing__hero-note">Free to use. No credit card required.</p>
        </div>
        <div className="landing__hero-visual">
          <SwimSlider />
          <div className="landing__hero-card landing__hero-card--1" aria-hidden="true">
            <span className="landing__hero-card-label">Distance</span>
            <span className="landing__hero-card-value">2,000m</span>
          </div>
          <div className="landing__hero-card landing__hero-card--2" aria-hidden="true">
            <span className="landing__hero-card-label">CSS Pace</span>
            <span className="landing__hero-card-value">1:37 /100m</span>
          </div>
        </div>
      </section>

      {/* Features grid */}
      <section className="landing__section">
        <h2 className="landing__section-title">Everything you need to swim faster</h2>
        <p className="landing__section-subtitle">
          One platform for analysis, coaching, training load, and your swim community.
        </p>
        <div className="landing__features">
          {FEATURES.map((f) => (
            <div key={f.title} className="landing__feature-card">
              <span className="landing__feature-icon" aria-hidden="true">{f.icon}</span>
              <h3 className="landing__feature-title">{f.title}</h3>
              <p className="landing__feature-description">{f.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="landing__section landing__section--alt">
        <h2 className="landing__section-title">How it works</h2>
        <div className="landing__steps">
          {STEPS.map((s) => (
            <div key={s.number} className="landing__step">
              <span className="landing__step-number">{s.number}</span>
              <h3 className="landing__step-title">{s.title}</h3>
              <p className="landing__step-description">{s.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Final CTA */}
      <section className="landing__cta">
        <h2 className="landing__cta-title">Ready to see what your swims are really telling you?</h2>
        <Link to="/register" className="landing__btn landing__btn--primary landing__btn--large">
          Create Your Free Account
        </Link>
      </section>

      {/* Footer */}
      <footer className="landing__footer">
        <span>© {new Date().getFullYear()} AI Swim Coach</span>
        <div className="landing__footer-links">
          <Link to="/terms">Terms &amp; Conditions</Link>
          <Link to="/privacy">Data Privacy</Link>
          <Link to="/support">Support</Link>
          <Link to="/faq">FAQ</Link>
        </div>
      </footer>
    </div>
  );
}
