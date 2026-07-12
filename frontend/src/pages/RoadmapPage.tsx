import { Link } from 'react-router-dom';
import './RoadmapPage.css';

interface RoadmapItem {
  status: 'shipped' | 'in-progress' | 'planned' | 'exploring';
  title: string;
  description: string;
}

const ROADMAP: RoadmapItem[] = [
  // Shipped
  { status: 'shipped', title: 'AI Coach Chat', description: 'Interactive coaching conversations about your technique, trends, and age-group comparisons' },
  { status: 'shipped', title: 'Detailed Session Analysis', description: 'Per-length splits, stroke breakdown, SWOLF tracking, and efficiency curves' },
  { status: 'shipped', title: 'Heart Rate Zones', description: 'Automatic HR zone calculation from FIT file data with visual breakdown' },
  { status: 'shipped', title: 'Training Plans', description: 'AI-generated multi-week structured training plans tailored to your goals' },
  { status: 'shipped', title: 'Personal Bests', description: 'Manual and auto-derived PBs with links to the source session' },
  { status: 'shipped', title: 'Friends & Social', description: 'Connect with other swimmers, view their activities, give kudos and comments' },
  { status: 'shipped', title: 'Bulk Import', description: 'Upload hundreds of FIT files at once (zip supported) to import your full history' },
  { status: 'shipped', title: 'Statistics & Yearly Totals', description: 'See your swimming history at a glance — distance, time, pace by year' },

  // In progress
  { status: 'in-progress', title: 'Garmin Connect Sync', description: 'Automatic sync from your Garmin watch — no more manual FIT file uploads' },
  { status: 'in-progress', title: 'Mobile App (PWA)', description: 'Install AI Swim Coach on your phone home screen for a native app experience' },

  // Planned
  { status: 'planned', title: 'Apple Watch Integration', description: 'Sync pool swim workouts directly from Apple Health' },
  { status: 'planned', title: 'Race Predictions', description: 'AI-powered race time predictions based on your training data and PBs' },
  { status: 'planned', title: 'Club & Squad Features', description: 'Coaches can view squad members\' sessions, set group training plans' },
  { status: 'planned', title: 'Open Water Swimming', description: 'Support for open water GPS-tracked swims with distance and pace mapping' },
  { status: 'planned', title: 'Technique Video Analysis', description: 'Upload underwater video for AI-powered stroke technique feedback' },
  { status: 'planned', title: 'Competition Calendar', description: 'Track upcoming meets, set target times, and get event-specific coaching' },

  // Exploring
  { status: 'exploring', title: 'Injury Prevention Alerts', description: 'AI detects overtraining patterns and suggests recovery before injury strikes' },
  { status: 'exploring', title: 'Nutrition & Recovery Guidance', description: 'Post-swim nutrition recommendations based on session intensity' },
  { status: 'exploring', title: 'Live Session Tracking', description: 'Real-time dashboard during a swim with pace alerts and set countdowns' },
  { status: 'exploring', title: 'Leaderboards & Challenges', description: 'Monthly distance challenges, age-group leaderboards, and virtual races' },
];

const STATUS_LABELS: Record<string, { label: string; emoji: string }> = {
  'shipped': { label: 'Shipped', emoji: '✅' },
  'in-progress': { label: 'In Progress', emoji: '🚧' },
  'planned': { label: 'Planned', emoji: '📋' },
  'exploring': { label: 'Exploring', emoji: '💡' },
};

/**
 * Roadmap page — shows where the app is going.
 */
export function RoadmapPage() {
  const grouped = {
    shipped: ROADMAP.filter(i => i.status === 'shipped'),
    'in-progress': ROADMAP.filter(i => i.status === 'in-progress'),
    planned: ROADMAP.filter(i => i.status === 'planned'),
    exploring: ROADMAP.filter(i => i.status === 'exploring'),
  };

  return (
    <div className="roadmap-page">
      <Link to="/" className="roadmap-page__back">← Back</Link>
      <h1 className="roadmap-page__heading">Product Roadmap</h1>
      <p className="roadmap-page__subtitle">
        Where AI Swim Coach is headed. We're building the most complete swim training platform — here's what's coming.
      </p>

      {Object.entries(grouped).map(([status, items]) => (
        <section key={status} className="roadmap-page__section">
          <h2 className="roadmap-page__section-title">
            {STATUS_LABELS[status].emoji} {STATUS_LABELS[status].label}
          </h2>
          <div className="roadmap-page__items">
            {items.map(item => (
              <div key={item.title} className={`roadmap-page__item roadmap-page__item--${status}`}>
                <h3 className="roadmap-page__item-title">{item.title}</h3>
                <p className="roadmap-page__item-desc">{item.description}</p>
              </div>
            ))}
          </div>
        </section>
      ))}

      <section className="roadmap-page__suggestions">
        <h2>Ideas We're Considering</h2>
        <p className="roadmap-page__suggestions-intro">
          These are features we think swimmers would love. Tell us which ones matter most to you — your votes decide what gets built next.
        </p>
        <div className="roadmap-page__ideas">
          <div className="roadmap-page__idea">
            <h3>🏅 Challenge-Based Goals</h3>
            <p>"Swim 10km this month" or "Hit your CSS pace 5 times" — gamified progress with badges and streaks</p>
          </div>
          <div className="roadmap-page__idea">
            <h3>👥 Club & Squad Management</h3>
            <p>Coaches can view their squad's sessions, set group plans, and track attendance</p>
          </div>
          <div className="roadmap-page__idea">
            <h3>🏁 Race Day Mode</h3>
            <p>Set a target race + time → get a taper plan, pacing strategy, and confidence score</p>
          </div>
          <div className="roadmap-page__idea">
            <h3>📊 Technique Scoring</h3>
            <p>A simple 1-100 "technique score" per session derived from SWOLF, DPS, and stroke rate trends</p>
          </div>
          <div className="roadmap-page__idea">
            <h3>📧 Weekly Insights Emails</h3>
            <p>"You swam 12% further than last week" — AI-generated summaries to keep you motivated</p>
          </div>
          <div className="roadmap-page__idea">
            <h3>🎁 Referral Rewards</h3>
            <p>Invite a friend → both get a free month of Premium. Great for squad adoption</p>
          </div>
          <div className="roadmap-page__idea">
            <h3>🏊‍♂️ Swim-Specific Wearable Metrics</h3>
            <p>Deeper integration with Garmin/Apple to pull in advanced metrics like SWOLF per arm, turn times</p>
          </div>
        </div>
        <div className="roadmap-page__feedback-cta">
          <h3>Want any of these? Let us know!</h3>
          <p>
            Email us at{' '}
            <a href="mailto:magshs@gmail.com?subject=AI Swim Coach Feature Request">magshs@gmail.com</a>
            {' '}with which features you'd love to see — or suggest something new. Your feedback directly shapes what we build.
          </p>
        </div>
      </section>
    </div>
  );
}
