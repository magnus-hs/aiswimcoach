import { Link } from 'react-router-dom';
import './Footer.css';

/**
 * Site footer — frames the page with the logo and utility links
 * (Terms & Conditions, Data Privacy, Support, FAQ).
 */
export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="footer" aria-label="Site footer">
      <div className="footer__inner">
        <div className="footer__brand">
          <svg
            className="footer__logo"
            role="img"
            aria-label="AI Swim Coach"
            viewBox="0 0 48 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <ellipse cx="14" cy="12" rx="9" ry="7" fill="none" stroke="var(--color-primary)" strokeWidth="2.5" />
            <ellipse cx="34" cy="12" rx="9" ry="7" fill="none" stroke="var(--color-primary)" strokeWidth="2.5" />
            <path d="M23 10 C24 8, 24 8, 25 10" stroke="var(--color-primary)" strokeWidth="2" fill="none" strokeLinecap="round" />
            <line x1="5" y1="11" x2="2" y2="11" stroke="var(--color-primary-light)" strokeWidth="2" strokeLinecap="round" />
            <line x1="43" y1="11" x2="46" y2="11" stroke="var(--color-primary-light)" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <span className="footer__app-name">AI Swim Coach</span>
        </div>

        <nav className="footer__links" aria-label="Footer links">
          <Link to="/terms" className="footer__link">Terms &amp; Conditions</Link>
          <Link to="/privacy" className="footer__link">Data Privacy</Link>
          <Link to="/support" className="footer__link">Support</Link>
          <Link to="/faq" className="footer__link">FAQ</Link>
          <Link to="/roadmap" className="footer__link">Roadmap</Link>
        </nav>
      </div>

      <div className="footer__bottom">
        <span className="footer__copy">© {year} AI Swim Coach</span>
      </div>
    </footer>
  );
}
