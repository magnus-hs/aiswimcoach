import { TrainingPlan } from '../types';

interface TrainingPlanResultProps {
  plan: TrainingPlan;
}

/**
 * Renders a structured training session plan with warm-up, main set, and cool-down.
 */
export function TrainingPlanResult({ plan }: TrainingPlanResultProps) {
  return (
    <section className="training-plan" aria-label="Training plan">
      <h2 className="training-plan__title">{plan.session_title}</h2>

      <div className="training-plan__section">
        <h3 className="training-plan__section-heading">Warm Up</h3>
        <ul className="training-plan__list">
          {plan.warm_up.map((item, i) => (
            <li key={i} className="training-plan__item">
              {item}
            </li>
          ))}
        </ul>
      </div>

      <div className="training-plan__section training-plan__section--main">
        <h3 className="training-plan__section-heading training-plan__section-heading--main">
          Main Set
        </h3>
        <ul className="training-plan__list">
          {plan.main_set.map((item, i) => (
            <li key={i} className="training-plan__item training-plan__item--main">
              {item}
            </li>
          ))}
        </ul>
      </div>

      <div className="training-plan__section">
        <h3 className="training-plan__section-heading">Cool Down</h3>
        <ul className="training-plan__list">
          {plan.cool_down.map((item, i) => (
            <li key={i} className="training-plan__item">
              {item}
            </li>
          ))}
        </ul>
      </div>

      <div className="training-plan__distance">
        <span className="training-plan__distance-badge">
          {plan.total_distance}m total
        </span>
      </div>

      <p className="training-plan__notes">{plan.focus_notes}</p>
    </section>
  );
}
