import './StaticPage.css';

/**
 * Support page.
 */
export function SupportPage() {
  return (
    <div className="static-page">
      <h1 className="static-page__heading">Support</h1>

      <p className="static-page__intro">
        Need a hand? We're happy to help with anything from uploading files to understanding your
        analysis.
      </p>

      <div className="static-page__card">
        <h2>Contact us</h2>
        <p>
          Email us at{' '}
          <a href="mailto:magshs@gmail.com">magshs@gmail.com</a>{' '}
          and we'll get back to you as soon as we can.
        </p>
        <p>
          To help us resolve your issue quickly, please include:
        </p>
        <ul>
          <li>The email address on your account.</li>
          <li>A description of what you were doing and what went wrong.</li>
          <li>If it relates to a specific swim, the date of the session.</li>
          <li>Your device and browser (e.g. iPhone Safari, Windows Chrome).</li>
        </ul>
      </div>

      <h2>Common topics</h2>
      <ul>
        <li>Uploading .fit files from your Garmin or other swim watch.</li>
        <li>Understanding pace, SWOLF, distance-per-stroke, and heart rate zones.</li>
        <li>Setting goals and tracking weekly, monthly, and yearly distance.</li>
        <li>Using the AI Coach for trends, comparisons, and recommendations.</li>
      </ul>
      <p>
        You may also find a quick answer on our <a href="/faq">FAQ</a> page.
      </p>
    </div>
  );
}
