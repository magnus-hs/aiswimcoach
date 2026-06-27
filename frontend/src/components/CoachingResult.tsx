import './CoachingResult.css';

export interface CoachingResultProps {
  /** Exactly three concise, actionable improvement tips. */
  tips: string[];
  /** One specific drill recommendation. */
  drill: string;
}

/**
 * Renders the AI coaching response: three numbered tips and a visually
 * distinct drill section.
 *
 * Validates: Requirements 1.6, 7.3
 */
export function CoachingResult({ tips, drill }: CoachingResultProps) {
  return (
    <section aria-label="Coaching results">
      <h2 className="coaching-result__heading">Your Coaching Tips</h2>
      <ol className="coaching-result__tips">
        {tips.map((tip, index) => (
          <li key={index} className="coaching-result__tip">
            <strong className="coaching-result__tip-label">
              Tip {index + 1}
            </strong>
            <span>{tip}</span>
          </li>
        ))}
      </ol>

      <aside className="coaching-result__drill" aria-label="Drill recommendation">
        <h3 className="coaching-result__drill-heading">Recommended Drill</h3>
        <p className="coaching-result__drill-text">{drill}</p>
      </aside>
    </section>
  );
}
