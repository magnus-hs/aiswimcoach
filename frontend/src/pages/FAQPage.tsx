import './StaticPage.css';

const FAQS: { q: string; a: string }[] = [
  {
    q: 'What files can I upload?',
    a: 'AI Swim Coach reads .fit files from Garmin and most swim watches. You can upload one or more files at a time from the Activities page.',
  },
  {
    q: 'Why is my session split into sets like 400m and 4×100m?',
    a: 'We read the lap markers your watch records each time you press the lap button, so your session structure reflects the sets you actually swam, with rest detected between them.',
  },
  {
    q: 'What is CSS and why does it matter?',
    a: 'Critical Swim Speed is your threshold (training) pace, calculated from a 400m and 200m time trial. It is used to categorise your training by energy system and to estimate race times. Note CSS is a training pace, not a race time.',
  },
  {
    q: 'What is SWOLF and distance per stroke?',
    a: 'SWOLF combines your time and stroke count for a length as an efficiency score (lower is better). Distance per stroke is how far you travel with each stroke — a simple measure of stroke efficiency.',
  },
  {
    q: 'What does the Turn Est. column mean?',
    a: 'Turn Est. is an approximation of your turn + push-off + glide time on each length. Your watch only records total wall-to-wall time and stroke count per length — it doesn\'t directly measure the turn itself. So we estimate it by comparing each length to the average length time in the same set: the average is treated as having a baseline turn overhead (~0.8s), and each length shows that baseline adjusted by how much faster or slower it was than the set average. It\'s useful for spotting which turns are costing you time, but it\'s an estimate, not a directly measured value.',
  },
  {
    q: 'How do goals work?',
    a: 'On the Goals page you can pick focus areas and set measurable weekly, monthly, and yearly distance targets plus a target race time. Your goals steer the AI Coach\'s analysis and show progress indicators under your dashboard charts.',
  },
  {
    q: 'How does the AI Coach use my data?',
    a: 'The AI Coach has access to your session history, profile, CSS, and goals. It identifies trends, compares you to age-group standards, and gives specific advice. Use the Intent options to steer a single question toward a topic.',
  },
  {
    q: 'Is the coaching advice medical advice?',
    a: 'No. All analysis and suggestions are for general training information only and are not medical advice. Train within your limits and consult a professional if you have any health concerns.',
  },
  {
    q: 'How do I delete my data?',
    a: 'Email us at magshs@gmail.com and we will remove your account and associated data.',
  },
];

/**
 * FAQ page.
 */
export function FAQPage() {
  return (
    <div className="static-page">
      <h1 className="static-page__heading">Frequently Asked Questions</h1>
      <p className="static-page__intro">
        Quick answers to common questions. Can't find what you need? Visit{' '}
        <a href="/support">Support</a> or email{' '}
        <a href="mailto:magshs@gmail.com">magshs@gmail.com</a>.
      </p>

      <div>
        {FAQS.map((item, i) => (
          <div key={i} className="static-page__faq-item">
            <p className="static-page__faq-q">{item.q}</p>
            <p className="static-page__faq-a">{item.a}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
