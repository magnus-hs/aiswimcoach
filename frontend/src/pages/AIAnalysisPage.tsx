import { AICoachChat } from '../components/AICoachChat';
import './AIAnalysisPage.css';

/**
 * Dedicated AI Analysis page — ask your AI coach anything about your training.
 */
export function AIAnalysisPage() {
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
          <div className="ai-analysis-page__capability">
            <span className="ai-analysis-page__capability-icon">📈</span>
            <div>
              <h3>Trend Analysis</h3>
              <p>Identifies patterns in your pace, SWOLF, and stroke rate across sessions. Spots improvements and regressions.</p>
            </div>
          </div>
          <div className="ai-analysis-page__capability">
            <span className="ai-analysis-page__capability-icon">🎯</span>
            <div>
              <h3>Goal Tracking</h3>
              <p>Evaluates progress towards your targets. Tells you if your current trajectory will get you there and what to adjust.</p>
            </div>
          </div>
          <div className="ai-analysis-page__capability">
            <span className="ai-analysis-page__capability-icon">💡</span>
            <div>
              <h3>Personalised Recommendations</h3>
              <p>Suggests specific sets, paces, and focus areas based on what your data reveals about strengths and weaknesses.</p>
            </div>
          </div>
          <div className="ai-analysis-page__capability">
            <span className="ai-analysis-page__capability-icon">⚡</span>
            <div>
              <h3>Training Load Insight</h3>
              <p>Analyses your energy system balance, work-to-rest ratios, and whether you're training the right systems for your goals.</p>
            </div>
          </div>
          <div className="ai-analysis-page__capability">
            <span className="ai-analysis-page__capability-icon">🏅</span>
            <div>
              <h3>Age Group Comparison</h3>
              <p>Compares your times against Masters Swimming standards and age-graded performance tables. Shows where you rank in your age group — club, county, regional, or national level.</p>
            </div>
          </div>
        </div>
      </div>

      <div className="ai-analysis-page__chat-section">
        <AICoachChat />
      </div>

      <div className="ai-analysis-page__examples">
        <h2>Example Questions</h2>
        <ul>
          <li>"How has my pace changed over the last month?"</li>
          <li>"Am I swimming enough threshold work to improve my CSS?"</li>
          <li>"My SWOLF seems to get worse after 1000m — what should I do?"</li>
          <li>"Design me a set to work on my 200m freestyle time"</li>
          <li>"Compare my last 5 sessions — what's improving and what's not?"</li>
          <li>"I want to break 1:20/100m — what does my data say about how close I am?"</li>
          <li>"What's my biggest limiter right now — fitness or technique?"</li>
          <li>"How do I compare to others in my age group?"</li>
          <li>"What level swimmer am I — club, county, or regional?"</li>
          <li>"Where would my times place me in Masters Swimming?"</li>
        </ul>
      </div>
    </div>
  );
}
