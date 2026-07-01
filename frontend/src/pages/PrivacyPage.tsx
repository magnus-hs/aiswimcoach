import './StaticPage.css';

/**
 * Data Privacy page.
 */
export function PrivacyPage() {
  return (
    <div className="static-page">
      <h1 className="static-page__heading">Data Privacy</h1>
      <p className="static-page__updated">Last updated: {new Date().getFullYear()}</p>

      <p className="static-page__intro">
        Your privacy matters. This page explains what data AI Swim Coach collects, how it is used,
        and the choices you have.
      </p>

      <h2>What we collect</h2>
      <ul>
        <li><strong>Account details:</strong> your email address and (if you sign in with Google) your Google profile name and picture.</li>
        <li><strong>Profile information:</strong> details you enter such as date of birth, nationality, locality, ability level, CSS pace, and goals.</li>
        <li><strong>Swim data:</strong> the activity (.fit) files you upload and the metrics derived from them — distance, pace, SWOLF, stroke, heart rate, splits, and session structure.</li>
      </ul>

      <h2>How we use your data</h2>
      <ul>
        <li>To calculate your swim metrics and display your sessions, charts, and history.</li>
        <li>To generate AI coaching analysis, comparisons, and progress toward your goals.</li>
        <li>To maintain your account and improve the service.</li>
      </ul>

      <h2>Where your data is stored</h2>
      <p>
        Your data is stored securely using Amazon Web Services (AWS) in the United States. Uploaded
        files are held in cloud storage and your session and profile data in a managed database.
        AI analysis is generated using AWS Bedrock; your relevant training data is sent to the model
        to produce responses and is not used to train third-party models.
      </p>

      <h2>Sharing</h2>
      <p>
        We do not sell your personal data. Data is only shared with the infrastructure providers
        (such as AWS) needed to run the service, and where required by law.
      </p>

      <h2>Your choices</h2>
      <ul>
        <li>You can edit or update your profile and goals at any time.</li>
        <li>You can request deletion of your account and associated data by contacting us.</li>
      </ul>

      <h2>Contact</h2>
      <p>
        For any privacy questions or data requests, email{' '}
        <a href="mailto:magshs@gmail.com">magshs@gmail.com</a>.
      </p>
    </div>
  );
}
