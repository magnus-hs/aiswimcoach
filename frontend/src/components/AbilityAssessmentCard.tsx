import { AbilityAssessment } from '../types';
import './AbilityAssessmentCard.css';

interface AbilityAssessmentCardProps {
  assessment: AbilityAssessment | null | undefined;
}

/**
 * AbilityAssessmentCard displays AI-generated competitive ability assessment.
 * 
 * Shows:
 *   - Percentile ranking within age group
 *   - Local competition ranking estimate
 *   - National competition ranking estimate
 *   - Competitive analysis considering age and population context
 * 
 * Only renders when assessment data is available (requires complete user profile).
 */
export function AbilityAssessmentCard({ assessment }: AbilityAssessmentCardProps) {
  if (!assessment) {
    return null;
  }

  return (
    <section className="ability-assessment-card" aria-label="Ability assessment">
      <h2 className="ability-assessment-card__heading">Competitive Ability Assessment</h2>
      
      <div className="ability-assessment-card__content">
        <div className="ability-assessment-card__section">
          <h3 className="ability-assessment-card__label">Percentile Ranking</h3>
          <p className="ability-assessment-card__value">{assessment.percentile_estimate}</p>
        </div>

        <div className="ability-assessment-card__section">
          <h3 className="ability-assessment-card__label">Local Ranking</h3>
          <p className="ability-assessment-card__value">{assessment.local_ranking}</p>
        </div>

        <div className="ability-assessment-card__section">
          <h3 className="ability-assessment-card__label">National Ranking</h3>
          <p className="ability-assessment-card__value">{assessment.national_ranking}</p>
        </div>

        <div className="ability-assessment-card__section ability-assessment-card__section--full">
          <h3 className="ability-assessment-card__label">Competitive Analysis</h3>
          <p className="ability-assessment-card__analysis">{assessment.competitive_analysis}</p>
        </div>
      </div>
    </section>
  );
}
