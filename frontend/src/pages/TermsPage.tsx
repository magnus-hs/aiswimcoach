import './StaticPage.css';

/**
 * Terms & Conditions page.
 */
export function TermsPage() {
  return (
    <div className="static-page">
      <h1 className="static-page__heading">Terms &amp; Conditions</h1>
      <p className="static-page__updated">Last updated: {new Date().getFullYear()}</p>

      <p className="static-page__intro">
        Welcome to AI Swim Coach. By creating an account and using this service you agree to the
        terms below. Please read them carefully.
      </p>

      <h2>1. Using the service</h2>
      <p>
        AI Swim Coach lets you upload swim activity files, view analysis of your sessions, and
        receive AI-generated coaching insights. You are responsible for keeping your account
        credentials secure and for all activity that happens under your account.
      </p>

      <h2>2. Coaching guidance is informational</h2>
      <p>
        The analysis, training suggestions, comparisons, and AI responses provided are for general
        informational and training purposes only. They are not medical, physiotherapy, or
        professional coaching advice. Always listen to your body, train within your limits, and
        consult a qualified professional before starting or changing a training programme,
        especially if you have any health concerns.
      </p>

      <h2>3. Your content</h2>
      <p>
        You retain ownership of the swim data and files you upload. By uploading, you grant us
        permission to process and store that data so we can provide the service to you — including
        generating metrics, charts, and AI analysis.
      </p>

      <h2>4. Acceptable use</h2>
      <ul>
        <li>Do not upload content you do not have the right to share.</li>
        <li>Do not attempt to disrupt, reverse-engineer, or gain unauthorised access to the service.</li>
        <li>Do not use the service for any unlawful purpose.</li>
      </ul>

      <h2>5. Availability</h2>
      <p>
        We work to keep the service running reliably but do not guarantee uninterrupted
        availability. Features may change, and the service is provided on an "as is" basis without
        warranties of any kind.
      </p>

      <h2>6. Limitation of liability</h2>
      <p>
        To the extent permitted by law, AI Swim Coach is not liable for any loss or injury arising
        from your use of the service or reliance on its analysis or recommendations.
      </p>

      <h2>7. Changes to these terms</h2>
      <p>
        We may update these terms from time to time. Continued use of the service after changes are
        published means you accept the revised terms.
      </p>

      <h2>8. Contact</h2>
      <p>
        Questions about these terms? Email us at{' '}
        <a href="mailto:magshs@gmail.com">magshs@gmail.com</a>.
      </p>
    </div>
  );
}
