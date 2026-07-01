import { useState } from 'react';
import { AICoachChat } from '../components/AICoachChat';
import './AIAnalysisPage.css';

const EXAMPLES = [
  'How has my pace changed over the last month?',
  'Am I swimming enough threshold work to improve my CSS?',
  'My SWOLF seems to get worse after 1000m — what should I do?',
  'Design me a set to work on my 200m freestyle time',
  'Compare my last 5 sessions — what\'s improving and what\'s not?',
  'I want to break 1:20/100m — what does my data say about how close I am?',
  'What\'s my biggest limiter right now — fitness or technique?',
  'How do I compare to others in my age group?',
  'What level swimmer am I — club, county, or regional?',
  'Where would my times place me in Masters Swimming?',
];

/** Coaching focus categories that steer the AI's answers. */
const INTENTS: { key: string; label: string; icon: string }[] = [
  { key: 'technique', label: 'Technique & Efficiency', icon: '🌊' },
  { key: 'endurance', label: 'Endurance & Base', icon: '🫁' },
  { key: 'speed', label: 'Speed & Sprint', icon: '⚡' },
  { key: 'threshold', label: 'Threshold / CSS', icon: '📈' },
  { key: 'race_prep', label: 'Race Prep & Taper', icon: '🏁' },
  { key: 'recovery', label: 'Recovery & Injury Prevention', icon: '🧘' },
  { key: 'fitness', label: 'General Fitness & Weight', icon: '❤️' },
  { key: 'open_water', label: 'Open Water', icon: '🌅' },
];

/**
 * Dedicated AI Analysis page — ask your AI coach anything about your training.
 */
export function AIAnalysisPage() {
  const [selectedPrompt, setSelectedPrompt] = useState('');
  const [intentOpen, setIntentOpen] = useState(false);
  const [selectedIntents, setSelectedIntents] = useState<string[]>([]);

  const toggleIntent = (key: string) => {
    setSelectedIntents((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  };

  return (
    <div className="ai-analysis-page">
      <h1 className="ai-analysis-page__heading">AI Coach Analysis</h1>
      <p className="ai-analysis-page__intro">
        Your AI coach has access to your full training history — every session, every metric.
        Ask questions and get data-driven insights about your swimming.
      </p>

      <div className="ai-analysis-page__what-it-does">
        <h2>What the AI Coach Can Do</h2>
        <div className="ai-analysis-page__capabilities">
          <button className="ai-analysis-page__capability" onClick={() => setSelectedPrompt('How is my pace trending over recent sessions?')}>
            <span className="ai-analysis-page__capability-icon">📈</span>
            <div>
              <h3>Trend Analysis</h3>
              <p>Identifies patterns in your pace, SWOLF, and stroke rate across sessions.</p>
            </div>
          </button>
          <button className="ai-analysis-page__capability" onClick={() => setSelectedPrompt('Am I on track to hit my targets?')}>
            <span className="ai-analysis-page__capability-icon">🎯</span>
            <div>
              <h3>Goal Tracking</h3>
              <p>Evaluates progress towards your targets and what to adjust.</p>
            </div>
          </button>
          <button className="ai-analysis-page__capability" onClick={() => setSelectedPrompt('What should I focus on in my next session?')}>
            <span className="ai-analysis-page__capability-icon">💡</span>
            <div>
              <h3>Personalised Recommendations</h3>
              <p>Suggests specific sets, paces, and focus areas based on your data.</p>
            </div>
          </button>
          <button className="ai-analysis-page__capability" onClick={() => setSelectedPrompt('Am I swimming enough threshold work to improve my CSS?')}>
            <span className="ai-analysis-page__capability-icon">⚡</span>
            <div>
              <h3>Training Load Insight</h3>
              <p>Analyses energy system balance and work-to-rest ratios.</p>
            </div>
          </button>
          <button className="ai-analysis-page__capability" onClick={() => setSelectedPrompt('How do I compare to others in my age group?')}>
            <span className="ai-analysis-page__capability-icon">🏅</span>
            <div>
              <h3>Age Group Comparison</h3>
              <p>Compares against Masters Swimming standards for your age group.</p>
            </div>
          </button>
        </div>
      </div>

      <div className="ai-analysis-page__intent">
        <button
          className="ai-analysis-page__intent-toggle"
          onClick={() => setIntentOpen((o) => !o)}
          aria-expanded={intentOpen}
        >
          <span className={`ai-analysis-page__intent-arrow ${intentOpen ? 'ai-analysis-page__intent-arrow--open' : ''}`}>▶</span>
          Intent
          {selectedIntents.length > 0 && (
            <span className="ai-analysis-page__intent-count">{selectedIntents.length} selected</span>
          )}
        </button>
        {intentOpen && (
          <div className="ai-analysis-page__intent-body">
            <p className="ai-analysis-page__intent-hint">
              Pick one or more focus areas to steer your coach's answers. Leave blank for general advice.
            </p>
            <div className="ai-analysis-page__intent-chips">
              {INTENTS.map((intent) => {
                const active = selectedIntents.includes(intent.key);
                return (
                  <button
                    key={intent.key}
                    className={`ai-analysis-page__intent-chip ${active ? 'ai-analysis-page__intent-chip--active' : ''}`}
                    onClick={() => toggleIntent(intent.key)}
                    aria-pressed={active}
                  >
                    <span className="ai-analysis-page__intent-chip-icon">{intent.icon}</span>
                    {intent.label}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>

      <div className="ai-analysis-page__chat-section">
        <AICoachChat externalPrompt={selectedPrompt} intents={selectedIntents} />
      </div>

      <div className="ai-analysis-page__examples">
        <h2>Try asking...</h2>
        <div className="ai-analysis-page__example-list">
          {EXAMPLES.map((example, i) => (
            <button
              key={i}
              className="ai-analysis-page__example-btn"
              onClick={() => setSelectedPrompt(example)}
            >
              {example}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
